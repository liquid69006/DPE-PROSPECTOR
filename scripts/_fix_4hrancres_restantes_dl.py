#!/usr/bin/env python3
"""4 corrections DL hr-ancres restantes (apres batch5).

Dry-run par defaut, '--apply' pour ecrire.

CORRECTION 1 (KV-only) :
  8B|RUE|FRANCOIS GILLET : social -> copro_non_immat
  Justification : 6 SIRENs distincts sur DX0034 (OPH 42.9% + 5 SCI/SAS),
  ratio MAJIC 21/52 = 40% (parc BDNB sous-couvert), c'est une vraie
  copro mixte non immatriculee, pas du social pur.

CORRECTION 2 (light bgid switch + RE-FUSE + KV social) :
  13B|RUE|DAUPHINE : meme ensemble que 7/9/11/13 RUE DAUPHINE (HBM
  Ville de Lyon / SACVL, bail emphyteotique sur parcelle AZ0071).
  Preuve : MAJIC AZ0071 contient '13B RUE DU DAUPHINE' 48 lots.
  - light : bgid bdnb-bg-S3VN-5QYG-KUV9 -> bdnb-bg-L2AS-75JZ-QX89
    (ancre 11 DAUPH), _fusion_auto=True, target=11|RUE|DAUPHINE
  - KV : POST {type:'social'} (absent du KV avant)
  Parc UI strict neutre (dedup par bgid : 13B partage desormais 75JZ-QX89
  avec 7/9/11/13).

CORRECTION 3 (light RE-FUSE strict Cambronne) :
  26B|RUE|CITE : meme bgid que 26 CITE (deja _fusion_auto vers
  ALLEE DES POETES AA0823708).
  - light : _fusion_auto=True, target=26|RUE|CITE (bgid deja identique)
  - KV : absent, rien
  Parc UI strict neutre (meme bgid).

CORRECTION 4 (light bgid switch + RE-FUSE) :
  14B|RUE|ESPERANCE : 14B physique = ensemble L'EMERAUDE 12/14/16
  ESPERANCE. BDNB lui attribuait par erreur le bgid XW3B-67GS
  (= bgid 15 ESPERANCE cote impair).
  - light : bgid bdnb-bg-5JEU-XW3B-67GS -> bdnb-bg-NZ67-8FQ2-8L1E
    (ancre 14 ESP, immat AA8145336), _fusion_auto=True,
    target=14|RUE|ESPERANCE
  - KV : absent, rien
  Parc UI strict neutre (dedup par bgid : 14B partage NZ67-8FQ2-8L1E
  avec 14/16 ESP).

Backups :
  light : secteur_dauphine_lacassagne_light.json.pre4hrancres.bak
  KV    : _kv_assign_dl.json.pre4hrancres.bak (deja remplace si rerun)
"""
import argparse, json, os, sys, shutil, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT     = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT    = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV_LOCAL = ROOT / "data" / "_kv_assign_dl.json"
BAK_LT   = LIGHT.with_suffix(LIGHT.suffix + ".pre4hrancres.bak")
BAK_KV   = KV_LOCAL.with_suffix(KV_LOCAL.suffix + ".pre4hrancres.bak")

API_URL  = "https://dpe-prospector-api.yann-bufferne.workers.dev"
ENDPOINT = f"{API_URL}/secteur-assignments/dauphine-lacassagne"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


# --- Corrections specifications ---
LIGHT_EDITS = [
    {
        "cle": "13B|RUE|DAUPHINE",
        "new_bgid": "bdnb-bg-L2AS-75JZ-QX89",
        "target":   "11|RUE|DAUPHINE",
        "tag":      "manual_2026-05-23_13bdauph_hbm",
    },
    {
        "cle": "26B|RUE|CITE",
        "new_bgid": "bdnb-bg-558F-914A-J3ZK",  # identique a 26 CITE = no-op bgid
        "target":   "26|RUE|CITE",
        "tag":      "manual_2026-05-23_26bcite_cambronne",
    },
    {
        "cle": "14B|RUE|ESPERANCE",
        "new_bgid": "bdnb-bg-NZ67-8FQ2-8L1E",
        "target":   "14|RUE|ESPERANCE",
        "tag":      "manual_2026-05-23_14besp_emeraude",
    },
]

KV_FLIPS = [
    {"cle": "8B|RUE|FRANCOIS GILLET", "expected": "social",
     "new_type": "copro_non_immat", "absent_ok": False},
]

KV_ADDS = [
    {"cle": "13B|RUE|DAUPHINE", "new_type": "social", "must_be_absent": True},
]


# --- Helpers ---
def http(method, url, headers, body=None, timeout=30):
    req = urllib.request.Request(
        url, method=method, headers=headers,
        data=(json.dumps(body).encode("utf-8") if body is not None else None))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def fail(msg):
    print(); print("!" * 90); print(f"!  ECHEC : {msg}"); print("!" * 90); sys.exit(10)


def short(bg): return bg[-9:] if bg else "-"


# --- Main ---
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="ecrire light + POST KV (sinon dry-run)")
    ap.add_argument("--token", default=None,
                    help="token Bearer (sinon argv[2]/env DPE_TOKEN)")
    args = ap.parse_args()

    token = (args.token or os.environ.get("DPE_TOKEN", "")).strip()
    hdr_get  = {"Authorization": f"Bearer {token}", "User-Agent": UA,
                "Accept": "application/json"} if token else None
    hdr_post = {**hdr_get, "Content-Type": "application/json"} if token else None

    print("=" * 95)
    print(f"  4 CORRECTIONS HR-ANCRES DL  ({'APPLY' if args.apply else 'DRY-RUN'})")
    print("=" * 95)

    # 1. Charge light
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    ad = light["adresses"]
    ad_by_cle = {a.get("cle"): a for a in ad}

    # 2. Charge KV live (sinon local en dry-run sans token)
    kv = None
    if token:
        print()
        print("--- GET KV live ---")
        code, raw = http("GET", ENDPOINT, hdr_get)
        if code != 200: fail(f"GET {code}: {raw[:200]}")
        kv = json.loads(raw)
        print(f"  KV live : {len(kv.get('assignments') or {})} assigns, "
              f"{len(kv.get('fusions') or {})} fusions")
    else:
        kv = json.loads(KV_LOCAL.read_text(encoding="utf-8"))
        print(f"  (sans token) KV local : {len(kv.get('assignments') or {})} assigns")
    assigns = kv.get("assignments") or {}

    # 3. Dry-run report - light edits
    print()
    print("--- DRY-RUN light edits ---")
    light_plan = []
    for e in LIGHT_EDITS:
        a = ad_by_cle.get(e["cle"])
        if not a: fail(f"cle {e['cle']!r} introuvable dans light")
        old_bgid = a.get("batiment_groupe_id") or ""
        old_fa   = a.get("_fusion_auto")
        old_tgt  = a.get("_fusion_auto_target")
        bgid_change = (old_bgid != e["new_bgid"])
        fa_change   = (old_fa is not True)
        tgt_change  = (old_tgt != e["target"])
        print(f"  {e['cle']:32s}")
        print(f"    bgid            : {short(old_bgid)} -> {short(e['new_bgid'])}"
              f"   {'(CHANGE)' if bgid_change else '(no-op)'}")
        print(f"    _fusion_auto    : {old_fa!r} -> True"
              f"   {'(CHANGE)' if fa_change else '(no-op)'}")
        print(f"    _fusion_auto_target : {old_tgt!r} -> {e['target']!r}"
              f"   {'(CHANGE)' if tgt_change else '(no-op)'}")
        print(f"    nb_log_bdnb     : {a.get('nb_log_bdnb')} (inchange, dedup bgid UI)")
        # Verify target exists
        tgt = ad_by_cle.get(e["target"])
        if not tgt: fail(f"target {e['target']!r} introuvable dans light")
        print(f"    target verif    : {e['target']} bgid={short(tgt.get('batiment_groupe_id') or '')} "
              f"immat={tgt.get('numero_immatriculation') or '-'}")
        light_plan.append({**e, "_old_bgid": old_bgid, "_old_fa": old_fa, "_old_tgt": old_tgt})
        print()

    # 4. Dry-run report - KV flips
    print("--- DRY-RUN KV flips ---")
    for f in KV_FLIPS:
        cur = assigns.get(f["cle"])
        cur_t = cur.get("type") if isinstance(cur, dict) else None
        ok = (cur_t == f["expected"]) or (f["absent_ok"] and not cur)
        print(f"  {f['cle']:32s}")
        print(f"    actuel  : {cur!r}")
        print(f"    attendu : type={f['expected']!r}")
        print(f"    cible   : type={f['new_type']!r}")
        if cur_t == f["new_type"]:
            print(f"    -> deja a la cible (no-op)")
        elif cur_t != f["expected"]:
            fail(f"flip {f['cle']!r} : etat actuel {cur_t!r} != attendu {f['expected']!r}")
        else:
            print(f"    -> FLIP confirme")
        print()

    print("--- DRY-RUN KV adds (hr-ancres re-fused devenues qualifiables) ---")
    for a_ in KV_ADDS:
        cur = assigns.get(a_["cle"])
        if cur and a_["must_be_absent"]:
            fail(f"add {a_['cle']!r} : DEJA present {cur!r} (attendu absent)")
        print(f"  {a_['cle']:32s} (absent) -> ajout {{type:{a_['new_type']!r}}}")
    print()

    if not args.apply:
        print("=" * 95)
        print("  DRY-RUN OK - rerunner avec --apply pour ecrire")
        print("=" * 95)
        return

    # 5. APPLY
    if not token:
        fail("--apply requiert un token (--token ou DPE_TOKEN)")
    print("=" * 95)
    print("  APPLY")
    print("=" * 95)

    # Backups
    shutil.copy2(LIGHT, BAK_LT);  print(f"  Backup light : {BAK_LT.name}")
    shutil.copy2(KV_LOCAL, BAK_KV); print(f"  Backup KV    : {BAK_KV.name}")

    # Light writes
    print()
    print("--- WRITE light ---")
    for e in light_plan:
        a = ad_by_cle[e["cle"]]
        a["batiment_groupe_id"]    = e["new_bgid"]
        a["_fusion_auto"]          = True
        a["_fusion_auto_target"]   = e["target"]
        a["_fusion_auto_source"]   = e["tag"]
        print(f"  {e['cle']:32s} bgid->{short(e['new_bgid'])} "
              f"_fusion_auto=True target={e['target']}")
    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print(f"  Ecrit : {LIGHT.name} ({len(ad)} adresses, indent=2)")

    # KV POST atomic
    print()
    print("--- POST KV atomic ---")
    new_assigns = dict(assigns)
    for f in KV_FLIPS:
        cur = new_assigns.get(f["cle"])
        cur_t = cur.get("type") if isinstance(cur, dict) else None
        if cur_t != f["new_type"]:
            new_assigns[f["cle"]] = {"type": f["new_type"]}
            print(f"  FLIP  {f['cle']:32s} {cur_t!r} -> {f['new_type']!r}")
    for a_ in KV_ADDS:
        if a_["cle"] not in new_assigns:
            new_assigns[a_["cle"]] = {"type": a_["new_type"]}
            print(f"  ADD   {a_['cle']:32s} -> {a_['new_type']!r}")

    fusions = kv.get("fusions") or {}
    noms    = kv.get("noms") or {}
    code, raw = http("POST", ENDPOINT, hdr_post,
                     body={"assignments": new_assigns, "fusions": fusions, "noms": noms})
    print(f"  POST HTTP {code} : {raw[:200]}")
    if code not in (200, 204): fail(f"POST KO {code}")

    # Re-GET verif
    code, raw = http("GET", ENDPOINT, hdr_get)
    if code != 200: fail(f"Re-GET {code}")
    kv_after = json.loads(raw)
    assigns_after = kv_after.get("assignments") or {}
    print(f"  Re-GET : {len(assigns_after)} assigns")

    errs = []
    for f in KV_FLIPS:
        cur = assigns_after.get(f["cle"])
        cur_t = cur.get("type") if isinstance(cur, dict) else None
        ok = cur_t == f["new_type"]
        print(f"    {f['cle']:32s} -> {cur!r}  {'OK' if ok else 'KO'}")
        if not ok: errs.append((f['cle'], cur_t, f["new_type"]))
    for a_ in KV_ADDS:
        cur = assigns_after.get(a_["cle"])
        cur_t = cur.get("type") if isinstance(cur, dict) else None
        ok = cur_t == a_["new_type"]
        print(f"    {a_['cle']:32s} -> {cur!r}  {'OK' if ok else 'KO'}")
        if not ok: errs.append((a_['cle'], cur_t, a_["new_type"]))
    if errs:
        fail(f"verif KV : {len(errs)} erreur(s)")

    KV_LOCAL.write_text(json.dumps(kv_after, ensure_ascii=False), encoding="utf-8")
    print(f"  Sync KV local : {KV_LOCAL.name}")

    print()
    print("=" * 95)
    print(f">>> SUCCES")
    print(f"    Light  : {len(LIGHT_EDITS)} adresses re-fused")
    print(f"    KV     : {len(KV_FLIPS)} flip(s) + {len(KV_ADDS)} ajout(s) "
          f"({len(assigns)} -> {len(assigns_after)})")
    print("=" * 95)


if __name__ == "__main__":
    main()
