"""
pipeline_bdnb_pivot.py — Audit lecture seule (dry-run).

Concept : pour chaque adresse hors-RNC active (predicat renderSecteur),
recupere via API BDNB `batiment_groupe_complet` (champ `l_libelle_adr`)
toutes les adresses BAN du batiment_groupe_id. Chaque adresse-pivot
est ensuite canonisee (regles `_canon_parts` make_light + SUBS
GAL/CAPT/AIRES bidirectionnelles) puis cherchee dans coproprietes[]
du snapshot secteur (cle_adresse). Si match -> candidat rattachement.

Throttling 0.1s entre appels API. Cache `data/_pivot_bdnb_cache.json`
pour eviter de re-appeler l'API. Sortie : `data/audit_pivot_bdnb.md`.
PYTHONUTF8=1 recommande. Aucune modification des fichiers de donnees
(seuls le rapport et le cache - artefact derive - sont ecrits).

Usage :
  python scripts/pipeline_bdnb_pivot.py
"""

import os
import re
import sys
import json
import time
import collections
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT_DL = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
LIGHT_MP = ROOT / "data" / "secteur_motte_picquet_light.json"
CACHE = ROOT / "data" / "_pivot_bdnb_cache.json"
REPORT = ROOT / "data" / "audit_pivot_bdnb.md"

BDNB_URL = ("https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
            "?select=batiment_groupe_id,l_libelle_adr,l_cle_interop_adr,"
            "libelle_adr_principale_ban,nb_adresse_valid_ban"
            "&batiment_groupe_id=in.")

# Normalisation alignee sur make_light _canon_parts.
VOIE = {"R": "RUE", "RUE": "RUE", "AV": "AVENUE", "AVE": "AVENUE",
        "AVENUE": "AVENUE", "BD": "BOULEVARD", "BLD": "BOULEVARD",
        "BOUL": "BOULEVARD", "BOULEVARD": "BOULEVARD", "CRS": "COURS",
        "COURS": "COURS", "IMP": "IMPASSE", "IMPASSE": "IMPASSE",
        "PL": "PLACE", "PLACE": "PLACE", "ALL": "ALLEE",
        "ALLEE": "ALLEE", "CHE": "CHEMIN", "CH": "CHEMIN",
        "CHEMIN": "CHEMIN", "QU": "QUAI", "QUAI": "QUAI",
        "RTE": "ROUTE", "ROUTE": "ROUTE", "SQ": "SQUARE",
        "SQUARE": "SQUARE", "MTE": "MONTEE", "MONTEE": "MONTEE",
        "PAS": "PASSAGE", "PASSAGE": "PASSAGE", "GR": "GRANDE RUE",
        "TSSE": "TERRASSE", "VLA": "VILLA"}
BIS = {"B": "B", "BIS": "B", "T": "T", "TER": "T", "Q": "Q",
       "QUATER": "Q", "A": "A", "C": "C", "D": "D"}
SAINTS = {"SAINT": "ST", "SAINTE": "STE", "SAINTES": "STES",
          "SAINTS": "STS"}
ARTICLES = {"DE", "DES", "DU", "D", "LA", "LE", "LES", "L", "AUX"}
# Substitutions abreviations attestees projet (bidirectionnelles)
SUBS_PAIRS = [("GAL", "GENERAL"), ("GEN", "GENERAL"), ("GENL", "GENERAL"),
              ("MAL", "MARECHAL"), ("CDT", "COMMANDANT"),
              ("CMDT", "COMMANDANT"), ("CAPT", "CAPITAINE"),
              ("CNE", "CAPITAINE"), ("DR", "DOCTEUR"),
              ("PR", "PROFESSEUR"), ("PROF", "PROFESSEUR"),
              ("PRES", "PRESIDENT"), ("MGR", "MONSEIGNEUR"),
              ("MNE", "MADELEINE"), ("FG", "FAUBOURG"),
              ("PCE", "PRINCE"), ("AYRES", "AIRES")]
SUBS = {}
for a, b in SUBS_PAIRS:
    SUBS.setdefault(a, b)
    SUBS.setdefault(b, a)
ACCENTS = str.maketrans("ÉÈÊÀÂÔÎÏÇÛÙ", "EEEAAOIICUU")

# Skip-list : faux positifs / cas instruits manuellement non-actionnables.
# Cle = (secteur, orph_cle, anchor_cle). Valeur = (date_instruction,
# commit, raison_metier). Le pipeline n'emet pas de match pour ces
# paires (mais re-detecte si une AUTRE ancre apparait pour le meme
# orph, ce qui resterait pertinent). Mettre a jour quand un cas est
# definitivement instruit.
SKIP_PAIRS = {
    ("dauphine_lacassagne",
     "18|RUE|ST ANTOINE",
     "17|RUE|ST ANTOINE"): (
        "2026-05-20", "cd74576",
        "FAUX POSITIF : bgid light PFFK (assigne par defaut "
        "par make_light num_voie BDNB) ne correspond pas au bgid "
        "BDNB authoritative reel 5RMC-KXL7-E97N (complexe 4/6 Ternois "
        "+ 93 Bellecombe + 18 St Antoine, 80 lgts). Aucune copro RNC "
        "propre sur 5RMC. Le pivot match est base sur le bgid light "
        "errone, pas sur l'identite reelle du bati. Resoudre demande "
        "soit (a) corriger le bgid de 18 ST ANTOINE dans le light, "
        "soit (b) fournir une preuve terrain rattachant 18 a une "
        "copro existante (AB5869177 via 94 Bellecombe ?)."),
}


def _txt(s):
    s = str(s or "").translate(ACCENTS).upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", s)).strip()


def canon_parts(raw):
    """raw libelle BAN -> (num+bis, NAT, NOM canonise). Reproduit la
    logique make_light._canon_parts en plus tolerant (gere libelle ban
    avec ' 75007 Paris' suffixe)."""
    s = _txt(raw)
    if not s:
        return "", "", ""
    toks = s.split()
    num, bis = "", ""
    if toks and toks[0][0].isdigit():
        m = re.match(r"(\d+)([A-Z]+)?$", toks[0])
        if m:
            num = str(int(m.group(1)))
            glued = m.group(2) or ""
            toks = toks[1:]
            if glued:
                if glued in BIS:
                    bis = BIS[glued]
                else:
                    toks = [glued] + toks
        else:
            mm = re.search(r"\d+", toks[0])
            num = str(int(mm.group())) if mm else ""
            toks = toks[1:]
    while toks and toks[0].isdigit():
        toks = toks[1:]
    if not bis and toks and toks[0] in BIS:
        bis = BIS[toks[0]]
        toks = toks[1:]
    nat = ""
    if toks and toks[0] in VOIE:
        nat = VOIE[toks[0]]
        toks = toks[1:]
    toks = [SAINTS.get(t, t) for t in toks]
    while len(toks) > 1 and toks[0] in ARTICLES:
        toks = toks[1:]
    out = []
    for t in toks:
        if t.isdigit() and len(t) == 5:
            break                          # postal code suffix
        if t in ("PARIS", "LYON", "MARSEILLE"):
            break
        out.append(t)
    # strip trailing 'PARIS XE ARRONDISSEMENT' etc.
    return (num + bis), nat, " ".join(out).strip()


def canon_cle(cle):
    """cle 'NUM|NAT|VOIE' -> (num, nat, voie) canonise (SAINTS +
    articles tete stripppes ; nat conserve)."""
    p = (cle or "").split("|")
    if len(p) < 3:
        return "", "", ""
    num = p[0].upper().strip()
    nat = p[1].upper().strip()
    toks = _txt(p[2]).split()
    toks = [SAINTS.get(t, t) for t in toks]
    while len(toks) > 1 and toks[0] in ARTICLES:
        toks = toks[1:]
    return num, nat, " ".join(toks).strip()


def voie_with_subs(voie):
    """applique SUBS (token a token) sur la voie canonique."""
    out = []
    for t in voie.split():
        if t in SUBS:
            # forme la plus longue (deterministe)
            out.append(t if len(t) > len(SUBS[t]) else SUBS[t])
        else:
            out.append(t)
    return " ".join(out)


def get_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(
                urllib.parse.quote(url, safe=":/?=&,()-."),
                headers={"User-Agent": "dpe-pivot/1.0",
                         "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:               # noqa: BLE001
            if i == retries - 1:
                return None
            time.sleep(1.0 * (i + 1))
    return None


def bdnb_addresses(bgids, cache):
    """{bgid -> {'l_libelle_adr': [...], 'l_cle_interop_adr': [...]}}
    via API BDNB par lots de 10 ; cache utilise et peuple."""
    todo = [b for b in dict.fromkeys(bgids) if b and b not in cache]
    n_calls = 0
    for i in range(0, len(todo), 10):
        batch = todo[i:i + 10]
        url = BDNB_URL + "(" + ",".join(batch) + ")"
        d = get_json(url)
        n_calls += 1
        seen = set()
        if isinstance(d, list):
            for o in d:
                bg = o.get("batiment_groupe_id")
                if bg:
                    cache[bg] = {
                        "l_libelle_adr": o.get("l_libelle_adr") or [],
                        "l_cle_interop_adr":
                            o.get("l_cle_interop_adr") or [],
                        "principal":
                            o.get("libelle_adr_principale_ban"),
                        "nb_valid": o.get("nb_adresse_valid_ban"),
                    }
                    seen.add(bg)
        for bg in batch:
            if bg not in seen:
                cache[bg] = {"l_libelle_adr": [],
                             "l_cle_interop_adr": [],
                             "principal": None, "nb_valid": 0}
        time.sleep(0.1)
    return n_calls


def collect(light):
    ad, co = light["adresses"], light["coproprietes"]
    by_cle = {a["cle"]: a for a in ad}
    cbc = {c["cle_adresse"]: c for c in co if c.get("cle_adresse")}
    fused = {a["cle"] for a in ad
             if a.get("_fusion_auto") and a.get("_fusion_cible")}
    targets = [a for a in ad
               if a["cle"] not in fused
               and a["cle"] not in cbc
               and not a.get("numero_immatriculation")
               and (a.get("nb_ventes_logement") or 0) > 0]
    # cop_idx : double-cle (num,nat,voie) ET (num,nat,voie_subs)
    cop_idx = collections.defaultdict(list)
    for c in co:
        ca = c.get("cle_adresse")
        if not ca:
            continue
        n, nat, voie = canon_cle(ca)
        cop_idx[(n, nat, voie)].append(c)
        vs = voie_with_subs(voie)
        if vs != voie:
            cop_idx[(n, nat, vs)].append(c)
    return ad, co, by_cle, cbc, fused, targets, cop_idx


def analyze(light, secteur, cache):
    ad, co, by_cle, cbc, fused, targets, cop_idx = collect(light)
    bgids = [a.get("batiment_groupe_id") for a in targets
             if a.get("batiment_groupe_id")]
    n_calls = bdnb_addresses(bgids, cache)
    results = []
    skipped = []                              # (orph, anchor, raison)
    for a in targets:
        cle = a["cle"]
        bg = a.get("batiment_groupe_id")
        entry = cache.get(bg, {}) or {}
        pivots = entry.get("l_libelle_adr") or []
        nb_valid = entry.get("nb_valid")
        own_canon = canon_cle(cle)
        own_subs = (own_canon[0], own_canon[1],
                    voie_with_subs(own_canon[2]))
        matches = []
        seen_anchors = set()
        for piv in pivots:
            pc = canon_parts(piv)
            if pc == own_canon or pc == own_subs:
                continue
            if not pc[2]:
                continue
            pc_subs = (pc[0], pc[1], voie_with_subs(pc[2]))
            for key in (pc, pc_subs):
                for c in cop_idx.get(key, []):
                    cle_anc = c.get("cle_adresse")
                    immat = c.get("numero_immatriculation")
                    if (cle_anc, immat) in seen_anchors:
                        continue
                    seen_anchors.add((cle_anc, immat))
                    # skip-list : (secteur, orph, ancre) instruites
                    sk = SKIP_PAIRS.get((secteur, cle, cle_anc))
                    if sk:
                        skipped.append({
                            "orph": cle, "anchor": cle_anc,
                            "immat": immat,
                            "vlog": a.get("nb_ventes_logement") or 0,
                            "date": sk[0], "commit": sk[1],
                            "raison": sk[2]})
                        continue
                    anc_obj = by_cle.get(cle_anc)
                    same_bg = (anc_obj
                               and anc_obj.get("batiment_groupe_id")
                               == bg)
                    anc_visible = (cle_anc in by_cle
                                   and cle_anc not in fused)
                    matches.append({
                        "pivot_libelle": piv,
                        "pivot_canon": pc,
                        "anchor_cle": cle_anc,
                        "anchor_bg": anc_obj
                        and anc_obj.get("batiment_groupe_id"),
                        "immat": immat,
                        "nom": c.get("nom_copropriete"),
                        "lots": c.get("nb_lots_habitation"),
                        "syndic": c.get("syndic"),
                        "same_bg": bool(same_bg),
                        "anc_visible": bool(anc_visible),
                        "via_subs": key != pc,
                    })
        if matches:
            results.append({
                "secteur": secteur, "cle": cle,
                "adresse": a.get("adresse"), "bg": bg,
                "vlog": a.get("nb_ventes_logement") or 0,
                "vtot": a.get("nb_ventes_total") or 0,
                "nblog": a.get("nb_log_bdnb"),
                "usage": a.get("usage_principal_bdnb"),
                "n_pivots": len(pivots),
                "nb_valid_ban": nb_valid,
                "matches": matches,
            })
    return results, len(targets), n_calls, skipped


def main():
    cache = (json.loads(CACHE.read_text(encoding="utf-8"))
             if CACHE.exists() else {})
    light_dl = json.loads(LIGHT_DL.read_text(encoding="utf-8"))
    light_mp = json.loads(LIGHT_MP.read_text(encoding="utf-8"))
    res_dl, nt_dl, nc_dl, sk_dl = analyze(
        light_dl, "dauphine_lacassagne", cache)
    res_mp, nt_mp, nc_mp, sk_mp = analyze(
        light_mp, "motte_picquet", cache)
    skipped = [("dauphine_lacassagne", s) for s in sk_dl] \
        + [("motte_picquet", s) for s in sk_mp]
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    rows = res_dl + res_mp

    def esc(s):
        return str(s).replace("|", "\\|") if s is not None else ""

    by_class = collections.Counter()
    for r in rows:
        m = r["matches"][0]
        by_class["parc-neutre (meme bgid)"
                 if m["same_bg"]
                 else "miroir (Acollas-type, bgid distinct)"] += 1
    n_via_subs = sum(1 for r in rows
                     for m in r["matches"] if m["via_subs"])
    n_anc_visible = sum(1 for r in rows
                        for m in r["matches"] if m["anc_visible"])

    L = []
    L.append("# Audit - pipeline RNC via pivot BDNB multi-adresses\n")
    L.append("> **Lecture seule.** Aucun fichier de donnees du light "
             "modifie. Cache `data/_pivot_bdnb_cache.json` peuple en "
             "ecriture (artefact derive, idempotent).\n")
    L.append("## Concept\n"
             "Pour chaque adresse **hors-RNC active** (predicat exact "
             "renderSecteur : `!fused & cle != cle_adresse copro & "
             "!numero_immatriculation & nb_ventes_logement>0`), on "
             "interroge l'API BDNB "
             "`batiment_groupe_complet?select=l_libelle_adr,"
             "l_cle_interop_adr&batiment_groupe_id=in.(...)` sur le "
             "`batiment_groupe_id` BDNB. Toutes les adresses BAN "
             "attachees au meme bati-groupe deviennent **pivots** : "
             "pour chacune, on canonise (regles `_canon_parts` "
             "make_light + SUBS GAL/CAPT/AYRES bidirectionnelles) et "
             "on cherche un match dans `coproprietes[].cle_adresse` "
             "du snapshot secteur. Si match -> candidat rattachement.\n")
    L.append("## Bilan\n")
    L.append("| secteur | hr-actives | matches pivot | "
             "skip-list | appels BDNB |\n|---|--:|--:|--:|--:|")
    L.append(f"| dauphine_lacassagne | {nt_dl} | "
             f"**{len(res_dl)}** | {len(sk_dl)} | {nc_dl} |")
    L.append(f"| motte_picquet | {nt_mp} | **{len(res_mp)}** | "
             f"{len(sk_mp)} | {nc_mp} |")
    L.append(f"| **total** | **{nt_dl+nt_mp}** | "
             f"**{len(rows)}** | **{len(skipped)}** | "
             f"{nc_dl+nc_mp} |\n")
    if rows:
        L.append("**Classification** : " + ", ".join(
            f"{k}={v}" for k, v in sorted(by_class.items())) + ".\n")
        L.append(f"**Apport** : {n_via_subs} match(es) trouve(s) "
                 "GRACE A SUBS (auraient ete rates sans). "
                 f"{n_anc_visible} ancre(s) deja visible(s) en pipe "
                 "(collision potentielle a verifier).\n")

    L.append("## Matches par adresse\n")
    if not rows:
        L.append("_Aucun match pivot trouve._\n")
    else:
        L.append("| secteur | cle hors-RNC | v_log | bgid | "
                 "adresse pivot BDNB | -> copro ancre | immat | "
                 "lots | syndic | type | collision |")
        L.append("|---|---|--:|---|---|---|---|--:|---|---|---|")
        for r in sorted(rows,
                        key=lambda x: (x["secteur"], -x["vlog"])):
            for m in r["matches"]:
                t = ("parc-neutre" if m["same_bg"]
                     else "miroir (Acollas-type)")
                if m["via_subs"]:
                    t += " [SUBS]"
                coll = "DEJA VISIBLE" if m["anc_visible"] else "-"
                L.append(
                    f"| {r['secteur'][:5]} | "
                    f"`{esc(r['cle'])}` | {r['vlog']} | "
                    f"`...{(r['bg'] or '')[-12:]}` | "
                    f"{esc(m['pivot_libelle'])[:46]} | "
                    f"`{esc(m['anchor_cle'])}` | {m['immat']} | "
                    f"{m['lots']} | "
                    f"{(m['syndic'] or '-')[:18]} | {t} | {coll} |")

    if skipped:
        L.append("\n## Cas skippes (skip-list documentee)\n")
        L.append("Paires (orph, ancre) instruites individuellement et "
                 "exclues du flux actionnable. Le pivot continue de "
                 "les detecter (le bgid light n'a pas change) mais ne "
                 "les remonte plus comme \"matches\".\n")
        L.append("| secteur | orph | -> ancre | immat | v_log | "
                 "instruit le | commit | raison |")
        L.append("|---|---|---|---|--:|---|---|---|")
        for sec, s in skipped:
            L.append(
                f"| {sec[:5]} | `{esc(s['orph'])}` | "
                f"`{esc(s['anchor'])}` | {s['immat']} | "
                f"{s['vlog']} | {s['date']} | `{s['commit']}` | "
                f"{s['raison'][:90]}... |")

    L.append("\n## Top 10 par ventes-logement relocalisables\n")
    if rows:
        L.append("| secteur | cle hors-RNC | v_log | v_tot | "
                 "-> copro candidate | immat | lots |")
        L.append("|---|---|--:|--:|---|---|--:|")
        for r in sorted(rows, key=lambda x: -x["vlog"])[:10]:
            m = r["matches"][0]
            L.append(
                f"| {r['secteur'][:5]} | `{esc(r['cle'])}` | "
                f"{r['vlog']} | {r['vtot']} | "
                f"{esc(m['pivot_libelle'])[:30]} -> "
                f"`{esc(m['anchor_cle'])}` | "
                f"{m['immat']} | {m['lots']} |")
    else:
        L.append("_(aucun)_\n")

    L.append("\n## Cas qui auraient ete rates sans pivot BDNB\n")
    L.append("Pipeline existant `make_light` : "
             "(1) jointure RNC->copro `copro_by_cle` exacte / "
             "ALIAS_RNC manuel ; (2) BDNB num+voie ; (3) GPS<50m "
             "(palier faible). Puis fusion-bgid stricte (parite "
             "homogene). **Aucun de ces paliers n'expose les autres "
             "adresses BAN du meme batiment** : si la copro RNC est "
             "ancree sur une voie/numero qui ne figure pas dans la "
             "cle DVF d'origine, le pipeline ne peut pas la trouver "
             "(c'est exactement la classe de cas A2/A3 et Acollas "
             "documentee dans `fix_mp_cibles_horsrnc.py`, instruite "
             "individuellement jusqu'a present).\n")
    L.append(f"Le pivot BDNB ouvre un NOUVEAU vecteur systematique : "
             f"il revele **{len(rows)} orpheline(s) DVF** "
             "rattachable(s) sans intervention manuelle au-dela de "
             "l'API. Sans ce pipeline, ces cas seraient laisses en "
             "categorie B faute de pouvoir etre detectes par "
             "cle/bgid stricte.\n")
    if n_anc_visible:
        L.append(f"\n**Attention** : {n_anc_visible} ancre(s) sont "
                 "**deja visibles** dans le rendu actuel (ont une "
                 "cle_adresse non fusee). Verifier avant tout fix : "
                 "une fusion supplementaire pourrait creer un "
                 "double-rendu ou un changement de principal "
                 "indesirable (cf. PIPELINE Sec 6).\n")

    L.append("\n## Methodologie + limites\n"
             "- API BDNB `api.bdnb.io/v1/bdnb/donnees/"
             "batiment_groupe_complet` (`select=l_libelle_adr,"
             "l_cle_interop_adr,libelle_adr_principale_ban,"
             "nb_adresse_valid_ban&batiment_groupe_id=in.(...)`), "
             "lots de 10, throttling 0.1s.\n"
             "- Cache `data/_pivot_bdnb_cache.json` (artefact "
             "derive, peut etre supprime).\n"
             "- Matching snapshot uniquement (pas de RNC live ici, "
             "rapide). Une 2e passe RNC live "
             "(`tabular-api 3ea8e2c3...`) sur les pivots sans "
             "match snapshot peut completer (cf. "
             "`audit_horsrnc_dvf.py` etape d).\n"
             "- Limites : (1) la canonisation des pivots reproduit "
             "make_light + SUBS minimaliste ; (2) un pivot peut "
             "matcher une copro qui n'est PAS sur le meme bgid -> "
             "miroir Acollas-type, ventes relocalisees mais BDNB "
             "buckets dedupliques (a verifier parc cas par cas, "
             "cf. PIPELINE Sec 6, fix_acollas_range / "
             "fix_mp_voie_abrev) ; (3) les ancres deja visibles "
             "doivent etre instruites RE-POINT (pattern A3 / "
             "fix_repoint_p2a) plutot que ALIAS.\n")

    L.append("\n---\n*`scripts/pipeline_bdnb_pivot.py` - dry-run "
             "uniquement. Aucune modification des fichiers du "
             "light. Cache + rapport seuls ecrits.*")

    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"DL: {nt_dl} hr-actives -> {len(res_dl)} matches pivot "
          f"({len(sk_dl)} skipped, {nc_dl} appels BDNB)")
    print(f"MP: {nt_mp} hr-actives -> {len(res_mp)} matches pivot "
          f"({len(sk_mp)} skipped, {nc_mp} appels BDNB)")
    print(f"total: {len(rows)} matches actionnables "
          f"({n_via_subs} via SUBS, {n_anc_visible} ancres visibles, "
          f"{len(skipped)} skipped)")
    print(f"cache: {CACHE.name} ({len(cache)} bgids)")
    print(f"rapport: {REPORT.name}")


if __name__ == "__main__":
    main()
