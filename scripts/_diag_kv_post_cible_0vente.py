#!/usr/bin/env python3
"""Diag post-apply tag cible_0vente (lecture seule).

Question : POST a renvoye assignments=604, attendu 538+118=656.
Ecart = 52. Verifier :
  - combien des 118 cles existaient deja dans KV avant ce POST
  - le compteur 'assignments' compte-t-il unique (set) ou operations
  - aucune cle social/mono/bureaux/mixte du batch MAJIC ecrasee
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")

# Etats KV :
#   pre_cible_0vente.bak : snapshot AVANT le tag 0-vente (post batch MAJIC)
#   _kv_assign_dl.json   : snapshot APRES (etat actuel local)
PRE = ROOT / "data" / "_kv_assign_dl.pre_cible_0vente.bak"
POST = ROOT / "data" / "_kv_assign_dl.json"

# Backup encore plus ancien : pre_batch_majic (avant batch MAJIC)
PRE_MAJIC = ROOT / "data" / "_kv_assign_dl.prebatch_majic.bak"

# Cles batch MAJIC + 132 BARABAN + canary 1 VILLETTE (a verifier intacts)
MAJIC_CLES_EXPECTED = {
    # SOCIAL (12) - le canary 1 VILLETTE est dans MONO et le 132 BARABAN ajoute apres
    "10|RUE|JEAN RENOIR": "social",
    "128|RUE|ANTOINE CHARIAL": "social",
    "12|RUE|ST SIDOINE": "social",
    "191|AVENUE|FELIX FAURE": "social",
    "20B|AVENUE|LACASSAGNE": "social",
    "22|RUE|ST ANTOINE": "social",
    "272|RUE|PAUL BERT": "social",
    "28|RUE|ETIENNE RICHERAND": "social",
    "35|RUE|ST ANTOINE": "social",
    "59|COURS|ALBERT THOMAS": "social",
    "59|RUE|BARABAN": "social",
    "66|AVENUE|LACASSAGNE": "social",
    # MIXTE (9)
    "14|RUE|DOCTEUR REBATEL": "mixte",
    "23|RUE|METALLURGIE": "mixte",
    "39|RUE|DAUPHINE": "mixte",
    "3|RUE|NAZARETH": "mixte",
    "52|RUE|ETIENNE RICHERAND": "mixte",
    "56|RUE|MAURICE FLANDIN": "mixte",
    "77|RUE|ETIENNE RICHERAND": "mixte",
    "7|COURS|ALBERT THOMAS": "mixte",
    "8|RUE|FRANCOIS GILLET": "mixte",
    # MONO (5 + 1 canary)
    "14|RUE|ROPOSTE": "mono",
    "1|RUE|VILLETTE": "mono",
    "20|RUE|FREDERIC MISTRAL": "mono",
    "251|RUE|PAUL BERT": "mono",
    "3|RUE|FRANCOIS GILLET": "mono",
    "41|AVENUE|LACASSAGNE": "mono",
    # BUREAUX (7)
    "256|COURS|LAFAYETTE": "bureaux",
    "2|RUE|BARA": "bureaux",
    "30|RUE|ANTOINE CHARIAL": "bureaux",
    "336|RUE|PAUL BERT": "bureaux",
    "5|COURS|ALBERT THOMAS": "bureaux",
    "79|RUE|DAUPHINE": "bureaux",
    "99|RUE|BARABAN": "bureaux",
    # Fix isole 132 BARABAN
    "132|RUE|BARABAN": "social",
}

print("=" * 78)
print("DIAG POST-APPLY TAG CIBLE_0VENTE_*")
print("=" * 78)

# 1. Compteurs
pre = json.loads(PRE.read_text(encoding="utf-8"))
post = json.loads(POST.read_text(encoding="utf-8"))
assigns_pre = (pre.get("assignments") if "_meta" in pre else pre) or pre.get("assignments", {})
# Le format de PRE est snapshot avec _meta ; verifier
if "assignments" in pre:
    assigns_pre = pre.get("assignments") or {}
else:
    assigns_pre = pre
assigns_post = post.get("assignments") or {}

print(f"\n[1] Compteurs assignments :")
print(f"    PRE  (pre_cible_0vente.bak)  : {len(assigns_pre)}")
print(f"    POST (_kv_assign_dl.json)    : {len(assigns_post)}")
print(f"    Diff bruts (POST - PRE)       : {len(assigns_post) - len(assigns_pre)}")

# 2. Cles cible_0vente_* dans POST
cibles_post = {c: v.get("type")
               for c, v in assigns_post.items()
               if (v or {}).get("type", "").startswith("cible_0vente")}
n_actives = sum(1 for t in cibles_post.values() if t == "cible_0vente_active")
n_isolees = sum(1 for t in cibles_post.values() if t == "cible_0vente_isolee")
print(f"\n[2] Cles cible_0vente_* dans POST :")
print(f"    cible_0vente_active : {n_actives}")
print(f"    cible_0vente_isolee : {n_isolees}")
print(f"    total cibles        : {len(cibles_post)}")

# 3. Decomposition : combien des cibles existaient deja dans PRE ?
deja_pre = [c for c in cibles_post if c in assigns_pre]
nouv_pre = [c for c in cibles_post if c not in assigns_pre]
print(f"\n[3] Pour chaque cible 0-vente dans POST :")
print(f"    cles deja presentes dans PRE (remplacees) : {len(deja_pre)}")
print(f"    cles ABSENTES de PRE (ajoutees)            : {len(nouv_pre)}")
print(f"    VERIF arithmetique :")
print(f"      attendu     : 538 + {len(nouv_pre)} = {538 + len(nouv_pre)}")
print(f"      observe     : {len(assigns_post)}")
print(f"      match       : {538 + len(nouv_pre) == len(assigns_post)}")

# 4. Pour les cles deja presentes : quels etaient leurs types AVANT ?
print(f"\n[4] Types pre-existants des {len(deja_pre)} cles remplacees :")
types_pre = Counter((assigns_pre.get(c) or {}).get("type", "(vide)")
                    for c in deja_pre)
for t, n in types_pre.most_common():
    print(f"    '{t}' : {n}")

# 5. Verif que les 34 (35 avec 132) cles MAJIC ont garde leur tag
print(f"\n[5] Verif persistance batch MAJIC ({len(MAJIC_CLES_EXPECTED)} cles attendues) :")
fails = []
ok = 0
absent = []
for cle, tag_attendu in MAJIC_CLES_EXPECTED.items():
    v_post = (assigns_post.get(cle) or {}).get("type")
    if v_post == tag_attendu:
        ok += 1
    elif v_post is None:
        absent.append(cle)
    else:
        fails.append((cle, tag_attendu, v_post))
print(f"    OK              : {ok}/{len(MAJIC_CLES_EXPECTED)}")
print(f"    Absentes du KV  : {len(absent)}")
for c in absent:
    print(f"      [ABS]  {c}")
print(f"    Tag CHANGE      : {len(fails)}")
for c, exp, got in fails:
    print(f"      [DIFF] {c:34s} attendu='{exp}' got='{got}'")

# 6. Distribution complete des types POST (pour panorama global)
print(f"\n[6] Distribution complete des types POST :")
types_post = Counter((v or {}).get("type", "(vide)")
                     for v in assigns_post.values())
for t, n in types_post.most_common():
    print(f"    {t:30s} : {n}")

# 7. Conclusion
print()
print("=" * 78)
print("CONCLUSION")
print("=" * 78)
print(f"  Compteur 'assignments' = nombre de cles UNIQUES (semantique set)")
print(f"  → POST atomique remplace assignments dict entier ;")
print(f"    cles deja presentes mises a jour, nouvelles ajoutees.")
print(f"  Diff 538 → {len(assigns_post)} :")
print(f"    +{len(nouv_pre)} nouvelles cles ajoutees (cible_0vente_*)")
print(f"    {len(deja_pre)} cles remplacees (sur place, pas de +1)")
print(f"  Batch MAJIC intact : {ok}/{len(MAJIC_CLES_EXPECTED)} cles "
      f"avec tag d'origine ; {len(fails)} ecrasement ; {len(absent)} absente.")
