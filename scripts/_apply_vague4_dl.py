#!/usr/bin/env python3
"""Vague 4 DL : 6 fixes simples (REBIND/RE-FUSE univoques) avec scan DVF integre.
Dry-run par defaut, --apply pour ecrire."""
import json, sys, shutil, argparse, unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
FULL  = ROOT / "data" / "secteur_dauphine_lacassagne.json"
BAK   = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.prev4.bak"

FIXES = [
    {"id":"F1","tag":"316pb_314pb",
     "label":"PAUL BERT 314/316 (AH0111229)",
     "ancre":"314|RUE|PAUL BERT","immat":"AH0111229",
     "src":"316|RUE|PAUL BERT","old_cible":"318|RUE|PAUL BERT"},
    {"id":"F2","tag":"3pehu_30philippe",
     "label":"SDC LES DOMES ST PHILIPPE (AC3393907)",
     "ancre":"30|RUE|ST PHILIPPE","immat":"AC3393907",
     "src":"3|RUE|MARCEL PEHU","old_cible":"23|RUE|ST MAXIMIN"},
    {"id":"F3","tag":"7sisley_aprim",
     "label":"APRIM (disambig #AI9420605)",
     "ancre":"7|RUE|PROFESSEUR PAUL SISLEY #AI9420605","immat":"AI9420605",
     "src":"7|RUE|PROFESSEUR PAUL SISLEY","old_cible":"7B|RUE|PROFESSEUR PAUL SISLEY"},
    {"id":"F4","tag":"9montbr_privilege_c",
     "label":"LE PRIVILEGE MONTBRILLANT C (disambig #AB6220503)",
     "ancre":"9|RUE|MONTBRILLANT #AB6220503","immat":"AB6220503",
     "src":"9|RUE|MONTBRILLANT","old_cible":"9B|RUE|MONTBRILLANT"},
    {"id":"F5","tag":"5montbr_parmilleux",
     "label":"LE PARMILLEUX (disambig #AA9380684)",
     "ancre":"5|RUE|MONTBRILLANT #AA9380684","immat":"AA9380684",
     "src":"5|RUE|MONTBRILLANT","old_cible":"5B|RUE|MONTBRILLANT"},
    {"id":"F6","tag":"3bara_bara",
     "label":"BARA (disambig #AE6121685)",
     "ancre":"3|RUE|BARA #AE6121685","immat":"AE6121685",
     "src":"3|RUE|BARA","old_cible":None},  # RE-FUSE Cambronne, no fauto
]

KV_DELETE_CLES = ["3|RUE|BARA"]  # copro_non_immat -> fauto


def to_int(x):
    try: return int(x)
    except: return 0
def to_float(x):
    try: return float(str(x).replace(",", "."))
    except: return 0.0


# ---------- DVF normalisation ----------
PARTICLES = {"de","du","la","le","les","des","d'","l'","au","aux"}
SAINT_MAP = {"saint":"ST","sainte":"STE","st":"ST","ste":"STE"}
def strip_accents(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode("ascii")
def voie_tokens(voie):
    out = set()
    for tok in voie.replace("-", " ").split():
        wl = strip_accents(tok).lower().rstrip(".")
        if not wl: continue
        if wl in PARTICLES: continue
        if wl in SAINT_MAP: out.add(SAINT_MAP[wl])
        else: out.add(strip_accents(tok).upper())
    return out
def cle_to_filter(cle):
    # Strip disambig suffix #IMMAT
    if " #" in cle: cle = cle.split(" #", 1)[0]
    num, _t, voie = cle.split("|", 2)
    suff = ""
    if num and num[-1].isalpha(): suff = num[-1].upper(); num = num[:-1]
    return num, suff, voie_tokens(voie)
def date_iso(d):
    try: j, mo, a = d.split("/"); return f"{a}-{mo}-{j}"
    except: return d


def scan_dvf(mutations, cles):
    """Compte ventes log + derniere + median EUR/m2 pour la liste de cles."""
    cle_filters = {c: cle_to_filter(c) for c in cles}
    by_cle = defaultdict(list)
    for m in mutations:
        nv = str(m.get("No voie","")).strip()
        btq = str(m.get("B/T/Q","")).strip().upper()
        v = str(m.get("Voie","")).strip()
        v_toks = voie_tokens(v)
        for c, (n, s, vs) in cle_filters.items():
            if nv == n and btq == s and vs == v_toks:
                by_cle[c].append(m); break
    return by_cle


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not LIGHT.exists(): sys.exit("light absent")
    doc = json.loads(LIGHT.read_text(encoding="utf-8"))
    md = doc.setdefault("metadata", {})
    if md.get("_correctif_vague4_dl") and not args.apply:
        print("  [info] marker deja present.")
    by_cle = {(a.get("cle") or ""): a for a in doc["adresses"]}
    co_by_immat = {c.get("numero_immatriculation"): c for c in doc["coproprietes"]
                   if c.get("numero_immatriculation")}

    # DVF scan
    full = json.loads(FULL.read_text(encoding="utf-8"))
    mutations = full.get("mutations_dvf") or []
    all_src_cles = [fx["src"] for fx in FIXES]
    dvf_by_cle = scan_dvf(mutations, all_src_cles)

    print("=" * 110)
    print(f"VAGUE 4 DL  ({'APPLY' if args.apply else 'DRY-RUN'})  -- 6 fixes simples")
    print("=" * 110)

    total_delta = 0
    log = []

    for fx in FIXES:
        print()
        print(f"--- {fx['id']} [{fx['tag']}]  {fx['label']}")
        a_anc = by_cle.get(fx["ancre"])
        if not a_anc:
            print(f"  [SKIP] ancre absente: {fx['ancre']}"); continue
        bg_anc = a_anc.get("batiment_groupe_id") or ""
        co = co_by_immat.get(fx["immat"])
        if co:
            print(f"  copro snapshot : nom={co.get('nom_copropriete')!r}  lots_tot={co.get('nb_lots_total')}  hab={co.get('nb_lots_habitation')}  syndic={co.get('syndic')!r}")

        a_src = by_cle.get(fx["src"])
        if not a_src:
            print(f"  [SKIP] src absent: {fx['src']}"); continue
        bg_cur = a_src.get("batiment_groupe_id") or ""
        cur_cible = a_src.get("_fusion_cible")
        bdnb_src = to_int(a_src.get("nb_log_bdnb"))
        op_name = "REBIND" if a_src.get("_fusion_auto") else "RE-FUSE"
        print(f"  [{op_name if args.apply else 'DRY'}] {fx['src']:42s}  bgid ...{bg_cur[-9:]} -> ...{bg_anc[-9:]}  bdnb={bdnb_src}  ex-cible='{cur_cible}'")

        # DVF
        dvf_muts = dvf_by_cle.get(fx["src"], [])
        log_dvf = [m for m in dvf_muts if to_float(m.get("Surface Carrez du 1er lot")) > 0 or to_float(m.get("Surface reelle bati")) > 0 or to_float(m.get("Valeur fonciere")) >= 30000]
        if dvf_muts:
            log_dvf.sort(key=lambda m: date_iso(m.get("Date mutation","")), reverse=True)
            last = log_dvf[0] if log_dvf else dvf_muts[0]
            print(f"  DVF src : {len(log_dvf)} log ({len(dvf_muts)} mut)  derniere {date_iso(last.get('Date mutation',''))} {to_float(last.get('Valeur fonciere')):,.0f} EUR".replace(",", " "))
        else:
            print(f"  DVF src : 0 mutation")

        if args.apply:
            a_src["_fusion_auto"] = True
            a_src["_fusion_cible"] = fx["ancre"]
            a_src["_bdnb_match"] = f"correctif_v4_{fx['tag']}_rebind"
            a_src["batiment_groupe_id"] = bg_anc
            log.append({"op":op_name,"cle":fx["src"],"cible":fx["ancre"],
                        "old_cible":cur_cible,"old_bgid":bg_cur})

            # Label sur ancre
            label_full = f"{fx['ancre'].replace('|',' ')} (sources fusees) / {fx['src'].replace('|',' ')}"
            a_anc["_fusion_auto_label"] = label_full
            srcs = list(a_anc.get("_fusion_auto_sources") or [])
            if fx["src"] not in srcs: srcs.append(fx["src"])
            a_anc["_fusion_auto_sources"] = srcs
            log.append({"op":"LABEL","cle":fx["ancre"],"label":label_full,"sources":srcs})

        # Dedup check
        if args.apply:
            bg_global = defaultdict(list)
            for a in doc["adresses"]:
                bgg = a.get("batiment_groupe_id") or ""
                if bgg: bg_global[bgg].append(a.get("cle") or "")
            if not bg_global.get(bg_cur):
                if bdnb_src:
                    total_delta -= bdnb_src
                    print(f"  bgid ...{bg_cur[-9:]} SUPPRIME -> -{bdnb_src}")

    if args.apply:
        md["_correctif_vague4_dl"] = {
            "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pattern":"Vague 4 DL : 6 fixes simples REBIND/RE-FUSE univoques + 4 disambig #immat",
            "fixes":[{"id":f["id"],"tag":f["tag"],"src":f["src"],"ancre":f["ancre"],
                      "immat":f["immat"]} for f in FIXES],
            "log":log,
            "delta_parc_dedup":total_delta,
        }
        if BAK.exists(): print(f"  [warn] backup existant -> ecrase")
        shutil.copy2(LIGHT, BAK)
        print(f"\n  [bak] {BAK.name}")
        LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [OK] LIGHT ecrit ({len(doc['adresses'])} adresses)")

    print()
    print("=" * 110)
    print(f"TOTAL DELTA dedup : {total_delta:+d} log")
    print("=" * 110)


if __name__ == "__main__":
    main()
