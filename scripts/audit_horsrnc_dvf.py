"""
Audit EXHAUSTIF (LECTURE SEULE, dry-run) des adresses hors-RNC a
ventes DVF, pour tenter de les rattacher au RNC. Parametre SECTEUR.

Cible = predicat hr-actif de renderSecteur (index.html:2205/2215) :
  cle non fusionnee (_fusion_auto) ET cle pas une cle_adresse de copro
  ET pas de numero_immatriculation ET nb_ventes_logement>0.
(= "Hors-RNC actifs" du dashboard, post tous correctifs.)

Pipeline par cible, dans l'ordre (on s'arrete au 1er hit) :
  a) BDNB rel_batiment_groupe_rnc (cache _horsrnc_bdnb_live*) -> immat
     -> presente dans coproprietes[] ?
  b) normalisation orthographique (AIRES<->AYRES, GAL<->GENERAL,
     ST<->SAINT, abrev, particules) -> match (num,voie) contre
     cle_adresse / adresse / nom_copropriete des copros du registre.
  c) proximite GPS < 30 m d'une copro VISIBLE (cle_adresse rendue)
     ET meme voie normalisee (anti-voisin).
  d) RNC open data live (tabular-api RNIC quotidien) sur la rue, si
     a/b/c ont echoue (batch par token de voie + code postal, cache).

Classement A (rattachable : mecanisme/immat/syndic/lots/ventes) ou B
(aucune copro -> monopropriete / non immatriculee). Impact parc
estime via replique de la regle renderSecteur S6. Aucune ecriture
des fichiers de donnees ; sortie = data/audit_horsrnc_dvf_<court>.md
"""

import os
import re
import csv
import json
import time
import math
import collections
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTEUR = os.environ.get("SECTEUR", "dauphine_lacassagne")
SUF = "" if SECTEUR == "dauphine_lacassagne" else "_" + SECTEUR
SHORT = "dauphine" if SECTEUR == "dauphine_lacassagne" else "motte"
LIGHT = ROOT / "data" / f"secteur_{SECTEUR}_light.json"
BDNB = ROOT / "data" / f"bdnb_{SECTEUR}.json"
CACHE_A = ROOT / "data" / f"_horsrnc_bdnb_live{SUF}.json"
CACHE_D = ROOT / "data" / f"_audit_rnc_live{SUF}.json"
REPORT = ROOT / "data" / f"audit_horsrnc_dvf_{SHORT}.md"
CPS = ["69003"] if SECTEUR == "dauphine_lacassagne" else ["75015", "75007"]
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"
NR = {"non connu", "", None}

# substitutions orthographiques (token entier)
SUBS = {
    "AYRES": "AIRES", "GAL": "GENERAL", "GEN": "GENERAL", "GENL": "GENERAL",
    "ST": "SAINT", "STE": "SAINTE", "DR": "DOCTEUR", "PR": "PROFESSEUR",
    "MAL": "MARECHAL", "MNE": "MADELEINE", "PCE": "PRINCE",
    "FG": "FAUBOURG", "GRDE": "GRANDE",
}
PARTICLES = {"DE", "DU", "DES", "LA", "LE", "L", "D", "AUX", "A", "ET"}
TYPE_KEEP = False  # la voie seule (sans type) suffit pour matcher


def norm_tokens(s):
    s = str(s or "").upper()
    s = s.replace("'", " ").replace("-", " ").replace(".", " ")
    s = (s.replace("É", "E").replace("È", "E").replace("Ê", "E")
         .replace("À", "A").replace("Â", "A").replace("Ô", "O")
         .replace("Î", "I").replace("Ï", "I").replace("Ç", "C")
         .replace("Û", "U").replace("Ù", "U"))
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    out = []
    for t in s.split():
        if t in PARTICLES:
            continue
        out.append(SUBS.get(t, t))
    return out


def voie_key(cle):
    """cle 'NUM|TYPE|VOIE' -> (num_norm, voie_norm) ; num garde
    suffixe bis/ter (B/T) ; voie = tokens normalises sans type."""
    p = str(cle or "").split("|")
    num = (p[0] or "").upper().strip() if p else ""
    voie = " ".join(norm_tokens(p[2] if len(p) > 2 else ""))
    return num, voie


def num_voie_in_text(txt):
    """extrait toutes paires (num, voie_norm) d'un texte libre
    (nom_copropriete / adresse). Heuristique : nombre suivi de mots."""
    res = []
    for m in re.finditer(r"(\d{1,4})\s*(BIS|TER|B|T)?\s+([A-Za-zÀ-ÿ' \-]{3,40})",
                          str(txt or "")):
        num = m.group(1) + ({"BIS": "B", "TER": "T", "B": "B", "T": "T"}
                            .get((m.group(2) or "").upper(), ""))
        voie = " ".join(norm_tokens(m.group(3)))
        # couper la voie aux mots parasites
        voie = re.sub(r"\b(PARIS|LYON|CEDEX)\b.*$", "", voie).strip()
        if voie:
            res.append((num.upper(), voie))
    return res


def hav(la1, lo1, la2, lo2):
    if None in (la1, lo1, la2, lo2):
        return 9e9
    R = 6371000.0
    p1, p2 = math.radians(la1), math.radians(la2)
    dp = math.radians(la2 - la1)
    dl = math.radians(lo2 - lo1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def get_json(url, retries=5):
    for i in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "dpe-audit/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            if i == retries - 1:
                return {}
            time.sleep(2.0 * (i + 1))
    return {}


def rnc_live_street(token, cp, cache):
    key = f"{token}|{cp}"
    if key in cache:
        return cache[key]
    rows, page = [], 1
    while True:
        q = urllib.parse.urlencode({
            "adresse_reference__contains": token,
            "code_postal_adresse__exact": cp, "page": page,
            "page_size": 50})
        d = get_json(f"{TAB}?{q}")
        data = d.get("data") or []
        rows += data
        if not data or not (d.get("links") or {}).get("next"):
            break
        page += 1
        time.sleep(0.2)
    slim = [{k: r.get(k) for k in (
        "numero_immatriculation", "nom_usage_copropriete",
        "adresse_reference", "numero_voie_adresse", "code_postal_adresse",
        "adresse_complementaire_1", "adresse_complementaire_2",
        "adresse_complementaire_3", "nombre_lots_habitation",
        "nombre_total_lots", "raison_sociale_representant_legal",
        "identification_representant_legal")} for r in rows]
    cache[key] = slim
    return slim


def parc_model(adrs, copros):
    """replique renderSecteur S6 (dedup bgid, lots RNC prioritaires)."""
    co = {c["cle_adresse"]: c for c in copros if c.get("cle_adresse")}
    RESID = {"Résidentiel collectif", "Résidentiel individuel"}
    fused = {a["cle"] for a in adrs
             if a.get("_fusion_auto") and a.get("_fusion_cible")}
    bgRnc, bgBd, immatBg = {}, {}, {}
    for a in adrs:
        if a["cle"] in fused:
            continue
        bg = a.get("batiment_groupe_id")
        cp = co.get(a["cle"])
        if bg and cp and (cp.get("nb_lots_habitation") or 0) > 0:
            im = cp.get("numero_immatriculation") or cp["cle_adresse"]
            immatBg.setdefault(im, bg)
            bgRnc.setdefault(immatBg[im], {})[im] = cp["nb_lots_habitation"]
        if (bg and not cp and a.get("usage_principal_bdnb") in RESID
                and (a.get("nb_log_bdnb") or 0) > 0 and bg not in bgBd):
            bgBd[bg] = a["nb_log_bdnb"]
    tot = 0
    for bg in set(bgRnc) | set(bgBd):
        tot += (sum(bgRnc[bg].values()) if bg in bgRnc else bgBd.get(bg, 0))
    return tot


def main():
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad, co = light["adresses"], light["coproprietes"]
    bdnb = json.loads(BDNB.read_text(encoding="utf-8"))
    snap_pri = {r["batiment_groupe_id"]: r.get("numero_immat_principal")
                for r in bdnb}
    cache_a = json.loads(CACHE_A.read_text(encoding="utf-8")) \
        if CACHE_A.exists() else {}
    cache_d = json.loads(CACHE_D.read_text(encoding="utf-8")) \
        if CACHE_D.exists() else {}

    by_cle = {}
    for a in ad:
        by_cle.setdefault(a["cle"], a)
    copro_by_immat = {c["numero_immatriculation"]: c for c in co
                      if c.get("numero_immatriculation")}
    copro_by_cle = {c["cle_adresse"]: c for c in co if c.get("cle_adresse")}
    addr_cles = {a["cle"] for a in ad}
    fused = {a["cle"] for a in ad
             if a.get("_fusion_auto") and a.get("_fusion_cible")}

    # cible = hr-actif canonique
    targets = [a for a in ad
               if a["cle"] not in fused
               and a["cle"] not in copro_by_cle
               and not a.get("numero_immatriculation")
               and (a.get("nb_ventes_logement") or 0) > 0]

    # index normalises du registre
    cle_norm = {}                       # (num,voie) -> [copro...]
    for c in co:
        ca = c.get("cle_adresse")
        if not ca:
            continue
        cle_norm.setdefault(voie_key(ca), []).append(c)
    text_norm = collections.defaultdict(list)   # (num,voie) -> [copro]
    for c in co:
        for nv in (num_voie_in_text(c.get("nom_copropriete"))
                   + num_voie_in_text(c.get("adresse"))):
            text_norm[nv].append(c)

    # copros VISIBLES (cle_adresse rendue, non fusionnee) pour proximite
    vis_copros = []
    for c in co:
        ca = c.get("cle_adresse")
        if ca in addr_cles and ca not in fused and c.get("latitude"):
            vis_copros.append(c)

    results = []
    todo_d = []                          # cibles -> etape d
    for a in targets:
        cle = a["cle"]
        bg = a.get("batiment_groupe_id")
        tnum, tvoie = voie_key(cle)
        rec = {"cle": cle, "adresse": a.get("adresse"),
               "bg": bg, "vlog": a.get("nb_ventes_logement") or 0,
               "vtot": a.get("nb_ventes_total") or 0,
               "nb_log_bdnb": a.get("nb_log_bdnb"),
               "usage": a.get("usage_principal_bdnb"),
               "lat": a.get("latitude"), "lon": a.get("longitude"),
               "via": None, "cls": None, "immat": None, "anchor": None,
               "copro_nom": None, "syndic": None, "lots": None,
               "mecanisme": None, "conf": None}

        # ---- a) BDNB rel ----
        immats = set((cache_a.get(bg, {}) or {}).get("immats") or [])
        sp = snap_pri.get(bg)
        if sp not in NR:
            immats.add(sp)
        hit_immats = [im for im in sorted(immats) if im in copro_by_immat]
        if hit_immats:
            im = hit_immats[0]
            c = copro_by_immat[im]
            anc = c.get("cle_adresse")
            rec.update(via="a_bdnb", cls="A", immat=im, anchor=anc,
                       copro_nom=c.get("nom_copropriete"),
                       syndic=c.get("syndic"),
                       lots=c.get("nb_lots_habitation"), conf="haute")
            results.append(rec)
            continue

        # ---- b) normalisation orthographique ----
        cand = list(cle_norm.get((tnum, tvoie), []))
        srcb = "cle_adresse"
        if not cand:
            cand = list(text_norm.get((tnum, tvoie), []))
            srcb = "nom/adresse"
        cand = [c for c in cand if c.get("numero_immatriculation")]
        if len(cand) >= 1:
            # privilegier une copro unique ; si plusieurs, prendre la
            # plus proche en GPS (desambiguisation)
            if len(cand) > 1 and a.get("latitude"):
                cand.sort(key=lambda c: hav(a["latitude"], a["longitude"],
                                            c.get("latitude"),
                                            c.get("longitude")))
            c = cand[0]
            rec.update(via=f"b_norm({srcb})", cls="A",
                       immat=c["numero_immatriculation"],
                       anchor=c.get("cle_adresse"),
                       copro_nom=c.get("nom_copropriete"),
                       syndic=c.get("syndic"),
                       lots=c.get("nb_lots_habitation"),
                       conf="haute" if srcb == "cle_adresse" else "moyenne")
            results.append(rec)
            continue

        # ---- c) proximite GPS < 30 m + meme voie ----
        if a.get("latitude"):
            best, bd = None, 31.0
            for c in vis_copros:
                _, cvoie = voie_key(c["cle_adresse"])
                if cvoie != tvoie:
                    continue
                dd = hav(a["latitude"], a["longitude"],
                         c["latitude"], c["longitude"])
                if dd < bd:
                    bd, best = dd, c
            if best:
                rec.update(via=f"c_gps({bd:.0f}m)", cls="A",
                           immat=best.get("numero_immatriculation"),
                           anchor=best.get("cle_adresse"),
                           copro_nom=best.get("nom_copropriete"),
                           syndic=best.get("syndic"),
                           lots=best.get("nb_lots_habitation"),
                           conf="moyenne")
                results.append(rec)
                continue

        todo_d.append((a, rec, tnum, tvoie))

    # ---- d) RNC live (batch par token de voie) ----
    tokens = {}
    for a, rec, tnum, tvoie in todo_d:
        p = str(a["cle"]).split("|")
        raw = norm_tokens(p[2] if len(p) > 2 else "")
        tok = max(raw, key=len) if raw else ""
        if len(tok) >= 4:
            tokens.setdefault(tok, []).append((a, rec, tnum, tvoie))
    n_live = 0
    for tok, items in tokens.items():
        rows = []
        for cp in CPS:
            rows += rnc_live_street(tok, cp, cache_d)
            n_live += 1
        # index live (num,voie) depuis reference + complementaires
        live_idx = collections.defaultdict(list)
        for r in rows:
            keys = num_voie_in_text(r.get("adresse_reference"))
            for f in ("adresse_complementaire_1", "adresse_complementaire_2",
                      "adresse_complementaire_3"):
                keys += num_voie_in_text(r.get(f))
            nv = str(r.get("numero_voie_adresse") or "")
            if nv:
                keys += num_voie_in_text(nv)
            for k in set(keys):
                live_idx[k].append(r)
        for a, rec, tnum, tvoie in items:
            m = live_idx.get((tnum, tvoie))
            if m:
                r = m[0]
                im = r.get("numero_immatriculation")
                in_reg = im in copro_by_immat
                rec.update(
                    via="d_rnc_live", cls="A",
                    immat=im, anchor=None,
                    copro_nom=r.get("nom_usage_copropriete"),
                    syndic=(r.get("raison_sociale_representant_legal")
                            or r.get("identification_representant_legal")),
                    lots=r.get("nombre_lots_habitation"),
                    conf="moyenne",
                    mecanisme=("registre+ (immat HORS "
                               f"{'553' if SHORT=='dauphine' else '821'})"
                               if not in_reg else "ALIAS_RNC"))
            else:
                rec.update(via="d_rnc_live", cls="B")
            results.append(rec)
    if cache_d:
        CACHE_D.write_text(json.dumps(cache_d, ensure_ascii=False, indent=1),
                           encoding="utf-8")

    # cibles restees sans etape d (pas de token) -> B
    seen = {id(r) for r in results}
    for a, rec, tnum, tvoie in todo_d:
        if id(rec) not in seen and rec["cls"] is None:
            rec["cls"] = "B"
            rec["via"] = "aucun"
            results.append(rec)

    # ---- mecanisme + impact parc (modele) ----
    A = [r for r in results if r["cls"] == "A"]
    B = [r for r in results if r["cls"] == "B"]
    for r in A:
        if r["mecanisme"]:
            continue
        anc = r["anchor"]
        aobj = by_cle.get(anc) if anc else None
        if anc and aobj is None:
            r["mecanisme"] = "ancre absente light (re-verif)"
        elif anc and aobj is not None:
            same = aobj.get("batiment_groupe_id") == r["bg"]
            if aobj.get("_fusion_auto") and aobj.get("_fusion_cible") == r["cle"]:
                r["mecanisme"] = "RE-POINT (ancre fusionnee dans la cible)"
            elif same:
                r["mecanisme"] = "ALIAS_RNC meme bgid (parc-neutre)"
            else:
                r["mecanisme"] = "ALIAS_RNC miroir bgid"
        else:
            r["mecanisme"] = "ALIAS_RNC"

    # ---- force de preuve : strong vs weak (parc-safety) ----
    # strong = identite forte & parc-sure (meme classe que les 7
    # deja appliquees) : immat BDNB-rel, OU variante orthographique
    # exacte sur cle_adresse, OU GPS tres proche AVEC meme bgid que
    # la copro (= meme batiment -> parc-neutre).
    for r in A:
        anc = r["anchor"]
        aobj = by_cle.get(anc) if anc else None
        same_bg = bool(aobj) and aobj.get("batiment_groupe_id") == r["bg"]
        v = r["via"]
        if v == "a_bdnb" or v == "b_norm(cle_adresse)" or same_bg:
            r["force"] = "strong"
        else:
            r["force"] = "weak"

    def model(rows):
        patched = json.loads(LIGHT.read_text(encoding="utf-8"))
        pby = {x["cle"]: x for x in patched["adresses"]}
        n = 0
        for r in rows:
            anc = r["anchor"]
            if not anc or anc not in pby or r["cle"] not in pby:
                continue
            s, dd = pby[r["cle"]], pby[anc]
            if dd.get("_fusion_auto") and dd.get("_fusion_cible") == r["cle"]:
                dd["_fusion_auto"] = None
                dd["_fusion_cible"] = None
                s["_fusion_auto"] = True
                s["_fusion_cible"] = anc
            else:
                if s.get("batiment_groupe_id") != dd.get("batiment_groupe_id"):
                    s["batiment_groupe_id"] = dd.get("batiment_groupe_id")
                    s["nb_log_bdnb"] = dd.get("nb_log_bdnb")
                    s["usage_principal_bdnb"] = dd.get("usage_principal_bdnb")
                s["_fusion_auto"] = True
                s["_fusion_cible"] = anc
            n += 1
        return parc_model(patched["adresses"], patched["coproprietes"]), n

    A_strong = [r for r in A if r["force"] == "strong"]
    A_weak = [r for r in A if r["force"] == "weak"]
    parc0 = parc_model(light["adresses"], co)
    parc_s, applied_s = model(A_strong)
    parc1, applied = model(A)

    # ---- bilan ----
    by_via = collections.Counter(r["via"] for r in A)
    by_mec = collections.Counter(r["mecanisme"] for r in A)
    topA = sorted(A_strong, key=lambda r: -r["vlog"])[:10]
    vlogA = sum(r["vlog"] for r in A)
    vlog_s = sum(r["vlog"] for r in A_strong)
    vlog_w = sum(r["vlog"] for r in A_weak)

    L = [f"# Audit hors-RNC + ventes DVF — secteur {SECTEUR}\n",
         "Lecture seule. Cible = prédicat *Hors-RNC actifs* de "
         "renderSecteur (non fusionnée, clé ≠ cle_adresse copro, sans "
         "immat, `nb_ventes_logement>0`).\n",
         "> **Lecture critique.** Une cible n'est **sûrement** "
         "rattachable que si l'identité est *forte* : immat via "
         "BDNB `rel_batiment_groupe_rnc`, **ou** variante "
         "orthographique exacte de `cle_adresse`, **ou** même "
         "`batiment_groupe_id` que la copro (même bâtiment → "
         "parc-neutre, classe des 7 déjà appliquées). Les autres "
         "(proximité GPS seule, match sur nom/adresse libre, RNC "
         "live) sont des **pistes à confirmer manuellement** : les "
         "appliquer en masse **détruit du parc** (ce sont des "
         "bâtiments DISTINCTS proches d'une copro, dont on retirerait "
         "le stock BDNB réel sans que la copro le gagne).\n",
         "## Bilan\n", "| Indicateur | Valeur |", "|---|--:|",
         f"| Cibles hors-RNC + ventes | **{len(targets)}** |",
         f"| → **A-fort** (rattachable sûr, parc-sûr) | "
         f"**{len(A_strong)}** |",
         f"| → A-faible (piste, confirmation manuelle) | "
         f"{len(A_weak)} |",
         f"| → B (monopropriété / non immatriculée) | **{len(B)}** |",
         f"| Ventes-log à relocaliser — A-fort | **{vlog_s}** |",
         f"| Ventes-log — A-faible (non sûr) | {vlog_w} |",
         f"| **Parc A-fort seul** : {parc0} → {parc_s} | "
         f"**{parc_s - parc0:+d}** ({applied_s} modélisés) |",
         f"| Parc A-fort+faible (illustre la destruction) : "
         f"{parc0} → {parc1} | {parc1 - parc0:+d} |",
         "\n### Répartition A par voie de résolution (force)\n",
         "| Étape | n | force |", "|---|--:|---|"]
    fby = collections.Counter((r["via"].split("(")[0], r["force"])
                              for r in A)
    for (k, f), v in sorted(fby.items(), key=lambda x: -x[1]):
        L.append(f"| {k} | {v} | {f} |")
    L += ["\n### Répartition A par mécanisme\n", "| Mécanisme | n |",
          "|---|--:|"]
    for k, v in by_mec.most_common():
        L.append(f"| {k} | {v} |")
    L += ["\n## Top 10 A-FORT par ventes-logement à relocaliser\n",
          "| Adresse (cle) | v_log | v_tot | via | immat | copro | "
          "syndic | lots | mécanisme |", "|---|--:|--:|---|---|---|---|--:|---|"]
    for r in topA:
        L.append(
            f"| `{r['cle']}` | {r['vlog']} | {r['vtot']} | {r['via']} | "
            f"{r['immat']} | {(r['copro_nom'] or '')[:26]} | "
            f"{(r['syndic'] or '')[:20]} | {r['lots']} | {r['mecanisme']} |")
    L += ["\n## A-FORT — rattachables sûrs (toutes)\n",
          "| cle | v_log | via | immat | anchor | copro | lots | "
          "mécanisme |", "|---|--:|---|---|---|---|--:|---|"]
    for r in sorted(A_strong, key=lambda x: (-x["vlog"], x["cle"])):
        L.append(
            f"| `{r['cle']}` | {r['vlog']} | {r['via']} | "
            f"{r['immat']} | `{r['anchor'] or ''}` | "
            f"{(r['copro_nom'] or '')[:24]} | {r['lots']} | "
            f"{r['mecanisme']} |")
    L += ["\n## A-FAIBLE — pistes (confirmation manuelle, NON "
          "applicables en masse)\n",
          "| cle | v_log | via | immat | anchor | copro | lots |",
          "|---|--:|---|---|---|---|--:|"]
    for r in sorted(A_weak, key=lambda x: (-x["vlog"], x["cle"])):
        L.append(
            f"| `{r['cle']}` | {r['vlog']} | {r['via']} | "
            f"{r['immat']} | `{r['anchor'] or ''}` | "
            f"{(r['copro_nom'] or '')[:24]} | {r['lots']} |")
    L += ["\n## Cibles B (structurellement hors-RNC)\n",
          "| cle | v_log | v_tot | nb_log_bdnb | usage | dernier essai |",
          "|---|--:|--:|--:|---|---|"]
    for r in sorted(B, key=lambda x: (-x["vlog"], x["cle"])):
        L.append(
            f"| `{r['cle']}` | {r['vlog']} | {r['vtot']} | "
            f"{r['nb_log_bdnb']} | {r['usage']} | {r['via']} |")
    REPORT.write_text("\n".join(L), encoding="utf-8")

    print(f"=== {SECTEUR} ===")
    print(f"cibles={len(targets)}  A_fort={len(A_strong)}  "
          f"A_faible={len(A_weak)}  B={len(B)}")
    print(f"  vlog A-fort={vlog_s} (parc {parc0}->{parc_s} "
          f"{parc_s-parc0:+d}, {applied_s} modelises)")
    print(f"  vlog A-faible={vlog_w} (parc A+faible {parc1} "
          f"{parc1-parc0:+d} = ILLUSTRE LA DESTRUCTION, NE PAS APPLIQUER)")
    print("via:", dict(by_via))
    print(f"appels RNC live: {n_live}  rapport: {REPORT.name}")


if __name__ == "__main__":
    main()
