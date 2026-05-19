"""
Diagnostic SURGICAL (LECTURE SEULE) — 12 adresses cibles Motte-Picquet
qui ont des ventes DVF mais semblent hors-RNC.

ETAPE 1 : dump light JSON pour chaque cle candidate (y compris les
          variantes d'orthographe : BUENOS AIRES/AYRES, GAL/GENERAL).
ETAPE 2 : pour chaque batiment_groupe_id, API ouverte BDNB
          rel_batiment_groupe_rnc (many-to-many) U numero_immat_principal
          du snapshot ; croisement avec coproprietes[] du light.

Aucune ecriture des fichiers de donnees. Cache reseau reutilise :
data/_horsrnc_bdnb_live_motte_picquet.json (lecture/ecriture cache only).
Sortie : stdout + data/diag_mp_cibles_horsrnc.md
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
BDNB = ROOT / "data" / "bdnb_motte_picquet.json"
CACHE = ROOT / "data" / "_horsrnc_bdnb_live_motte_picquet.json"
REPORT = ROOT / "data" / "diag_mp_cibles_horsrnc.md"

API = "https://api.bdnb.io/v1/bdnb/donnees"
PAUSE = 0.35
NR = {"non connu", "", None}
RNC_MATCH = {"immat", "immat_fix", "immat_live_fix", "immat_horsrnc_fix"}

# cibles -> liste de cles candidates (variantes d'orthographe incluses)
CIBLES = {
    "6 RUE CHAMPFLEURY": ["6|RUE|CHAMPFLEURY"],
    "1 RUE DE BUENOS AIRES": ["1|RUE|BUENOS AIRES", "1|RUE|BUENOS AYRES",
                              "1B|RUE|BUENOS AYRES"],
    "5 RUE DU GAL LAMBERT": ["5|RUE|GAL LAMBERT", "5|RUE|GENERAL LAMBERT"],
    "6 AVENUE DU GAL DETRIE": ["6|AVENUE|GAL DETRIE",
                               "6|AVENUE|GENERAL DETRIE"],
    "ALLEE LEON BOURGEOIS": ["|ALLEE|LEON BOURGEOIS"],
    "55 AVENUE SUFFREN": ["55|AVENUE|SUFFREN"],
    "21 AVENUE CHARLES FLOQUET": ["21|AVENUE|CHARLES FLOQUET"],
    "2 RUE DE BUENOS AIRES": ["2|RUE|BUENOS AIRES", "2|RUE|BUENOS AYRES"],
    "3 RUE DE BUENOS AIRES": ["3|RUE|BUENOS AIRES", "3|RUE|BUENOS AYRES"],
    "4 AVENUE OCTAVE GREARD": ["4|AVENUE|OCTAVE GREARD"],
    "4 RUE DE BUENOS AIRES": ["4|RUE|BUENOS AIRES", "4|RUE|BUENOS AYRES"],
    "69/71/73 QUAI JACQUES CHIRAC": ["69|QUAI|JACQUES CHIRAC",
                                     "71|QUAI|JACQUES CHIRAC",
                                     "73|QUAI|JACQUES CHIRAC"],
}

FIELDS = ["cle", "adresse", "batiment_groupe_id", "numero_immatriculation",
          "nb_ventes_logement", "nb_ventes_total", "nb_lots_habitation",
          "nb_log_bdnb", "_bdnb_match", "_coord_source", "_fusion_auto",
          "_fusion_cible", "_fusion_auto_sources", "usage_principal_bdnb",
          "syndic", "_syndic_src"]


def get_json(url, retries=6):
    for i in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "dpe-diag/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504):
                ra = e.headers.get("Retry-After") if e.headers else None
                try:
                    wait = float(ra)
                except (TypeError, ValueError):
                    wait = min(60.0, 3.0 * (2 ** i))
                if i == retries - 1:
                    print(f"    !! abandon {e.code}")
                    return []
                time.sleep(wait)
            else:
                if i == retries - 1:
                    return []
                time.sleep(2.0 * (i + 1))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if i == retries - 1:
                return []
            time.sleep(2.0 * (i + 1))
    return []


def fetch_rel_immats(bg):
    rows, off = [], 0
    while True:
        page = get_json(f"{API}/rel_batiment_groupe_rnc"
                         f"?batiment_groupe_id=eq.{bg}&offset={off}")
        rows += page
        if len(page) < 10:
            break
        off += 10
    return sorted({r["numero_immat"] for r in rows
                   if r.get("numero_immat") not in NR})


def fetch_bg_rnc(bg):
    rows = get_json(f"{API}/batiment_groupe_rnc?batiment_groupe_id=eq.{bg}")
    if not rows:
        return {}
    r = rows[0]
    return {"nom": r.get("l_nom_copro"), "nb_log": r.get("nb_log"),
            "nb_lot_tot": r.get("nb_lot_tot"),
            "immat_principal": r.get("numero_immat_principal")}


def main():
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    bdnb = json.loads(BDNB.read_text(encoding="utf-8"))
    ad = light["adresses"]
    co = light["coproprietes"]

    by_cle = {}
    for a in ad:
        by_cle.setdefault(a.get("cle"), []).append(a)
    copro_by_immat = {c["numero_immatriculation"]: c for c in co
                      if c.get("numero_immatriculation")}
    cle_adresse_set = {c.get("cle_adresse") for c in co if c.get("cle_adresse")}
    addr_cles = {a.get("cle") for a in ad}
    snap_principal = {r["batiment_groupe_id"]: r.get("numero_immat_principal")
                      for r in bdnb}

    def cle_paired(cle):
        return bool(cle) and cle in cle_adresse_set

    def visible(im):
        c = copro_by_immat.get(im)
        return bool(c) and (c.get("cle_adresse") in addr_cles)

    out = ["# Diagnostic 12 cibles MP hors-RNC (lecture seule)\n"]
    bg_to_query = set()
    rows_e1 = []

    print("=" * 78)
    print("ETAPE 1 — light JSON")
    print("=" * 78)
    for cible, cles in CIBLES.items():
        print(f"\n### {cible}")
        out.append(f"\n## {cible}\n")
        found_any = False
        for cle in cles:
            recs = by_cle.get(cle, [])
            if not recs:
                print(f"  [{cle}] : ABSENTE du light")
                out.append(f"- `{cle}` : **ABSENTE du light**")
                continue
            found_any = True
            for a in recs:
                paired = cle_paired(cle)
                d = {f: a.get(f) for f in FIELDS}
                bg = a.get("batiment_groupe_id")
                if bg and not paired:
                    bg_to_query.add(bg)
                rows_e1.append((cible, cle, paired, d))
                print(f"  [{cle}] paired_RNC={paired}")
                for f in FIELDS:
                    print(f"      {f:24s}= {a.get(f)!r}")
                out.append(
                    f"- `{cle}` — paired_RNC=**{paired}** "
                    f"bgid=`{bg}` immat=`{a.get('numero_immatriculation')}` "
                    f"v_log={a.get('nb_ventes_logement')} "
                    f"v_tot={a.get('nb_ventes_total')} "
                    f"lots_hab={a.get('nb_lots_habitation')} "
                    f"log_bdnb={a.get('nb_log_bdnb')} "
                    f"_bdnb_match=`{a.get('_bdnb_match')}` "
                    f"_coord_source=`{a.get('_coord_source')}` "
                    f"_fusion_auto={a.get('_fusion_auto')} "
                    f"_fusion_cible=`{a.get('_fusion_cible')}` "
                    f"usage=`{a.get('usage_principal_bdnb')}`")
        if not found_any:
            print("  (aucune cle candidate presente)")

    # ETAPE 2 — BDNB
    print("\n" + "=" * 78)
    print("ETAPE 2 — BDNB rel_batiment_groupe_rnc + snapshot principal")
    print("=" * 78)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) \
        if CACHE.exists() else {}
    todo = sorted(b for b in bg_to_query if b not in cache)
    print(f"bgid a interroger (hors-RNC) : {len(bg_to_query)} "
          f"(todo live {len(todo)}, cache {len(cache)})")
    for i, bg in enumerate(todo, 1):
        immats = fetch_rel_immats(bg)
        time.sleep(PAUSE)
        meta = fetch_bg_rnc(bg) if immats else {}
        time.sleep(PAUSE)
        cache[bg] = {"immats": immats, "meta": meta}
        print(f"  {i}/{len(todo)} {bg} -> {immats}")
    if todo:
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                         encoding="utf-8")

    out.append("\n## ETAPE 2 — BDNB rel_batiment_groupe_rnc\n")
    for cible, cle, paired, d in rows_e1:
        if paired:
            continue
        bg = d.get("batiment_groupe_id")
        if not bg:
            print(f"\n{cible} [{cle}] : pas de bgid")
            out.append(f"- {cible} `{cle}` : pas de bgid")
            continue
        ent = cache.get(bg, {})
        immats = set(ent.get("immats") or [])
        sp = snap_principal.get(bg)
        if sp not in NR:
            immats.add(sp)
        meta = ent.get("meta") or {}
        print(f"\n{cible} [{cle}] bg={bg}")
        print(f"  rel_immats(live)={sorted(ent.get('immats') or [])} "
              f"snap_principal={sp}")
        print(f"  bdnb_meta nom={meta.get('nom')} "
              f"nb_log={meta.get('nb_log')} "
              f"nb_lot_tot={meta.get('nb_lot_tot')}")
        line = (f"- {cible} `{cle}` bg=`{bg}` "
                f"rel_immats={sorted(ent.get('immats') or [])} "
                f"snap_principal=`{sp}` "
                f"bdnb_nom={meta.get('nom')} nb_log={meta.get('nb_log')}")
        if not immats:
            print("  -> AUCUN immat RNC cote BDNB")
            out.append(line + " — **AUCUN immat BDNB**")
            continue
        for im in sorted(immats):
            in553 = im in copro_by_immat
            vis = visible(im) if in553 else False
            c = copro_by_immat.get(im, {})
            tag = ("R_VIS deja visible" if vis
                   else "R_INV invisible (LIEN RATE)" if in553
                   else "HORS registre 553")
            print(f"  immat {im}: {tag} "
                  f"| copro={c.get('nom_copropriete')} "
                  f"syndic={c.get('syndic')} "
                  f"cle_adresse={c.get('cle_adresse')} "
                  f"lots_hab_rnc={c.get('nb_lots_habitation_rnc')}")
            out.append(
                f"  - immat **{im}** — {tag} | "
                f"copro={c.get('nom_copropriete')!r} "
                f"syndic={c.get('syndic')!r} "
                f"cle_adresse=`{c.get('cle_adresse')}` "
                f"lots_hab_rnc={c.get('nb_lots_habitation_rnc')}")

    REPORT.write_text("\n".join(out), encoding="utf-8")
    print(f"\nRapport : {REPORT}")


if __name__ == "__main__":
    main()
