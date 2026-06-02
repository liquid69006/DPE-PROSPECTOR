#!/usr/bin/env python3
"""Fix cles malformees MONTCHAT (Manche A, pile rouge - 10 items).

Calque du fix DL clemalformee (scripts/fix_clemalformee.py, commit ff0af4a) :
quand make_light n'a pas su extraire le numero d'une copro RNC, sa
cle_adresse devient malformee ('|TYPE|VOIE' num vide, ou '||NOM 53 RUE X'
nom de copro mis en cle). On re-pointe cle_adresse vers la vraie cle
valide + on propage immat/nb_lots/syndic/taux vers l'adresse cible (qui
devient RNC -> badge implicite 'Copropriete').

Dry-run par defaut, --apply pour ecrire. Backup .preclemalf.bak.
Idempotent (re-run = no-op via marqueur metadata + detection cles deja
posees). Repli gracieux (skip + log si copro/adresse absente ou divergente).

LES 10 DISPOSITIONS (analysees Manche A + lookups live RNC/BAN) :

  REBIND copro -> cle valide existante :
    1  AC6769996  |RUE|DAUPHINE                    -> 75|RUE|DAUPHINE
       (IDENTIQUE a DL : meme immat a cheval DL/Montchat, meme rebind 75)
    2  AC7341035  ||TERRASSES DE MAREUIL 15 ...    -> 15B|RUE|VILLEBOIS MAREUIL
       (15 est fuse dans 15B - MEME bgid XRJV - ancre VISIBLE = 15B)
    3  AC8010274  ||ROCHAIX 63 ...                 -> 63|RUE|PROFESSEUR ROCHAIX
    5  AD3160348  ||REVERSY 71 ...                 -> 71|AVENUE|LACASSAGNE
    6  AD5117908  |RUE|ST ISIDORE  (LE SECRET)     -> 44|RUE|ST ISIDORE
       (lookup : RNC ref_cad_2 69123383DH0137 -> BDNB bgid S5D6 = les '44' ;
        BAN reverse coords RNC -> '44ter Rue Saint Isidore'. 44 etait fuse
        dans 42 (L'ECRIN AD4688198, bgid B5YZ DISTINCT) : on UN-FUSE 44 -
        bati distinct, copro distincte, meme parcelle. Pas de double-compte
        bgid (B5YZ != S5D6).)
    7  AD7135940  ||RESIDENCE D ARSONVAL 53 ...    -> 53|RUE|PROFESSEUR ROCHAIX

  INJECT (cle valide absente) + REBIND, clone-based (pattern Suffren DL) :
    4  AC8318594  ||VILLA FOUCAULD 12 A 20 ...     -> 12|RUE|JEANNE D ARC (cree)
    8  AD9466327  ||TERRASSES LACASSAGNE 201 203.. -> 201|AVENUE|LACASSAGNE (cree)

  RENAME adresse (cle malformee = ligne adresse, pas copro) :
    9  |RUE|TRARIEUX  (bgid SY4L, 1 log BDNB)      -> 74|RUE|TRARIEUX
       (lookup : BDNB rel_adresse bgid SY4L -> cle_interop 69383_7115_00074 ;
        BAN reverse coords -> 72/74 Rue Trarieux. 74 absent du light -> on
        renomme la ligne elle-meme, pas de collision/merge.)

  DENY (irrecuperable) -> data/_cles_invalides_montchat.json :
    10 |RUE|CELLARD  (0 donnee : pas d'immat/bgid/coords/log)

Effet ATTENDU sur le parc : NON-NEUTRE. Les 8 copros etaient invisibles
(cle_adresse orpheline) ; rebindees/injectees, elles deviennent visibles ->
le parc AUGMENTE d'environ la somme de leurs nb_lots_habitation (dedup
bgid pres). Voir _dryrun pour le delta decompose.
"""
import json
import sys
import shutil
import copy
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\Station 5\DPE-PROSPECTOR")
LIGHT = ROOT / "data" / "secteur_montchat_light.json"
BAK = ROOT / "data" / "secteur_montchat_light.json.preclemalf.bak"
DENYLIST = ROOT / "data" / "_cles_invalides_montchat.json"

DATE = "2026-06-02"

# Champs propages depuis la copro RNC vers l'adresse cible.
CHAMPS_PROP = [
    "numero_immatriculation",
    "nb_lots_habitation",
    "taux_rotation",
    "classement_rotation",
    "syndic",
    "_syndic_src",
]


def prop_val(copro, f):
    """Mapping copro -> adresse (taux_rotation provient de
    taux_rotation_5ans cote copro)."""
    if f == "taux_rotation":
        return copro.get("taux_rotation_5ans")
    return copro.get(f)


# --- REBIND : (immat, old_cle, new_cle, unfuse?) ---
REBIND = [
    ("AC6769996", "|RUE|DAUPHINE",                                       "75|RUE|DAUPHINE",            False),
    ("AC7341035", "||TERRASSES DE MAREUIL 15 RUE VILLEBOIS MAREUIL",      "15B|RUE|VILLEBOIS MAREUIL",  False),
    ("AC8010274", "||ROCHAIX 63 RUE DU PROFESSEUR ROCHAIX",              "63|RUE|PROFESSEUR ROCHAIX",  False),
    ("AD3160348", "||REVERSY 71 AVENUE LACASSAGNE",                       "71|AVENUE|LACASSAGNE",       False),
    ("AD5117908", "|RUE|ST ISIDORE",                                      "44|RUE|ST ISIDORE",          True),
    ("AD7135940", "||RESIDENCE D ARSONVAL 53 RUE DU PROFESSEUR ROCHAIX",  "53|RUE|PROFESSEUR ROCHAIX",  False),
]

# --- INJECT : (immat, old_cle, new_cle, clone_cle) ---
# clone_cle = adresse voisine de la meme voie dont on copie coords/bgid/iris/ilot.
INJECT = [
    ("AC8318594", "||VILLA FOUCAULD 12 A 20 RUE JEANNE D ARC",   "12|RUE|JEANNE D ARC",   "15|RUE|JEANNE D ARC"),
    ("AD9466327", "||TERRASSES LACASSAGNE 201 203 AVENUE LACASSAGNE", "201|AVENUE|LACASSAGNE", "203|AVENUE|LACASSAGNE"),
]

# --- RENAME adresse : (old_cle, new_cle) ---
RENAME_ADDR = [
    ("|RUE|TRARIEUX", "74|RUE|TRARIEUX"),
]

# --- DENY : (cle, immat_or_None, raison, note) ---
DENY = [
    ("|RUE|CELLARD", None,
     "adresse_malformee_sans_donnee_irrecuperable",
     "Ligne adresse sans immat/bgid/coords/nb_log_bdnb. Aucun levier de "
     "rebind (num introuvable, bati non geolocalise). Irrecuperable."),
]


def to_int(x):
    try:
        return int(x)
    except Exception:
        return 0


def parc_strict(adlist, colist):
    """Modele parc UI (dedup bgid + priorite nb_lots_habitation copro/RNC).
    Reproduit la logique fix_alasseur_inject.parc_model (fusion-aware)."""
    co = {c.get("cle_adresse"): c for c in colist if c.get("cle_adresse")}
    RESID = {"Résidentiel collectif", "Résidentiel individuel"}
    fused = {a["cle"] for a in adlist
             if a.get("_fusion_auto") and a.get("_fusion_cible")}
    bgRncLots, bgBdnb, immatBg = {}, {}, {}
    for a in adlist:
        cle = a.get("cle")
        if cle in fused:
            continue
        bg = a.get("batiment_groupe_id")
        cp = co.get(cle)
        # immat porte sur l'adresse OU copro presente : compte RNC
        immat = a.get("numero_immatriculation") or (cp.get("numero_immatriculation") if cp else None)
        nlots = to_int(a.get("nb_lots_habitation")) or (to_int(cp.get("nb_lots_habitation")) if cp else 0)
        if bg and (cp or immat) and nlots > 0:
            key = immat or cle
            immatBg.setdefault(key, bg)
            bgRncLots.setdefault(immatBg[key], {})[key] = nlots
        if bg and not cp and not immat and a.get("usage_principal_bdnb") in RESID \
                and to_int(a.get("nb_log_bdnb")) > 0 and bg not in bgBdnb:
            bgBdnb[bg] = to_int(a.get("nb_log_bdnb"))
    parc = 0
    for bg in set(bgRncLots) | set(bgBdnb):
        parc += (sum(bgRncLots[bg].values()) if bg in bgRncLots
                 else bgBdnb.get(bg, 0))
    return parc


def count_copros_visibles(adlist, colist):
    """Nb adresses portant badge implicite Copropriete (RNC) et visibles."""
    co_cles = {c.get("cle_adresse") for c in colist if c.get("cle_adresse")}
    fused = {a["cle"] for a in adlist
             if a.get("_fusion_auto") and a.get("_fusion_cible")}
    n = 0
    for a in adlist:
        if a["cle"] in fused:
            continue
        if a.get("numero_immatriculation") or a["cle"] in co_cles:
            n += 1
    return n


def count_malformees(adlist, colist):
    def bad(cle):
        cle = cle or ""
        num = cle.split("|")[0] if "|" in cle else cle
        return not (num[:1].isdigit() if num else False)
    n = 0
    for a in adlist:
        if bad(a.get("cle")):
            n += 1
    for c in colist:
        if bad(c.get("cle_adresse")):
            n += 1
    return n


def apply_ops(doc, log):
    ad = doc["adresses"]
    co = doc["coproprietes"]
    by_cle = {a.get("cle"): a for a in ad}
    co_by_immat = {c.get("numero_immatriculation"): c for c in co
                   if c.get("numero_immatriculation")}
    co_by_cle = {}
    for c in co:
        co_by_cle.setdefault(c.get("cle_adresse"), []).append(c)

    nb = {"rebind": 0, "inject": 0, "rename": 0, "deny": 0, "skip": 0}

    def do_rebind(c, a, new_cle, unfuse, kind):
        props = []
        for f in CHAMPS_PROP:
            v = prop_val(c, f)
            if v is None or v == "":
                continue
            if a.get(f) != v:
                a[f] = v
                props.append(f)
        if unfuse and (a.get("_fusion_auto") or a.get("_fusion_cible")):
            old_anchor = a.get("_fusion_cible")
            a["_fusion_auto"] = None
            a["_fusion_cible"] = None
            log.append(f"      [UN-FUSE] {new_cle} (devient ancre RNC visible)")
            # Nettoyer l'ANCRE precedente : retirer new_cle de ses
            # _fusion_auto_sources (sinon ref stale : l'ancre liste une source
            # un-fusee). Si l'ancre n'a plus de source -> retirer aussi le
            # label '42/44...' devenu faux. Idempotent (re-run sur, by_cle dispo).
            anc = by_cle.get(old_anchor) if old_anchor else None
            if anc and isinstance(anc.get("_fusion_auto_sources"), list):
                anc["_fusion_auto_sources"] = [s for s in anc["_fusion_auto_sources"] if s != new_cle]
                if not anc["_fusion_auto_sources"]:
                    anc.pop("_fusion_auto_sources", None)
                    anc.pop("_fusion_auto_label", None)
                log.append(f"      [UN-FUSE] ancre {old_anchor} : sources nettoyees")
        a["_bdnb_match"] = "immat_rebind_clemalf"
        c["cle_adresse"] = new_cle
        log.append(f"  [{kind}] {c.get('numero_immatriculation')}  -> '{new_cle}'  +propag {props}")

    # REBIND
    for immat, old_cle, new_cle, unfuse in REBIND:
        c = co_by_immat.get(immat)
        a = by_cle.get(new_cle)
        if not c:
            log.append(f"  [SKIP] copro {immat} absente")
            nb["skip"] += 1
            continue
        if c.get("cle_adresse") == new_cle:
            log.append(f"  [NOOP] {immat} deja sur '{new_cle}'")
            continue
        if c.get("cle_adresse") != old_cle:
            log.append(f"  [WARN] {immat} cle '{c.get('cle_adresse')}' != attendu '{old_cle}' (patch quand meme)")
        if not a:
            log.append(f"  [SKIP] adresse cible '{new_cle}' absente ({immat})")
            nb["skip"] += 1
            continue
        do_rebind(c, a, new_cle, unfuse, "REBIND")
        nb["rebind"] += 1

    # INJECT + REBIND
    for immat, old_cle, new_cle, clone_cle in INJECT:
        c = co_by_immat.get(immat)
        if not c:
            log.append(f"  [SKIP] copro {immat} absente (inject)")
            nb["skip"] += 1
            continue
        if c.get("cle_adresse") == new_cle and new_cle in by_cle:
            log.append(f"  [NOOP] {immat} deja injectee sur '{new_cle}'")
            continue
        if new_cle in by_cle:
            # adresse deja presente (re-run partiel) -> rebind simple
            do_rebind(c, by_cle[new_cle], new_cle, False, "REBIND(re-run)")
            nb["rebind"] += 1
            continue
        clone = by_cle.get(clone_cle)
        if not clone:
            log.append(f"  [SKIP] clone '{clone_cle}' absent pour inject {immat}")
            nb["skip"] += 1
            continue
        num = new_cle.split("|")[0]
        adr_label = clone.get("adresse")  # ex "15 Rue ... | ... | cp | commune"
        new_adr = {
            "cle": new_cle,
            "adresse": adr_label,  # libelle clone (commune/cp identiques) ; num reel via cle
            "batiment_groupe_id": clone.get("batiment_groupe_id"),
            "longitude": clone.get("longitude"),
            "latitude": clone.get("latitude"),
            "code_iris": clone.get("code_iris"),
            "_ilot": clone.get("_ilot"),
            "_coord_source": "clone_inject_clemalf",
            "numero_immatriculation": c.get("numero_immatriculation"),
            "nb_lots_habitation": c.get("nb_lots_habitation"),
            "nb_log_bdnb": clone.get("nb_log_bdnb"),
            "usage_principal_bdnb": clone.get("usage_principal_bdnb"),
            "_usage_bdnb_src": clone.get("_usage_bdnb_src"),
            "type_batiment": clone.get("type_batiment"),
            "annee_construction": clone.get("annee_construction"),
            "dans_majic": clone.get("dans_majic"),
            "sci_proprietaire": clone.get("sci_proprietaire"),
            "sci_nom": None,
            "sci_siren": None,
            "syndic": c.get("syndic"),
            "_syndic_src": c.get("_syndic_src"),
            "taux_rotation": c.get("taux_rotation_5ans"),
            "classement_rotation": c.get("classement_rotation"),
            "taux_rotation_logement": None,
            "classement_rotation_logement": None,
            "_taux_logement_src": None,
            "nb_ventes_logement": 0,
            "nb_ventes_total": 0,
            "ventes_par_an": {},
            "ventes_par_an_logement": {},
            "classe_dpe": None,
            "type_chauffage": None,
            "_fusion_auto": None,
            "_fusion_cible": None,
            "_bdnb_match": "immat_inject_clemalf",
        }
        ad.append(new_adr)
        by_cle[new_cle] = new_adr
        c["cle_adresse"] = new_cle
        log.append(f"  [INJECT] {immat}  cree '{new_cle}' (clone '{clone_cle}' bgid={clone.get('batiment_groupe_id')} ilot={clone.get('_ilot')}) + rebind")
        nb["inject"] += 1

    # RENAME adresse
    for old_cle, new_cle in RENAME_ADDR:
        a = by_cle.get(old_cle)
        if not a:
            if new_cle in by_cle:
                log.append(f"  [NOOP] adresse deja renommee '{new_cle}'")
            else:
                log.append(f"  [SKIP] adresse '{old_cle}' absente (rename)")
                nb["skip"] += 1
            continue
        if new_cle in by_cle:
            log.append(f"  [SKIP] collision : '{new_cle}' existe deja (rename {old_cle})")
            nb["skip"] += 1
            continue
        a["cle"] = new_cle
        a["_bdnb_match"] = "rename_clemalf"
        by_cle[new_cle] = a
        log.append(f"  [RENAME] adresse '{old_cle}' -> '{new_cle}'")
        nb["rename"] += 1

    return nb


def update_denylist(apply, log):
    arr = json.loads(DENYLIST.read_text(encoding="utf-8")) if DENYLIST.exists() else []
    existing = {o.get("cle") for o in arr}
    added = 0
    for cle, immat, raison, note in DENY:
        if cle in existing:
            log.append(f"  [NOOP] deny '{cle}' deja present")
            continue
        arr.append({"cle": cle, "immat": immat, "raison": raison,
                    "note": note, "date": DATE})
        added += 1
        log.append(f"  [DENY] +'{cle}'  ({raison})")
    if apply and added:
        DENYLIST.write_text(json.dumps(arr, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    return added


def main():
    apply = "--apply" in sys.argv
    if not LIGHT.exists():
        sys.exit("light absent: " + str(LIGHT))

    doc0 = json.loads(LIGHT.read_text(encoding="utf-8"))
    md = doc0.get("metadata", {})
    already = bool(md.get("_correctif_clemalformee_montchat"))

    doc = copy.deepcopy(doc0)
    log = []
    print("=" * 78)
    print(f"FIX CLES MALFORMEES MONTCHAT (Manche A) - {'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 78)
    if already:
        print("  [info] _correctif_clemalformee_montchat deja present (re-run idempotent).")

    parc0 = parc_strict(doc["adresses"], doc["coproprietes"])
    copro0 = count_copros_visibles(doc["adresses"], doc["coproprietes"])
    nadr0 = len(doc["adresses"])
    mal0 = count_malformees(doc["adresses"], doc["coproprietes"])

    nb = apply_ops(doc, log)
    n_deny = update_denylist(apply, log)

    parc1 = parc_strict(doc["adresses"], doc["coproprietes"])
    copro1 = count_copros_visibles(doc["adresses"], doc["coproprietes"])
    nadr1 = len(doc["adresses"])
    mal1 = count_malformees(doc["adresses"], doc["coproprietes"])

    print()
    print("--- OPERATIONS ---")
    for line in log:
        print(line)

    print()
    print("--- BILAN ---")
    print(f"  rebind={nb['rebind']} inject={nb['inject']} rename={nb['rename']} deny={n_deny} skip={nb['skip']}")
    print(f"  cles malformees (light) : {mal0} -> {mal1}")
    print(f"  copros visibles         : {copro0} -> {copro1}  ({copro1-copro0:+d})")
    print(f"  adresses                : {nadr0} -> {nadr1}  ({nadr1-nadr0:+d})")
    print(f"  parc strict (secL)      : {parc0} -> {parc1}  ({parc1-parc0:+d})")
    # decomposition delta : somme lots des copros rendues visibles
    immats = [x[0] for x in REBIND] + [x[0] for x in INJECT]
    co_by_immat = {c.get("numero_immatriculation"): c for c in doc["coproprietes"]}
    somme = sum(to_int(co_by_immat.get(i, {}).get("nb_lots_habitation")) for i in immats)
    print(f"  Sigma nb_lots_hab des 8 copros rebindees/injectees : {somme}")
    print(f"  (delta parc {parc1-parc0:+d} ~ {somme} a dedup-bgid pres ; ST ISIDORE un-fuse = bgid distinct)")

    if apply:
        if BAK.exists():
            print(f"\n  [warn] backup existant -> ecrase: {BAK.name}")
        shutil.copy2(LIGHT, BAK)
        print(f"  [bak] {BAK.name}")
        md = doc.setdefault("metadata", {})
        entry = {
            "date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pattern": "REBIND/INJECT/RENAME/DENY cle_adresse (bug make_light Montchat extraction num)",
            "autorite": "RNC live (tabular-api 3ea8e2c3) ref_cad + numero_immatriculation ; BDNB rel_parcelle/rel_adresse ; BAN reverse-geocode",
            "rebind": nb["rebind"], "inject": nb["inject"],
            "rename": nb["rename"], "deny": n_deny, "skip": nb["skip"],
            "rebind_list": [{"immat": i, "old": o, "new": n} for i, o, n, _ in REBIND],
            "inject_list": [{"immat": i, "old": o, "new": n, "clone": cl} for i, o, n, cl in INJECT],
            "rename_list": [{"old": o, "new": n} for o, n in RENAME_ADDR],
            "deny_list": [d[0] for d in DENY],
            "parc_avant": parc0, "parc_apres": parc1,
        }
        # idempotent : append a une liste si re-run
        if isinstance(md.get("_correctif_clemalformee_montchat"), list):
            md["_correctif_clemalformee_montchat"].append(entry)
        elif md.get("_correctif_clemalformee_montchat"):
            md["_correctif_clemalformee_montchat"] = [md["_correctif_clemalformee_montchat"], entry]
        else:
            md["_correctif_clemalformee_montchat"] = entry
        LIGHT.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        print(f"  [OK] light ecrit. Deny-list ecrite ({n_deny} ajout).")
    else:
        print("\n  >>> DRY-RUN : aucune ecriture. Relancer avec --apply.")


if __name__ == "__main__":
    main()
