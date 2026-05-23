#!/usr/bin/env python3
"""Dry-run RE-FUSE bgid - 20 suffixees DL avec parent ancre meme bgid.

Pour chaque cle suffixee :
  1. Recupere son _fusion_cible actuel (pose au cherrypick)
  2. Lookup parent dans light.adresses
  3. Verifie meme bgid (sinon : fallback parent_bgid_current[0])
  4. Ajoute la cle suffixee au parent._fusion_auto_sources (dedup + tri)
  5. Reconstruit parent._fusion_auto_label depuis (parent_num + sources_nums)

Aucune ecriture - lecture seule.
"""
import json, re, sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
TRIAGE = ROOT / "data" / "_triage_85_suffixes_dl.json"

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
by_cle = {a.get("cle"): a for a in ad}

triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
RE_FUSE = list(triage.get("re_fuse_bgid") or [])

# Re-extract parent_bgid_current per cle (au cas ou)
by_cle_triage = {d["cle"]: d for d in triage.get("detail") or []}

def num_key(n):
    """Cle de tri (int_base, suffix)."""
    m = re.match(r"^(\d+)([A-Z]*)$", n or "")
    if not m: return (10**9, n or "")
    return (int(m.group(1)), m.group(2))

def build_label(parent_cle, all_source_cles):
    """Build 'N1/N2 TYPE VOIE_A / N3/N4 TYPE VOIE_B' depuis parent + sources.

    Multi-voie supporte : sources avec (type, voie) differents du parent
    creent un segment separe avec ' / ' (cf labels existants type
    '24 RUE GABILLOT / 233 RUE PAUL BERT').
    """
    pn, ptv, pvoie = parent_cle.split("|", 2)
    by_voie = defaultdict(list)
    by_voie[(ptv, pvoie)].append(pn)
    for s in all_source_cles:
        sp = s.split("|", 2)
        if len(sp) == 3:
            by_voie[(sp[1], sp[2])].append(sp[0])
    # Segments : parent voie en 1er, autres voies dans ordre d'apparition
    parent_key = (ptv, pvoie)
    seen_voies = [parent_key]
    for s in all_source_cles:
        sp = s.split("|", 2)
        if len(sp) == 3 and (sp[1], sp[2]) not in seen_voies:
            seen_voies.append((sp[1], sp[2]))
    segs = []
    for k in seen_voies:
        nums = []
        seen_n = set()
        for n in sorted(by_voie[k], key=num_key):
            if n not in seen_n:
                nums.append(n); seen_n.add(n)
        segs.append("/".join(nums) + " " + k[0] + " " + k[1])
    return " / ".join(segs)

print("=" * 90)
print(f"DRY-RUN RE-FUSE bgid - 20 cles suffixees DL")
print("=" * 90)
print(f"  Light : {len(ad)} adresses")
print(f"  RE-FUSE cibles : {len(RE_FUSE)}")

# Groupe par parent (cible FA) -> liste de cles a ajouter en sources
by_parent = defaultdict(list)  # parent_cle -> [child_cle, ...]
ORPHANS = []         # parent absent ou bgid mismatch
BGID_MISMATCH = []   # parent existe mais bgid different

def walk_to_real_ancre(start_cle, bgid_ref, prefer_native=True, visited=None):
    """Remonte la chaine FA jusqu'a un real ancre (non-FA) avec meme bgid.

    prefer_native=True : ignore les ancres cherrypicked (avec _injection_indice)
    pour favoriser une cle native pre-existante. Si seule une ancre cherrypicked
    est disponible, on l'accepte en 2eme passe.
    """
    if visited is None: visited = set()
    cur = start_cle
    hops = 0
    fallback_cherrypicked = None
    while cur and cur not in visited and hops < 5:
        visited.add(cur)
        a = by_cle.get(cur)
        if not a: break
        if a.get("batiment_groupe_id") != bgid_ref: break
        if not a.get("_fusion_auto"):  # real ancre trouvee
            if prefer_native and a.get("_injection_indice"):
                fallback_cherrypicked = cur
                # continuer le walk vers cible si possible (mais ancre = end normalement)
                break
            return (cur, hops)
        cur = a.get("_fusion_cible")
        hops += 1
    return (fallback_cherrypicked, hops)

for cle in RE_FUSE:
    a = by_cle.get(cle)
    if not a:
        ORPHANS.append((cle, "cle absente light")); continue
    cible = a.get("_fusion_cible")
    bgid = a.get("batiment_groupe_id")
    rec = by_cle_triage.get(cle, {})
    parents_bgid = rec.get("bgid_parents_current") or []

    parent_cle = None
    # 1. Walk FA chain depuis cible jusqu'au real ancre meme bgid (prefer native)
    if cible:
        real, hops = walk_to_real_ancre(cible, bgid, prefer_native=True)
        if real and not by_cle.get(real, {}).get("_injection_indice"):
            parent_cle = real
        else:
            parent_in_cible = by_cle.get(cible)
            if parent_in_cible and parent_in_cible.get("batiment_groupe_id") != bgid:
                BGID_MISMATCH.append((cle, cible, bgid, parent_in_cible.get("batiment_groupe_id")))

    # 2. Fallback : iterer parents_bgid_current + walker pour resoudre chains
    if not parent_cle and parents_bgid:
        # 1ere passe : prefer cle native (pre-existante non cherrypicked)
        for p in parents_bgid:
            ap = by_cle.get(p)
            if not ap: continue
            real, _ = walk_to_real_ancre(p, bgid, prefer_native=True)
            if real and not by_cle.get(real, {}).get("_injection_indice"):
                parent_cle = real; break
        # 2eme passe : accepter cle cherrypicked si pas mieux
        if not parent_cle:
            for p in parents_bgid:
                real, _ = walk_to_real_ancre(p, bgid, prefer_native=False)
                if real:
                    parent_cle = real; break

    if not parent_cle:
        ORPHANS.append((cle, f"no real ancre meme bgid (cible='{cible}' parents={parents_bgid})"))
        continue
    # Filtres securite :
    # - cle parent malformee (type voie vide : pattern fix-clemalformee-rebind)
    parts_p = parent_cle.split("|", 2)
    if len(parts_p) == 3 and parts_p[1] == "":
        ORPHANS.append((cle, f"parent cle malformee : {parent_cle!r}"))
        continue
    # - parent FA (no-op cosmetique sans visibilite UI)
    if by_cle.get(parent_cle, {}).get("_fusion_auto"):
        ORPHANS.append((cle, f"parent est FA, no-op UI : {parent_cle!r}"))
        continue
    by_parent[parent_cle].append(cle)

print()
print(f"  Parents distincts a etendre : {len(by_parent)}")
print(f"  Cles fusionnables           : {sum(len(v) for v in by_parent.values())}")
print(f"  Orphans (parent absent)     : {len(ORPHANS)}")
print(f"  Bgid mismatch FA cible      : {len(BGID_MISMATCH)}")

if ORPHANS:
    print()
    print(f"[ORPHANS - skip] :")
    for c, msg in ORPHANS:
        print(f"  - {c:36s} : {msg}")

if BGID_MISMATCH:
    print()
    print(f"[BGID MISMATCH info - traite via fallback parent_bgid_current] :")
    for c, cible, bg_child, bg_parent in BGID_MISMATCH:
        print(f"  - {c:36s} cible={cible!r}  child_bgid=...{bg_child[-9:]}  parent_bgid=...{(bg_parent or '-')[-9:]}")

# --- Simulation extension labels/sources ---
print()
print("=" * 90)
print(f"OPERATIONS PROPOSEES (parent -> sources + label)")
print("=" * 90)

OPS = []  # liste (parent_cle, old_label, new_label, old_sources, new_sources, added_cles)
for parent_cle, child_cles in sorted(by_parent.items()):
    parent = by_cle[parent_cle]
    old_label = parent.get("_fusion_auto_label") or ""
    old_sources = list(parent.get("_fusion_auto_sources") or [])
    # Ajouter les nouveaux (dedup)
    new_sources = list(old_sources)
    added = []
    for c in child_cles:
        if c not in new_sources:
            new_sources.append(c); added.append(c)
    # Trier les sources par num
    new_sources.sort(key=lambda c: num_key(c.split("|")[0]))
    # Build label
    new_label = build_label(parent_cle, new_sources)
    OPS.append({
        "parent": parent_cle, "old_label": old_label, "new_label": new_label,
        "old_sources": old_sources, "new_sources": new_sources, "added": added,
        "child_cles": child_cles,
    })

for op in OPS:
    print()
    print(f"  PARENT {op['parent']}")
    print(f"    AVANT label   : {op['old_label']!r}")
    print(f"    AVANT sources : {op['old_sources']}")
    print(f"    + AJOUT {len(op['added'])} cles : {op['added']}")
    print(f"    APRES label   : {op['new_label']!r}")
    print(f"    APRES sources : {op['new_sources']}")

# --- Verifications ---
print()
print("=" * 90)
print("VERIFICATIONS PRE-APPLY")
print("=" * 90)
# 1. Aucune cle suffixee non-traitee dans by_parent
treated = {c for op in OPS for c in op["added"]}
not_treated = [c for c in RE_FUSE if c not in treated and c not in [o[0] for o in ORPHANS]]
print(f"  Cles RE-FUSE non-traitees (hors orphans) : {len(not_treated)}")
for c in not_treated:
    print(f"    - {c} (ATTENTION)")
# 2. Pas de modification cle existante autre que parent
print(f"  Cles a modifier : {len(OPS)} parents (sources + label) + 0 cles suffixees touchees")

# --- Delta parc UI estime ---
USAGE_RESID = {"Résidentiel collectif", "Résidentiel individuel"}
co_by_cle = {c.get("cle_adresse"): c for c in doc["coproprietes"] if c.get("cle_adresse")}

def parc_ui(adresses):
    by_bgid = {}
    for a in adresses:
        if a.get("_fusion_auto"): continue
        bgid = a.get("batiment_groupe_id") or "<NB>" + (a.get("cle") or "")
        cm = co_by_cle.get(a.get("cle"))
        n_rnc = (cm or {}).get("nb_lots_habitation") or 0
        n_bdnb = a.get("nb_log_bdnb") or 0
        usage_ok = (a.get("usage_principal_bdnb") or "") in USAGE_RESID
        n = n_rnc if n_rnc else (n_bdnb if usage_ok else 0)
        if not n: continue
        if bgid in by_bgid:
            by_bgid[bgid] = max(by_bgid[bgid], n)
        else:
            by_bgid[bgid] = n
    return sum(by_bgid.values()), len(by_bgid)

parc, n_bg = parc_ui(ad)
print()
print(f"  Parc UI : {parc} lgts sur {n_bg} bgids")
print(f"  Operations = label + sources sur ancres existantes -> parc UI INCHANGE")
print(f"  (la cle FA enfant reste dedup-bgid avec parent ancre, pas de double-comptage)")

# --- Side effects ---
print()
print("=" * 90)
print("SIDE EFFECTS")
print("=" * 90)
print(f"  - {len(OPS)} ancres parents recevront _fusion_auto_label + _fusion_auto_sources etendus")
print(f"  - 0 cle enfant (suffixee) modifiee (deja FA avec cible OK)")
print(f"  - 0 copro modifiee")
print(f"  - 0 KV touche (les sources etendues n'affectent que la VISIBILITE UI)")

print()
print("=" * 90)
print(f">>> DRY-RUN RE-FUSE bgid TERMINE")
print(f"    {len(OPS)} parents a etendre, {sum(len(o['added']) for o in OPS)} cles ajoutees aux sources")
print(f"    {len(ORPHANS)} orphans skipped")
print("=" * 90)
