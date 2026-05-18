"""
Correctif ADDITIF : taux de rotation "logement strict" (exclut les
mutations DVF dependance/commerce SEULE).

Contexte (voir memoire audit-dvf-coherence) : `ventes_par_an` compte les
mutations DVF UNIQUES tous types ; une vente de parking/cave ISOLEE
(sans logement dans l'acte) y est incluse -> taux de rotation
sur-evalue (num. tous locaux / denom. lots habitation).

⚠️ Le generateur DVF n'est PAS dans le depot : on ne peut pas rejouer
exactement sa jointure adresse<->mutation. La jointure best-effort
(No voie + tokens Voie normalises) est fidele a ~94,7 % (exact) /
95,5 % (+/-1). Une REECRITURE de `ventes_par_an` serait DESTRUCTRICE
(corromprait ~56 adresses a jointure divergente, au-dela du seul
retrait des dependances).

-> Strategie NON DESTRUCTIVE : on n'ecrase JAMAIS `ventes_par_an` /
`nb_ventes_total`. On AJOUTE des champs :
  - ventes_par_an_logement, nb_ventes_logement
  - taux_rotation_logement, classement_rotation_logement (taux ANNUEL
    et classe, memes formules que le dashboard sctTauxAnnuel/
    sctClassAnnuel : t>=5 Tres actif, >=2.5 Actif, >=1 Modere, sinon Fige)
  - _taux_logement_src : filtre_habitation | copie_sans_dependance |
    copie_jointure_incertaine
On ancre sur la valeur AUTORITATIVE `nb_ventes_total`/`ventes_par_an`
et on SOUSTRAIT seulement le delta de mutations dependance-SEULE
identifiees (clamp >=0). Adresse a jointure incertaine (|derive-stored|
>1) : champs _logement = copie de l'original + flag (jamais corrompu).

Le dashboard (index.html) continue de lire `ventes_par_an` -> rendu
INCHANGE (preuve de non-destructivite via test_render_secteur.js).
Basculer l'affichage sur le metrique strict = etape SEPAREE (modif
index.html), hors scope.

Cible : data/secteur_dauphine_lacassagne_light.json. Backup distinct
.pretauxlog.bak (abort si present). Dry-run par defaut.

Usage :
  python scripts/fix_taux_logement.py            # DRY-RUN
  python scripts/fix_taux_logement.py --apply
"""

import sys
import json
import collections
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "data" / "secteur_dauphine_lacassagne_light.json"
FULL = ROOT / "data" / "secteur_dauphine_lacassagne.json"
BAK = ROOT / "data" / "secteur_dauphine_lacassagne_light.json.pretauxlog.bak"

ANS = ["2021", "2022", "2023", "2024", "2025"]
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
    la = light["adresses"]
    co = light["coproprietes"]
    M = full["mutations_dvf"]
    coproByCle = {c["cle_adresse"]: c for c in co if c.get("cle_adresse")}

    mut_idx = collections.defaultdict(list)
    for m in M:
        mut_idx[(numof(m.get("No voie")), toks(m.get("Voie")))].append(m)

    n_rel = n_unrel = n_delta = 0
    tot_stored = tot_log = 0
    reclass = collections.Counter()
    sample = []

    for a in la:
        cle = a.get("cle")
        vpa = a.get("ventes_par_an") or {}
        stored = a.get("nb_ventes_total") or 0
        p = (cle or "").split("|")
        rows = mut_idx.get((numof(p[0]), toks(p[-1])), []) if cle else []
        # mutations uniques par an : tous types vs touchant >=1 habitation
        muts = collections.defaultdict(set)         # an -> {(date,valeur)}
        types = collections.defaultdict(set)        # (date,valeur) -> {code}
        for m in rows:
            k = (m.get("Date mutation"), m.get("Valeur fonciere"))
            muts[yr(m)].add(k)
            types[k].add(str(m.get("Code type local")))
        deriv_all = sum(len(muts[y]) for y in ANS)
        dep_only = {}
        for y in ANS:
            dep_only[y] = sum(1 for k in muts[y]
                              if not ({"1", "2"} & types[k]))
        reliable = abs(deriv_all - stored) <= 1
        delta = sum(dep_only.values())

        if not reliable:
            src = "copie_jointure_incertaine"
            vlog = dict(vpa)
            nlog = stored
            n_unrel += 1
        elif delta == 0:
            src = "copie_sans_dependance"
            vlog = dict(vpa)
            nlog = stored
            n_rel += 1
        else:
            src = "filtre_habitation"
            vlog = {y: max(0, (vpa.get(y) or 0) - dep_only.get(y, 0))
                    for y in ANS if (vpa.get(y) or 0) or dep_only.get(y, 0)}
            nlog = sum(vlog.values())
            n_rel += 1
            n_delta += 1

        tot_stored += stored
        tot_log += nlog
        # taux affiche (approx : denom = copro lots si copro sinon nb_log_bdnb)
        cp = coproByCle.get(cle)
        denom = (cp.get("nb_lots_habitation") if cp
                 and (cp.get("nb_lots_habitation") or 0) > 0 else None)
        if denom is None:
            denom = a.get("nb_log_bdnb") if (a.get("nb_log_bdnb") or 0) > 0 \
                else None
        t_old = taux_annuel(stored, denom)
        t_new = taux_annuel(nlog, denom)
        c_old, c_new = classe(t_old), classe(t_new)
        if c_old != c_new and src == "filtre_habitation":
            reclass[f"{c_old} -> {c_new}"] += 1
            if len(sample) < 15:
                sample.append((cle, stored, nlog, t_old, t_new,
                               c_old, c_new))

        if apply:
            a["ventes_par_an_logement"] = vlog
            a["nb_ventes_logement"] = nlog
            a["taux_rotation_logement"] = t_new
            a["classement_rotation_logement"] = c_new
            a["_taux_logement_src"] = src

    print("=" * 72)
    print("CORRECTIF ADDITIF — taux rotation 'logement strict' "
          "(dependances exclues)")
    print("=" * 72)
    print(f"Mode                              : "
          f"{'APPLY' if apply else 'DRY-RUN'}")
    print(f"Adresses                          : {len(la)}")
    print(f"  jointure fiable                 : {n_rel}")
    print(f"    dont delta dependance applique : {n_delta}")
    print(f"  jointure incertaine (intacte+flag): {n_unrel}")
    print(f"Ventes (autoritatif, inchange)    : {tot_stored}")
    print(f"Ventes 'logement strict'          : {tot_log}  "
          f"(-{tot_stored - tot_log}, "
          f"-{(tot_stored - tot_log) / tot_stored * 100:.1f}%)")
    print(f"`ventes_par_an` SURCHARGE ?        : NON (additif seulement)")
    print("-" * 72)
    print("Reclassements rotation estimes (adresses filtre_habitation) :")
    for k, v in reclass.most_common():
        print(f"  {k:24} : {v}")
    print("-" * 72)
    print("Echantillon (cle | v_tot -> v_log | taux% old->new | classe) :")
    for cle, s, nl, to, tn, co_, cn in sample:
        print(f"  {cle[:34]:<34} {s:>3}->{nl:<3} | "
              f"{to}->{tn} | {co_} -> {cn}")
    print("=" * 72)

    if not apply:
        print("DRY-RUN : aucun fichier modifie. --apply pour ecrire "
              "(champs *_logement AJOUTES, originaux intacts).")
        return
    if BAK.exists():
        print(f"ABORT : backup {BAK.name} existe deja.")
        return
    BAK.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    meta = light.setdefault("metadata", {})
    meta["_correctif_taux_logement"] = (
        f"Champs ADDITIFS ventes_par_an_logement / nb_ventes_logement / "
        f"taux_rotation_logement / classement_rotation_logement / "
        f"_taux_logement_src ajoutes ({n_delta} adr avec delta dependance, "
        f"{n_unrel} adr jointure incertaine = copie intacte+flag). "
        f"`ventes_par_an`/`nb_ventes_total` NON modifies (autoritatifs). "
        f"Ventes strictes {tot_log} vs {tot_stored} (-"
        f"{(tot_stored - tot_log) / tot_stored * 100:.1f}%). Dashboard "
        f"inchange (lit toujours ventes_par_an) ; bascule = modif "
        f"index.html separee.")
    LIGHT.write_text(json.dumps(light, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"Sauvegarde : {BAK.name}")
    print(f"Ecrit : {LIGHT.name} (champs *_logement ajoutes, "
          f"originaux intacts)")


if __name__ == "__main__":
    main()
