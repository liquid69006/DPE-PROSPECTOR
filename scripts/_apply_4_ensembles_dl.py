#!/usr/bin/env python3
"""Apply sequentiel E3 / E2 / E4 / E5 - production.

Phase A : E3 - POST KV 2|RUE|VILLETTE -> copro_non_immat
Phase B : E2 - light.json : RE-POINT 233 PB bgid + label 24 GABILLOT
Phase C : E4 - light.json : RE-POINT+FUSE 6 MILIEU + label 4 MILIEU
                + POST KV : DELETE 6 MILIEU (hygiene mono orphelin)
Phase D : E5 - light.json : INJECT AF2921443 + ATTRIBUER + RE-POINT 20 DAUPH
                + cleanup 18 DAUPH + POST KV : DELETE 2 ST PHILIPPE

Chaque phase : backup + apply + verif. Stop sur 1ere erreur.
COMMIT post-phases mais PAS DE PUSH.
"""
import json, sys, os, shutil, urllib.parse, urllib.request, urllib.error, time
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"

API_URL = "https://dpe-prospector-api.yann-bufferne.workers.dev"
KV_ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"
RID_RNC = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID_RNC}/data/"

TOKEN = os.environ.get("DPE_TOKEN", "").strip()
if not TOKEN: print("ERREUR : DPE_TOKEN manquant"); sys.exit(2)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
HDR_GET  = {"Authorization": f"Bearer {TOKEN}", "User-Agent": UA, "Accept": "application/json"}
HDR_POST = {**HDR_GET, "Content-Type": "application/json"}

def http(method, url, headers=None, body=None):
    req = urllib.request.Request(url, method=method, headers=headers or {},
                                 data=(json.dumps(body).encode("utf-8") if body is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

def http_get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"_error": str(e)[:200]}

def kv_get():
    code, raw = http("GET", KV_ENDPOINT, HDR_GET)
    if code != 200: raise RuntimeError(f"KV GET {code}: {raw[:200]}")
    return json.loads(raw)

def kv_post(payload):
    code, raw = http("POST", KV_ENDPOINT, HDR_POST, body=payload)
    if code not in (200, 204): raise RuntimeError(f"KV POST {code}: {raw[:200]}")
    return raw

def backup(path, suffix):
    bak = path.with_suffix(path.suffix + suffix)
    shutil.copy2(path, bak)
    return bak

def section(title):
    print()
    print("#" * 90)
    print(f"# {title}")
    print("#" * 90)

def fail(msg):
    print()
    print("!" * 90)
    print(f"!  ECHEC : {msg}")
    print("!  STOP - aucune phase suivante executee")
    print("!" * 90)
    sys.exit(10)


# ============================================================
# PHASE A : E3 - POST KV 2|RUE|VILLETTE -> copro_non_immat
# ============================================================
section("PHASE A - E3 : POST KV 2|RUE|VILLETTE -> copro_non_immat")
TARGET_CLE_E3 = "2|RUE|VILLETTE"

kv = kv_get()
assigns_before = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
noms = kv.get("noms") or {}
print(f"  KV avant : {len(assigns_before)} assigns")

# Backup
bak_kv_a = backup(KV_LOCAL, ".prephaseA.bak") if KV_LOCAL.exists() else None
print(f"  Backup local KV : {bak_kv_a and bak_kv_a.name}")

# Merge
assigns_new = dict(assigns_before)
if assigns_new.get(TARGET_CLE_E3, {}).get("type") == "copro_non_immat":
    print(f"  IDEMPOTENT : {TARGET_CLE_E3} deja copro_non_immat")
else:
    assigns_new[TARGET_CLE_E3] = {"type": "copro_non_immat"}
    raw = kv_post({"assignments": assigns_new, "fusions": fusions, "noms": noms})
    print(f"  POST OK : {raw[:120]}")

# Verif
kv_after = kv_get()
val_after = (kv_after.get("assignments") or {}).get(TARGET_CLE_E3)
if not val_after or val_after.get("type") != "copro_non_immat":
    fail(f"E3 verif : {TARGET_CLE_E3} -> {val_after}")
print(f"  Verif re-GET : {TARGET_CLE_E3} -> {val_after}  OK")
print(f"  KV apres : {len(kv_after.get('assignments') or {})} assigns")

# Sync local
KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
print(f"  Local KV sync : {KV_LOCAL.name}")
print(f"  >>> PHASE A OK")


# ============================================================
# Lecture light pour phases B/C/D (un seul backup, modifs in-place)
# ============================================================
section("PRE-CHARGEMENT light.json + backup combine BCD")
bak_light_bcd = backup(LIGHT, ".prephasesBCD.bak")
print(f"  Backup light : {bak_light_bcd.name}")
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad = doc["adresses"]
co = doc["coproprietes"]
by_cle_ad = {(a.get("cle") or ""): a for a in ad}
print(f"  Chargement OK : {len(ad)} adresses, {len(co)} copros")


# ============================================================
# PHASE B : E2 - RE-POINT 233 PB bgid + label 24 GABILLOT
# ============================================================
section("PHASE B - E2 : RE-POINT 233 PAUL BERT -> bgid 24 GABILLOT + label")

E2_ANCRE = "24|RUE|GABILLOT"
E2_REPOINT = "233|RUE|PAUL BERT"
a_ancre_e2 = by_cle_ad.get(E2_ANCRE)
a_repoint_e2 = by_cle_ad.get(E2_REPOINT)
if not a_ancre_e2 or not a_repoint_e2:
    fail(f"E2 cles absentes : {E2_ANCRE} {a_ancre_e2 is not None} | {E2_REPOINT} {a_repoint_e2 is not None}")

bgid_ancre_e2 = a_ancre_e2.get("batiment_groupe_id")
bgid_repoint_avant_e2 = a_repoint_e2.get("batiment_groupe_id")
print(f"  Avant : {E2_REPOINT}.bgid = {bgid_repoint_avant_e2}")
print(f"  Cible : {E2_REPOINT}.bgid -> {bgid_ancre_e2}")

# Apply
a_repoint_e2["batiment_groupe_id"] = bgid_ancre_e2
a_ancre_e2["_fusion_auto_label"] = "24 RUE GABILLOT / 233 RUE PAUL BERT"
a_ancre_e2["_fusion_auto_sources"] = [E2_REPOINT]

# Verif
if a_repoint_e2["batiment_groupe_id"] != bgid_ancre_e2:
    fail(f"E2 RE-POINT non applique")
if a_ancre_e2.get("_fusion_auto_label") != "24 RUE GABILLOT / 233 RUE PAUL BERT":
    fail(f"E2 label non applique")
print(f"  Apres : {E2_REPOINT}.bgid = {a_repoint_e2['batiment_groupe_id']}")
print(f"  Apres : {E2_ANCRE}._fusion_auto_label = {a_ancre_e2.get('_fusion_auto_label')!r}")
print(f"  Apres : {E2_ANCRE}._fusion_auto_sources = {a_ancre_e2.get('_fusion_auto_sources')!r}")
print(f"  >>> PHASE B OK (in-memory)")


# ============================================================
# PHASE C : E4 - RE-POINT 6 MILIEU + FA + label + DELETE KV
# ============================================================
section("PHASE C - E4 : RE-POINT+FUSE 6 MILIEU + DELETE KV mono orphelin")

E4_ANCRE = "4|RUE|MILIEU"
E4_FUSE = "6|RUE|MILIEU"
a_ancre_e4 = by_cle_ad.get(E4_ANCRE)
a_fuse_e4 = by_cle_ad.get(E4_FUSE)
if not a_ancre_e4 or not a_fuse_e4:
    fail(f"E4 cles absentes")

bgid_ancre_e4 = a_ancre_e4.get("batiment_groupe_id")
bgid_fuse_avant_e4 = a_fuse_e4.get("batiment_groupe_id")
bdnb_fuse_e4 = a_fuse_e4.get("nb_log_bdnb", 0)
print(f"  Avant : {E4_FUSE}.bgid = {bgid_fuse_avant_e4}  bdnb={bdnb_fuse_e4}")
print(f"  Cible : {E4_FUSE}.bgid -> {bgid_ancre_e4}, FA cible='{E4_ANCRE}'")

# Apply light
a_fuse_e4["batiment_groupe_id"] = bgid_ancre_e4
a_fuse_e4["_fusion_auto"] = True
a_fuse_e4["_fusion_cible"] = E4_ANCRE
a_ancre_e4["_fusion_auto_label"] = "4/6 RUE MILIEU"
a_ancre_e4["_fusion_auto_sources"] = [E4_FUSE]

if a_fuse_e4["batiment_groupe_id"] != bgid_ancre_e4: fail("E4 RE-POINT non applique")
if not a_fuse_e4.get("_fusion_auto"): fail("E4 FA non applique")
if a_fuse_e4.get("_fusion_cible") != E4_ANCRE: fail("E4 FA cible incorrect")
print(f"  Apres : {E4_FUSE}.bgid = {a_fuse_e4['batiment_groupe_id']}  FA={a_fuse_e4.get('_fusion_auto')}  cible={a_fuse_e4.get('_fusion_cible')!r}")
print(f"  Apres : {E4_ANCRE}._fusion_auto_label = {a_ancre_e4.get('_fusion_auto_label')!r}")
print(f"  Apres : {E4_ANCRE}._fusion_auto_sources = {a_ancre_e4.get('_fusion_auto_sources')!r}")
print(f"  >>> PHASE C light OK (in-memory)")

# Apply KV DELETE 6 MILIEU
print()
print("  KV DELETE 6 MILIEU (hygiene mono orphelin) :")
kv_c = kv_get()
assigns_c = kv_c.get("assignments") or {}
if E4_FUSE in assigns_c:
    new_assigns_c = {k:v for k,v in assigns_c.items() if k != E4_FUSE}
    kv_post({"assignments": new_assigns_c,
             "fusions": kv_c.get("fusions") or {},
             "noms": kv_c.get("noms") or {}})
    kv_c2 = kv_get()
    if E4_FUSE in (kv_c2.get("assignments") or {}):
        fail(f"E4 KV DELETE {E4_FUSE} : verif echec")
    print(f"  KV DELETE OK : {E4_FUSE} retire")
    print(f"  KV : {len(assigns_c)} -> {len(kv_c2.get('assignments') or {})}")
    KV_LOCAL.write_text(json.dumps(kv_c2, ensure_ascii=False), encoding="utf-8")
else:
    print(f"  IDEMPOTENT : {E4_FUSE} deja absent KV")
print(f"  >>> PHASE C OK")


# ============================================================
# PHASE D : E5 - INJECT AF2921443 + propagation + RE-POINT 20 DAUPHINE
# ============================================================
section("PHASE D - E5 : INJECT AF2921443 + RE-POINT 20 DAUPH + cleanup 18 DAUPH")

E5_ANCRE = "2|RUE|ST PHILIPPE"
E5_REPOINT = "20|RUE|DAUPHINE"
E5_OLD_ANCRE = "18|RUE|DAUPHINE"  # ancien cible FA pour 20
IMMAT_NEW = "AF2921443"

a_ancre_e5 = by_cle_ad.get(E5_ANCRE)
a_repoint_e5 = by_cle_ad.get(E5_REPOINT)
a_old_ancre_e5 = by_cle_ad.get(E5_OLD_ANCRE)
if not all([a_ancre_e5, a_repoint_e5, a_old_ancre_e5]):
    fail(f"E5 cles absentes : 2 ST PHILIPPE / 20 DAUPH / 18 DAUPH")

# Idempotence : si copro AF2921443 deja injectee, skip INJECT
if any(c.get("numero_immatriculation") == IMMAT_NEW for c in co):
    print(f"  IDEMPOTENT : copro {IMMAT_NEW} deja dans light")
else:
    # Fetch RNC live AF2921443
    url = TAB + "?" + urllib.parse.urlencode({"numero_immatriculation__exact": IMMAT_NEW})
    rnc_res = http_get_json(url, timeout=20)
    if not isinstance(rnc_res, dict) or not rnc_res.get("data"):
        fail(f"E5 fetch RNC live {IMMAT_NEW} : {rnc_res}")
    rnc_data = rnc_res["data"][0]

    # Construire copro a injecter (schema based on existing copros)
    nb_hab = (rnc_data.get("nombre_lots_usage_habitation")
              or rnc_data.get("nombre_lots_habitation_bureaux_commerces")
              or 2)
    nb_tot = rnc_data.get("nombre_total_lots", 3)
    new_copro = {
        "numero_immatriculation": IMMAT_NEW,
        "nom_copropriete": rnc_data.get("nom_usage_copropriete") or "LE DAUPHINE",
        "syndic": rnc_data.get("nom_societe_mandataire") or "",
        "_syndic_src": "rnc_live",
        "adresse": rnc_data.get("adresse_reference", ""),
        "longitude": a_ancre_e5.get("longitude"),
        "latitude": a_ancre_e5.get("latitude"),
        "code_iris": a_ancre_e5.get("code_iris"),
        "cle_adresse": E5_ANCRE,
        "nb_lots_total": nb_tot,
        "nb_lots_habitation": nb_hab,
        "nb_lots_habitation_rnc": nb_hab,
        "nb_log_bdnb": a_ancre_e5.get("nb_log_bdnb", 2),
        "nb_ventes_2021_2025": 0,
        "ventes_par_an": {},
        "taux_rotation_5ans": 0.0,
        "classement_rotation": "Fige",
        "_injection_correctif": "fix_st_philippe_dauphine_e5_2026-05-23",
    }
    co.append(new_copro)
    print(f"  INJECT copro {IMMAT_NEW} : nom='{new_copro['nom_copropriete']}', "
          f"tot={nb_tot}, hab={nb_hab}, cle='{E5_ANCRE}'")

# Propagation sur 2 ST PHILIPPE (ATTRIBUER)
nb_hab_for_prop = next((c["nb_lots_habitation"] for c in co
                         if c.get("numero_immatriculation") == IMMAT_NEW), 2)
nom_copro_for_prop = next((c["nom_copropriete"] for c in co
                            if c.get("numero_immatriculation") == IMMAT_NEW), "LE DAUPHINE")
a_ancre_e5["numero_immatriculation"] = IMMAT_NEW
a_ancre_e5["nb_lots_habitation"] = nb_hab_for_prop
a_ancre_e5["taux_rotation"] = 0.0
a_ancre_e5["classement_rotation"] = "Fige"
print(f"  ATTRIBUER {E5_ANCRE} : immat={IMMAT_NEW}, lots_hab={nb_hab_for_prop}, taux=0, classement='Fige'")

# RE-POINT 20 DAUPHINE
bgid_ancre_e5 = a_ancre_e5.get("batiment_groupe_id")
bgid_repoint_avant = a_repoint_e5.get("batiment_groupe_id")
fa_cible_avant = a_repoint_e5.get("_fusion_cible")
a_repoint_e5["batiment_groupe_id"] = bgid_ancre_e5
a_repoint_e5["_fusion_auto"] = True
a_repoint_e5["_fusion_cible"] = E5_ANCRE
print(f"  RE-POINT {E5_REPOINT} : bgid {bgid_repoint_avant} -> {bgid_ancre_e5}")
print(f"  RE-FUSE  {E5_REPOINT} : cible '{fa_cible_avant}' -> '{E5_ANCRE}'")

# Label sur 2 ST PHILIPPE
a_ancre_e5["_fusion_auto_label"] = "2 RUE ST PHILIPPE / 20 RUE DAUPHINE"
a_ancre_e5["_fusion_auto_sources"] = [E5_REPOINT]
print(f"  LABEL {E5_ANCRE} : '2 RUE ST PHILIPPE / 20 RUE DAUPHINE'")

# Cleanup 18 DAUPHINE (perd 20 dans sa chain)
sources_18 = a_old_ancre_e5.get("_fusion_auto_sources") or []
if E5_REPOINT in sources_18:
    new_sources_18 = [s for s in sources_18 if s != E5_REPOINT]
    a_old_ancre_e5["_fusion_auto_sources"] = new_sources_18 if new_sources_18 else None
    if not new_sources_18:
        # plus aucune source -> retirer label
        a_old_ancre_e5.pop("_fusion_auto_label", None)
        a_old_ancre_e5.pop("_fusion_auto_sources", None)
    print(f"  CLEANUP {E5_OLD_ANCRE} : sources {sources_18} -> {new_sources_18}")
else:
    print(f"  IDEMPOTENT : {E5_OLD_ANCRE} sources sans {E5_REPOINT}")

# Verifs in-memory
if a_ancre_e5.get("numero_immatriculation") != IMMAT_NEW: fail("E5 immat propagation manque")
if a_repoint_e5.get("_fusion_cible") != E5_ANCRE: fail("E5 RE-FUSE incorrect")
if a_repoint_e5.get("batiment_groupe_id") != bgid_ancre_e5: fail("E5 RE-POINT incorrect")
if E5_REPOINT in (a_old_ancre_e5.get("_fusion_auto_sources") or []):
    fail("E5 cleanup 18 DAUPH echoue")
print(f"  >>> PHASE D light OK (in-memory)")

# Apply KV DELETE 2 ST PHILIPPE
print()
print("  KV DELETE 2 ST PHILIPPE (hygiene mono orphelin -> copro RNC) :")
kv_d = kv_get()
assigns_d = kv_d.get("assignments") or {}
if E5_ANCRE in assigns_d:
    new_assigns_d = {k:v for k,v in assigns_d.items() if k != E5_ANCRE}
    kv_post({"assignments": new_assigns_d,
             "fusions": kv_d.get("fusions") or {},
             "noms": kv_d.get("noms") or {}})
    kv_d2 = kv_get()
    if E5_ANCRE in (kv_d2.get("assignments") or {}):
        fail(f"E5 KV DELETE {E5_ANCRE} : verif echec")
    print(f"  KV DELETE OK : {E5_ANCRE} retire")
    print(f"  KV : {len(assigns_d)} -> {len(kv_d2.get('assignments') or {})}")
    KV_LOCAL.write_text(json.dumps(kv_d2, ensure_ascii=False), encoding="utf-8")
else:
    print(f"  IDEMPOTENT : {E5_ANCRE} deja absent KV")
print(f"  >>> PHASE D OK")


# ============================================================
# ECRITURE light.json (apres toutes phases light B+C+D)
# ============================================================
section("ECRITURE light.json (post B/C/D)")
LIGHT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"  light.json ecrit : {LIGHT.name}")

# Verif lecture
doc_check = json.loads(LIGHT.read_text(encoding="utf-8"))
n_co = len(doc_check["coproprietes"])
n_ad = len(doc_check["adresses"])
inj_present = any(c.get("numero_immatriculation") == IMMAT_NEW for c in doc_check["coproprietes"])
print(f"  Re-read : {n_ad} ad ({len(doc['adresses'])} attendu)  {n_co} co ({len(doc['coproprietes'])} attendu)")
print(f"  INJECT {IMMAT_NEW} present : {inj_present}")
if n_ad != len(doc["adresses"]) or n_co != len(doc["coproprietes"]):
    fail("light.json re-read mismatch")
if not inj_present:
    fail(f"INJECT {IMMAT_NEW} absent apres re-read")

# Verif les modifs B/C/D persistent
ad_check = {(a.get("cle") or ""): a for a in doc_check["adresses"]}
def ck(c, k, v, name):
    actual = c.get(k) if c else None
    if actual != v:
        fail(f"VERIF post-write : {name}.{k} = {actual!r} (attendu {v!r})")
    return True

# E2 verifs
ck(ad_check.get(E2_REPOINT), "batiment_groupe_id", bgid_ancre_e2, E2_REPOINT)
ck(ad_check.get(E2_ANCRE), "_fusion_auto_label", "24 RUE GABILLOT / 233 RUE PAUL BERT", E2_ANCRE)
print(f"  E2 verifs OK")
# E4 verifs
ck(ad_check.get(E4_FUSE), "batiment_groupe_id", bgid_ancre_e4, E4_FUSE)
ck(ad_check.get(E4_FUSE), "_fusion_cible", E4_ANCRE, E4_FUSE)
ck(ad_check.get(E4_ANCRE), "_fusion_auto_label", "4/6 RUE MILIEU", E4_ANCRE)
print(f"  E4 verifs OK")
# E5 verifs
ck(ad_check.get(E5_ANCRE), "numero_immatriculation", IMMAT_NEW, E5_ANCRE)
ck(ad_check.get(E5_REPOINT), "_fusion_cible", E5_ANCRE, E5_REPOINT)
ck(ad_check.get(E5_REPOINT), "batiment_groupe_id", bgid_ancre_e5, E5_REPOINT)
# 18 DAUPH cleanup
s_18 = ad_check.get(E5_OLD_ANCRE, {}).get("_fusion_auto_sources")
if s_18 and E5_REPOINT in s_18:
    fail(f"E5 cleanup 18 DAUPH echoue : sources contient encore {E5_REPOINT}")
print(f"  E5 verifs OK")

print()
print("=" * 90)
print(">>> TOUTES PHASES APPLIQUEES + VERIFIEES (A KV / B light / C light+KV / D light+KV)")
print(f"    light.json {len(doc['adresses'])} ad, {len(doc['coproprietes'])} co")
print(f"    backups : prephaseA.bak (KV), prephasesBCD.bak (light)")
print(f"    COMMIT a faire manuellement par l'orchestrateur, PAS DE PUSH")
print("=" * 90)
