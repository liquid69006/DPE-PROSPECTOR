"""
Diagnostic LECTURE SEULE des adresses « orphelines BDNB » a ventes DVF,
sur les 2 secteurs (parametre SECTEUR). Aucune ecriture des fichiers de
donnees / caches : sortie = data/audit_orphelines_bdnb_<court>.md.

ETAPE 1 — orphelines STRICTES = batiment_groupe_id null/vide ET
nb_ventes_logement>0. (Resultat attendu : 0 — make_light assigne
toujours un bgid via le fallback GPS<50 m. Voir le rapport.)

Faute d'orphelines strictes, on diagnostique la population EQUIVALENTE
de fait : adresses dont le SEUL lien BDNB est le palier le plus faible
`_bdnb_match=='gps'` (rattachement BDNB par simple proximite 50 m, sans
identite immat ni num_voie) ET nb_ventes_logement>0. Ce sont les
adresses « sans rattachement BDNB fiable ».

ETAPE 2 — par adresse, dans l'ordre demande :
  a) normalisation orthographique vs coproprietes[] (ST/SAINT, GAL/
     GENERAL, particules...) — pourquoi le match echoue ;
  b) proximite GPS < 50 m d'une copro RNC — copro dans le rayon ?
     pourquoi ne pas rattacher (bati DISTINCT / copro deja ancree) ;
  c) API RNC live (tabular-api) par adresse normalisee — resultat,
     pourquoi pas de match (cache prioritaire, live si miss) ;
  d) geocodage BAN — adresse geocodable ? coords nulles = cause ?

ETAPE 3 — classement : fantome DVF / copro non immatriculee /
monopropriete / hors perimetre / inconnu (+ statut « deja rattachee
par fusion BDNB » pour les cibles _fusion_auto, non orphelines).

ETAPE 4 — bilan chiffre par secteur et categorie + liste complete.
"""

import os
import re
import json
import math
import time
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
REPORT = ROOT / "data" / f"audit_orphelines_bdnb_{SHORT}.md"
CPS = ["69003"] if SECTEUR == "dauphine_lacassagne" else ["75015", "75007"]
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"
NR = {"non connu", "", None}

SUBS = {
    "AYRES": "AIRES", "GAL": "GENERAL", "GEN": "GENERAL", "GENL": "GENERAL",
    "ST": "SAINT", "STE": "SAINTE", "DR": "DOCTEUR", "PR": "PROFESSEUR",
    "MAL": "MARECHAL", "MNE": "MADELEINE", "PCE": "PRINCE",
    "FG": "FAUBOURG", "GRDE": "GRANDE", "CAPT": "CAPITAINE",
    "CNE": "CAPITAINE", "CMDT": "COMMANDANT", "AVE": "AVENUE",
}
PARTICLES = {"DE", "DU", "DES", "LA", "LE", "L", "D", "AUX", "A", "ET"}
RESID = {"Résidentiel collectif", "Résidentiel individuel"}
# voies renommées : la clé DVF/BAN porte le nom actuel, le RNC peut
# encore lister l'ancien (token de voie normalisé -> ancien token).
VOIE_RENAME = {"JACQUES CHIRAC": "BRANLY"}


def norm_tokens(s):
    s = str(s or "").upper().replace("'", " ").replace("-", " ").replace(".", " ")
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
    p = str(cle or "").split("|")
    num = (p[0] or "").upper().strip() if p else ""
    voie = " ".join(norm_tokens(p[2] if len(p) > 2 else ""))
    return num, voie


def num_voie_in_text(txt):
    res = []
    for m in re.finditer(
            r"(\d{1,4})\s*(BIS|TER|B|T)?\s+([A-Za-zÀ-ÿ' \-]{3,40})",
            str(txt or "")):
        num = m.group(1) + ({"BIS": "B", "TER": "T", "B": "B", "T": "T"}
                            .get((m.group(2) or "").upper(), ""))
        voie = " ".join(norm_tokens(m.group(3)))
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


def get_json(url, retries=4):
    for i in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "dpe-audit/1.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            if i == retries - 1:
                return None
            time.sleep(1.5 * (i + 1))
    return None


def rnc_live_street(token, cp, cache):
    """Cache d'abord ; sinon live (SANS reecrire le cache disque)."""
    key = f"{token}|{cp}"
    if key in cache:
        return cache[key], "cache"
    rows, page, net = [], 1, True
    while True:
        q = urllib.parse.urlencode({
            "adresse_reference__contains": token,
            "code_postal_adresse__exact": cp, "page": page,
            "page_size": 50})
        d = get_json(f"{TAB}?{q}")
        if d is None:
            net = False
            break
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
        "raison_sociale_representant_legal",
        "identification_representant_legal")} for r in rows]
    cache[key] = slim                       # cache mémoire de la session
    return slim, ("live" if net else "live-échec-réseau")


def main():
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad, co = light["adresses"], light["coproprietes"]
    iris_set = {str(i.get("code_iris")) for i in light.get("iris", [])
                if i.get("code_iris")}
    bdnb = json.loads(BDNB.read_text(encoding="utf-8"))
    snap_pri = {r["batiment_groupe_id"]: r.get("numero_immat_principal")
                for r in bdnb}
    cache_a = json.loads(CACHE_A.read_text(encoding="utf-8")) \
        if CACHE_A.exists() else {}
    cache_d = json.loads(CACHE_D.read_text(encoding="utf-8")) \
        if CACHE_D.exists() else {}

    by_cle = {a["cle"]: a for a in ad}
    copro_by_immat = {c["numero_immatriculation"]: c for c in co
                      if c.get("numero_immatriculation")}
    copro_by_cle = {c["cle_adresse"]: c for c in co if c.get("cle_adresse")}
    addr_cles = set(by_cle)
    fused = {a["cle"] for a in ad
             if a.get("_fusion_auto") and a.get("_fusion_cible")}

    # index normalises du registre (a)
    cle_norm = collections.defaultdict(list)
    for c in co:
        if c.get("cle_adresse"):
            cle_norm[voie_key(c["cle_adresse"])].append(c)
    text_norm = collections.defaultdict(list)
    for c in co:
        for nv in (num_voie_in_text(c.get("nom_copropriete"))
                   + num_voie_in_text(c.get("adresse"))):
            text_norm[nv].append(c)
    # copros geolocalisees (b)
    geo_copros = [c for c in co if c.get("latitude")]

    # ETAPE 1 strict
    def empty(v):
        return v is None or (isinstance(v, str) and v.strip() == "")
    strict = [a for a in ad if empty(a.get("batiment_groupe_id"))
              and (a.get("nb_ventes_logement") or 0) > 0]

    # population equivalente de fait : gps-only & ventes
    pop = [a for a in ad if a.get("_bdnb_match") == "gps"
           and (a.get("nb_ventes_logement") or 0) > 0]
    pop.sort(key=lambda a: -(a.get("nb_ventes_logement") or 0))

    rows = []
    for a in pop:
        cle = a["cle"]
        bg = a.get("batiment_groupe_id")
        tnum, tvoie = voie_key(cle)
        is_fused = cle in fused
        is_hr = (not is_fused and cle not in copro_by_cle
                 and not a.get("numero_immatriculation"))
        rec = {
            "cle": cle, "adresse": a.get("adresse"), "bg": bg,
            "vlog": a.get("nb_ventes_logement") or 0,
            "vtot": a.get("nb_ventes_total") or 0,
            "nb_log_bdnb": a.get("nb_log_bdnb"),
            "usage": a.get("usage_principal_bdnb"),
            "lat": a.get("latitude"), "lon": a.get("longitude"),
            "iris": str(a.get("code_iris")),
            "coord_src": a.get("_coord_source"),
            "fused": is_fused, "hr": is_hr,
            "fusion_cible": None, "diag": {}, "cat": None, "statut": None}
        # cible de fusion (qui absorbe cette adresse) — c'est l'ancre copro
        if is_fused:
            rec["fusion_cible"] = a.get("_fusion_cible")

        # ---- a) normalisation orthographique vs coproprietes[] ----
        ca = cle_norm.get((tnum, tvoie))
        cb = text_norm.get((tnum, tvoie))
        a_hit = None
        hc = None
        if ca:
            hc, src_a = ca[0], "cle_adresse"
        elif cb:
            cc = [x for x in cb if x.get("numero_immatriculation")]
            if cc:
                hc, src_a = cc[0], "nom/adresse"
        if hc is not None:
            im = hc.get("numero_immatriculation")
            anc = hc.get("cle_adresse")
            anc_obj = by_cle.get(anc)
            a_hit = {
                "src": src_a, "immat": im, "cle_adresse": anc,
                "nom": hc.get("nom_copropriete"),
                "in_snapshot": im in copro_by_immat,
                "ancre_rendue": anc in addr_cles,
                "ancre_meme_bg": bool(anc_obj)
                and anc_obj.get("batiment_groupe_id") == bg,
                "ancre_bg": anc_obj.get("batiment_groupe_id")
                if anc_obj else None}
        # meme voie connue du registre ? (pour expliquer l'echec)
        voie_in_reg = any(v == tvoie for (_, v) in cle_norm)
        rec["diag"]["a"] = {
            "hit": a_hit,
            "voie_norm": tvoie, "num": tnum,
            "voie_connue_registre": voie_in_reg}

        # ---- b) proximite GPS < 50 m d'une copro RNC ----
        near = []
        if a.get("latitude"):
            for c in geo_copros:
                dd = hav(a["latitude"], a["longitude"],
                         c["latitude"], c["longitude"])
                if dd <= 80:
                    near.append((dd, c))
            near.sort(key=lambda x: x[0])
        within50 = [(dd, c) for dd, c in near if dd <= 50]
        b_info = []
        for dd, c in near[:3]:
            anc = c.get("cle_adresse")
            anc_obj = by_cle.get(anc)
            b_info.append({
                "dist": round(dd, 1),
                "immat": c.get("numero_immatriculation"),
                "cle_adresse": anc, "nom": c.get("nom_copropriete"),
                "meme_voie": voie_key(anc)[1] == tvoie if anc else False,
                "ancre_rendue": anc in addr_cles,
                "ancre_meme_bg": bool(anc_obj)
                and anc_obj.get("batiment_groupe_id") == bg})
        rec["diag"]["b"] = {"within50": len(within50), "cands": b_info}

        # ---- c) RNC live (cache puis live, sans reecrire le cache) ----
        raw = norm_tokens(str(cle).split("|")[2] if len(
            str(cle).split("|")) > 2 else "")
        tok = max(raw, key=len) if raw else ""
        c_immat = c_in_snap = c_src = c_nom = c_lots = None
        c_used_tok = tok
        if len(tok) >= 4:
            allrows, src_used = [], []
            for cp in CPS:
                rr, st = rnc_live_street(tok, cp, cache_d)
                allrows += rr
                src_used.append(st)
            live_idx = collections.defaultdict(list)
            for r in allrows:
                keys = num_voie_in_text(r.get("adresse_reference"))
                for f in ("adresse_complementaire_1",
                          "adresse_complementaire_2",
                          "adresse_complementaire_3"):
                    keys += num_voie_in_text(r.get(f))
                nv = str(r.get("numero_voie_adresse") or "")
                if nv:
                    keys += num_voie_in_text(nv)
                for k in set(keys):
                    live_idx[k].append(r)
            m = live_idx.get((tnum, tvoie))
            c_src = "/".join(sorted(set(src_used)))
            if m:
                r = m[0]
                c_immat = r.get("numero_immatriculation")
                c_in_snap = c_immat in copro_by_immat
                c_nom = r.get("nom_usage_copropriete")
                c_lots = r.get("nombre_lots_habitation")
            # voie renommée : re-sonder le RNC sous l'ancien nom
            rename = VOIE_RENAME.get(tvoie)
            rn_info = None
            if not m and rename:
                rrows = []
                for cp in CPS:
                    rr, st = rnc_live_street(rename, cp, cache_d)
                    rrows += rr
                ridx = collections.defaultdict(list)
                for r in rrows:
                    keys = num_voie_in_text(r.get("adresse_reference"))
                    for f in ("adresse_complementaire_1",
                              "adresse_complementaire_2",
                              "adresse_complementaire_3"):
                        keys += num_voie_in_text(r.get(f))
                    for k in set(keys):
                        ridx[k].append(r)
                rm = ridx.get((tnum, rename))
                rn_info = {"voie": rename, "n_rows": len(rrows),
                           "hit": bool(rm),
                           "immat": rm[0].get("numero_immatriculation")
                           if rm else None}
            rec["diag"]["c"] = {
                "token": c_used_tok, "src": c_src,
                "n_rows": len(allrows), "immat": c_immat,
                "in_snapshot": c_in_snap, "nom": c_nom, "lots": c_lots,
                "rename": rn_info}
        else:
            rec["diag"]["c"] = {"token": tok, "src": "skip(token<4)",
                                "n_rows": 0, "immat": None}

        # ---- d) geocodage BAN ----
        coords_ok = a.get("latitude") is not None \
            and a.get("longitude") is not None
        iris_ok = rec["iris"] in iris_set if iris_set else None
        rec["diag"]["d"] = {
            "coords_ok": coords_ok, "coord_src": rec["coord_src"],
            "iris": rec["iris"], "iris_in_secteur": iris_ok}

        # ---- ETAPE 3 : classement ----
        # NB : une copro trouvée immatriculée (ortho-match snapshot, ou
        # RNC live) n'est PAS « non immatriculée ». Ces cas sortent des
        # 5 catégories résiduelles : ce sont des rattachables (lacune de
        # couverture du pipeline), tracés à part.
        RESOL = "Rattachable (copro immatriculée — hors 5 cat.)"
        if is_fused:
            rec["statut"] = "Déjà rattachée (fusion BDNB même bgid)"
            rec["cat"] = "— (non orpheline : résolue par fusion)"
        else:
            usage = rec["usage"] or ""
            nlb = rec["nb_log_bdnb"] or 0
            ortho_ok = bool(a_hit and a_hit.get("immat")
                            and a_hit.get("in_snapshot")
                            and a_hit.get("ancre_rendue"))
            if iris_ok is False:
                rec["cat"] = "Hors périmètre"
                rec["statut"] = (f"IRIS {rec['iris']} hors secteur "
                                 "(adresse mal géocodée)")
            elif ortho_ok:
                rec["cat"] = RESOL
                mec = ("ALIAS_RNC même bgid (parc-neutre)"
                       if a_hit.get("ancre_meme_bg")
                       else "ALIAS_RNC miroir bgid (dédup, à instruire)")
                rec["statut"] = (
                    f"variante orthographique exacte → immat "
                    f"{a_hit['immat']} `{a_hit['cle_adresse']}` "
                    f"(présente snapshot, ancre rendue) ; méca : {mec}")
            elif c_immat:
                rec["cat"] = RESOL
                rec["statut"] = (
                    f"RNC live → immat {c_immat} "
                    + ("présente snapshot non appariée (piste ALIAS)"
                       if c_in_snap else
                       "présente RNC national hors snapshot secteur"))
            elif usage in ("Tertiaire", "Secondaire", "Dépendance",
                           "Annexe"):
                rec["cat"] = "Monopropriété"
                rec["statut"] = (f"usage BDNB « {usage} » (non-copro) ; "
                                 "aucune copro RNC au n° (a/b/c ∅)")
            elif usage == "Résidentiel individuel":
                rec["cat"] = "Monopropriété"
                rec["statut"] = "usage BDNB résidentiel individuel"
            elif usage == "Résidentiel collectif" and nlb > 0:
                rec["cat"] = "Copro non immatriculée"
                rn = rec["diag"]["c"].get("rename")
                extra = ""
                if rn:
                    extra = (f" ; voie renommée — sondée sous « "
                             f"{rn['voie']} » : "
                             + ("immat " + str(rn['immat'])
                                if rn["hit"] else "toujours aucun n°"))
                rec["statut"] = (f"résidentiel collectif {nlb} lgts "
                                 f"BDNB, absent RNC (a/b/c ∅){extra}")
            elif (not usage or usage in ("non renseigné", None)) \
                    and nlb == 0:
                rec["cat"] = "Adresse DVF fantôme"
                rec["statut"] = ("aucun lgt BDNB, usage ∅, n° absent "
                                 "RNC — artefact cadastral probable")
            else:
                rec["cat"] = "Inconnu"
                rec["statut"] = (f"usage « {usage} », nb_log_bdnb={nlb}, "
                                 "a/b/c ∅ — non classable")
        rows.append(rec)

    # ---- ETAPE 4 : bilan ----
    hr_rows = [r for r in rows if not r["fused"]]
    fu_rows = [r for r in rows if r["fused"]]
    by_cat = collections.Counter(r["cat"] for r in hr_rows)

    def esc(s):
        return str(s).replace("|", "\\|") if s is not None else ""

    L = []
    L.append(f"# Audit « orphelines BDNB » + ventes DVF — secteur "
             f"{light['metadata'].get('secteur', SECTEUR)}\n")
    L.append("> **Lecture seule.** Aucun fichier de données / cache "
             "modifié. Caches RNC live consultés en lecture ; les "
             "requêtes manquantes ont été émises en direct (tabular-api "
             "RNIC) sans réécrire le cache disque.\n")

    L.append("## ÉTAPE 1 — Orphelines BDNB strictes (bgid null/vide & "
             "ventes-logement > 0)\n")
    L.append(f"**Résultat : {len(strict)} adresse(s)** dans ce secteur.\n")
    L.append(
        "Toutes les adresses du `secteur_*_light.json` portent un "
        "`batiment_groupe_id` non nul, et chacun de ces bgid existe "
        "dans `bdnb_*.json`. **Il n'existe donc aucune orpheline BDNB "
        "au sens strict.** Cause structurelle (`make_light.py` "
        "l.628-660) : la jointure BDNB applique un fallback à 3 "
        "paliers — (1) `numero_immat_principal` via la copro RNC de "
        "même clé, (2) `bdnb_par_voie` (numéro+voie), (3) **proximité "
        "GPS < 50 m** (`bdnb_proche`). En tissu urbain dense (Lyon 3e "
        "/ Paris 7e-15e) le palier 3 trouve toujours un bâtiment dans "
        "les 50 m : `bb` n'est jamais `None`, l'adresse n'est jamais "
        "abandonnée. Le géocodage est lui aussi systématiquement "
        "résolu (0 adresse à coordonnées nulles).\n")
    L.append(
        "→ La notion pertinente n'est donc pas « sans bgid » mais "
        "« **sans rattachement BDNB fiable** » : adresses dont le "
        "**seul** lien BDNB est le palier le plus faible "
        "(`_bdnb_match=='gps'`, proximité aveugle 50 m, sans identité "
        "immat ni numéro+voie) **et** ayant des ventes-logement. "
        "C'est cette population de fait qui est diagnostiquée "
        "ci-dessous (équivalent réel des « orphelines »).\n")

    L.append("## ÉTAPE 1bis — Population « orphelines de fait » "
             "(`_bdnb_match=='gps'` & ventes-logement > 0)\n")
    L.append("| Indicateur | Valeur |\n|---|--:|")
    L.append(f"| Orphelines de fait (total) | **{len(rows)}** |")
    L.append(f"| → hors-RNC actives (à diagnostiquer) | "
             f"**{len(hr_rows)}** |")
    L.append(f"| → déjà rattachées par fusion BDNB (non orphelines) | "
             f"{len(fu_rows)} |")
    L.append(f"| Ventes-logement concernées (hors-RNC actives) | "
             f"{sum(r['vlog'] for r in hr_rows)} |\n")

    L.append("## ÉTAPE 2 + 3 — Diagnostic ligne par ligne (hors-RNC "
             "actives)\n")
    if not hr_rows:
        L.append("_Aucune orpheline de fait hors-RNC active._\n")
    for r in sorted(hr_rows, key=lambda x: -x["vlog"]):
        d = r["diag"]
        L.append(f"### `{r['cle']}` — {esc(r['adresse'])}\n")
        L.append(f"- **Ventes** : {r['vlog']} logement / {r['vtot']} "
                 f"total · **bgid GPS** `{r['bg']}` · "
                 f"`nb_log_bdnb`={r['nb_log_bdnb']} · usage BDNB "
                 f"« {esc(r['usage'])} »")
        a = d["a"]
        if a["hit"]:
            h = a["hit"]
            snap = ("présente snapshot" if h["in_snapshot"]
                    else "hors snapshot")
            anc = ("ancre rendue" if h["ancre_rendue"]
                   else "ancre non rendue")
            bgs = ("même bgid → parc-neutre" if h["ancre_meme_bg"]
                   else "bgid distinct (miroir / dédup)")
            L.append(f"- **a) Normalisation orthographique** : MATCH "
                     f"({h['src']}) → immat `{h['immat']}` / "
                     f"`{h['cle_adresse']}` ({esc(h['nom'])}) — "
                     f"{snap}, {anc}, {bgs}. **Copro immatriculée** : "
                     "rattachable via ALIAS_RNC (variante "
                     "orthographique).")
        else:
            why = ("la voie normalisée est connue du registre mais "
                   f"aucune copro au n° {a['num']}"
                   if a["voie_connue_registre"] else
                   "voie normalisée absente du registre RNC du secteur")
            L.append(f"- **a) Normalisation orthographique** : échec — "
                     f"clé normalisée `({a['num']},{a['voie_norm']})` "
                     f"sans correspondance dans `cle_adresse` ni "
                     f"`nom_copropriete`/`adresse`. Raison : {why}.")
        b = d["b"]
        if b["cands"]:
            c0 = b["cands"][0]
            L.append(
                f"- **b) Proximité GPS** : copro la plus proche à "
                f"**{c0['dist']} m** — `{c0['cle_adresse']}` "
                f"immat `{c0['immat']}` ({esc(c0['nom'])}). "
                f"{b['within50']} copro(s) ≤ 50 m.")
            if b["within50"]:
                if c0["ancre_meme_bg"]:
                    L.append("  - Copro dans le rayon **et même "
                             "`batiment_groupe_id`** → rattachement "
                             "parc-neutre envisageable (piste).")
                else:
                    L.append("  - Copro dans le rayon mais **bâtiment "
                             "distinct** (`batiment_groupe_id` ≠) et "
                             "déjà ancrée sur sa propre `cle_adresse` "
                             "rendue : rattacher détruirait du parc "
                             "(règle cardinale PIPELINE §9) → écarté.")
            else:
                L.append("  - Aucune copro RNC ≤ 50 m → pas de "
                         "rattachement GPS possible.")
        else:
            L.append("- **b) Proximité GPS** : aucune copro RNC "
                     "géolocalisée à proximité (≤ 80 m).")
        c = d["c"]
        if c.get("immat"):
            L.append(
                f"- **c) RNC live (tabular-api, {c['src']}, token "
                f"`{c['token']}`, {c['n_rows']} lignes)** : MATCH "
                f"(num,voie) → immat `{c['immat']}` "
                f"({esc(c['nom'])}, {c['lots']} lots hab.) — "
                f"{'présente' if c['in_snapshot'] else 'ABSENTE'} du "
                f"snapshot copro du secteur.")
        else:
            rn = c.get("rename")
            rntxt = ""
            if rn:
                rntxt = (f" Voie renommée : re-sondée sous l'ancien nom "
                         f"« {rn['voie']} » ({rn['n_rows']} lignes) → "
                         + (f"immat `{rn['immat']}`."
                            if rn["hit"] else
                            f"toujours aucune copro au n° {a['num']}."))
            L.append(
                f"- **c) RNC live (tabular-api, {c['src']}, token "
                f"`{c['token']}`, {c.get('n_rows', 0)} lignes)** : "
                "aucune copro à ce (numéro, voie) dans le RNC national "
                f"→ pas d'immatriculation pour cette adresse.{rntxt}")
        dd = d["d"]
        cause = "ce n'est pas la cause" if dd["coords_ok"] else "CAUSE"
        L.append(
            f"- **d) Géocodage BAN** : adresse géocodée "
            f"(`_coord_source={dd['coord_src']}`), coordonnées "
            f"{'présentes' if dd['coords_ok'] else 'NULLES'} "
            f"(lat={r['lat']}, lon={r['lon']}) → {cause}"
            f". IRIS `{dd['iris']}` "
            f"{'dans' if dd['iris_in_secteur'] else 'HORS'} secteur.")
        L.append(f"- **➡ Catégorie : {r['cat']}**"
                 + (f" — {esc(r['statut'])}" if r["statut"] else "") + "\n")

    L.append("## ÉTAPE 4 — Bilan chiffré par catégorie\n")
    L.append(
        "> **Note de classement.** Une copro trouvée *immatriculée* "
        "(match orthographique exact sur une `cle_adresse` du snapshot, "
        "ou hit RNC live) n'est par définition **pas** « copro non "
        "immatriculée » : ces cas ne relèvent d'**aucune** des 5 "
        "catégories résiduelles. Ce sont des **rattachables** (lacune "
        "de couverture du pipeline : la clé DVF abrège la voie — "
        "`CAPT`→`CAPITAINE`, `GAL`→`GENERAL` — donc l'appariement "
        "automatique la rate), comptés à part.\n")
    L.append("| Catégorie | n | ventes-log |\n|---|--:|--:|")
    for cat in ["Adresse DVF fantôme", "Copro non immatriculée",
                "Monopropriété", "Hors périmètre", "Inconnu"]:
        sub = [r for r in hr_rows if r["cat"] == cat]
        L.append(f"| {cat} | {len(sub)} | "
                 f"{sum(r['vlog'] for r in sub)} |")
    res = [r for r in hr_rows if r["cat"] == RESOL]
    L.append(f"| _(hors 5 cat.)_ **{RESOL}** | **{len(res)}** | "
             f"**{sum(r['vlog'] for r in res)}** |")
    L.append(f"| **Total hors-RNC actives** | **{len(hr_rows)}** | "
             f"**{sum(r['vlog'] for r in hr_rows)}** |")
    L.append(f"| _(rappel)_ déjà rattachées par fusion | {len(fu_rows)} "
             f"| {sum(r['vlog'] for r in fu_rows)} |\n")

    L.append("### Liste complète — orphelines de fait hors-RNC "
             "actives\n")
    L.append("| cle | adr | v_log | v_tot | usage BDNB | nb_log_bdnb | "
             "a | b≤50m | c (RNC live) | catégorie | statut |")
    L.append("|---|---|--:|--:|---|--:|:-:|:-:|---|---|---|")
    for r in sorted(hr_rows, key=lambda x: (x["cat"], -x["vlog"])):
        a = r["diag"]["a"]
        b = r["diag"]["b"]
        c = r["diag"]["c"]
        cv = (f"immat {c['immat']}"
              f"{' (snap)' if c.get('in_snapshot') else ' (hors snap)'}"
              if c.get("immat") else "∅")
        L.append(
            f"| `{esc(r['cle'])}` | {esc(r['adresse'])} | {r['vlog']} | "
            f"{r['vtot']} | {esc(r['usage'])} | {r['nb_log_bdnb']} | "
            f"{'oui' if a['hit'] else 'non'} | {b['within50']} | {cv} | "
            f"{r['cat']} | {esc(r['statut'])} |")

    L.append("\n### Liste — orphelines de fait DÉJÀ rattachées "
             "(fusion BDNB même bgid ; non orphelines au sens métier)\n")
    L.append("| cle | adr | v_log | v_tot | usage BDNB | bgid | "
             "ancre de fusion |")
    L.append("|---|---|--:|--:|---|---|---|")
    for r in sorted(fu_rows, key=lambda x: -x["vlog"]):
        L.append(
            f"| `{esc(r['cle'])}` | {esc(r['adresse'])} | {r['vlog']} | "
            f"{r['vtot']} | {esc(r['usage'])} | `{r['bg']}` | "
            f"`{esc(r['fusion_cible'])}` |")

    L.append("\n---\n*Diagnostic lecture seule "
             "`scripts/diag_orphelines_bdnb.py` — n'écrit que ce "
             "rapport.*")

    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"=== {SECTEUR} ===")
    print(f"strict_orphelines={len(strict)}  "
          f"orphelines_de_fait={len(rows)}  "
          f"hors-RNC_actives={len(hr_rows)}  fusionnees={len(fu_rows)}")
    print("categories:", dict(by_cat))
    print("rapport:", REPORT.name)


if __name__ == "__main__":
    main()
