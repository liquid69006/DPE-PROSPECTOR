#!/usr/bin/env python3
"""
Diag ensemble 224 COURS LAFAYETTE + 215 RUE BONNEL (DL) - lecture seule.

ETAPES :
  1) light : bgid, immat, parcelle, bdnb, fauto, KV
  2) RNC live : ref_cad sur parcelles + adresse_complementaire matching
  3) BDNB : l_libelle_adr (pivot)
  4) Mecanisme propose + delta parc estime
"""
import json, os, sys, time, urllib.parse, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
os.environ.setdefault("PYTHONUTF8", "1")

ROOT  = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
KV    = ROOT / "data" / "_kv_assign_dl.json"
CACHE_BG  = ROOT / "data" / "_bgid_parcelle_dl.json"
CACHE_RNC = ROOT / "data" / "_scan_parc_rnc_dl.json"

RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
TAB = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"
BDNB_PARC = "https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_parcelle?batiment_groupe_id=eq."
BDNB_ADR  = "https://api.bdnb.io/v1/bdnb/donnees/rel_batiment_groupe_adresse?batiment_groupe_id=eq."


def to_int(x):
    try: return int(x)
    except Exception: return 0


# ---------- Caches + fetchers ----------
cache_bg  = json.loads(CACHE_BG.read_text(encoding="utf-8")) if CACHE_BG.exists() else {}
cache_rnc = json.loads(CACHE_RNC.read_text(encoding="utf-8")) if CACHE_RNC.exists() else {}


def bdnb_to_rnc(p):
    if not p or len(p) < 14: return None
    if p[:2] == "69" and p[5:8] == "000": return "69123383" + p[8:]
    if p[:2] == "75" and p[5:8] == "000": return "75056" + p[2:5] + p[8:]
    return None


def fetch_bdnb_parcelles(bgid):
    if not bgid: return []
    if bgid in cache_bg: return cache_bg[bgid]
    try:
        with urllib.request.urlopen(BDNB_PARC + bgid, timeout=20) as r:
            parcs = [x.get("parcelle_id") for x in json.loads(r.read()) if x.get("parcelle_id")]
    except Exception as e:
        print(f"   ! BDNB parcelle err {bgid}: {e}"); parcs = []
    cache_bg[bgid] = parcs
    time.sleep(0.05)
    return parcs


def fetch_bdnb_adr_libelle(bgid):
    """l_libelle_adr du bati (pivot, plus large que cle UI)."""
    if not bgid: return ""
    try:
        with urllib.request.urlopen(BDNB_ADR + bgid + "&order=classe_adresse.asc", timeout=20) as r:
            rows = json.loads(r.read())
        # rel_batiment_groupe_adresse a l_libelle_adr concatene
        labs = sorted({(x.get("libelle_adr_principale_ban") or "") for x in rows
                       if x.get("libelle_adr_principale_ban")})
        return " | ".join(labs)
    except Exception as e:
        return f"(err: {e})"


def fetch_rnc_by_refcad(parc_rnc):
    if not parc_rnc: return []
    if parc_rnc in cache_rnc: return cache_rnc[parc_rnc]
    seen = {}
    for col in ("reference_cadastrale_1","reference_cadastrale_2","reference_cadastrale_3"):
        url = TAB + "?" + urllib.parse.urlencode({f"{col}__exact": parc_rnc})
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read()).get("data", [])
        except Exception as e:
            print(f"   ! RNC live err {col}={parc_rnc}: {e}"); data = []
        for row in data:
            im = row.get("numero_immatriculation")
            if im and im not in seen:
                seen[im] = {
                    "immat": im,
                    "nom":     row.get("nom_usage_copropriete") or "",
                    "syndic":  row.get("nom_personne_morale") or "",
                    "adresse_ref": row.get("adresse_reference") or "",
                    "adresse_compl_1": row.get("adresse_complementaire_1") or "",
                    "adresse_compl_2": row.get("adresse_complementaire_2") or "",
                    "lots_tot": row.get("nombre_total_lots"),
                    "lots_hab": row.get("nombre_lots_usage_habitation"),
                    "date_immat": row.get("date_premiere_immatriculation") or "",
                    "ref_col": col,
                    "ref_cad_1": row.get("reference_cadastrale_1"),
                    "ref_cad_2": row.get("reference_cadastrale_2"),
                    "ref_cad_3": row.get("reference_cadastrale_3"),
                }
        time.sleep(0.08)
    out = list(seen.values())
    cache_rnc[parc_rnc] = out
    return out


def fetch_rnc_by_adresse(query):
    """Recherche par adresse_reference (fallback)."""
    out = []
    for col in ("adresse_reference", "adresse_complementaire_1", "adresse_complementaire_2"):
        url = TAB + "?" + urllib.parse.urlencode({f"{col}__contains": query.upper()})
        try:
            req = urllib.request.Request(url, headers={"Accept":"application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read()).get("data", [])
        except Exception as e:
            print(f"   ! RNC adr err {col}={query}: {e}"); data = []
        for row in data:
            im = row.get("numero_immatriculation")
            if not im or any(x["immat"] == im for x in out): continue
            out.append({
                "immat": im, "match_col": col,
                "nom": row.get("nom_usage_copropriete") or "",
                "syndic": row.get("nom_personne_morale") or "",
                "adresse_ref": row.get("adresse_reference") or "",
                "adresse_compl_1": row.get("adresse_complementaire_1") or "",
                "adresse_compl_2": row.get("adresse_complementaire_2") or "",
                "lots_tot": row.get("nombre_total_lots"),
                "lots_hab": row.get("nombre_lots_usage_habitation"),
                "ref_cad_1": row.get("reference_cadastrale_1"),
                "ref_cad_2": row.get("reference_cadastrale_2"),
                "ref_cad_3": row.get("reference_cadastrale_3"),
            })
        time.sleep(0.1)
    return out


# ---------- Data ----------
doc = json.loads(LIGHT.read_text(encoding="utf-8"))
ad_by_cle = {(a.get("cle") or ""): a for a in doc["adresses"]}
co_by_cle = {(c.get("cle_adresse") or ""): c for c in doc["coproprietes"]}
co_by_immat = {c.get("numero_immatriculation"): c for c in doc["coproprietes"]
               if c.get("numero_immatriculation")}
immat_secteur = set(co_by_immat.keys())
kv = json.loads(KV.read_text(encoding="utf-8"))
assigns = kv.get("assignments") or {}
fusions = kv.get("fusions") or {}
fusion_tgts = set(fusions.values())


def kv_type(cle):
    if cle in assigns: return (assigns[cle] or {}).get("type")
    if cle in fusions: return f"fusion-src->{fusions[cle]}"
    if cle in fusion_tgts: return "fusion-tgt"
    return None


CIBLES = ["224|COURS|LAFAYETTE", "215|RUE|BONNEL"]


# ---------- ETAPE 1 : light ----------
print("=" * 110)
print("ETAPE 1 - LIGHT (snapshot local)")
print("=" * 110)
rows = []
for c in CIBLES:
    a  = ad_by_cle.get(c)
    co = co_by_cle.get(c)
    if not a:
        # essayer variantes BD/BOULEVARD/RUE etc
        candidates = [k for k in ad_by_cle if c.split("|",2)[-1] in k and c.split("|")[0] in k]
        print(f"  {c:40s} ABSENT direct ; candidats proches : {candidates[:5]}")
        rows.append({"cle": c, "absent": True}); continue
    bg = a.get("batiment_groupe_id") or ""
    rows.append({
        "cle": c, "absent": False, "in_co": bool(co),
        "bgid": bg,
        "immat": a.get("numero_immatriculation") or (co or {}).get("numero_immatriculation") or "",
        "bdnb":  to_int(a.get("nb_log_bdnb")),
        "vlog":  to_int(a.get("nb_ventes_logement")),
        "rot":   a.get("taux_rotation_logement"),
        "bdnb_match": a.get("_bdnb_match"),
        "fauto":      a.get("_fusion_auto"),
        "fauto_cible": a.get("_fusion_cible"),
        "sci":   a.get("sci_proprietaire") == "oui",
        "sci_nom": a.get("sci_nom"),
        "kv":    kv_type(c),
        "nom_copro": (co or {}).get("nom_usage_copropriete"),
        "lots_tot":  (co or {}).get("nombre_total_lots"),
        "lots_hab":  (co or {}).get("nombre_lots_usage_habitation"),
    })
    bg9 = "..." + bg[-9:] if bg else "-"
    print(f"  {c:40s}")
    print(f"      bgid={bg9}  in_co={bool(co)}  immat={rows[-1]['immat'] or '-'}  "
          f"bdnb={rows[-1]['bdnb']}  vlog={rows[-1]['vlog']}  rot={rows[-1]['rot']}")
    print(f"      bdnb_match={rows[-1]['bdnb_match']!r}  fauto={rows[-1]['fauto']!r}  "
          f"cible={rows[-1]['fauto_cible']!r}")
    print(f"      SCI proprio={rows[-1]['sci']}  SCI nom={rows[-1]['sci_nom']!r}  "
          f"KV={rows[-1]['kv'] or '(non-q)'}")
    if co:
        print(f"      copro snapshot : nom={rows[-1]['nom_copro']!r}  lots_tot={rows[-1]['lots_tot']}  "
              f"hab={rows[-1]['lots_hab']}")


# ---------- ETAPE 2 : RNC live ----------
print()
print("=" * 110)
print("ETAPE 2 - RNC live (ref_cad + adresse_complementaire)")
print("=" * 110)
all_parcs = []
for r in rows:
    if r.get("absent"): continue
    bg = r["bgid"]
    if not bg: continue
    parcs_bg = fetch_bdnb_parcelles(bg)
    parcs_rnc = [bdnb_to_rnc(p) for p in parcs_bg if bdnb_to_rnc(p)]
    all_parcs.extend(parcs_rnc)
    print(f"  {r['cle']:40s}  parcelles BDNB={parcs_bg}  RNC={parcs_rnc}")
    r["parcs_bg"] = parcs_bg
    r["parcs_rnc"] = parcs_rnc

parcs_unique = sorted(set(all_parcs))
print(f"  Parcelles RNC distinctes : {parcs_unique}")

if parcs_unique != list(set(all_parcs)) or len(parcs_unique) >= 1:
    print()
    print("  --- Scan RNC par ref_cad ---")
    cands_refcad = {}
    for pr in parcs_unique:
        hits = fetch_rnc_by_refcad(pr)
        for h in hits:
            cands_refcad.setdefault(h["immat"], h)
        print(f"    parc {pr} -> {len(hits)} cand(s)")
        for h in hits:
            tag = " [DEJA-SECTEUR]" if h["immat"] in immat_secteur else " >>> NOUVEAU"
            print(f"      {tag}  {h['immat']}  '{(h['nom'] or '')[:38]}'  "
                  f"lots_tot={h['lots_tot']} hab={h['lots_hab']}  "
                  f"ref1={h.get('ref_cad_1')}  ref2={h.get('ref_cad_2')}")
            if h.get("adresse_ref"):
                print(f"         adr_ref       : {h['adresse_ref']}")
            if h.get("adresse_compl_1"):
                print(f"         adr_compl_1   : {h['adresse_compl_1']}")
            if h.get("adresse_compl_2"):
                print(f"         adr_compl_2   : {h['adresse_compl_2']}")

# ---------- Recherche par adresse (au cas ou ref_cad RNC vide) ----------
print()
print("  --- Recherche RNC live par adresse_reference / complementaire ---")
queries = ["224", "215 BONNEL", "224 LAFAYETTE"]
seen_im = set()
hits_adr = []
for q in queries:
    hits = fetch_rnc_by_adresse(q)
    new_hits = [h for h in hits if h["immat"] not in seen_im]
    seen_im.update(h["immat"] for h in new_hits)
    # filtre Lyon 3e / 69123 / 69003 / mention LAFAYETTE ou BONNEL
    relevant = []
    for h in new_hits:
        txt = " ".join([h.get("adresse_ref",""), h.get("adresse_compl_1",""),
                        h.get("adresse_compl_2","")]).upper()
        if "LAFAYETTE" in txt or "BONNEL" in txt:
            if "69" in txt and ("003" in txt or "Lyon" in txt or "LYON" in txt):
                relevant.append(h)
            else:
                # garder quand meme si LAFAYETTE+BONNEL ensemble
                if "LAFAYETTE" in txt and "BONNEL" in txt:
                    relevant.append(h)
    print(f"    query '{q}' -> {len(hits)} cand(s), {len(relevant)} pertinent(s) (LAFAYETTE/BONNEL Lyon)")
    for h in relevant:
        hits_adr.append(h)
        tag = " [DEJA-SECTEUR]" if h["immat"] in immat_secteur else " >>> NOUVEAU"
        print(f"      {tag}  {h['immat']}  '{(h['nom'] or '')[:36]}'  "
              f"lots_tot={h['lots_tot']} hab={h['lots_hab']}  match={h['match_col']}")
        print(f"         adr_ref       : {h['adresse_ref']}")
        if h.get("adresse_compl_1"): print(f"         adr_compl_1   : {h['adresse_compl_1']}")
        if h.get("adresse_compl_2"): print(f"         adr_compl_2   : {h['adresse_compl_2']}")
        print(f"         ref_cad : {h.get('ref_cad_1')} / {h.get('ref_cad_2')} / {h.get('ref_cad_3')}")
        print(f"         syndic  : {h.get('syndic')}")


# ---------- ETAPE 3 : BDNB l_libelle_adr ----------
print()
print("=" * 110)
print("ETAPE 3 - BDNB rel_batiment_groupe_adresse (pivot l_libelle_adr)")
print("=" * 110)
for r in rows:
    if r.get("absent") or not r["bgid"]: continue
    lab = fetch_bdnb_adr_libelle(r["bgid"])
    print(f"  {r['cle']:40s}  bgid=...{r['bgid'][-9:]}")
    print(f"     l_libelle_adr : {lab}")


# Persistance cache
CACHE_BG.write_text(json.dumps(cache_bg, ensure_ascii=False, indent=2), encoding="utf-8")
CACHE_RNC.write_text(json.dumps(cache_rnc, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- ETAPE 4 : mecanisme propose ----------
print()
print("=" * 110)
print("ETAPE 4 - DIAGNOSTIC + MECANISME PROPOSE")
print("=" * 110)
present = [r for r in rows if not r.get("absent")]
bgids = sorted({r['bgid'] for r in present if r['bgid']})
parcs = sorted({p for r in present for p in (r.get('parcs_bg') or [])})
immats_snapshot = [r['immat'] for r in present if r['immat']]
new_cands = []  # collectes ci-dessous
# combiner refcad + adr
all_cands = list(hits_adr)
for h in (cache_rnc.get(p, []) for p in parcs_unique):
    pass  # deja imprime

print(f"  Adresses presentes en light : {len(present)}/{len(CIBLES)}")
print(f"  bgids distincts             : {len(bgids)} ({['...'+b[-9:] for b in bgids]})")
print(f"  parcelles BDNB distinctes   : {len(parcs)}")
print(f"  immats RNC dans snapshot    : {immats_snapshot}")
print(f"  RNC live cands par adresse  : {len(hits_adr)}")

# Heuristique mecanisme :
if len(present) < 2:
    print("  >>> Une des 2 adresses ABSENTE du light - probablement INJECT label-only requis")
elif immats_snapshot:
    print(f"  >>> Ancre RNC presente : {immats_snapshot[0]}")
    print(f"      Mecanisme probable : RE-FUSE Cambronne (si parcelle commune) ou Fondary (multi-parc)")
elif hits_adr:
    print(f"  >>> RNC live NOUVELLE detectee : {[h['immat'] for h in hits_adr]}")
    print(f"      Mecanisme probable : INJECT copro + attribution ancre + RE-FUSE de l'autre")
else:
    print(f"  >>> Aucun RNC trouve - pattern ETIQUETAGE pur (pivot interne)")

print()
print("  Calcul Delta parc estime depend du resultat ci-dessus :")
for r in present:
    print(f"    {r['cle']:40s}  bdnb={r['bdnb']}  -> contribue actuellement BDNB={r['bdnb']} sur bgid {('...'+r['bgid'][-9:]) if r['bgid'] else '-'}")
