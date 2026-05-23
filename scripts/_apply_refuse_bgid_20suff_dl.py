#!/usr/bin/env python3
"""Apply RE-FUSE bgid 20 suffixes DL - extension label/sources parents.

Re-utilise la logique du dry-run (walker FA chain + filtres securite).
Modifie en place les _fusion_auto_label + _fusion_auto_sources des
ancres parents identifiees + tag _correctif_refuse_indice.

Skip : 24B (parent malforme), 26B (no real ancre native disponible).
"""
import json, re, sys, shutil
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
TRIAGE = ROOT / "data" / "_triage_85_suffixes_dl.json"
BAK = LIGHT.with_suffix(LIGHT.suffix + ".prerefuse20.bak")
MARKER = "fix_refuse_bgid_20suff_dl_2026-05-23"

def fail(msg):
    print(); print("!" * 90); print(f"!  ECHEC : {msg}"); print("!" * 90); sys.exit(10)

doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
by_cle = {a.get("cle"): a for a in ad}
triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
RE_FUSE = list(triage.get("re_fuse_bgid") or [])
by_cle_triage = {d["cle"]: d for d in triage.get("detail") or []}

N_AD0 = len(ad)
N_CO0 = len(doc["coproprietes"])

print("=" * 90)
print(f"APPLY RE-FUSE bgid - 20 suffixes DL")
print("=" * 90)
print(f"  Light AVANT : {N_AD0} adresses, {N_CO0} copros")

# --- Backup ---
shutil.copy2(LIGHT, BAK)
print(f"  Backup : {BAK.name}")

# --- Helpers (copies du dry-run) ---
def num_key(n):
    m = re.match(r"^(\d+)([A-Z]*)$", n or "")
    if not m: return (10**9, n or "")
    return (int(m.group(1)), m.group(2))

def build_label(parent_cle, all_source_cles):
    pn, ptv, pvoie = parent_cle.split("|", 2)
    by_voie = defaultdict(list)
    by_voie[(ptv, pvoie)].append(pn)
    for s in all_source_cles:
        sp = s.split("|", 2)
        if len(sp) == 3:
            by_voie[(sp[1], sp[2])].append(sp[0])
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

def walk_to_real_ancre(start_cle, bgid_ref, prefer_native=True, visited=None):
    if visited is None: visited = set()
    cur = start_cle
    hops = 0
    fallback_cherrypicked = None
    while cur and cur not in visited and hops < 5:
        visited.add(cur)
        a = by_cle.get(cur)
        if not a: break
        if a.get("batiment_groupe_id") != bgid_ref: break
        if not a.get("_fusion_auto"):
            if prefer_native and a.get("_injection_indice"):
                fallback_cherrypicked = cur; break
            return (cur, hops)
        cur = a.get("_fusion_cible")
        hops += 1
    return (fallback_cherrypicked, hops)

# --- Resolve parent for each RE-FUSE cle ---
by_parent = defaultdict(list)
ORPHANS = []

for cle in RE_FUSE:
    a = by_cle.get(cle)
    if not a:
        ORPHANS.append((cle, "cle absente light")); continue
    cible = a.get("_fusion_cible")
    bgid = a.get("batiment_groupe_id")
    rec = by_cle_triage.get(cle, {})
    parents_bgid = rec.get("bgid_parents_current") or []

    parent_cle = None
    if cible:
        real, _ = walk_to_real_ancre(cible, bgid, prefer_native=True)
        if real and not by_cle.get(real, {}).get("_injection_indice"):
            parent_cle = real
    if not parent_cle and parents_bgid:
        for p in parents_bgid:
            ap = by_cle.get(p)
            if not ap: continue
            real, _ = walk_to_real_ancre(p, bgid, prefer_native=True)
            if real and not by_cle.get(real, {}).get("_injection_indice"):
                parent_cle = real; break
        if not parent_cle:
            for p in parents_bgid:
                real, _ = walk_to_real_ancre(p, bgid, prefer_native=False)
                if real:
                    parent_cle = real; break
    if not parent_cle:
        ORPHANS.append((cle, f"no real ancre meme bgid"))
        continue
    # Filtres securite
    parts_p = parent_cle.split("|", 2)
    if len(parts_p) == 3 and parts_p[1] == "":
        ORPHANS.append((cle, f"parent malforme : {parent_cle!r}"))
        continue
    if by_cle.get(parent_cle, {}).get("_fusion_auto"):
        ORPHANS.append((cle, f"parent FA : {parent_cle!r}"))
        continue
    by_parent[parent_cle].append(cle)

# --- Apply ---
print()
print(f"  Apply in-memory ({len(by_parent)} parents, {sum(len(v) for v in by_parent.values())} cles fusionnables)")
APPLIED = []
for parent_cle, child_cles in sorted(by_parent.items()):
    parent = by_cle[parent_cle]
    old_sources = list(parent.get("_fusion_auto_sources") or [])
    new_sources = list(old_sources)
    added = []
    for c in child_cles:
        if c not in new_sources:
            new_sources.append(c); added.append(c)
    new_sources.sort(key=lambda c: num_key(c.split("|")[0]))
    new_label = build_label(parent_cle, new_sources)
    # Apply
    parent["_fusion_auto_sources"] = new_sources
    parent["_fusion_auto_label"] = new_label
    parent["_correctif_refuse_indice"] = MARKER
    APPLIED.append((parent_cle, added, new_label))
    print(f"    OK  {parent_cle:36s}  +{len(added)} -> '{new_label[:60]}'")

if ORPHANS:
    print()
    print(f"  ORPHANS (skipped) : {len(ORPHANS)}")
    for c, msg in ORPHANS:
        print(f"    SKIP {c:36s} : {msg}")

# --- Ecriture light.json ---
print()
print(f"  Ecriture light.json...")
with LIGHT.open("w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)

# --- Verif post-write ---
doc_check = json.loads(LIGHT.read_text(encoding="utf-8"))
if len(doc_check["adresses"]) != N_AD0:
    fail(f"count adresses change {N_AD0}->{len(doc_check['adresses'])}")
if len(doc_check["coproprietes"]) != N_CO0:
    fail(f"count copros change {N_CO0}->{len(doc_check['coproprietes'])}")
ad_check = {a.get("cle"): a for a in doc_check["adresses"]}
ok = 0
for parent_cle, added, new_label in APPLIED:
    a = ad_check.get(parent_cle, {})
    if a.get("_fusion_auto_label") != new_label:
        fail(f"VERIF post-write : {parent_cle} label = {a.get('_fusion_auto_label')!r} (attendu {new_label!r})")
    if a.get("_correctif_refuse_indice") != MARKER:
        fail(f"VERIF post-write : {parent_cle} marker absent")
    # Verifier sources contiennent les added
    cur_sources = a.get("_fusion_auto_sources") or []
    for c in added:
        if c not in cur_sources:
            fail(f"VERIF post-write : {parent_cle} sources sans {c}")
    ok += 1
print(f"  Verif post-write : {ok}/{len(APPLIED)} OK")

print()
print("=" * 90)
print(f">>> APPLY OK - {len(APPLIED)} parents etendus, {sum(len(a[1]) for a in APPLIED)} cles dans sources")
print(f"    Backup : {BAK.name}")
print(f"    Commit a faire par orchestrateur. PAS DE PUSH.")
print("=" * 90)
