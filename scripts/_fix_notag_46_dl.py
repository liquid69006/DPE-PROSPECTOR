#!/usr/bin/env python3
"""Reclassement KV DL : PATCH 44 cles sans tag KV -> mono / social / bureaux.

Issu du cross-check des 171 MONO Phase 2 (ratio>=0.9 + 1 SIREN + 100%
lots PM) vs etat KV : 46 adresses sans tag KV identifiees, dont 44
classifiees automatiquement par heuristique :
  - 30 SOCIAL : top SIREN bailleur public / HLM / ESH / medico-social
                (Alliade, OPH, GrandLyon Habitat, IRA HLM, IN'LI AURA,
                 SA Construction Ville Lyon, Hospices Civils Lyon,
                 Commune Lyon, Communaute Urbaine, CDC Habitat, SCIC,
                 Fondation Aralis...)
  - 5 BUREAUX : usage_principal_bdnb = Tertiaire + 1 SIREN 100% (3
                facades 27/29/31 ANTOINE CHARIAL Commune Lyon, 34
                GENERAL MOUTON DUVERNET Departement Rhone, 39B
                AVENUE LACASSAGNE SCI KIM).
  - 9 MONO   : SCI ou foncieres privees clairement identifiees
                (FONCIERE VESTA, SCI 7-9-11 RUE DU MILIEU, SCI NSK)
                + 6 cas residentiels collectifs 1 SIREN 100% (ATC,
                ANVIRO, UZLIE, BARABAN, JUNE, KEVOCEANE) qui
                presentent la signature mono-propriete (1 SIREN
                privee patrimoniale a 100% des lots PM).

2 cas EXCLUS de ce lot (a decider manuellement plus tard) :
  - 10 RUE ST MAXIMIN (SAINT PHILIPPE, bdnb=1, Resid individuel)
  - 264B RUE PAUL BERT (AR 2006, bdnb=1, Resid individuel)
  Raison : maisons individuelles bdnb=1, le top SIREN pourrait etre
  une SCI familiale ou une societe gestionnaire. Qualif a affiner
  apres examen terrain.

Pattern script identique a _fix_reclass_10_dl.py :
  GET KV live -> audit (cle absente du KV OU tag deja correct -> SKIP)
  -> backup .prenotag46.bak -> rebuild new_assigns avec {'type': target}
  -> POST atomique -> Re-GET verif per-cle -> sync local.

Idempotent : SKIP si tag deja pose (heritage UI ou autre fix entre
temps), pas d'override.

Usage :
  python scripts/_fix_notag_46_dl.py <JWT_TOKEN>
  ou : DPE_TOKEN=<jwt> python scripts/_fix_notag_46_dl.py
"""
import json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK      = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".prenotag46.bak")

API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

TOKEN = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DPE_TOKEN", "")).strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant (argv1 ou env)"); sys.exit(2)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

# 44 cibles : (cle, target_type)
# Tri thematique pour relisibilite, le script ne depend pas de l'ordre.
CIBLES = [
    # ── SOCIAL (30) ── top SIREN bailleur public / social / medico ──
    ("20|RUE|JEANNE HACHETTE",           "social"),  # SA CONSTR VILLE LYON x4 facades
    ("22|RUE|JEANNE HACHETTE",           "social"),
    ("24|RUE|JEANNE HACHETTE",           "social"),
    ("26|RUE|JEANNE HACHETTE",           "social"),
    ("9|RUE|JEAN PIERRE LEVY",           "social"),  # ALLIADE HABITAT
    ("28|RUE|CLAUDIUS PIONCHON",         "social"),  # GRAND LYON HABITAT OPH x3
    ("26|RUE|CLAUDIUS PIONCHON",         "social"),
    ("24|RUE|CLAUDIUS PIONCHON",         "social"),
    ("32|RUE|MAURICE FLANDIN",           "social"),  # HOSPICES CIVILS LYON x3
    ("36|RUE|MAURICE FLANDIN",           "social"),
    ("7|RUE|AUBIGNY",                    "social"),
    ("150|AVENUE|FELIX FAURE",           "social"),  # IRA HLM x4 facades
    ("152|AVENUE|FELIX FAURE",           "social"),
    ("154|AVENUE|FELIX FAURE",           "social"),
    ("158|AVENUE|FELIX FAURE",           "social"),
    ("9|RUE|CLAUDIUS PIONCHON",          "social"),  # ALLIADE HABITAT
    ("25|RUE|MAURICE FLANDIN",           "social"),  # SA CONSTR VILLE LYON
    ("206|AVENUE|FELIX FAURE",           "social"),  # IN'LI AURA
    ("26|RUE|ST VICTORIEN",              "social"),  # ALLIADE HABITAT
    ("48|RUE|STE ANNE DE BARABAN",       "social"),  # ALLIADE HABITAT
    ("4|PASSAGE|EDOUARD AYNARD",         "social"),  # ALLIADE HABITAT
    ("18|RUE|TURBIL",                    "social"),  # OPH METROPOLE LYON
    ("323|RUE|PAUL BERT",                "social"),  # CDC HABITAT SOCIAL
    ("97|RUE|DAUPHINE",                  "social"),  # SA CONSTR VILLE LYON
    ("12|RUE|RIBOUD",                    "social"),  # SA CONSTR VILLE LYON
    ("41|RUE|ETIENNE RICHERAND",         "social"),  # OPH METROPOLE LYON
    ("280|RUE|PAUL BERT",                "social"),  # COMMUNE DE LYON
    ("22|RUE|ESPERANCE",                 "social"),  # SCIC LES 3 COLONNES (medico-social)
    ("345|RUE|PAUL BERT",                "social"),  # COMMUNAUTE URBAINE DE LYON
    ("15B|RUE|DAUPHINE",                 "social"),  # FONDATION ARALIS
    ("42|RUE|AUBIGNY",                   "social"),  # FONCIERE VESTA (deplace de mono->social
                                                      #  apres validation user 2026-05-25 : foncier social/intermediaire)

    # ── BUREAUX (5) ── usage Tertiaire + 1 SIREN 100% ──
    ("27|RUE|ANTOINE CHARIAL",           "bureaux"), # COMMUNE LYON Tertiaire x3
    ("29|RUE|ANTOINE CHARIAL",           "bureaux"),
    ("31|RUE|ANTOINE CHARIAL",           "bureaux"),
    ("34|RUE|GENERAL MOUTON DUVERNET",   "bureaux"), # DEPARTEMENT RHONE Tertiaire
    ("39B|AVENUE|LACASSAGNE",            "bureaux"), # SCI KIM Tertiaire

    # ── MONO (7) ── SCI / fonciere privee patrimoniale 100% ──
    ("9|RUE|MILIEU",                     "mono"),    # SCI 7-9-11 RUE DU MILIEU
    ("2|RUE|ST PHILIPPE",                "mono"),    # SCI NSK
    ("11|RUE|PETITES SOEURS",            "mono"),    # ANVIRO (bdnb=10)
    ("19|RUE|DAUPHINE",                  "mono"),    # UZLIE (bdnb=9)
    ("6|RUE|MILIEU",                     "mono"),    # BARABAN (bdnb=6)
    ("7|RUE|MILIEU",                     "mono"),    # JUNE (bdnb=6)
    ("248|RUE|PAUL BERT",                "mono"),    # KEVOCEANE (bdnb=2)

    # ── EXCLUS de ce lot (decision manuelle ulterieure) ──
    #   10|RUE|ST MAXIMIN     SAINT PHILIPPE bdnb=1 Resid individuel
    #   264B|RUE|PAUL BERT    AR 2006 bdnb=1 Resid individuel
    #   1|RUE|VILLETTE        ATC bdnb=24 -- exclu par user 2026-05-25
    #                          (ATC syndic possible, pas mono patrimonial sur)
    #   42|RUE|AUBIGNY        FONCIERE VESTA -- DEPLACE vers SOCIAL
    #                          (cf section social ci-dessus)
]


def http(method, url, headers=None, body=None):
    req = urllib.request.Request(
        url, method=method, headers=headers or {},
        data=(json.dumps(body).encode("utf-8") if body is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def fail(msg):
    print(); print("!" * 90); print(f"!  ECHEC : {msg}"); print("!" * 90); sys.exit(10)


print("=" * 90)
print(f"KV DL : PATCH {len(CIBLES)} cles sans tag KV -> mono / social / bureaux")
print("=" * 90)

code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"GET {code}: {raw[:200]}")
kv = json.loads(raw)
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms    = kv.get("noms") or {}
print(f"  KV live avant : {len(assigns)} assigns, {len(fusions)} fusions, {len(noms)} noms")

print()
print("  Audit pre-PATCH (cle sans tag KV requis ; SKIP si deja posee) :")
to_patch = []
skip = []
for cle, target in CIBLES:
    cur = assigns.get(cle)
    tag = (cur or {}).get("type")
    if tag == target:
        print(f"    {cle:<37} -> SKIP (deja type={target}, idempotent)")
        skip.append((cle, f"deja-{target}"))
    elif tag:
        # Tag different existant -> SKIP (pas d override)
        print(f"    {cle:<37} -> SKIP (tag actuel = {tag!r}, attendu vide ; pas d override)")
        skip.append((cle, f"tag-actuel-{tag}"))
    else:
        # Pas de tag -> on cree avec type=target
        print(f"    {cle:<37} -> CREATE type={target}")
        to_patch.append((cle, target))

if not to_patch:
    print()
    print("=" * 90)
    print(">>> IDEMPOTENT : aucune cle a creer (toutes deja taggees)")
    print("=" * 90)
    sys.exit(0)

if KV_LOCAL.exists():
    shutil.copy2(KV_LOCAL, BAK)
    print()
    print(f"  Backup KV local : {BAK.name}")

new_assigns = dict(assigns)
counts = {}
for cle, target in to_patch:
    # Cle absente du KV : CREATE simple. Cle deja la mais sans 'type' (cas rare) :
    # spread pour preserver d'eventuels autres champs.
    new_assigns[cle] = {**(assigns.get(cle) or {}), "type": target}
    counts[target] = counts.get(target, 0) + 1
breakdown = ", ".join(f"{t}={n}" for t, n in sorted(counts.items()))
print()
print(f"  POST atomique (CREATE {len(to_patch)} cle(s), breakdown : {breakdown}, KV {len(assigns)} -> {len(new_assigns)}) ...")
code, raw = http("POST", ENDPOINT, HDR_POST,
                 body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
print(f"  POST HTTP {code} : {raw[:200]}")
if code not in (200, 204): fail(f"POST KO {code}")

code, raw = http("GET", ENDPOINT, HDR_GET)
if code != 200: fail(f"Re-GET {code}")
kv_after = json.loads(raw)
assigns_after = kv_after.get("assignments") or {}
print(f"  Re-GET : {len(assigns_after)} assigns")
print()
print("  Verif post-PATCH :")
errs = []
for cle, target in to_patch:
    after = assigns_after.get(cle)
    if not after:
        print(f"    {cle:<37} -> KO (cree puis disparu)")
        errs.append(cle); continue
    if after.get("type") != target:
        print(f"    {cle:<37} -> KO (type={after.get('type')!r}, attendu {target})")
        errs.append(cle); continue
    print(f"    {cle:<37} -> OK type={target}")
if errs: fail(f"PATCH incomplet : {errs}")

KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Sync KV local : {KV_LOCAL.name}")

print()
print("=" * 90)
print(f">>> SUCCES : {len(to_patch)} cle(s) creees ({breakdown}), KV {len(assigns)} -> {len(assigns_after)}")
if skip:
    print(f">>> {len(skip)} cle(s) skip : {[(k, r) for k, r in skip]}")
print("=" * 90)
