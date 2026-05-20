"""
pipeline_bdnb_pivot_reverse.py — Passe INVERSE du pivot BDNB.

Direction inverse de scripts/pipeline_bdnb_pivot.py :
  - Forward : orph hr-active -> son bgid -> BDNB l_libelle_adr ->
              match cle_adresse copro.
  - Reverse : copro RNC visible -> son bgid (via cle_adresse) -> BDNB
              l_libelle_adr -> match parmi les adresses hr-actives.

Pourquoi : la forward rate les cas P2c (parite mixte d'angle) ou
l'orpheline DVF est sur un bgid different du principal mais BDNB
groupe les deux. Si le bgid principal est celui de la copro RNC,
chercher depuis la copro permet de remonter aux orphelines.

FILTRES :
  - copro c : cle_adresse presente dans le light, non fusee (visible
    comme principal), porte un numero_immatriculation
  - orph candidate : cle hors-RNC active du light (predicat exact
    renderSecteur : !fused, cle ∉ cle_adresse copro, !immat,
    nb_ventes_logement>0)
  - skip-list (SKIP_PAIRS herite de pipeline_bdnb_pivot)
  - normalisation : canon_parts + SUBS bidirectionnels herites
  - collision : si plusieurs copros sur le meme bgid -> flag

Cache `data/_pivot_bdnb_cache.json` partage avec la passe forward
(idempotent). Sortie : `data/audit_pivot_bdnb_reverse.md`. Lecture
seule, aucune modification des donnees.

Usage :
  python scripts/pipeline_bdnb_pivot_reverse.py
"""

import sys
import json
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
# Reuse helpers from forward pipeline (canon_parts, canon_cle,
# voie_with_subs, bdnb_addresses, SUBS, SKIP_PAIRS, CACHE paths).
from pipeline_bdnb_pivot import (   # noqa: E402
    canon_parts, canon_cle, voie_with_subs,
    bdnb_addresses, CACHE, LIGHT_DL, LIGHT_MP, SKIP_PAIRS,
)

REPORT = ROOT / "data" / "audit_pivot_bdnb_reverse.md"


def collect_reverse(light):
    """Renvoie : copros scannables (visibles, immat, bgid valide) +
    hr_idx (cle canonique -> [hr_active_cle]) + sets/maps utiles."""
    ad, co = light["adresses"], light["coproprietes"]
    by_cle = {a["cle"]: a for a in ad}
    cbc = {c["cle_adresse"]: c for c in co if c.get("cle_adresse")}
    fused = {a["cle"] for a in ad
             if a.get("_fusion_auto") and a.get("_fusion_cible")}

    # hr-actives index (cle canon + variantes SUBS)
    hr_idx = collections.defaultdict(list)
    hr_actives = []
    for a in ad:
        cle = a["cle"]
        if cle in fused:
            continue
        if cle in cbc:
            continue
        if a.get("numero_immatriculation"):
            continue
        if (a.get("nb_ventes_logement") or 0) <= 0:
            continue
        n, nat, voie = canon_cle(cle)
        hr_idx[(n, nat, voie)].append(cle)
        vs = voie_with_subs(voie)
        if vs != voie:
            hr_idx[(n, nat, vs)].append(cle)
        hr_actives.append(cle)

    # copros scannables
    copros_scan = []
    for c in co:
        anc = c.get("cle_adresse")
        immat = c.get("numero_immatriculation")
        if not anc or not immat:
            continue
        anc_obj = by_cle.get(anc)
        if anc_obj is None:
            continue
        if anc_obj.get("_fusion_auto") and anc_obj.get("_fusion_cible"):
            # ancre elle-meme fusionnee -> non principale, on saute
            continue
        bg = anc_obj.get("batiment_groupe_id")
        if not bg:
            continue
        copros_scan.append((c, anc_obj, bg))

    # collision : copros multiples par bgid
    bg_to_copros = collections.defaultdict(list)
    for c, anc_obj, bg in copros_scan:
        bg_to_copros[bg].append(c)

    return (ad, co, by_cle, cbc, fused, hr_idx, hr_actives,
            copros_scan, bg_to_copros)


def analyze_reverse(light, secteur, cache):
    (ad, co, by_cle, cbc, fused, hr_idx, hr_actives,
     copros_scan, bg_to_copros) = collect_reverse(light)

    # pre-fetch BDNB pour tous les bgids des copros scannables
    bgids = [bg for _, _, bg in copros_scan]
    n_calls = bdnb_addresses(bgids, cache)

    results = []
    skipped = []
    seen_pairs = set()      # (orph_cle, anchor_cle) dedup

    for c, anc_obj, bg in copros_scan:
        anc = c["cle_adresse"]
        immat = c["numero_immatriculation"]
        own_canon = canon_cle(anc)
        own_subs = (own_canon[0], own_canon[1],
                    voie_with_subs(own_canon[2]))
        entry = cache.get(bg, {}) or {}
        pivots = entry.get("l_libelle_adr") or []
        n_other_copros = len(bg_to_copros[bg]) - 1

        for piv in pivots:
            pc = canon_parts(piv)
            if pc == own_canon or pc == own_subs:
                continue
            if not pc[2]:
                continue
            pc_subs = (pc[0], pc[1], voie_with_subs(pc[2]))
            for key in (pc, pc_subs):
                for orph_cle in hr_idx.get(key, []):
                    if (orph_cle, anc) in seen_pairs:
                        continue
                    seen_pairs.add((orph_cle, anc))
                    sk = SKIP_PAIRS.get((secteur, orph_cle, anc))
                    if sk:
                        a = by_cle[orph_cle]
                        skipped.append({
                            "orph": orph_cle, "anchor": anc,
                            "immat": immat,
                            "vlog": a.get("nb_ventes_logement") or 0,
                            "date": sk[0], "commit": sk[1],
                            "raison": sk[2]})
                        continue
                    a = by_cle[orph_cle]
                    same_bg = a.get("batiment_groupe_id") == bg
                    via_subs = (key != pc)
                    results.append({
                        "secteur": secteur,
                        "orph": orph_cle,
                        "orph_bg": a.get("batiment_groupe_id"),
                        "orph_vlog": a.get("nb_ventes_logement") or 0,
                        "orph_vtot": a.get("nb_ventes_total") or 0,
                        "orph_usage": a.get("usage_principal_bdnb"),
                        "anchor": anc, "anchor_bg": bg,
                        "immat": immat,
                        "nom": c.get("nom_copropriete"),
                        "lots": c.get("nb_lots_habitation"),
                        "syndic": c.get("syndic"),
                        "pivot_libelle": piv,
                        "same_bg": bool(same_bg),
                        "via_subs": via_subs,
                        "n_other_copros_bgid": n_other_copros,
                    })
    return results, n_calls, skipped, len(hr_actives), len(copros_scan)


def main():
    cache = (json.loads(CACHE.read_text(encoding="utf-8"))
             if CACHE.exists() else {})
    light_dl = json.loads(LIGHT_DL.read_text(encoding="utf-8"))
    light_mp = json.loads(LIGHT_MP.read_text(encoding="utf-8"))
    res_dl, nc_dl, sk_dl, na_dl, nco_dl = analyze_reverse(
        light_dl, "dauphine_lacassagne", cache)
    res_mp, nc_mp, sk_mp, na_mp, nco_mp = analyze_reverse(
        light_mp, "motte_picquet", cache)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    rows = res_dl + res_mp
    skipped = [("dauphine_lacassagne", s) for s in sk_dl] \
        + [("motte_picquet", s) for s in sk_mp]

    def esc(s):
        return str(s).replace("|", "\\|") if s is not None else ""

    by_class = collections.Counter()
    for r in rows:
        by_class["parc-neutre (meme bgid)"
                 if r["same_bg"]
                 else "miroir (Acollas-type)"] += 1
    n_via_subs = sum(1 for r in rows if r["via_subs"])
    n_collisions = sum(1 for r in rows
                       if r["n_other_copros_bgid"] > 0)

    L = []
    L.append("# Audit - pipeline pivot BDNB INVERSE\n")
    L.append("> Lecture seule. Cache `data/_pivot_bdnb_cache.json` "
             "partage avec la passe forward (artefact derive).\n")
    L.append("## Concept\n"
             "Passe INVERSE du pivot : pour chaque copro RNC visible "
             "dans le snapshot (cle_adresse presente dans le light, "
             "non fusee, avec immat), on interroge l'API BDNB "
             "`batiment_groupe_complet.l_libelle_adr` sur le bgid de "
             "son adresse principale. Chaque pivot retourne est "
             "compare aux adresses hors-RNC actives (predicat exact "
             "renderSecteur). Si match -> orph rattachable a cette "
             "copro. Couvre les cas que la passe forward rate (P2c "
             "parite mixte, ancres ajoutees post-make_light).\n")
    L.append("## Bilan\n")
    L.append("| secteur | hr-actives | copros scannees | matches | "
             "skip-list | appels BDNB |\n|---|--:|--:|--:|--:|--:|")
    L.append(f"| dauphine_lacassagne | {na_dl} | {nco_dl} | "
             f"**{len(res_dl)}** | {len(sk_dl)} | {nc_dl} |")
    L.append(f"| motte_picquet | {na_mp} | {nco_mp} | "
             f"**{len(res_mp)}** | {len(sk_mp)} | {nc_mp} |")
    L.append(f"| **total** | {na_dl+na_mp} | {nco_dl+nco_mp} | "
             f"**{len(rows)}** | {len(skipped)} | {nc_dl+nc_mp} |\n")
    if rows:
        L.append("**Classification** : " + ", ".join(
            f"{k}={v}" for k, v in sorted(by_class.items())) + ".\n")
        L.append(f"**Apport** : {n_via_subs} match(es) via SUBS ; "
                 f"{n_collisions} cas avec collision (autre copro sur "
                 "meme bgid -> ambiguite a verifier).\n")

    L.append("## Matches par adresse\n")
    if not rows:
        L.append("_Aucun nouveau match trouve par la passe inverse._\n")
    else:
        L.append("| secteur | orph hors-RNC | v_log | bg orph | "
                 "<- copro ancre (visible) | immat | lots | syndic | "
                 "type | autres copros bgid |")
        L.append("|---|---|--:|---|---|---|--:|---|---|--:|")
        for r in sorted(rows,
                        key=lambda x: (x["secteur"], -x["orph_vlog"])):
            t = ("parc-neutre" if r["same_bg"]
                 else "miroir (Acollas-type)")
            if r["via_subs"]:
                t += " [SUBS]"
            L.append(
                f"| {r['secteur'][:5]} | "
                f"`{esc(r['orph'])}` | {r['orph_vlog']} | "
                f"`...{(r['orph_bg'] or '')[-12:]}` | "
                f"`{esc(r['anchor'])}` | {r['immat']} | "
                f"{r['lots']} | "
                f"{(r['syndic'] or '-')[:18]} | {t} | "
                f"{r['n_other_copros_bgid']} |")

    L.append("\n## Top 10 par ventes-logement relocalisables\n")
    if rows:
        L.append("| secteur | orph hors-RNC | v_log | v_tot | "
                 "<- copro candidate | immat | lots | nom copro |")
        L.append("|---|---|--:|--:|---|---|--:|---|")
        for r in sorted(rows, key=lambda x: -x["orph_vlog"])[:10]:
            L.append(
                f"| {r['secteur'][:5]} | `{esc(r['orph'])}` | "
                f"{r['orph_vlog']} | {r['orph_vtot']} | "
                f"`{esc(r['anchor'])}` | {r['immat']} | {r['lots']} | "
                f"{(r['nom'] or '-')[:34]} |")
    else:
        L.append("_(aucun)_\n")

    if skipped:
        L.append("\n## Cas skippes (skip-list partagee avec forward)\n")
        L.append("| secteur | orph | anchor | immat | v_log | date | "
                 "commit | raison |")
        L.append("|---|---|---|---|--:|---|---|---|")
        for sec, s in skipped:
            L.append(
                f"| {sec[:5]} | `{esc(s['orph'])}` | "
                f"`{esc(s['anchor'])}` | {s['immat']} | {s['vlog']} "
                f"| {s['date']} | `{s['commit']}` | "
                f"{s['raison'][:90]}... |")

    L.append("\n## Comparaison forward vs reverse\n"
             "- **Forward** (pipeline_bdnb_pivot.py) : direction "
             "orph -> bgid orph -> BDNB pivots -> copros. Rate les "
             "cas ou le bgid de l'orph est different de celui de la "
             "copro (corner parite-mixte, ordering passes).\n"
             "- **Reverse** (ce pipeline) : direction copro RNC -> "
             "bgid copro -> BDNB pivots -> hr-actives. Couvre "
             "exactement le complementaire : trouve les orphelines "
             "que la copro 'reclamait' via BDNB mais que make_light "
             "n'a pas regroupees.\n"
             "- **Union ideale** = forward U reverse. La paire (orph, "
             "anchor) peut apparaitre dans les 2 (meme cas) ou un "
             "seul (asymetrie). Pour appliquer en lot, traiter "
             "l'union dedupliquee.\n")

    L.append("\n## Methodologie + limites\n"
             "- Cache BDNB partage entre forward et reverse "
             "(idempotent, 1 appel par bgid maxi sur les 2 passes).\n"
             "- SUBS bidirectionnels herites (GAL/CAPT/AYRES).\n"
             "- Skip-list partagee (SKIP_PAIRS de "
             "pipeline_bdnb_pivot).\n"
             "- Filtre collision : flag `autres copros bgid` > 0 "
             "signale qu'un AUTRE syndicat existe sur le meme bgid "
             "(rare ; ARMONIAL I + sous-syndicats par exemple) -> "
             "verifier avant rattachement.\n"
             "- Limites : les bgids avec une seule adresse-pivot ne "
             "produiront aucun match (rien a remonter). Les cas a "
             "vraie ambiguite (orph pourrait appartenir a 2 copros "
             "voisines avec bgid different mais meme adresse BAN) "
             "produisent collision flag.\n")

    L.append("\n---\n*`scripts/pipeline_bdnb_pivot_reverse.py` - "
             "dry-run uniquement. Aucune modification du light. "
             "Cache + rapport seuls ecrits.*")

    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"DL: {na_dl} hr-actives, {nco_dl} copros scannees -> "
          f"{len(res_dl)} matches ({len(sk_dl)} skipped, "
          f"{nc_dl} appels BDNB)")
    print(f"MP: {na_mp} hr-actives, {nco_mp} copros scannees -> "
          f"{len(res_mp)} matches ({len(sk_mp)} skipped, "
          f"{nc_mp} appels BDNB)")
    print(f"total: {len(rows)} matches "
          f"({n_via_subs} via SUBS, {n_collisions} collisions, "
          f"{len(skipped)} skipped)")
    print(f"cache: {CACHE.name} ({len(cache)} bgids)")
    print(f"rapport: {REPORT.name}")


if __name__ == "__main__":
    main()
