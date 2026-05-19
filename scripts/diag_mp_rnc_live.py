"""
ETAPE 3 — Interrogation LIVE du RNC open data (RNIC actualisation
quotidienne, resource tabular-api 3ea8e2c3-...) pour les adresses MP
sans resultat BDNB. LECTURE SEULE — n'ecrit que data/diag_mp_rnc_live.md.

Pour chaque rue cible : filtre code_postal in {75007,75015} ET
adresse_reference / adresse_complementaire_* contenant le token rue.
On affiche immat, nom, adresse_reference, compl_1/2/3, lots hab,
lots total, parcelles, syndic. Croisement local : l'immat est-il deja
dans coproprietes[] du light ?
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_motte_picquet_light.json"
REPORT = ROOT / "data" / "diag_mp_rnc_live.md"
RID = "3ea8e2c3-0038-464a-b17e-cd5c91f65ce2"
BASE = f"https://tabular-api.data.gouv.fr/api/resources/{RID}/data/"

# rue -> (token recherche, codes postaux plausibles)
TARGETS = {
    "55 AVENUE SUFFREN": ("SUFFREN", ["75007", "75015"], "55"),
    "21 AVENUE CHARLES FLOQUET": ("FLOQUET", ["75007"], "21"),
    "2 RUE DE BUENOS AIRES": ("BUENOS", ["75007"], "2"),
    "4 RUE DE BUENOS AIRES": ("BUENOS", ["75007"], "4"),
    "69/71/73 QUAI JACQUES CHIRAC": ("BRANLY", ["75007", "75015"],
                                     "69|71|73"),
    "69/71/73 QUAI JACQUES CHIRAC (chirac)": ("CHIRAC", ["75007", "75015"],
                                              "69|71|73"),
    "69/71/73 QUAI JACQUES CHIRAC (grenelle quai)": ("GRENELLE",
                                                     ["75015"], "69|71|73"),
}
FIELDS = ["numero_immatriculation", "nom_usage_copropriete",
          "adresse_reference", "code_postal_adresse", "numero_voie_adresse",
          "adresse_complementaire_1", "adresse_complementaire_2",
          "adresse_complementaire_3", "nombre_adresses_complementaires",
          "nombre_lots_habitation", "nombre_total_lots",
          "nombre_lots_stationnement", "reference_cadastrale_1",
          "reference_cadastrale_2", "reference_cadastrale_3",
          "raison_sociale_representant_legal",
          "identification_representant_legal",
          "syndicat_principal_ou_secondaire",
          "numero_immatriculation_syndicat_principal"]


def get(url, retries=5):
    for i in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "dpe-diag/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            if i == retries - 1:
                print(f"  !! {e}")
                return {}
            time.sleep(2.0 * (i + 1))
    return {}


def fetch_street(token, cp):
    """Toutes les lignes RNC dont adresse_reference contient `token`
    et code_postal == cp (pagination)."""
    rows, page = [], 1
    while True:
        q = urllib.parse.urlencode({
            "adresse_reference__contains": token,
            "code_postal_adresse__exact": cp,
            "page": page, "page_size": 50})
        d = get(f"{BASE}?{q}")
        data = d.get("data") or []
        rows += data
        nxt = (d.get("links") or {}).get("next")
        if not nxt or not data:
            break
        page += 1
        time.sleep(0.25)
    return rows


def main():
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    local_immats = {c["numero_immatriculation"]
                    for c in light["coproprietes"]
                    if c.get("numero_immatriculation")}

    out = ["# ETAPE 3 — RNC open data live (lecture seule)\n",
           "Resource RNIC actualisation quotidienne "
           f"`{RID}` via tabular-api.\n"]
    seen_global = {}

    for label, (token, cps, nums) in TARGETS.items():
        print("=" * 74)
        print(label, f"(token={token} cp={cps} nums~{nums})")
        print("=" * 74)
        out.append(f"\n## {label} — token `{token}` cp {cps}\n")
        wanted = set(nums.split("|"))
        for cp in cps:
            rows = fetch_street(token, cp)
            print(f"  cp {cp}: {len(rows)} lignes RNC ({token})")
            for r in rows:
                im = r.get("numero_immatriculation")
                nv = str(r.get("numero_voie_adresse") or "")
                ar = (r.get("adresse_reference") or "")
                cs = " | ".join(
                    str(r.get(f) or "") for f in
                    ("adresse_complementaire_1", "adresse_complementaire_2",
                     "adresse_complementaire_3"))
                hit = (nv in wanted) or any(
                    f" {n} " in f" {ar} " or f" {n} " in f" {cs} "
                    for n in wanted)
                mark = " <<<" if hit else ""
                if hit:
                    seen_global.setdefault(label, []).append(r)
                line = (f"  {im} | nv={nv} | {ar[:46]} | compl=[{cs[:60]}] "
                        f"| hab={r.get('nombre_lots_habitation')} "
                        f"tot={r.get('nombre_total_lots')} "
                        f"| {r.get('raison_sociale_representant_legal') or r.get('identification_representant_legal')}"
                        f" | local={'OUI' if im in local_immats else 'non'}"
                        f"{mark}")
                print(line)
                if hit:
                    out.append(
                        f"- **{im}** — {r.get('nom_usage_copropriete')!r} "
                        f"| ref=`{ar}` nv={nv} cp={r.get('code_postal_adresse')} "
                        f"| compl=[{cs}] "
                        f"| hab={r.get('nombre_lots_habitation')} "
                        f"tot={r.get('nombre_total_lots')} "
                        f"park={r.get('nombre_lots_stationnement')} "
                        f"| cad=[{r.get('reference_cadastrale_1')},"
                        f"{r.get('reference_cadastrale_2')},"
                        f"{r.get('reference_cadastrale_3')}] "
                        f"| syndic={r.get('raison_sociale_representant_legal') or r.get('identification_representant_legal')!r} "
                        f"| sdc={r.get('syndicat_principal_ou_secondaire')} "
                        f"| **DEJA dans light={'OUI' if im in local_immats else 'NON'}**")
            time.sleep(0.3)

    out.append("\n## Synthese hits\n")
    for label, rs in seen_global.items():
        out.append(f"- {label} : {len(rs)} candidat(s) "
                   f"-> {[x.get('numero_immatriculation') for x in rs]}")
    REPORT.write_text("\n".join(out), encoding="utf-8")
    print(f"\nRapport : {REPORT}")


if __name__ == "__main__":
    main()
