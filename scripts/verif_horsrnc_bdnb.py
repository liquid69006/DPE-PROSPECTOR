"""
Passe INVERSE : adresses dashboard HORS-RNC -> existe-t-il un lien RNC
cote BDNB que le pipeline aurait rate ? (LECTURE SEULE, dry-run).

Une adresse de secteur_dauphine_lacassagne_light.json est "hors-RNC" si
elle n'est PAS appairee au registre RNC (= tableau `coproprietes`), c.-a-d.
ni son `cle` n'est la `cle_adresse` d'une copro, ni son batiment BDNB n'a
ete matche par immatriculation (`_bdnb_match` not in immat/immat_fix/
immat_live_fix).

Pour chaque adresse hors-RNC (via son `batiment_groupe_id`) on interroge
l'API ouverte BDNB (api.bdnb.io, sans cle) :
  - rel_batiment_groupe_rnc?batiment_groupe_id=eq.<bg>  -> {numero_immat}
    (table many-to-many, source de verite ; le snapshot ne garde que
     numero_immat_principal = projection lossy)
  - batiment_groupe_rnc?batiment_groupe_id=eq.<bg>      -> l_nom_copro,
    nb_log (pour le rapport / plausibilite)

Chaque immat trouve est classe :
  R_VIS  immat dans nos 553 copros, copro DEJA visible ailleurs  -> cosmetique
  R_INV  immat dans nos 553 copros, copro INVISIBLE partout       -> lien RATE
  HORS   immat absent de nos 553 copros (hors secteur / filtre)   -> info

Lecture seule. Cache reseau : data/_horsrnc_bdnb_live.json (resumable).
Sortie : stdout + data/verif_horsrnc_bdnb_report.md. Aucune ecriture des
fichiers de donnees.
"""

import json
import time
import collections
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
BDNB = ROOT / "data" / "bdnb_dauphine_lacassagne.json"
CACHE = ROOT / "data" / "_horsrnc_bdnb_live.json"
REPORT = ROOT / "data" / "verif_horsrnc_bdnb_report.md"

API = "https://api.bdnb.io/v1/bdnb/donnees"
PAUSE = 0.12
NR = {"non connu", "", None}
RNC_MATCH = {"immat", "immat_fix", "immat_live_fix"}


def get_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dpe-verif/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))
    return []


def fetch_rel_immats(bg):
    """bgid -> sorted list of numero_immat (paginated, anon cap = 10)."""
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
    """bgid -> {nom:[...], nb_log, nb_lot_tot} via batiment_groupe_rnc."""
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
    ad, co = light["adresses"], light["coproprietes"]

    # registre RNC = coproprietes
    copro = {c["numero_immatriculation"]: c for c in co
             if c.get("numero_immatriculation")}

    # Le dashboard relie une adresse a une copro UNIQUEMENT par
    # coproByCle[a.cle] == c.cle_adresse (chaine EXACTE, suffixe #immat
    # B3 compris ; cf. index.html:2102-2103,2162,2201). Aucun repli sur
    # le numero de base, aucun rendu copro par bgid. -> match exact.
    cle_adresse_exact = {c.get("cle_adresse") for c in co
                         if c.get("cle_adresse")}
    addr_cles = {a.get("cle") for a in ad}

    def cle_paired(cle):                       # adresse montre une copro ?
        return bool(cle) and cle in cle_adresse_exact

    def visible(im):                           # copro rendue dans l'arbre ?
        c = copro.get(im)
        return bool(c) and (c.get("cle_adresse") in addr_cles)

    # ETAPE 1 - adresses hors-RNC = aucune copro affichee au dashboard
    # (a.cle n'est exactement aucune cle_adresse). Definition fidele au
    # rendu : on NE filtre PAS sur _bdnb_match (le dashboard ne s'en sert
    # pas pour l'affichage RNC ; une adresse _bdnb_match=immat dont la cle
    # n'est aucune cle_adresse s'affiche quand meme SANS copro).
    hors = [a for a in ad if not cle_paired(a.get("cle"))]
    hors_strict = [a for a in hors
                   if a.get("_bdnb_match") not in RNC_MATCH]
    bgids = sorted({a["batiment_groupe_id"] for a in hors
                    if a.get("batiment_groupe_id")})
    print(f"Adresses totales                       : {len(ad)}")
    print(f"Adresses hors-RNC (aucune copro affichee): {len(hors)}")
    print(f"  dont _bdnb_match != immat (strict)    : {len(hors_strict)}")
    print(f"  dont _bdnb_match == immat* (D1)       : "
          f"{len(hors) - len(hors_strict)}")
    print(f"bgid hors-RNC distincts                 : {len(bgids)}")

    snap_principal = {r["batiment_groupe_id"]: r.get("numero_immat_principal")
                      for r in bdnb}

    # ETAPE 2 - interrogation live (cache resumable)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    todo = [b for b in bgids if b not in cache]
    print(f"bgid a interroger en LIVE   : {len(todo)} "
          f"(cache {len(cache)})")
    for i, bg in enumerate(todo, 1):
        immats = fetch_rel_immats(bg)
        time.sleep(PAUSE)
        meta = fetch_bg_rnc(bg) if immats else {}
        time.sleep(PAUSE)
        cache[bg] = {"immats": immats, "meta": meta}
        if i % 25 == 0 or i == len(todo):
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                             encoding="utf-8")
            print(f"  {i:3}/{len(todo)} bgid live")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    # ETAPE 3 - classification
    R_VIS, R_INV, HORS = [], [], []
    for a in hors:
        bg = a.get("batiment_groupe_id")
        if not bg:
            continue
        ent = cache.get(bg, {})
        immats = set(ent.get("immats") or [])
        sp = snap_principal.get(bg)
        if sp not in NR:
            immats.add(sp)            # union snapshot principal
        if not immats:
            continue
        meta = ent.get("meta") or {}
        for im in sorted(immats):
            rec = {
                "cle": a.get("cle"), "adresse": a.get("adresse"),
                "bg": bg, "immat": im,
                "_bdnb_match": a.get("_bdnb_match"),
                "snap_principal": sp if sp not in NR else None,
                "src_snap": im == sp, "src_live": im in (ent.get("immats") or []),
                "bdnb_nom": meta.get("nom"), "bdnb_nb_log": meta.get("nb_log"),
            }
            if im not in copro:
                HORS.append(rec)
            elif visible(im):
                c = copro[im]
                rec.update(nom=c.get("nom_copropriete"),
                           syndic=c.get("syndic"),
                           cle_adresse=c.get("cle_adresse"),
                           lots=c.get("nb_lots_habitation_rnc"))
                R_VIS.append(rec)
            else:
                c = copro[im]
                rec.update(nom=c.get("nom_copropriete"),
                           syndic=c.get("syndic"),
                           cle_adresse=c.get("cle_adresse"),
                           lots=c.get("nb_lots_habitation_rnc"))
                R_INV.append(rec)

    def uniq_addr(rs):
        return len({(r["cle"], r["bg"]) for r in rs})

    print("=" * 66)
    print("HORS-RNC -> lien RNC cote BDNB ?  (live, lecture seule)")
    print("=" * 66)
    print(f"Adresses hors-RNC                         : {len(hors)}")
    print(f"  avec >=1 immat RNC cote BDNB            : "
          f"{uniq_addr(R_VIS + R_INV + HORS)}")
    print(f"  -> immat = copro secteur DEJA visible   : "
          f"{uniq_addr(R_VIS)} adr / {len({r['immat'] for r in R_VIS})} immat")
    print(f"  -> immat = copro secteur INVISIBLE      : "
          f"{uniq_addr(R_INV)} adr / {len({r['immat'] for r in R_INV})} immat"
          f"   <<< LIEN RATE")
    print(f"  -> immat HORS registre 553              : "
          f"{uniq_addr(HORS)} adr / {len({r['immat'] for r in HORS})} immat")
    print("=" * 66)

    def tbl(rs):
        o = ["| Adresse | bgid | immat BDNB | src | copro RNC / nom BDNB | "
             "syndic | lgts |", "|---|---|---|---|---|---|--:|"]
        seen = set()
        for r in sorted(rs, key=lambda x: x["cle"]):
            key = (r["cle"], r["immat"])
            if key in seen:
                continue
            seen.add(key)
            src = ("snap+live" if r["src_snap"] and r["src_live"]
                   else "live" if r["src_live"] else "snap")
            nom = r.get("nom") or (" ".join(r["bdnb_nom"])
                                   if r.get("bdnb_nom") else "—")
            o.append(f"| {r['adresse'] or r['cle']} | `{r['bg']}` | "
                     f"{r['immat']} | {src} | {nom[:34]} | "
                     f"{(r.get('syndic') or '—')[:24]} | "
                     f"{r.get('lots') if r.get('lots') is not None else '—'} |")
        return "\n".join(o)

    md = [
        "# Hors-RNC → lien RNC côté BDNB ? (live, lecture seule)\n",
        "Adresse *hors-RNC* = non appairée au registre `coproprietes` "
        "(ni `cle`↔`cle_adresse`, ni `_bdnb_match` immat). Source : API "
        "ouverte `rel_batiment_groupe_rnc` (many-to-many) ∪ "
        "`numero_immat_principal` du snapshot.\n",
        "## Bilan\n", "| Indicateur | Valeur |", "|---|--:|",
        f"| Adresses hors-RNC (aucune copro affichée au dashboard) "
        f"| {len(hors)} |",
        f"| dont strict (`_bdnb_match` ≠ immat) | {len(hors_strict)} |",
        f"| dont D1 (`_bdnb_match` = immat mais clé ≠ cle_adresse) "
        f"| {len(hors) - len(hors_strict)} |",
        f"| bgid hors-RNC distincts | {len(bgids)} |",
        f"| Adresses avec ≥1 immat RNC côté BDNB | "
        f"{uniq_addr(R_VIS + R_INV + HORS)} |",
        f"| → copro secteur **déjà visible** (cosmétique) | "
        f"{uniq_addr(R_VIS)} adr |",
        f"| → copro secteur **INVISIBLE** (lien raté) | "
        f"**{uniq_addr(R_INV)} adr** |",
        f"| → immat **hors registre 553** | {uniq_addr(HORS)} adr |",
        "\n## R_INV — copros secteur invisibles rattachées par BDNB "
        "(cible ÉTAPE 3)\n",
        tbl(R_INV) if R_INV else "_aucune_",
        "\n## R_VIS — copro déjà visible ailleurs (aucune action, "
        "anti-double-comptage)\n",
        tbl(R_VIS) if R_VIS else "_aucune_",
        "\n## HORS — immat BDNB hors de nos 553 copros (info)\n",
        f"_{uniq_addr(HORS)} adresses ; détail tronqué_\n",
        tbl(HORS[:60]) if HORS else "_aucune_",
        "",
    ]
    REPORT.write_text("\n".join(md), encoding="utf-8")
    print(f"Rapport écrit : {REPORT}")
    print(f"Cache         : {CACHE}")


if __name__ == "__main__":
    main()
