#!/usr/bin/env python3
"""Tag KV des cibles 0-vente CERTIFIEES (survivants ultime scan).

LECTURE/DRY puis APPLY explicite.

LOT a tagger :
  - 62 cles COPRO_ABSENTE_DVF (= 0 mut Apt parcelle 5 ans, parc fige
    confirme par DVF)
  - 1 cle 141 RUE DAUPHINE (retrait du tag 'mixte' fantome PUIS
    tagging cible_0vente_*)
  - 1 cle 227 RUE FELIX FAURE (override terrain : ASSOCIATION DE
    L'HOTEL SOCIAL = asso privee, copro classique avec PP - NI mono
    NI social, donc cible 0-vente normale)
  = 64 cles a tagger en cible_0vente_active OU cible_0vente_isolee

SOUS-TAG :
  - active : un voisin +/-2 (meme voie) a nb_ventes_logement > 0
             (= quartier liquide, copro figee dedans = cible chaude)
  - isolee : aucun voisin ne vend (zone dormante)

EXCLUS du batch (a traiter separement) :
  - 4 MONO_NON_DETECTE restants (227 FF deplace dans le batch via
    override terrain)
  - 2 COPRO_FIGEE (parcelle active : 2 DAUPHINE, 10 NAZARETH)
  - 4 RATTACHEES (correctif light)

Procedure :
  1. GET KV live
  2. 141 DAUPHINE : confirmer tag 'mixte' sans _qualif_source
  3. Audit 63 cles : aucune ne doit deja etre cible_0vente_*
  4. Backup data/_kv_assign_dl.pre_certif_0vente.bak
  5. DRY-RUN affichage + STOP
  6. Sur apply :
     - del assigns['141|RUE|DAUPHINE'] (retrait mixte fantome)
     - POST KV avec les 63 cibles taggees
     - re-GET 3 temoins
     - maj cache local
"""
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
ENRICH = ROOT / "data" / "_enrich_majic_dl_full.json"
DVF = Path(r"C:\Users\Station 5\dvf_dauphine_lacassagne.json")
KV_BAK = ROOT / "data" / "_kv_assign_dl.pre_certif_0vente.bak"

API = "https://dpe-prospector-api.yann-bufferne.workers.dev"
AGENCE = "dauphine-lacassagne"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/531.36")
ANS = ("2021", "2022", "2023", "2024", "2025")
JWT = os.environ.get("DPE_JWT") or ""

# Helpers normalisation
ABBR = {"SAINT": "ST", "SAINTE": "STE", "DOCTEUR": "DR", "PROFESSEUR": "PR"}
ART = {"DU", "DE", "DES", "LA", "LE", "LES", "L", "D", "A", "AU", "AUX",
       "ET", "BIS", "TER"}


def toks(s):
    s = (s or "").upper().replace("'", " ")
    return tuple(sorted(ABBR.get(t, t)
                        for t in re.split(r"[^A-Z0-9]+", s)
                        if t and t not in ART))


def parse_cle(cle):
    p = (cle or "").split("|")
    if len(p) != 3:
        return None
    m = re.match(r"^(\d+)([A-Z]*)$", p[0].strip().upper())
    if not m:
        return None
    return int(m.group(1)), m.group(2), p[1], toks(p[2])


HLM_NEEDLES = (
    "HABITAT", "HLM", "GRANDLYON", "ALLIADE", "BATIGERE",
    "CDC HABITAT", "FONCIERE D'HABITAT", "IMMOBILIERE RHONE",
    "ALPES ISERE", "SACVL", "OPAC", "ESH", "FONCIERE HABITAT",
    "ADOMA", "ERILIA", "IN'LI", "INLI", "DYNACITE", "3F RESIDENCES",
    "ICF", "FONDATION ARALIS", "OPH ", " OPH",
    "OFFICE PUBLIC DE L HABITAT", "OFFICE PUBLIC DE L'HABITAT",
)
PUBLIC_NON_HLM = (
    "COMMUNE DE LYON", "METROPOLE DE LYON", "DEPARTEMENT DU RHONE",
    "REGION AUVERGNE", "REGION RHONE", "ETAT ", "ETAT,",
    "HOSPICES CIVILS", "CENTRE HOSPITALIER",
    "COMMUNAUTE URBAINE", "GRAND LYON", "DIRECTION DE L IMMOBILIER",
    "SEM ", "FONCIERE VESTA", "FONCIERE PIERRE",
    "CENTRE REGIONAL OEUVRES", "CROUS",
    "ASSOCIATION DIOCESAINE", "FONDATION", "ITINOVA",
    "INSTITUT NATIONAL", "INSTITUT DE FRANCE",
)


def is_hlm(d):
    d = (d or "").upper()
    return any(n in d for n in HLM_NEEDLES if n.strip())


def is_public_non_hlm(d):
    d = (d or "").upper()
    return any(n in d for n in PUBLIC_NON_HLM)


def kv_req(method, path, body=None):
    if not JWT:
        sys.exit("  [abort] env DPE_JWT absente")
    url = f"{API}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {JWT}", "User-Agent": UA,
               "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    do_apply = (len(sys.argv) > 1 and sys.argv[1].lower() == "apply")
    mode = "APPLY" if do_apply else "DRY-RUN"
    print("=" * 78)
    print(f"TAG CIBLES 0-VENTE CERTIFIEES DL  ({mode})")
    print("=" * 78)

    # 1. GET KV live
    print("\n[1] GET KV live cloud...")
    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    if st != 200:
        sys.exit(f"  GET KV err: {st} {body}")
    assigns = body.get("assignments") or {}
    fusions = body.get("fusions") or {}
    noms = body.get("noms") or {}
    print(f"  assignments={len(assigns)}  fusions={len(fusions)}")

    # 2. Charger contexte (light + enrich + DVF)
    print("\n[2] Chargement contexte...")
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = doc["adresses"]
    co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
    by_cle = {(a.get("cle") or ""): a for a in ad}
    enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
    enrich_by_cle = {r["cle"]: r for r in enrich["results"]}
    dvf = json.loads(DVF.read_text(encoding="utf-8"))
    print(f"  light={len(ad)}, copros={len(co_by_cle)}, dvf={len(dvf)}")

    # ------------------------------------------------------------
    # REPRODUIT L'ULTIME SCAN POUR IDENTIFIER LES 62 COPRO_ABSENTE_DVF
    # ------------------------------------------------------------
    print("\n[3] Reproduction ultime scan -> identification 62 COPRO_ABSENTE_DVF")

    # fusedSrc + mergedInto + autoMerged
    def vpa(a):
        return a.get("ventes_par_an_logement") or {}

    merged_into = {}
    fused_src = set()
    for src, dst in fusions.items():
        sa = by_cle.get(src)
        if not sa or not dst or src == dst:
            continue
        fused_src.add(src)
        m = merged_into.setdefault(dst, {"ventes": {}})
        for y in ANS:
            m["ventes"][y] = m["ventes"].get(y, 0) + (vpa(sa).get(y, 0) or 0)

    auto_merged = {}
    for a in ad:
        cible = a.get("_fusion_cible") or a.get("_fusion_auto_target")
        cle = a.get("cle") or ""
        if a.get("_fusion_auto") and cible and cle not in fused_src:
            fused_src.add(cle)
            am = auto_merged.setdefault(cible, {"ventes": {}})
            for y in ANS:
                am["ventes"][y] = am["ventes"].get(y, 0) + (vpa(a).get(y, 0) or 0)

    def passes_sans_ventes(a):
        cle = a.get("cle") or ""
        if cle in fused_src:
            return False
        asSv = assigns.get(cle) or {}
        t = asSv.get("type") or ""
        if t in ("social", "bureaux", "mono"):
            return False
        is_rnc = (cle in co_by_cle) or bool(a.get("numero_immatriculation"))
        is_ni = (t == "copro_non_immat")
        is_mixte = (t == "mixte")
        if not (is_rnc or is_ni or is_mixte):
            return False
        own_n = int(a.get("nb_ventes_logement") or 0)
        if own_n > 0:
            return False
        own_vpa = a.get("ventes_par_an_logement") or {}
        if any((own_vpa.get(y) or 0) > 0 for y in ANS):
            return False
        if is_rnc:
            mi = merged_into.get(cle)
            if mi and any((mi["ventes"].get(y) or 0) > 0 for y in ANS):
                return False
        am = auto_merged.get(cle)
        if am and any((am["ventes"].get(y) or 0) > 0 for y in ANS):
            return False
        return True

    population = [a for a in ad if passes_sans_ventes(a)]
    print(f"  Population Sans ventes UI (cloud) : {len(population)}")

    # Index bgid -> [a]
    cles_par_bgid = defaultdict(list)
    for a in ad:
        bg = a.get("batiment_groupe_id") or ""
        if bg:
            cles_par_bgid[bg].append(a)

    # DVF index par parcelle
    dvf_by_parc = defaultdict(list)
    for m in dvf:
        sec = m.get("Section") or ""
        plan = (m.get("No plan") or "").lstrip("0") or "0"
        if str(m.get("Code type local") or "").strip() in ("1", "2"):
            dvf_by_parc[(sec, plan)].append(m)

    def parc_to_dvf_key(parc):
        return (parc[8:10], parc[10:].lstrip("0") or "0")

    def mut_an_parcelle(cle):
        e = enrich_by_cle.get(cle, {})
        parcs = e.get("parcelles_bdnb") or []
        seen = set()
        for parc in parcs:
            for m in dvf_by_parc.get(parc_to_dvf_key(parc), []):
                seen.add((m.get("Date mutation"), m.get("No disposition"),
                          m.get("Valeur fonciere")))
        return len(seen) / 5.0

    def classify_dominant(cle):
        e = enrich_by_cle.get(cle, {})
        sirens = e.get("sirens") or []
        n_lots = e.get("majic_lots") or 0
        if n_lots == 0 or not sirens:
            return ("AUTRE", None, 0)
        hlm_lots = sum(s.get("lots") or 0 for s in sirens
                       if is_hlm(s.get("denomination")))
        pub_lots = sum(s.get("lots") or 0 for s in sirens
                       if is_public_non_hlm(s.get("denomination")))
        if hlm_lots * 100 / n_lots >= 50:
            return ("HLM_DOMINANT", None, hlm_lots * 100 / n_lots)
        if pub_lots * 100 / n_lots >= 50:
            return ("PUBLIC_DOMINANT", None, pub_lots * 100 / n_lots)
        return ("AUTRE", None, 0)

    def is_mono_top(cle):
        """Top SIREN >= 80% lots PM ? (mono-soft)"""
        e = enrich_by_cle.get(cle, {})
        sirens = e.get("sirens") or []
        n_lots = e.get("majic_lots") or 0
        if not sirens or n_lots == 0:
            return False
        top = sirens[0]
        return ((top.get("lots") or 0) * 100 / n_lots) >= 80

    # Filtre 1 : fantomes
    pop1 = []
    for a in population:
        cle = a.get("cle") or ""
        cp = co_by_cle.get(cle, {})
        bg = a.get("batiment_groupe_id") or ""
        bdnb = int(a.get("nb_log_bdnb") or 0)
        lots = int(cp.get("nb_lots_habitation") or 0)
        fa = bool(a.get("_fusion_auto"))
        if not bg or (bdnb == 0 and lots == 0) or fa:
            continue
        pop1.append(a)

    # Filtre 2 : rattachees
    pop2 = []
    for a in pop1:
        cle = a.get("cle") or ""
        bg = a.get("batiment_groupe_id") or ""
        has_selling_neighbor_bgid = any(
            int(av.get("nb_ventes_logement") or 0) > 0
            for av in cles_par_bgid.get(bg, [])
            if (av.get("cle") or "") != cle
        )
        if has_selling_neighbor_bgid:
            continue
        pop2.append(a)

    # Filtre 3 : sociaux/publics (deja taggees mixte par DVF reclassement
    # sont DEJA passees ici car leur tag mixte est dans le pop). Mais
    # ce filtre 3 utilise MAJIC HLM dominant : ces 3 cles 117 BARABAN /
    # 141 DAUPHINE / 24 FREDERIC MISTRAL sont signalees. On a vu qu'elles
    # sont DEJA mixte = OK. Pour le batch CIBLE 0-vente : on les EXCLUE
    # (comme le filtre 3 le faisait) sauf 141 DAUPHINE qu'on traite a
    # part (retrait du tag mixte fantome + tagging cible).
    SPECIAL_141 = "141|RUE|DAUPHINE"
    SPECIAL_227FF = "227|AVENUE|FELIX FAURE"
    pop3 = []
    excluded_filter3 = []
    for a in pop2:
        cle = a.get("cle") or ""
        if cle == SPECIAL_141:
            # cas particulier traite a part
            continue
        cat, _, pct = classify_dominant(cle)
        if cat in ("HLM_DOMINANT", "PUBLIC_DOMINANT"):
            mut_an = mut_an_parcelle(cle)
            if mut_an < 2.0:
                excluded_filter3.append((cle, cat, pct))
                continue
        pop3.append(a)

    # Filtre 4 : tertiaire
    pop4 = []
    for a in pop3:
        usage = (a.get("usage_principal_bdnb") or "").lower()
        if "tertiaire" in usage or "bureau" in usage:
            continue
        pop4.append(a)

    # OVERRIDES TERRAIN : cles classifiees mono-soft mais confirmees
    # terrain comme copros classiques (PP + 1 SIREN minoritaire).
    # Force leur inclusion dans le lot CIBLE (NI mono NI social).
    TERRAIN_OVERRIDE_COPRO = {
        "227|AVENUE|FELIX FAURE": (
            "ASSOCIATION DE L'HOTEL SOCIAL = asso de droit prive, "
            "4 lots PM minoritaires, le reste PP : copro classique."
        ),
    }

    # Sous-classification : COPRO_ABSENTE_DVF / MONO / COPRO_FIGEE
    copro_absente = []
    mono_soft = []
    copro_figee_active = []
    for a in pop4:
        cle = a.get("cle") or ""
        # Override terrain : copro classique forcee dans cible
        if cle in TERRAIN_OVERRIDE_COPRO:
            mut_an = mut_an_parcelle(cle)
            if mut_an == 0:
                copro_absente.append(a)
            else:
                copro_figee_active.append(a)
            continue
        mut_an = mut_an_parcelle(cle)
        if is_mono_top(cle):
            mono_soft.append(a)
        elif mut_an == 0:
            copro_absente.append(a)
        else:
            copro_figee_active.append(a)

    print(f"  COPRO_ABSENTE_DVF        : {len(copro_absente)}")
    print(f"  MONO_NON_DETECTE         : {len(mono_soft)}")
    print(f"  COPRO_FIGEE active       : {len(copro_figee_active)}")
    print(f"  TERRAIN_OVERRIDE applique: {len(TERRAIN_OVERRIDE_COPRO)} "
          f"cles forcees en cible (NI mono NI social)")

    # ------------------------------------------------------------
    # CONSTITUTION DU LOT (62 + 141 DAUPHINE + 227 FELIX FAURE)
    # ------------------------------------------------------------
    print()
    print("=" * 78)
    print("[LOT] = COPRO_ABSENTE_DVF + 141 DAUPHINE + override terrain (227 FF)")
    print("=" * 78)

    lot = list(copro_absente)
    # Ajouter 141 DAUPHINE (special case retrait mixte fantome)
    a141 = by_cle.get(SPECIAL_141)
    if a141:
        # ne pas dupliquer si deja dans copro_absente
        if not any((x.get("cle") or "") == SPECIAL_141 for x in lot):
            lot.append(a141)
    else:
        print(f"  [warn] {SPECIAL_141} absent du light")

    print(f"  Lot total : {len(lot)} cles")

    # ------------------------------------------------------------
    # AUDIT
    # ------------------------------------------------------------
    print("\n[AUDIT] verifications par cle")

    # Voisinage : active/isolee
    voie_to_cles = defaultdict(list)
    for a in ad:
        cle = a.get("cle") or ""
        parsed = parse_cle(cle)
        if parsed is None:
            continue
        num, suffix, tv, vt = parsed
        voie_to_cles[(tv, vt)].append((num, cle, a))

    def voisin_vend(a):
        """Voisin num +/-2 meme voie avec nb_ventes_logement>0 ?"""
        parsed = parse_cle(a.get("cle") or "")
        if parsed is None:
            return False, []
        num, suffix, tv, vt = parsed
        voisins = []
        for n_v, cle_v, av in voie_to_cles.get((tv, vt), []):
            if cle_v == (a.get("cle") or ""):
                continue
            if abs(n_v - num) > 2:
                continue
            if int(av.get("nb_ventes_logement") or 0) > 0:
                voisins.append((cle_v, av.get("nb_ventes_logement")))
        return bool(voisins), voisins

    will_patch = []
    excluded = []
    for a in lot:
        cle = a.get("cle") or ""
        cur_t = ((assigns.get(cle) or {}).get("type")) or ""
        cur_full = assigns.get(cle) or {}
        # Cas special 141 DAUPHINE : retrait tag mixte fantome
        if cle == SPECIAL_141:
            if cur_t != "mixte":
                excluded.append((cle, f"141 DAUPHINE tag != 'mixte' ({cur_t!r})"))
                continue
            if cur_full.get("_qualif_source"):
                excluded.append((cle,
                    f"141 DAUPHINE a _qualif_source='{cur_full.get('_qualif_source')}' "
                    f"(=tag protege, ne pas toucher)"))
                continue
        # Cas special 227 FELIX FAURE : override l'override DVF decollect
        # Tag attendu : 'mixte' AVEC _qualif_source='dvf_decollect'
        # (consigne user : asso de droit prive = NI mono NI social)
        elif cle == SPECIAL_227FF:
            if cur_t != "mixte":
                excluded.append((cle, f"227 FF tag != 'mixte' ({cur_t!r})"))
                continue
            qs = cur_full.get("_qualif_source")
            if qs != "dvf_decollect":
                excluded.append((cle,
                    f"227 FF _qualif_source='{qs}' (attendu 'dvf_decollect')"))
                continue
            # OK : on va override le tag DVF decollect par cible terrain
        else:
            # Audit normal : ne pas re-tagger si deja cible_0vente_*
            if cur_t in ("cible_0vente_active", "cible_0vente_isolee"):
                excluded.append((cle, f"deja {cur_t}"))
                continue
            if cur_t in ("social", "bureaux", "mono"):
                excluded.append((cle, f"tag protege courant : '{cur_t}'"))
                continue
        active, voisins = voisin_vend(a)
        new_tag = "cible_0vente_active" if active else "cible_0vente_isolee"
        will_patch.append({
            "cle": cle, "a": a,
            "cur_full": cur_full, "cur_t": cur_t,
            "new_tag": new_tag, "active": active, "voisins": voisins,
        })

    print(f"\n  Lot               : {len(lot)}")
    print(f"  A patcher         : {len(will_patch)}")
    print(f"  Exclus            : {len(excluded)}")
    for cle, raison in excluded:
        print(f"    [SKIP] {cle:32s} {raison}")

    # ------------------------------------------------------------
    # BACKUP
    # ------------------------------------------------------------
    print(f"\n[BAK] Backup -> {KV_BAK.name}")
    snapshot = {
        "_meta": {
            "captured_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agence": AGENCE,
            "purpose": ("pre-certif-0vente-dl : 62 COPRO_ABSENTE_DVF + "
                         "141 DAUPHINE (retrait mixte fantome). Backup "
                         "distinct des autres .bak."),
            "n_to_patch": len(will_patch),
            "n_excluded": len(excluded),
        },
        "assignments": assigns,
        "fusions": fusions,
        "noms": noms,
    }
    if KV_BAK.exists():
        print(f"  [warn] backup existant -> ecrase: {KV_BAK.name}")
    KV_BAK.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"  ecrit {len(assigns)} assignments")

    # ------------------------------------------------------------
    # DRY-RUN tableau
    # ------------------------------------------------------------
    print()
    print("=" * 120)
    print("DRY-RUN : tableau a patcher (tri nb_log DESC)")
    print("=" * 120)

    def eff_log(a):
        cle = a.get("cle") or ""
        cp = co_by_cle.get(cle)
        if cp:
            v = cp.get("nb_lots_habitation")
            if v is not None:
                try:
                    return int(v)
                except (TypeError, ValueError):
                    pass
        return int(a.get("nb_log_bdnb") or 0)

    will_patch.sort(key=lambda r: -eff_log(r["a"]))

    print(f"  {'#':>3} {'cle':32s} {'nb_log':>6} {'tag avant':18s} -> "
          f"{'nouveau tag':24s} {'active':6s} voisins")
    print("  " + "-" * 118)
    cnt = Counter()
    for i, r in enumerate(will_patch, 1):
        n = eff_log(r["a"])
        cur_str = r["cur_t"] or "(absent)"
        voisins_str = ",".join(f"{c.split('|')[0]}({v})"
                                for c, v in r["voisins"][:2])
        active_str = "ACTIVE" if r["active"] else "isolee"
        print(f"  {i:>3} {r['cle']:32s} {n:>6} {cur_str:18s} -> "
              f"{r['new_tag']:24s} {active_str:6s} {voisins_str}")
        cnt[r["new_tag"]] += 1

    print()
    print(f"  Repartition :")
    for k, v in cnt.most_common():
        print(f"    {k:30s} : {v}")

    print()
    print(f"  Note 141 DAUPHINE : retrait du tag 'mixte' fantome PUIS pose")
    print(f"  du tag cible_0vente_* (operation atomique sur 1 cle).")

    if not do_apply:
        print()
        print("=" * 78)
        print("DRY-RUN : STOP. Lance avec 'apply' pour POSTer.")
        print(f"  A patcher : {len(will_patch)}  ;  Exclus : {len(excluded)}")
        print(f"  Backup : {KV_BAK.name}")
        print("=" * 78)
        return

    # ------------------------------------------------------------
    # APPLY
    # ------------------------------------------------------------
    print()
    print("=" * 78)
    print("APPLY : POST atomique...")
    print("=" * 78)
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    for r in will_patch:
        cle = r["cle"]
        # Pour 141 DAUPHINE : retrait mixte fantome puis pose nouveau tag.
        # Pour 227 FF : override l'override DVF decollect.
        # Atomique : on remplace l'entry par le nouveau tag.
        assigns[cle] = {
            "type": r["new_tag"],
            "_qualif_source": "ultime_scan_certif",
            "_qualif_date": now_iso,
        }
        if cle == SPECIAL_141:
            assigns[cle]["_qualif_note"] = ("retrait tag 'mixte' fantome "
                                              "sans qualif_source pre-existant")
        if cle == SPECIAL_227FF:
            assigns[cle]["_qualif_note"] = ("terrain override : ASSO DE "
                                              "L'HOTEL SOCIAL = asso de droit "
                                              "prive (NI mono NI social) ; "
                                              "remplace _qualif_source="
                                              "dvf_decollect anterieur")

    st, body = kv_req("POST", f"/secteur-assignments/{AGENCE}",
                       {"assignments": assigns, "fusions": fusions,
                        "noms": noms})
    print(f"  status={st}  body={body}")
    if st != 200:
        sys.exit("  POST echec")

    # Verif
    print("\n[VERIF] re-GET 3 temoins (dont 141 DAUPHINE)...")
    st, body = kv_req("GET", f"/secteur-assignments/{AGENCE}")
    if st != 200:
        sys.exit(f"  Re-GET err: {body}")
    a2 = body.get("assignments") or {}
    sample = [SPECIAL_141]
    rest = [r["cle"] for r in will_patch if r["cle"] != SPECIAL_141]
    random.seed(42)
    sample += random.sample(rest, min(2, len(rest)))
    fails = 0
    for cle in sample:
        v = a2.get(cle)
        expected = next((r["new_tag"] for r in will_patch
                          if r["cle"] == cle), None)
        ok = bool(v) and v.get("type") == expected
        print(f"  [{'OK' if ok else 'FAIL'}] {cle:32s} -> {v}")
        if not ok:
            fails += 1
    if fails:
        sys.exit(f"  [abort] {fails} fails")

    # Maj local
    kv_local = json.loads(KV_LOCAL.read_text(encoding="utf-8")) \
        if KV_LOCAL.exists() else {"assignments": {}}
    kv_local["assignments"] = assigns
    KV_LOCAL.write_text(json.dumps(kv_local, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"\n  [local] {KV_LOCAL.name} mis a jour ({len(assigns)} assigns)")

    # Maj _social_overrides_dl.json : retirer 227 FF si patche (override
    # passe de dvf_decollect vers ultime_scan_certif, ne plus le tracker
    # comme override social).
    OVERRIDES = ROOT / "data" / "_social_overrides_dl.json"
    if OVERRIDES.exists() and any(r["cle"] == SPECIAL_227FF for r in will_patch):
        ov_doc = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        before_n = len(ov_doc.get("overrides", []))
        ov_doc["overrides"] = [o for o in ov_doc.get("overrides", [])
                                if o.get("cle") != SPECIAL_227FF]
        after_n = len(ov_doc["overrides"])
        ov_doc.setdefault("_meta", {})["last_cleanup"] = {
            "date": now_iso,
            "removed": [SPECIAL_227FF],
            "reason": ("terrain override : asso prive non social, "
                        "deplace en cible 0-vente certifiee"),
        }
        OVERRIDES.write_text(json.dumps(ov_doc, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        print(f"  [overrides] {OVERRIDES.name} : "
              f"{before_n} -> {after_n} (retire {SPECIAL_227FF})")

    print()
    print("=" * 78)
    print(f"APPLY REUSSI : {len(will_patch)} cles tagges ; "
          f"{len(excluded)} exclues.")
    print("=" * 78)


if __name__ == "__main__":
    main()
