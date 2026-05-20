"""
Audit systematique des copros RNC multi-parcelles (lecture seule).

Source-of-truth : ref_cadastrale_2 / ref_cadastrale_3 non vides dans
le snapshot RNC du secteur = la copro declare explicitement
plusieurs bgids BDNB distincts. C'est la preuve la plus solide
d'une multi-bgid non encore fusionnee dans le pipeline (cf. fix
Fondary/Croix Nivert 0b05a1e).

Methode :
  1. Scanner snapshot RNC raw (secteur_*.json) pour les copros avec
     reference_cadastrale_2/3 non vide.
  2. Pour chaque copro multi-parcelles, deux jointures :
     - A) cadastrale : RNC ref_cadastrale_N normalisee <->
          BDNB l_parcelle_id normalisee -> bgids candidats. Pour
          chaque bgid, lister les adresses[] light du secteur.
     - B) adresse compl : RNC adresse_complementaire_N parsee ->
          cle adresse -> match dans adresses[] light.
  3. Identifier les cas ACTIONNABLES :
       - copro RNC visible dans le light (immat present dans une
         adresse) sur l'une de ses parcelles
       - adresse[] hors-RNC (immat=None) sur une AUTRE parcelle
         de la meme copro RNC
     -> candidats au re-point pattern Fremicourt/Cambronne/Fondary.

Note : BDNB Dauphine-Lacassagne n'a pas de l_parcelle_id (champ
absent) -> jointure cadastrale (A) impossible pour DL ; seule la
methode B (adresse compl) est utilisee. Pour MP, on combine A + B.

Sortie : data/audit_copros_multiparcelles.md (lecture seule,
aucune modification des donnees).

Usage : PYTHONUTF8=1 python scripts/audit_copros_multiparcelles.py
"""

import json
import re
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "audit_copros_multiparcelles.md"

SECTEURS = [
    ("motte_picquet", "Motte-Picquet (Paris 15)", "PARIS15"),
    ("dauphine_lacassagne", "Dauphine-Lacassagne (Lyon 3e)", "LYON383"),
]


# ─────────────────────────────────────────────────────────────────────
def parcelle_key(s):
    """Normalise un code cadastral 14-char vers cle commune.
    Renvoie None si format non reconnu."""
    s = (s or "").strip()
    if not s or len(s) < 14:
        return None
    if s.startswith("75"):
        if s[5:8] == "000" and s[2] == "1":           # BDNB Paris
            return f"PARIS{s[3:5]}|{s[8:10].upper()}|{s[10:14]}"
        if s[2:5] == "056" and s[5] == "1":           # RNC Paris
            return f"PARIS{s[6:8]}|{s[8:10].upper()}|{s[10:14]}"
    if s.startswith("69"):
        if s[2:5] == "123" and s[5:8].isdigit():      # RNC Lyon Metro
            return f"LYON{s[5:8]}|{s[8:10].upper()}|{s[10:14]}"
        if s[2:5] == "383" and s[5:8] == "000":       # alt
            return f"LYON383|{s[8:10].upper()}|{s[10:14]}"
        if s[2:5] == "266":                           # Villeurbanne
            return f"VILLEURBANNE|{s[8:10].upper()}|{s[10:14]}"
    return None


def field(c, *names):
    for n in names:
        v = c.get(n)
        if v not in (None, "", "non connu"):
            return v
    return None


# Normalisation adresse compl -> cle adresse (best-effort)
# RNC format compl : '91 r fondary 75015 Paris', '20 BIS AVENUE LACASSAGNE 69003 LYON'
VOIE_ABBR = {
    "r": "RUE", "rue": "RUE",
    "bd": "BOULEVARD", "boulevard": "BOULEVARD", "bld": "BOULEVARD",
    "av": "AVENUE", "avenue": "AVENUE", "ave": "AVENUE",
    "pl": "PLACE", "place": "PLACE",
    "pas": "PASSAGE", "passage": "PASSAGE", "psg": "PASSAGE",
    "imp": "IMPASSE", "impasse": "IMPASSE",
    "all": "ALLEE", "allee": "ALLEE", "allée": "ALLEE",
    "sq": "SQUARE", "square": "SQUARE",
    "qu": "QUAI", "quai": "QUAI",
    "vla": "VILLA", "villa": "VILLA",
    "cit": "CITE", "cite": "CITE", "cité": "CITE",
    "ch": "CHEMIN", "chemin": "CHEMIN",
    "rte": "ROUTE", "route": "ROUTE",
    "ptr": "PETITE RUE", "ruelle": "RUELLE",
    "cours": "COURS",
}

# Words to skip when looking for voie name
VOIE_NOISE = {"de", "la", "le", "les", "du", "des", "d", "l"}


def cle_from_compl(s):
    """Tente de derouler une cle 'NUM|TYPE_VOIE|NOM_VOIE' depuis une
    adresse RNC compl. Renvoie None si parsing impossible."""
    s = (s or "").strip().lower()
    if not s or s == "non connu":
        return None
    # remove postal+ville (4-5 digits puis tout le reste)
    s = re.sub(r"\s+(?:75\d{3}|69\d{3})\b.*$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    parts = s.split()
    if len(parts) < 2:
        return None
    # numero (possibly with letter suffix : "20", "20bis", "20 bis", "13B", "13 b")
    m = re.match(r"^(\d+)\s*([a-z])?$", parts[0])
    if not m:
        return None
    num = m.group(1)
    suffix = (m.group(2) or "").upper()
    # cas "20 BIS xxx" or "20bis xxx"
    if len(parts) >= 2 and parts[1].lower() in ("bis", "ter", "b"):
        if parts[1].lower() == "bis":
            suffix = "B"
        if parts[1].lower() == "ter":
            suffix = "T"
        if parts[1].lower() == "b":
            suffix = "B"
        parts = [parts[0]] + parts[2:]
    if suffix:
        num = num + suffix
    rest = parts[1:]
    if not rest:
        return None
    # type voie
    tv = rest[0].lower()
    type_voie = VOIE_ABBR.get(tv)
    if type_voie:
        rest = rest[1:]
    else:
        # peut etre que c'est sans type explicite (ex Lyon "1 rue de la villette")
        # on prend RUE par defaut si premier token = mot generique
        # ou laisse vide
        type_voie = ""
    # nom voie : reste, en retirant 'de la' 'des' etc, mais on garde tout
    nom = " ".join(rest).upper().strip()
    # Skip leading "DE LA " "DE " "DU " "DES " "L'"
    nom = re.sub(r"^\s*(DE\s+LA\s+|DE\s+L'?\s*|DE\s+|DU\s+|DES\s+|L\s*'\s*)", "", nom)
    nom = nom.strip(",.; ")
    if not nom:
        return None
    return f"{num}|{type_voie}|{nom}"


def main():
    out_lines = []
    out_lines.append("# Audit copros multi-parcelles (RNC `reference_cadastrale_2/3`)\n")
    out_lines.append(
        "Source : snapshot RNC raw `data/secteur_*.json` (champ "
        "`reference_cadastrale_2`/`_3` non vide). Cette declaration "
        "**explicite** par RNC est la preuve la plus solide d'une "
        "copro RNC multi-bati sur plusieurs bgids BDNB distincts "
        "(cf. precedent fix Fondary/Croix Nivert `0b05a1e`).\n"
    )
    out_lines.append(
        "**Note jointure cadastrale** : Paris (75) = jointure "
        "BDNB.l_parcelle_id <-> RNC.ref_cadastrale via normalisation "
        "`PARIS{arr}|{SECT}|{NUM}` ; Lyon Dauphine = jointure "
        "**indisponible** (l_parcelle_id absent dans `bdnb_dauphine_"
        "lacassagne.json`) -> fallback methode B (adresse compl <-> "
        "adresses[] light).\n"
    )

    total_multi_all = 0
    total_actionable_all = 0
    actionable_summary = []

    for sect, label, region_key in SECTEURS:
        raw_path = DATA / f"secteur_{sect}.json"
        light_path = DATA / f"secteur_{sect}_light.json"
        bdnb_path = DATA / f"bdnb_{sect}.json"
        if not (raw_path.exists() and light_path.exists() and bdnb_path.exists()):
            out_lines.append(f"\n## [{label}] FICHIERS MANQUANTS, secteur ignore\n")
            continue
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        light = json.loads(light_path.read_text(encoding="utf-8"))
        bdnb = json.loads(bdnb_path.read_text(encoding="utf-8"))

        # Build cadastral index (only Paris has l_parcelle_id BDNB)
        parc_to_bgids = collections.defaultdict(set)
        for b in bdnb:
            for p in (b.get("l_parcelle_id") or []):
                k = parcelle_key(p)
                if k:
                    parc_to_bgids[k].add(b["batiment_groupe_id"])
        has_cad_index = len(parc_to_bgids) > 0

        # Build adresses index by cle + by bgid
        adr_by_cle = {a["cle"]: a for a in light["adresses"]}
        adr_by_bgid = collections.defaultdict(list)
        for a in light["adresses"]:
            bg = a.get("batiment_groupe_id")
            if bg:
                adr_by_bgid[bg].append(a)
        # copros indexed by immat for "is visible"
        copro_by_immat_light = {c.get("numero_immatriculation"): c
                                for c in light["coproprietes"]
                                if c.get("numero_immatriculation")}

        # Scan multi-parcelle copros in raw
        copros = raw.get("coproprietes", [])
        multi = []
        for c in copros:
            rc2 = (c.get("reference_cadastrale_2") or "").strip()
            rc3 = (c.get("reference_cadastrale_3") or "").strip()
            if rc2 or rc3:
                multi.append(c)
        total_multi_all += len(multi)

        out_lines.append(f"\n## [{label}]  (snapshot raw : {len(copros)} copros)\n")
        out_lines.append(
            f"**Copros multi-parcelles** : {len(multi)} declarent au "
            "moins une `reference_cadastrale_2` (et/ou `_3`).\n"
        )
        out_lines.append(
            f"**Jointure cadastrale BDNB** : "
            f"{'OUI' if has_cad_index else 'NON'} "
            f"({'champ l_parcelle_id present' if has_cad_index else 'champ l_parcelle_id absent dans bdnb_'+sect+'.json'}).\n"
        )

        # Analyse cas par cas
        nb_action = 0
        rows = []
        for c in multi:
            immat = field(c, "numero_immatriculation",
                          "numero_d_immatriculation")
            nom = field(c, "nom_copropriete",
                        "nom_d_usage_de_la_copropriete")
            nlots = field(c, "nombre_lots_habitation",
                          "nombre_de_lots_a_usage_d_habitation")
            adr_ref = field(c, "adresse_reference",
                            "adresse_de_reference")
            syndic = field(c, "raison_sociale_du_representant_legal",
                           "raison_sociale_representant_legal")
            mandat = field(c, "mandat_en_cours_dans_la_copropriete",
                           "mandat_en_cours")
            rc1 = (c.get("reference_cadastrale_1") or "").strip()
            rc2 = (c.get("reference_cadastrale_2") or "").strip()
            rc3 = (c.get("reference_cadastrale_3") or "").strip()
            compl1 = field(c, "adresse_complementaire_1") or ""
            compl2 = field(c, "adresse_complementaire_2") or ""
            compl3 = field(c, "adresse_complementaire_3") or ""

            # (A) Jointure cadastrale : pour chaque ref_cadastrale,
            # trouver les bgids et leurs adresses
            parc_bgids = []          # liste de (rc, key, bgids, [(cle_adr, immat)])
            for rc in (rc1, rc2, rc3):
                if not rc:
                    continue
                k = parcelle_key(rc)
                bgids = sorted(parc_to_bgids.get(k, set())) if k else []
                adrs = []
                for bg in bgids:
                    for a in adr_by_bgid.get(bg, []):
                        adrs.append((a["cle"], a.get("numero_immatriculation")))
                parc_bgids.append((rc, k, bgids, adrs))

            # (B) Matching adresse compl -> cle adresse
            compl_matches = []
            for compl in (compl1, compl2, compl3):
                k_adr = cle_from_compl(compl)
                # Plusieurs strategies de matching dans adr_by_cle :
                hit = None
                if k_adr:
                    # match exact
                    if k_adr in adr_by_cle:
                        hit = k_adr
                    else:
                        # fuzzy : compare just num|nom_voie (sans type)
                        num, _tv, nom = k_adr.split("|", 2)
                        for cle in adr_by_cle:
                            cnum, ctv, cnom = (cle.split("|") + ["", ""])[:3]
                            if cnum == num and cnom == nom:
                                hit = cle
                                break
                compl_matches.append((compl, k_adr, hit))

            # Visibilite : la copro est-elle dans light ?
            visible_cle = None
            if immat and immat in copro_by_immat_light:
                visible_cle = copro_by_immat_light[immat].get("cle_adresse")

            # Cas actionnable : copro visible + au moins une adresse
            # orpheline (immat=None) sur un autre bgid de la copro,
            # OU une compl_N qui match une adresse hors-RNC du light.
            # On EXCLUT les orphelins deja fusionnes vers l'ancre
            # visible (_fa=True / _fc=visible_cle) : idempotent, rien
            # a faire. Cf. fix_multiparcelles_dl_lot.py dry-run du
            # 2026-05-20 qui a confirme 9/9 idempotents sur 7 cas.
            # On deduplique par cle adresse pour eviter les doublons
            # quand la meme adresse apparait via plusieurs parcelles.
            def _is_already_fused(cle_adr):
                a = adr_by_cle.get(cle_adr) or {}
                return (a.get("_fusion_auto") is True
                        and a.get("_fusion_cible") == visible_cle)

            actionable_bgid_adrs = []
            already_bgid = []        # orph deja fuse vers la bonne cible
            seen_a = set()
            for rc, k, bgids, adrs in parc_bgids:
                for (cle_adr, immat_adr) in adrs:
                    if (immat_adr is None and cle_adr != visible_cle
                            and cle_adr not in seen_a):
                        seen_a.add(cle_adr)
                        if _is_already_fused(cle_adr):
                            already_bgid.append((cle_adr, bgids))
                        else:
                            actionable_bgid_adrs.append((cle_adr, bgids))
            actionable_compl = []
            already_compl = []
            seen_b = set()
            for (compl, k_adr, hit) in compl_matches:
                if hit and hit != visible_cle and hit not in seen_b:
                    seen_b.add(hit)
                    a = adr_by_cle.get(hit)
                    if a and a.get("numero_immatriculation") is None:
                        if _is_already_fused(hit):
                            already_compl.append((compl, hit))
                        else:
                            actionable_compl.append((compl, hit))

            is_actionable = bool(visible_cle) and (
                actionable_bgid_adrs or actionable_compl
            )
            is_already_ok = (bool(visible_cle)
                             and (already_bgid or already_compl)
                             and not is_actionable)
            if is_actionable:
                nb_action += 1

            rows.append({
                "immat": immat,
                "nom": nom,
                "nlots": nlots,
                "syndic": syndic,
                "mandat": mandat,
                "adr_ref": adr_ref,
                "rc1": rc1, "rc2": rc2, "rc3": rc3,
                "compl1": compl1, "compl2": compl2, "compl3": compl3,
                "parc_bgids": parc_bgids,
                "compl_matches": compl_matches,
                "visible_cle": visible_cle,
                "actionable_bgid_adrs": actionable_bgid_adrs,
                "actionable_compl": actionable_compl,
                "already_bgid": already_bgid,
                "already_compl": already_compl,
                "is_actionable": is_actionable,
                "is_already_ok": is_already_ok,
            })

        total_actionable_all += nb_action
        nb_already_ok = sum(1 for r in rows if r["is_already_ok"])
        out_lines.append(
            f"\n**Cas actionnables (RESTANTS)** : {nb_action} / "
            f"{len(multi)} (copro visible + orphelin(s) **non encore "
            "fusionne(s)** vers cette ancre).\n"
        )
        out_lines.append(
            f"**Cas DEJA-FUSE-OK** : {nb_already_ok} (orphelins "
            "deja `_fa=True / _fc=ancre`, aucun fix requis - "
            "confirme par `scripts/fix_multiparcelles_dl_lot.py` "
            "dry-run du 2026-05-20).\n"
        )

        # ─── Tableau detaille ───
        out_lines.append(f"\n### Detail des {len(multi)} copros multi-parcelles\n")
        out_lines.append(
            "| # | immat | nom | nlots | parc | rc1 | rc2 | rc3 | "
            "visible? | statut | candidats |"
        )
        out_lines.append(
            "|--:|---|---|--:|--:|---|---|---|---|---|---|"
        )
        for i, r in enumerate(rows, 1):
            cands = []
            for cle_adr, bgids in r["actionable_bgid_adrs"]:
                cands.append(f"`{cle_adr}` (bgid cadastral)")
            for compl, hit in r["actionable_compl"]:
                cands.append(f"`{hit}` (compl)")
            # cas already-fuse-ok : signaler dans candidats avec marker
            for cle_adr, bgids in r["already_bgid"]:
                cands.append(f"`{cle_adr}` ✓deja-fuse")
            for compl, hit in r["already_compl"]:
                cands.append(f"`{hit}` ✓deja-fuse")
            cands_txt = "<br>".join(sorted(set(cands))) if cands else "—"
            vis = (f"`{r['visible_cle']}`" if r["visible_cle"]
                   else "❌ INVISIBLE")
            if r["is_actionable"]:
                act = "**✅ RESTANT**"
            elif r["is_already_ok"]:
                act = "✓ deja-fuse-ok"
            elif r["visible_cle"]:
                act = "(aucun candidat)"
            else:
                act = "—"
            out_lines.append(
                f"| {i} | `{r['immat']}` | "
                f"{(r['nom'] or '')[:36]} | "
                f"{r['nlots'] or '—'} | "
                f"{1 + bool(r['rc2']) + bool(r['rc3'])} | "
                f"`{r['rc1'][-6:] if r['rc1'] else '—'}` | "
                f"`{r['rc2'][-6:] if r['rc2'] else '—'}` | "
                f"`{r['rc3'][-6:] if r['rc3'] else '—'}` | "
                f"{vis} | {act} | {cands_txt} |"
            )

        # ─── Cas actionnables — fiche complete ───
        if nb_action:
            out_lines.append(
                f"\n### Cas actionnables (fiche complete)\n"
            )
            for i, r in enumerate(rows, 1):
                if not r["is_actionable"]:
                    continue
                out_lines.append(
                    f"\n#### {i}. `{r['immat']}` — {r['nom'] or '(sans nom)'}"
                )
                out_lines.append(f"- **Adresse de reference** : `{r['adr_ref'] or '—'}`")
                out_lines.append(
                    f"- **Lots habitation** : {r['nlots']} · "
                    f"**Syndic** : {r['syndic'] or '—'} · "
                    f"**Mandat** : {r['mandat'] or '—'}"
                )
                out_lines.append(
                    f"- **Visible (ancre principale dans light)** : "
                    f"`{r['visible_cle']}`"
                )
                out_lines.append("- **Parcelles RNC** :")
                for rc, k, bgids, adrs in r["parc_bgids"]:
                    bgs_txt = (", ".join(f"`{b}`" for b in bgids)
                               or "_(non trouve dans BDNB)_")
                    adrs_txt = ", ".join(
                        f"`{ca}` (immat={im})"
                        for ca, im in adrs) or "_(aucune adresse light)_"
                    out_lines.append(
                        f"   - `{rc}` -> key=`{k}` -> "
                        f"bgids: {bgs_txt} -> adresses[]: {adrs_txt}"
                    )
                if r["actionable_bgid_adrs"]:
                    out_lines.append("- **Adresses orphelines (jointure cadastrale)** :")
                    for cle_adr, bgids in r["actionable_bgid_adrs"]:
                        a = adr_by_cle.get(cle_adr, {})
                        out_lines.append(
                            f"   - `{cle_adr}` — bgid `{a.get('batiment_groupe_id')}` "
                            f"— nb_log_bdnb={a.get('nb_log_bdnb')} "
                            f"— vlog={a.get('nb_ventes_logement') or 0} "
                            f"— _fa={a.get('_fusion_auto')}"
                        )
                if r["actionable_compl"]:
                    out_lines.append("- **Adresses orphelines (jointure compl RNC)** :")
                    for compl, hit in r["actionable_compl"]:
                        a = adr_by_cle.get(hit, {})
                        out_lines.append(
                            f"   - compl `{compl!r}` -> "
                            f"`{hit}` — bgid `{a.get('batiment_groupe_id')}` "
                            f"— nb_log_bdnb={a.get('nb_log_bdnb')} "
                            f"— vlog={a.get('nb_ventes_logement') or 0} "
                            f"— _fa={a.get('_fusion_auto')}"
                        )

                orph_set = set()
                for c, _ in r["actionable_bgid_adrs"]:
                    orph_set.add(c)
                for _, c in r["actionable_compl"]:
                    orph_set.add(c)
                # Enrichir avec info ventes pour priorisation
                orph_detail = []
                for o in sorted(orph_set):
                    a = adr_by_cle.get(o, {})
                    orph_detail.append({
                        "cle": o,
                        "vlog": a.get("nb_ventes_logement") or 0,
                        "nb_log_bdnb": a.get("nb_log_bdnb"),
                        "_fa": a.get("_fusion_auto"),
                        "_fc": a.get("_fusion_cible"),
                    })
                actionable_summary.append({
                    "sect": sect,
                    "label": label,
                    "immat": r["immat"],
                    "ancre": r["visible_cle"],
                    "orphelins": sorted(orph_set),
                    "orph_detail": orph_detail,
                    "rcs": [r["rc1"], r["rc2"], r["rc3"]],
                    "nom": r["nom"],
                    "nlots": r["nlots"],
                    "syndic": r["syndic"],
                })

    # ─── Bilan global ───
    out_lines.append("\n---\n## Bilan global\n")
    out_lines.append(
        f"- Copros multi-parcelles RNC scannees : **{total_multi_all}** "
        "sur les 2 secteurs."
    )
    out_lines.append(
        f"- Cas **actionnables** (copro visible + au moins un "
        f"orphelin hors-RNC sur une autre parcelle/bgid) : "
        f"**{total_actionable_all}**."
    )
    out_lines.append(
        "\n**Lecture des colonnes orphelin** : `vlog` = ventes "
        "logement actuelles sur l'adresse orpheline (pertinence "
        "DVF) ; `_fa=True` indique que l'adresse est deja fusionnee "
        "ailleurs - re-pointer la chaine entiere (voir `_fusion_cible`)."
    )
    if actionable_summary:
        out_lines.append("\n### Synthese des cas actionnables (orphelins dedupliques)\n")
        out_lines.append(
            "| sect | immat | ancre | orphelin | vlog | nb_log_bdnb | _fa | _fc | nom copro | nlots |"
        )
        out_lines.append("|---|---|---|---|--:|--:|---|---|---|--:|")
        for c in actionable_summary:
            for o in c["orph_detail"]:
                fa = "✅" if o["_fa"] else "—"
                fc = (f"`{o['_fc']}`" if o['_fc'] else "—")
                out_lines.append(
                    f"| {c['sect'][:6]} | `{c['immat']}` | "
                    f"`{c['ancre']}` | `{o['cle']}` | "
                    f"{o['vlog']} | {o['nb_log_bdnb'] or '—'} | "
                    f"{fa} | {fc} | "
                    f"{(c['nom'] or '')[:30]} | {c['nlots']} |"
                )

    # ─── Recommandations operationnelles ───
    out_lines.append("\n### Priorisation suggeree\n")
    high = [c for c in actionable_summary
            for o in c["orph_detail"] if o["vlog"] >= 2]
    out_lines.append(
        f"- **{len(high)} orphelin(s) avec vlog ≥ 2** (priorite haute, "
        "ventes DVF a relocaliser) :"
    )
    seen = set()
    for c in actionable_summary:
        for o in c["orph_detail"]:
            if o["vlog"] >= 2 and (c["immat"], o["cle"]) not in seen:
                seen.add((c["immat"], o["cle"]))
                out_lines.append(
                    f"   - `{c['immat']}` ({c['nlots']} lots, "
                    f"{(c['syndic'] or '—')[:22]}) <- "
                    f"`{o['cle']}` vlog={o['vlog']}"
                )
    out_lines.append(
        "\n- **Re-points sans ventes (`vlog=0`)** : interet principalement "
        "dedup multi-bgid (parc plus propre), pas de relocalisation DVF. "
        "Pattern Cambronne/Fondary."
    )
    out_lines.append(
        "\n- **Orphelins `_fa=True` (deja fusionnes ailleurs)** : "
        "le re-point vers la copro multi-parcelles correcte doit "
        "absorber la chaine de fusion existante. Pattern "
        "fix_pivot_bdnb_lot (chain_in -> meme ancre)."
    )

    # Note copros invisibles - collecter pendant la boucle precedente
    invisibles = []
    for sect, label, region_key in SECTEURS:
        light_path = DATA / f"secteur_{sect}_light.json"
        raw_path = DATA / f"secteur_{sect}.json"
        if not (light_path.exists() and raw_path.exists()):
            continue
        light = json.loads(light_path.read_text(encoding="utf-8"))
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        cbi = {c.get("numero_immatriculation") for c in light["coproprietes"]
               if c.get("numero_immatriculation")}
        for c in raw.get("coproprietes", []):
            rc2 = (c.get("reference_cadastrale_2") or "").strip()
            rc3 = (c.get("reference_cadastrale_3") or "").strip()
            if not (rc2 or rc3):
                continue
            immat = field(c, "numero_immatriculation",
                          "numero_d_immatriculation")
            if immat and immat not in cbi:
                invisibles.append({
                    "sect": sect,
                    "immat": immat,
                    "nom": field(c, "nom_copropriete",
                                 "nom_d_usage_de_la_copropriete"),
                    "adr_ref": field(c, "adresse_reference",
                                     "adresse_de_reference"),
                    "nlots": field(c, "nombre_lots_habitation",
                                   "nombre_de_lots_a_usage_d_habitation"),
                    "rc1": (c.get("reference_cadastrale_1") or "").strip(),
                    "rc2": rc2, "rc3": rc3,
                })

    out_lines.append("\n### Copros multi-parcelles INVISIBLES\n")
    if invisibles:
        out_lines.append(
            f"**{len(invisibles)} copro(s)** multi-parcelles dont "
            "l'immatriculation n'est present dans aucune adresse du "
            "light. Necessite injection prealable (pattern `fix_"
            "horsrnc_attribution` cat. A/B2 ou pattern Suffren si "
            "absente du snapshot RNC).\n"
        )
        out_lines.append(
            "| sect | immat | nom | nlots | adr_ref | rc1 | rc2 | rc3 |"
        )
        out_lines.append("|---|---|---|--:|---|---|---|---|")
        for inv in invisibles:
            out_lines.append(
                f"| {inv['sect'][:6]} | `{inv['immat']}` | "
                f"{(inv['nom'] or '')[:34]} | {inv['nlots'] or '—'} | "
                f"{(inv['adr_ref'] or '')[:40]} | "
                f"`{inv['rc1'][-6:] if inv['rc1'] else '—'}` | "
                f"`{inv['rc2'][-6:] if inv['rc2'] else '—'}` | "
                f"`{inv['rc3'][-6:] if inv['rc3'] else '—'}` |"
            )
    else:
        out_lines.append(
            "Aucune copro multi-parcelles invisible (toutes les "
            "copros multi-cadastrales sont rattachees a une adresse "
            "du light).\n"
        )

    # ─── Limites de l'audit ───
    out_lines.append("\n### Limites de l'audit\n")
    out_lines.append(
        "1. **Snapshot RNC fige** : le scan utilise `secteur_*.json` "
        "(snapshot ingere a une date donnee). Des copros peuvent "
        "avoir renseigne `reference_cadastrale_2/3` plus recemment "
        "dans RNC live - un re-scan periodique via RNC live pourrait "
        "reveler des cas supplementaires.\n"
        "2. **Jointure cadastrale Lyon indisponible** : "
        "`bdnb_dauphine_lacassagne.json` n'a pas de `l_parcelle_id` "
        "-> seule la methode B (compl <-> adresses) est utilisee "
        "pour DL, plus fragile (depend du parsing d'adresse).\n"
        "3. **Faux positifs methode B** : un match `compl -> cle "
        "adresse` peut correspondre a une autre copro homonyme (cf. "
        "260 PAUL BERT vlog=5 mais nb_log_bdnb=1 = local "
        "commercial, ou 14 CARRY deja fusionne dans 6 CARRY). "
        "Verifier le bgid avant tout re-point.\n"
        "4. **`_fa=True` indique deja fusionne** : un re-point doit "
        "absorber toute la chaine `_fusion_cible -> orphelin` "
        "(pattern `fix_pivot_bdnb_lot.absorbe_chaine`).\n"
    )

    out_lines.append(
        "\n---\n*Audit en lecture seule. Source : "
        "`secteur_*.json` snapshot RNC + `bdnb_*.json` BDNB enrichi "
        "+ `secteur_*_light.json` (adresses + copros). Genere par "
        "`scripts/audit_copros_multiparcelles.py` "
        "(PYTHONUTF8=1).*"
    )
    OUT.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"OK : ecrit {OUT}")
    print(f"  total multi-parcelles : {total_multi_all}")
    print(f"  total actionnables    : {total_actionable_all}")


if __name__ == "__main__":
    main()
