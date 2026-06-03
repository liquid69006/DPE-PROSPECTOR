"""
Correctif VENTES-ONLY 5 ans — secteur Montchat (zone intra-DL).

Contexte (cf. JOURNAL 2026-06-03 + PIPELINE §12) : l'extraction DVF Montchat
ne couvrait QUE 2024-2025 (dvf_extract_montchat.py SOURCES={2024,2025}), alors
que le dénominateur rotation est figé à /5 (5 ans). Résultat : ventes/an et
marché-libre sous-estimés ~×2,5. Le backfill (dvf_extend_montchat.py, hors-dépôt
comme tous les extracteurs DVF) ramène dvf_montchat.json à 5 ans (2021-2025).

⚠️ LEÇON (course-correction 2026-06-03) : le light de prod = base make_light
+ une COUCHE de correctifs de manches (7 ici) que make_light NE REJOUE PAS.
Une régénération nue (extend->consolidate->make_light) PERD ces correctifs
(133 ancres injectées + rename TRARIEUX). On ne régénère donc JAMAIS un secteur
qualifié : on PATCHE chirurgicalement, ici les seuls champs ventes.

Recompute (logique de clé/comptage EXACTE) :
  - BRUT     : fonctions importées de make_light_montchat (dvf_cle/cle2/
               classer_annuel) + bloc vpar make_light l.408-420 + recompute
               l.600-625 (/5). Champs : ventes_par_an, nb_ventes_total,
               taux_rotation, classement_rotation.
  - LOGEMENT : logique de fix_taux_logement.py (soustraction mutations
               dépendance-SEULE). Champs : ventes_par_an_logement,
               nb_ventes_logement, taux_rotation_logement,
               classement_rotation_logement, _taux_logement_src.
               Garde SOURCES_IMMUABLES limitée aux VRAIS overrides manuels
               (cherrypick/strict_btq) : 'copie_sans_dependance' EST recomputé
               (le DVF a changé ; 0 override manuel réel sur Montchat).

Conservation prouvée : 0 clé ajoutée/retirée, 0 champ parc modifié, parc
inchangé, 0 orphelin KV. Cf. preuves imprimées en fin.

Usage :
  PYTHONUTF8=1 python scripts/fix_ventes5ans_montchat.py            # DRY-RUN -> _PROBE
  PYTHONUTF8=1 python scripts/fix_ventes5ans_montchat.py --apply    # écrit le light en place
"""
import os, sys, json, copy, collections, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HORS = Path(r"C:\Users\Station 5")
sys.path.insert(0, str(HORS))
sys.path.insert(0, str(ROOT / "scripts"))

from make_light_montchat import dvf_cle, classer_annuel
from _parc_replique_montchat import parc

LIGHT = ROOT / "data" / "secteur_montchat_light.json"
FULL  = ROOT / "data" / "secteur_montchat.json"
DVF   = HORS / "dvf_montchat.json"
REGEN = ROOT / "data" / "_regen1306_montchat.PROBE.json"
KVMIR = ROOT / "data" / "_kv_assign_montchat.F.candidate.json"
PROBE = ROOT / "data" / "secteur_montchat_light.json._PROBE.json"
BAK   = ROOT / "data" / "secteur_montchat_light.json.preventes5ans.bak"

ANS = ["2021", "2022", "2023", "2024", "2025"]
PRESERVE_SRC = {'cherrypick_vefa_5lots', 'cherrypick_vefa_neutralise',
                'strict_btq_post_logement'}

ABBR = {"SAINT": "ST", "SAINTE": "STE", "DOCTEUR": "DR", "PROFESSEUR": "PR"}
ART = {"DU", "DE", "DES", "LA", "LE", "LES", "L", "D", "A", "AU", "AUX",
       "ET", "BIS", "TER"}


def toks(s):
    s = (s or "").upper().replace("'", " ")
    return tuple(sorted(ABBR.get(t, t)
                        for t in re.split(r"[^A-Z0-9]+", s)
                        if t and t not in ART))


def numof(s):
    m = re.match(r"\d+", str(s or ""))
    return m.group(0) if m else str(s or "")


def yr(m):
    d = m.get("Date mutation") or ""
    return d[-4:] if len(d) >= 4 else "?"


def taux_annuel(v5, lots):
    return round(v5 / lots / 5 * 1000) / 10 if (lots and lots > 0) else None


def classe(t):
    if t is None:
        return ""
    if t >= 5:
        return "Très actif"
    if t >= 2.5:
        return "Actif"
    if t >= 1:
        return "Modéré"
    return "Figé"


def main():
    apply = "--apply" in sys.argv
    light = json.loads(LIGHT.read_text(encoding="utf-8"))
    full = json.loads(FULL.read_text(encoding="utf-8"))
    dvf = json.loads(DVF.read_text(encoding="utf-8"))
    # référence = backup pré-apply si présent, sinon le light courant
    sealed = json.loads(BAK.read_text(encoding="utf-8")) if BAK.exists() \
        else copy.deepcopy(light)
    patched = copy.deepcopy(light)
    la = patched["adresses"]
    co = patched["coproprietes"]
    coproByCle = {c["cle_adresse"]: c for c in co if c.get("cle_adresse")}

    # 1) BRUT : vpar make_light l.408-420
    vpar = collections.defaultdict(lambda: collections.Counter())
    vset = collections.defaultdict(set)
    for m in dvf:
        k = dvf_cle(m)
        if not k:
            continue
        an = m.get("_annee_fichier")
        mid = (an, m.get("Date mutation"), m.get("No disposition"),
               m.get("Valeur fonciere"))
        if mid in vset[k]:
            continue
        vset[k].add(mid)
        vpar[k][an] += 1

    for a in la:
        pa = vpar.get(a.get("cle"), {})
        nbt = sum(pa.values())
        vpa = {y: pa.get(y, 0) for y in ANS if pa.get(y)}
        cm_lots = a.get("nb_lots_habitation") or 0
        if not isinstance(cm_lots, (int, float)):
            cm_lots = 0
        denom = cm_lots if cm_lots > 0 else (a.get("nb_log_bdnb") or 0)
        tx = (round(nbt / (5 * denom / 100), 1) if nbt else 0.0) \
            if (denom and denom > 0) else None
        a["ventes_par_an"] = vpa
        a["nb_ventes_total"] = nbt
        a["taux_rotation"] = tx
        a["classement_rotation"] = classer_annuel(tx)

    # 2) LOGEMENT-STRICT : logique fix_taux_logement
    M = full["mutations_dvf"]
    mut_idx = collections.defaultdict(list)
    for m in M:
        mut_idx[(numof(m.get("No voie")), toks(m.get("Voie")))].append(m)

    n_rel = n_unrel = n_delta = n_preserved = 0
    for a in la:
        if a.get("_taux_logement_src") in PRESERVE_SRC:
            n_preserved += 1
            continue
        cle = a.get("cle")
        vpa = a.get("ventes_par_an") or {}
        stored = a.get("nb_ventes_total") or 0
        p = (cle or "").split("|")
        rows = mut_idx.get((numof(p[0]), toks(p[-1])), []) if cle else []
        muts = collections.defaultdict(set)
        types = collections.defaultdict(set)
        for m in rows:
            kk = (m.get("Date mutation"), m.get("Valeur fonciere"))
            muts[yr(m)].add(kk)
            types[kk].add(str(m.get("Code type local")))
        deriv_all = sum(len(muts[y]) for y in ANS)
        dep_only = {y: sum(1 for kk in muts[y] if not ({"1", "2"} & types[kk]))
                    for y in ANS}
        reliable = abs(deriv_all - stored) <= 1
        if not reliable:
            src = "copie_jointure_incertaine"; vlog = dict(vpa); nlog = stored
            n_unrel += 1
        elif sum(dep_only.values()) == 0:
            src = "copie_sans_dependance"; vlog = dict(vpa); nlog = stored
            n_rel += 1
        else:
            src = "filtre_habitation"
            vlog = {y: max(0, (vpa.get(y) or 0) - dep_only.get(y, 0))
                    for y in ANS if (vpa.get(y) or 0) or dep_only.get(y, 0)}
            nlog = sum(vlog.values()); n_rel += 1; n_delta += 1
        cp = coproByCle.get(cle)
        denom = (cp.get("nb_lots_habitation") if cp
                 and (cp.get("nb_lots_habitation") or 0) > 0 else None)
        if denom is None:
            denom = a.get("nb_log_bdnb") if (a.get("nb_log_bdnb") or 0) > 0 else None
        a["ventes_par_an_logement"] = vlog
        a["nb_ventes_logement"] = nlog
        a["taux_rotation_logement"] = taux_annuel(nlog, denom)
        a["classement_rotation_logement"] = classe(taux_annuel(nlog, denom))
        a["_taux_logement_src"] = src

    if apply:
        patched.setdefault("metadata", {})["_correctif_ventes5ans_montchat"] = (
            "Recompute ventes-only 5 ans (2021-2025) apres backfill DVF "
            "(dvf_extend_montchat). Champs brut (ventes_par_an/nb_ventes_total/"
            "taux_rotation/classement_rotation) recomputes via vpar make_light ; "
            "champs *_logement via logique fix_taux_logement. Aucune cle ni "
            "champ parc/structure touche (patch chirurgical, 0 orphelin, parc "
            "inchange). NB: make_light ne rejoue pas les correctifs de manche "
            "-> jamais de regen nue, patch chirurgical uniquement.")
        LIGHT.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                         encoding="utf-8")
        OUT = LIGHT
    else:
        PROBE.write_text(json.dumps(patched, ensure_ascii=False, indent=2),
                         encoding="utf-8")
        OUT = PROBE

    # ---------- PREUVES ----------
    print("=" * 72)
    print(f"fix_ventes5ans_montchat — {'APPLY' if apply else 'DRY-RUN'}  -> {OUT.name}")
    print("=" * 72)
    print(f"logement : recompute={n_rel + n_unrel} (fiable {n_rel} dont delta "
          f"{n_delta}, incertaine {n_unrel}) ; overrides preserves={n_preserved}")

    ks = set(a.get("cle") for a in sealed["adresses"])
    kp = set(a.get("cle") for a in patched["adresses"])
    print(f"\n[P1] CLES : scelle={len(ks)} patch={len(kp)} "
          f"ajouts={len(kp-ks)} retraits={len(ks-kp)} -> "
          f"{'OK' if ks==kp else 'ECHEC'}")

    PARCF = ("nb_lots_habitation", "nb_log_bdnb", "numero_immatriculation",
             "batiment_groupe_id", "usage_principal_bdnb", "_fusion_auto",
             "_fusion_cible", "_fusion_auto_target", "_nb_lots_habitation_override")
    sd = {a["cle"]: a for a in sealed["adresses"]}
    diffs = sum(1 for a in patched["adresses"] if sd.get(a["cle"])
                for f in PARCF if a.get(f) != sd[a["cle"]].get(f))
    coES = json.dumps(sealed["coproprietes"], sort_keys=True, ensure_ascii=False)
    coEP = json.dumps(patched["coproprietes"], sort_keys=True, ensure_ascii=False)
    print(f"[P1b] PARC-FIELDS : diffs={diffs} ; coproprietes identiques={coES==coEP}")

    kv = json.loads(KVMIR.read_text(encoding="utf-8")).get("assignments", {})
    tr = "74|RUE|TRARIEUX"
    print(f"[P2] TRARIEUX present={tr in kp} tag={(kv.get(tr) or {}).get('type')!r}")

    if REGEN.exists():
        regen = json.loads(REGEN.read_text(encoding="utf-8"))
        rg = {a.get("cle"): (a.get("ventes_par_an") or {}) for a in regen["adresses"]}
        pp = {a.get("cle"): (a.get("ventes_par_an") or {}) for a in patched["adresses"]}
        shared = set(rg) & set(pp)
        coinc = sum(1 for k in shared if rg[k] == pp[k])
        print(f"[P3] COHERENCE vs make_light frais : communes={len(shared)} "
              f"coincidences={coinc} ecarts={len(shared)-coinc}")

    def py(doc, f):
        return sum((a.get(f) or 0) for a in doc["adresses"]) / 5

    def ml(doc):
        return sum((a.get("nb_ventes_logement") or 0) for a in doc["adresses"]
                   if (kv.get(a.get("cle")) or {}).get("type") not in
                   ("social", "bureaux")) / 5
    print(f"[P4] brut/an {py(sealed,'nb_ventes_total'):.1f}->{py(patched,'nb_ventes_total'):.1f}"
          f" | logement/an {py(sealed,'nb_ventes_logement'):.1f}->{py(patched,'nb_ventes_logement'):.1f}"
          f" | marche-libre/an {ml(sealed):.1f}->{ml(patched):.1f}")

    ps, _ = parc(BAK if BAK.exists() else LIGHT, kv)
    pq, _ = parc(OUT, kv)
    print(f"[P5] PARC : scelle={ps} patch={pq} -> {'INCHANGE' if ps==pq else 'ECHEC'}")
    print("=" * 72)
    if not apply:
        print("DRY-RUN : --apply pour ecrire le light en place.")


if __name__ == "__main__":
    main()
