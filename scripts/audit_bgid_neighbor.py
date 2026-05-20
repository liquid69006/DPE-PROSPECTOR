"""
audit_bgid_neighbor.py — Audit lecture seule du bug "wrong bgid
voisin assigne par num_voie/gps BDNB" (cf. cas 23/25/27 FREMICOURT).

Cause-racine investiguee : make_light fait un fallback en 3 paliers
pour la jointure BDNB (cf. PIPELINE Sec 4). Les paliers faibles
`num_voie` (BDNB par voie/numero approxime) et `gps` (< 50 m)
peuvent assigner a une adresse impaire (ex. 23 FREMICOURT) le bgid
du voisin pair (ex. bgid de 22 FREMICOURT = autre copro distincte)
parce que BDNB indexe le bati sous l'adresse paire principale.

Resultat : le pipeline pivot (forward) cherche la copro via ce
mauvais bgid -> rate l'identification. La passe reverse passe car
elle iter depuis la copro -> bgid copro -> pivots BAN -> match
hr-actives, MAIS uniquement si le bgid de la copro est dans le
cache au moment du scan (couvert pour les copros visibles).

ETAPE 1 : Pour chaque adresse hors-RNC avec `_bdnb_match in
('gps','num_voie')`, interroger BDNB sur le bgid light, recuperer
`l_libelle_adr`, canoniser, et verifier si l'adresse cle figure
parmi les pivots. Si NON -> wrong bgid.

ETAPE 2 : Pour chaque wrong-bgid case avec vlog>0, chercher le
TRUE bgid (via le cache reverse-lookup OU via BAN + BDNB rel),
puis verifier si ce TRUE bgid heberge une copro RNC connue (snapshot
secteur).

ETAPE 3 : Recommandations (cf. rapport).

Lecture seule. Cache `data/_pivot_bdnb_cache.json` peuple en ecriture
(artefact derive, partage avec les autres pipelines). Sortie :
`data/audit_bgid_neighbor.md`.

Usage :
  python scripts/audit_bgid_neighbor.py
"""

import sys
import json
import time
import collections
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_bdnb_pivot import (   # noqa: E402
    canon_parts, canon_cle, voie_with_subs,
    bdnb_addresses, CACHE, LIGHT_DL, LIGHT_MP, get_json,
)

REPORT = ROOT / "data" / "audit_bgid_neighbor.md"


def ban_search(q):
    """BAN search: q -> cle_interop_adr (or None)."""
    u = ('https://api-adresse.data.gouv.fr/search/?'
         + urllib.parse.urlencode({'q': q, 'limit': 1}))
    d = get_json(u)
    if isinstance(d, dict):
        feats = d.get('features') or []
        if feats:
            return feats[0].get('properties', {}).get('id')
    return None


def bdnb_rel_addr_to_bgid(cle_ban):
    """rel_batiment_groupe_adresse : cle_ban -> bgid (premier hit)."""
    url = ('https://api.bdnb.io/v1/bdnb/donnees/'
           'rel_batiment_groupe_adresse?cle_interop_adr=eq.'
           + cle_ban
           + '&select=batiment_groupe_id,fiabilite&limit=3')
    d = get_json(url)
    if isinstance(d, list) and d:
        return d[0].get('batiment_groupe_id')
    return None


def cle_to_query(cle, cp_hint):
    """cle 'NUM[BIS]|TYPE|VOIE' -> query BAN lisible."""
    p = (cle or '').split('|')
    if len(p) < 3:
        return None
    num, typ, nom = p[0], p[1], p[2]
    return ' '.join(x for x in [num, typ, nom, cp_hint] if x).strip()


def main():
    cache = (json.loads(CACHE.read_text(encoding="utf-8"))
             if CACHE.exists() else {})
    light_dl = json.loads(LIGHT_DL.read_text(encoding="utf-8"))
    light_mp = json.loads(LIGHT_MP.read_text(encoding="utf-8"))

    # 1. Pre-fetch missing bgids for hors-RNC + weak match
    all_results = []                          # rows pour le rapport
    by_sec = {}                               # secteur -> details

    for secteur, light, cp_hint in [
            ('dauphine_lacassagne', light_dl, '69003 Lyon'),
            ('motte_picquet', light_mp, '75015 Paris')]:
        ad = light["adresses"]
        co = light["coproprietes"]
        by_cle = {a["cle"]: a for a in ad}
        cbc = {c["cle_adresse"]: c for c in co if c.get("cle_adresse")}
        fused = {a["cle"] for a in ad
                 if a.get("_fusion_auto") and a.get("_fusion_cible")}
        # copro_by_bgid : pour verifier si le TRUE bgid heberge une copro
        copro_by_bgid = collections.defaultdict(list)
        for c in co:
            ca = c.get("cle_adresse")
            if ca and ca in by_cle and by_cle[ca].get("batiment_groupe_id"):
                copro_by_bgid[by_cle[ca]["batiment_groupe_id"]].append(c)
        # candidates : hors-RNC + weak match + bgid present
        candidates = []
        for a in ad:
            if a.get("numero_immatriculation"):
                continue
            if a["cle"] in cbc:
                continue
            if a.get("_bdnb_match") not in ("num_voie", "gps"):
                continue
            if not a.get("batiment_groupe_id"):
                continue
            candidates.append(a)
        # pre-fetch missing bgids
        bgids = [a["batiment_groupe_id"] for a in candidates]
        missing = [b for b in dict.fromkeys(bgids) if b not in cache]
        print(f"=== {secteur} : {len(candidates)} candidates "
              f"(hors-RNC + weak match), {len(missing)} bgids a "
              "fetcher BDNB...")
        if missing:
            bdnb_addresses(missing, cache)
        # save cache after fetch
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                         encoding="utf-8")
        # reverse map : addr_canon -> [bgids cache] (BDNB authoritative)
        addr_to_bgid = collections.defaultdict(list)
        for bg, entry in cache.items():
            for piv in (entry.get('l_libelle_adr') or []):
                pc = canon_parts(piv)
                if pc[2]:
                    addr_to_bgid[pc].append(bg)
        # audit chaque candidate
        wrong = []
        correct = 0
        for a in candidates:
            cle = a["cle"]
            bg = a["batiment_groupe_id"]
            entry = cache.get(bg, {}) or {}
            pivots = entry.get("l_libelle_adr") or []
            own = canon_cle(cle)
            own_subs = (own[0], own[1], voie_with_subs(own[2]))
            pivot_canons = set()
            for piv in pivots:
                pc = canon_parts(piv)
                if pc[2]:
                    pivot_canons.add(pc)
                    pcs = (pc[0], pc[1], voie_with_subs(pc[2]))
                    if pcs != pc:
                        pivot_canons.add(pcs)
            if own in pivot_canons or own_subs in pivot_canons:
                correct += 1
                continue
            # WRONG bgid : chercher le TRUE bgid
            true_bgids = addr_to_bgid.get(own, []) \
                or addr_to_bgid.get(own_subs, [])
            # filtrer : exclure le wrong bgid lui-meme (on cherche un autre)
            true_bgids = [b for b in true_bgids if b != bg]
            wrong.append({
                "secteur": secteur, "cle": cle, "bg_light": bg,
                "vlog": a.get("nb_ventes_logement") or 0,
                "vtot": a.get("nb_ventes_total") or 0,
                "nblog_bdnb": a.get("nb_log_bdnb"),
                "usage": a.get("usage_principal_bdnb"),
                "match": a.get("_bdnb_match"),
                "fused": a["cle"] in fused,
                "fcible": a.get("_fusion_cible"),
                "pivots_bg_light": pivots,
                "true_bgids_cache": true_bgids,
                "true_bgid": None, "true_via": None,
                "copro_at_true": None,
            })
        # Pour les wrong + vlog>0 sans true_bgid en cache, query BAN+BDNB rel
        to_query = [w for w in wrong
                    if w["vlog"] > 0 and not w["true_bgids_cache"]]
        print(f"  {len(wrong)} wrong-bgid ({correct} correct), "
              f"{len(to_query)} a investiguer via BAN+BDNB rel...")
        for w in to_query:
            q = cle_to_query(w["cle"], cp_hint)
            ban_id = ban_search(q) if q else None
            time.sleep(0.1)
            if not ban_id:
                continue
            tb = bdnb_rel_addr_to_bgid(ban_id)
            time.sleep(0.1)
            if tb and tb != w["bg_light"]:
                w["true_bgid"] = tb
                w["true_via"] = "BAN+BDNB rel"
        # Aussi pour wrong avec true_bgids_cache, choisir le 1er
        for w in wrong:
            if w["true_bgid"] is None and w["true_bgids_cache"]:
                w["true_bgid"] = w["true_bgids_cache"][0]
                w["true_via"] = "cache reverse-lookup"
            # check copro at true_bgid
            if w["true_bgid"]:
                cops = copro_by_bgid.get(w["true_bgid"], [])
                if cops:
                    c = cops[0]
                    w["copro_at_true"] = {
                        "cle_adresse": c.get("cle_adresse"),
                        "immat": c.get("numero_immatriculation"),
                        "lots": c.get("nb_lots_habitation"),
                        "nom": c.get("nom_copropriete"),
                    }
        by_sec[secteur] = {"candidates": len(candidates),
                           "correct": correct, "wrong": wrong}
        all_results.extend(wrong)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                         encoding="utf-8")

    # bilan
    def esc(s):
        return str(s).replace("|", "\\|") if s is not None else ""

    L = []
    L.append("# Audit - bug \"wrong bgid voisin\" "
             "(make_light num_voie/gps)\n")
    L.append("> Lecture seule. Cache `data/_pivot_bdnb_cache.json` "
             "peuple. Aucune modification des donnees light.\n")
    L.append("## Cause-racine\n"
             "make_light fait la jointure BDNB en 3 paliers (PIPELINE "
             "Sec 4) : (1) `immat` via copro RNC, (2) `num_voie` BDNB "
             "(par voie/numero approxime), (3) `gps` (<50m). Les "
             "paliers 2 et 3 peuvent assigner a une adresse impaire "
             "(ex. 23 FREMICOURT) le bgid du voisin pair (ex. bgid "
             "de 22 FREMICOURT = autre copro distincte) parce que "
             "BDNB indexe le bati sous l'adresse paire principale. "
             "Le pipeline pivot forward cherche ensuite la copro via "
             "ce mauvais bgid -> rate. La passe reverse couvre la "
             "plupart de ces cas via copro -> bgid -> pivots BAN.\n")
    L.append("## Bilan par secteur\n")
    L.append("| secteur | candidates (hors-RNC + weak match) | "
             "correct | **wrong** | wrong+vlog>0 | "
             "actionable (vrai bgid avec copro RNC) |")
    L.append("|---|--:|--:|--:|--:|--:|")
    for sec, info in by_sec.items():
        wrong = info["wrong"]
        wrong_vlog = [w for w in wrong if w["vlog"] > 0
                      and not w["fused"]]
        actionable = [w for w in wrong_vlog if w["copro_at_true"]]
        L.append(
            f"| {sec} | {info['candidates']} | {info['correct']} | "
            f"**{len(wrong)}** | {len(wrong_vlog)} | "
            f"**{len(actionable)}** |")
    L.append("")

    # actionable cases (par secteur)
    L.append("## Cas ACTIONNABLES (wrong bgid + vlog>0 + true bgid "
             "heberge copro RNC connue, non encore fuses)\n")
    n_act = 0
    for sec, info in by_sec.items():
        actionable = [w for w in info["wrong"]
                      if w["vlog"] > 0 and not w["fused"]
                      and w["copro_at_true"]]
        if not actionable:
            L.append(f"### {sec} : aucun cas\n")
            continue
        L.append(f"### {sec} : {len(actionable)} cas\n")
        L.append("| cle hors-RNC | v_log | bgid light | TRUE bgid | "
                 "TRUE copro (cle_adresse) | immat | lots | nom | "
                 "via |")
        L.append("|---|--:|---|---|---|---|--:|---|---|")
        for w in sorted(actionable, key=lambda x: -x["vlog"]):
            c = w["copro_at_true"]
            L.append(
                f"| `{esc(w['cle'])}` | {w['vlog']} | "
                f"`...{w['bg_light'][-12:]}` | "
                f"`...{w['true_bgid'][-12:]}` | "
                f"`{esc(c['cle_adresse'])}` | {c['immat']} | "
                f"{c['lots']} | {(c['nom'] or '-')[:32]} | "
                f"{w['true_via']} |")
        n_act += len(actionable)
        L.append("")

    # wrong sans copro actionnable (cf. 18 ST ANTOINE = mono / non immat)
    L.append("## Cas wrong-bgid + vlog>0 SANS copro actionnable (vraie "
             "monopropriete / non immat)\n")
    for sec, info in by_sec.items():
        sub = [w for w in info["wrong"]
               if w["vlog"] > 0 and not w["fused"]
               and not w["copro_at_true"]]
        if not sub:
            continue
        L.append(f"### {sec} : {len(sub)} cas (residuels cat. B)\n")
        L.append("| cle hors-RNC | v_log | bgid light | TRUE bgid | "
                 "match |")
        L.append("|---|--:|---|---|---|")
        for w in sorted(sub, key=lambda x: -x["vlog"])[:15]:
            tb = f"`...{w['true_bgid'][-12:]}`" if w['true_bgid'] \
                else "(introuvable BAN)"
            L.append(
                f"| `{esc(w['cle'])}` | {w['vlog']} | "
                f"`...{w['bg_light'][-12:]}` | {tb} | {w['match']} |")
        L.append("")

    L.append("## ETAPE 3 - Recommandations\n")
    L.append(
        "**(a) Correction amont make_light (regen requise, RISQUE)** : "
        "modifier le palier `num_voie`/`gps` pour valider que l'adresse "
        "figure dans `l_libelle_adr` du bgid BDNB candidat. Si non, "
        "tenter via `rel_batiment_groupe_adresse` (BAN cle_interop -> "
        "bgid authoritative). Cout : +N appels API par regen, mais "
        "regen INTERDITE en l'etat (PIPELINE Sec 3) -> il faudrait "
        "rejouer toute la chaine `fix_*` apres regen. **A eviter**.\n\n"
        "**(b) Correction aval pipeline reverse (DEJA EN PLACE, "
        "extension possible)** : le `pipeline_bdnb_pivot_reverse.py` "
        "iter depuis chaque copro RNC -> bgid copro -> pivots BAN -> "
        "match hr-active. Couvre par construction le cas \"wrong bgid "
        "+ true bgid heberge copro\" (le match utilise la canonique "
        "BAN, pas le bgid light). **Si des cas restent en wrong-bgid "
        "actionnables ICI, c'est que la reverse a rate par "
        "bgid-non-cache au moment du run -> re-executer "
        "`pipeline_bdnb_pivot_reverse.py`**, le cache est desormais "
        "etendu par cet audit (toutes les bgids hors-RNC weak indexees "
        "BDNB).\n\n"
        "**(c) Correction des bgids errones eux-memes (CHIRURGICAL, "
        "RECOMMANDE pour les cas isoles)** : pour les wrong-bgid sans "
        "copro actionnable mais ou le TRUE bgid est connu, le bgid "
        "peut etre corrige par adoption MIRROR du true bgid via un "
        "fix dedie. **Risque : changer le bgid peut deplacer la "
        "contribution parc**. Mesurer parc_model avant. **A "
        "instruire individuellement** pour cas a haut impact.\n\n"
        "**Conclusion** : (b) est la voie deja consacree. Cet audit "
        "vient enrichir le cache et identifier explicitement les "
        "actionnables restants -> les appliquer via le mecanisme "
        "miroir-bgid existant (cf. fix_pivot_bdnb_reverse_lot) si "
        "non couverts.\n")

    L.append("---\n*`scripts/audit_bgid_neighbor.py` - lecture seule. "
             "Cache + rapport seuls ecrits.*")

    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"\nTotal wrong bgids : {sum(len(s['wrong']) for s in by_sec.values())}")
    print(f"Total actionable cases : {n_act}")
    print(f"cache: {CACHE.name} ({len(cache)} bgids)")
    print(f"rapport: {REPORT.name}")


if __name__ == "__main__":
    main()
