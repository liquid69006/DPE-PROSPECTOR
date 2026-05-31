/*
 * Test de rendu headless du dashboard secteur.
 *
 * Extrait la VRAIE fonction renderSecteur() (+ helpers) de index.html et
 * l'execute dans un vm Node avec un shim DOM minimal, contre le fichier
 * light patche ET le backup .bak. Verifie :
 *   - aucune exception levee par renderSecteur()
 *   - le HTML produit est non vide
 *   - les 42 copros injectees apparaissent (absentes du .bak)
 *   - une paire B3 (copro injectee + copro d'origine de l'adresse
 *     partagee) apparait distinctement
 *   - la ligne resume est coherente (lgts patche > lgts .bak)
 *
 * Usage : node scripts/test_render_secteur.js
 */
const fs = require("fs");
const vm = require("vm");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const HTML = fs.readFileSync(path.join(ROOT, "index.html"), "utf8").split(/\r?\n/);
const slice = (a, b) => HTML.slice(a - 1, b).join("\n"); // lignes 1-based inclusives

// Blocs sources de index.html (numeros de ligne verifies — A REVERIFIER
// apres toute edition d'index.html : ces plages sont codees en dur et un
// decalage decoupe renderSecteur au mauvais endroit -> SyntaxError).
// RESYNC 2026-05-19 : index.html avait ete edite (ajout sctClassAnnuel,
// decalage ~+12 lignes) -> les anciennes plages (2046.. .) decoupaient
// mid-statement (Unexpected token '.' sur window.secteurSetAssign).
// RESYNC 2026-05-31 : rattrapage du refactor renderSecteur du 2026-05-24
// (ilot top-level : suppression niveau IRIS, memoire secteurOpenIlot,
// secteurCaptureOpenIlot(), window.ilotEffectif, filtres dropdown
// Categorie/RNC/Ventes). Le test etait inexecutable depuis (plages 2148..
// perimees + globals manquants). Plages recalees sur la structure courante
// (6600+ lignes) ; stubs des nouveaux globals ajoutes dans runRender.
// RESYNC 2026-05-31 (marche libre) : refonte "strict = MARCHE LIBRE"
// (exclusion ancres social/bureaux, fusion-aware) -> sctGen alourdi (fold) +
// renderSecteur deplace en 4817-5397. Plages re-recalees.
const SRC = [
  slice(2512, 2525),   // ROT_COLOR + TYPE_OPTS + TYPE_LABELS + TYPE_BADGE_COLORS
  slice(4715, 4717),   // esc
  slice(4719, 4723),   // secteurNorm
  slice(4767, 4815),   // sctTauxAnnuel..sctClassAnnuel + SCTW + DPE_COLOR + sctDpe..normalizeAdresseDisplay
  slice(4817, 5397),   // renderSecteur (parc / strict / hr-actif / sctQ / marche libre)
].join("\n\n");

function mkEl() {
  return {
    _html: "", _text: "",
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; },
    set textContent(v) { this._text = v; }, get textContent() { return this._text; },
    style: {},
  };
}

function runRender(jsonPath, strict, search, hrActif, assign) {
  const secteurData = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
  const searchEl = mkEl(); searchEl.value = search || "";
  const els = {
    "secteur-tree": mkEl(),
    "secteur-resume": mkEl(),
    "secteur-colhead": mkEl(),
    "secteur-search": searchEl,
  };
  const sandbox = {
    secteurData,
    // secteurAssign : par defaut {} (n'exerce PAS l'exclusion marche libre).
    // Un fixture peuple (cf ASSIGN_DL) l'injecte pour le test marche libre.
    secteurFusions: {}, secteurNoms: {}, secteurAssign: assign || {}, secteurNoLog: false,
    secteurStrict: !!strict,
    secteurVille: process.env.SECTEUR === "motte_picquet" ? "Paris 15" : "Lyon 3",
    // Globals introduits par le refactor renderSecteur 2026-05-24 (ilot
    // top-level) : doivent exister dans le contexte sinon ReferenceError.
    // Valeurs neutres = aucun filtre, etat ilots par defaut.
    secteurCategoriesSelected: new Set(),
    secteurLogement: "", secteurRncFilter: "", secteurVentes: "",
    secteurOpenIlot: null, secteurSciByCle: {}, secteurFilteredCount: 0,
    secteurCaptureOpenIlot: () => {},
    window: {},                       // renderSecteur fait window.ilotEffectif = ...
    document: { getElementById: (id) => els[id] || mkEl() },
    console,
  };
  // [REBASE 2026-05-31] "Hors-RNC actifs" n'est plus un toggle dedie
  // (secteurHrActif supprime au refactor 2026-05-24) : il est porte par la
  // combinaison des dropdowns RNC='hors-rnc' + Ventes='avec'. On mappe le
  // parametre hrActif du test sur cette combinaison.
  if (hrActif) { sandbox.secteurRncFilter = "hors-rnc"; sandbox.secteurVentes = "avec"; }
  vm.createContext(sandbox);
  let error = null;
  try {
    vm.runInContext(SRC + "\nrenderSecteur();", sandbox, { timeout: 15000 });
  } catch (e) {
    error = e;
  }
  runRender._lastSandbox = sandbox;
  return { error, els, n: secteurData.adresses.length };
}

function check(name, cond) {
  console.log(`  ${cond ? "OK  " : "FAIL"}  ${name}`);
  if (!cond) process.exitCode = 1;
}

// Secteur parametrable (defaut dauphine -> comportement inchange).
const SECTEUR = process.env.SECTEUR || "dauphine_lacassagne";
const DAUPH = SECTEUR === "dauphine_lacassagne";
const CUR = path.join(ROOT, "data", `secteur_${SECTEUR}_light.json`);
const BAK = path.join(ROOT, "data", `secteur_${SECTEUR}_light.json.bak`);

console.log("=== Rendu sur .bak (pre-fix) ===");
const bak = runRender(BAK);
if (bak.error) { console.log("  THROW:", bak.error.message); process.exitCode = 1; }
const bakHtml = bak.els["secteur-tree"]._html || "";
const bakResume = bak.els["secteur-resume"]._text || "";
console.log("  adresses:", bak.n, "| resume:", bakResume);
check("renderSecteur() ne leve pas (.bak)", !bak.error);
check("HTML non vide (.bak)", bakHtml.length > 1000);

console.log("\n=== Rendu sur fichier patche ===");
const cur = runRender(CUR);
if (cur.error) { console.log("  THROW:", cur.error.message, "\n", cur.error.stack); }
const curHtml = cur.els["secteur-tree"]._html || "";
const curResume = cur.els["secteur-resume"]._text || "";
console.log("  adresses:", cur.n, "| resume:", curResume);
check("renderSecteur() ne leve pas (patche)", !cur.error);
check("HTML non vide (patche)", curHtml.length > 1000);

// Toutes les lignes injectees par les correctifs (quel que soit le
// marqueur) doivent etre rendues. .bak = etat precedent (roule a chaque
// apply) -> on ne compare PAS un delta fige, on verifie les invariants.
const sd = JSON.parse(fs.readFileSync(CUR, "utf8"));
const MARKERS = ["immat_fix", "immat_live_fix", "immat_horsrnc_fix"];
const injRows = sd.adresses.filter(a => MARKERS.includes(a._bdnb_match));
console.log("\n=== Lignes injectees rendues ===");
check("au moins 1 ligne injectee", injRows.length >= 1);
// REBASE 2026-05-31 : une copro injectee peut depuis avoir ete FUSIONNEE
// (relocalisee sous son ancre via _fusion_auto, cf rebase Montbrillant
// 2026-05-19) -> plus rendue par sa propre ligne mais ventes/lots conserves
// sur l'ancre. Invariant = chaque injectee est RENDUE OU FUSIONNEE (aucune
// disparition silencieuse).
let nbVis = 0, nbFused = 0;
for (const a of injRows) {
  if (curHtml.includes(`data-cle="${a.cle}"`)) nbVis++;
  else if (a._fusion_auto && (a._fusion_cible || a._fusion_auto_target)) nbFused++;
}
check(`injectees rendues OU fusionnees (${nbVis} rendues + ${nbFused} fusionnees == ${injRows.length})`,
  nbVis + nbFused === injRows.length);

// B3 : test specifique Dauphine (cle '5|RUE|MONTBRILLANT' / immat
// AA9380684) -> gate sur le secteur. Generique pour les autres.
if (DAUPH) {
  console.log("\n=== Desambiguisation B3 (5 rue Montbrillant) ===");
  const monrows = sd.adresses.filter(a => /^5\|RUE\|MONTBRILLANT/.test(a.cle));
  console.log("  lignes:", monrows.map(a =>
    a.cle + (a._bdnb_match === "immat_fix" ? " [fix]" : "")).join("  ;  "));
  check("2 lignes distinctes pour 5 rue Montbrillant", monrows.length === 2);
  // REBASE 2026-05-19 (cf. fix_alias_rnc_meme_bgid) : la ligne ORIGINE
  // non suffixee `5|RUE|MONTBRILLANT` n'est PLUS rendue car le lot
  // ALIAS_RNC meme-bgid l'a (legitimement) fusionnee dans sa vraie
  // copro `5B|RUE|MONTBRILLANT` (AA9253212, BDNB-rel + meme bgid,
  // parc-neutre). L'invariant B3 = la copro INJECTEE suffixee #immat
  // se rend distinctement ; l'origine peut etre rendue OU fusionnee
  // (relocalisee) sans casser la desambiguisation.
  const moOrig = sd.adresses.find(a => a.cle === "5|RUE|MONTBRILLANT");
  check('origine 5|RUE|MONTBRILLANT rendue OU fusionnee (relocalisee)',
    curHtml.includes('data-cle="5|RUE|MONTBRILLANT"')
    || !!(moOrig && moOrig._fusion_auto && moOrig._fusion_cible));
  check('row B3 injectee rendu (data-cle="5|RUE|MONTBRILLANT #AA9380684")',
    curHtml.includes('data-cle="5|RUE|MONTBRILLANT #AA9380684"'));
} else {
  console.log(`\n=== B3 Montbrillant : ignore (secteur=${SECTEUR}) ===`);
}

// Garde-fou : aucune copro (immat) rendue par 2 lignes distinctes
console.log("\n=== Aucun double-rendu de copro ===");
const cbc = {};
(sd.coproprietes || []).forEach(c => { if (c.cle_adresse) cbc[c.cle_adresse] = c; });
const seenImmat = {};
let dupImmat = 0;
(sd.adresses || []).forEach(a => {
  const c = cbc[a.cle];
  if (c && c.numero_immatriculation) {
    seenImmat[c.numero_immatriculation] = (seenImmat[c.numero_immatriculation] || 0) + 1;
    if (seenImmat[c.numero_immatriculation] === 2) dupImmat++;
  }
});
check(`aucune immat sur 2 lignes (${dupImmat} doublons)`, dupImmat === 0);

// Coherence resume : lgts patche > lgts .bak
const lgt = s => { const m = /([\d   ]+) lgts/.exec(s); return m ? parseInt(m[1].replace(/[^\d]/g, "")) : -1; };
const adr = s => { const m = /^(\d+) adresses/.exec(s); return m ? parseInt(m[1]) : -1; };
console.log("\n=== Coherence agregats ===");
console.log(`  lgts .bak=${lgt(bakResume)}  ->  patche=${lgt(curResume)}`);
console.log(`  adresses .bak=${adr(bakResume)}  ->  patche=${adr(curResume)}`);
// .bak = etat precedent (roule a chaque apply). Invariant REEL =
// le PARC ne regresse jamais (lgts monotone). REBASE 2026-05-19
// (cf. fix_alias_rnc_meme_bgid) : le NOMBRE de lignes rendues peut
// DECROITRE — un correctif de fusion (ALIAS_RNC) relocalise des
// adresses orphelines hors-RNC sous leur copro (moins de lignes,
// parc & ventes conserves, c'est le but). Le delta adresses devient
// informatif (borne de sanite : reste > 0), la conservation forte
// (parc +0, Sigma ventes identiques) est verifiee par le Change 1
// (secL == replique exacte) et l'audit applicatif.
const dAdr = adr(curResume) - adr(bakResume);
console.log(`  adresses delta vs .bak = ${dAdr} `
  + `(decroissance possible : fusions ALIAS relocalisees)`);
check(`lgts patche >= lgts .bak (${lgt(bakResume)} -> ${lgt(curResume)})`,
  lgt(curResume) >= lgt(bakResume));
check(`adresses rendues > 0 (sanite, delta ${dAdr})`,
  adr(curResume) > 0);

// Toggle "Ventes strictes" : meme fichier, secteurStrict=true.
// Invariants : pas d'exception ; ventes/an strict <= brut (depend. exclues) ;
// logements/adresses INCHANGES (le toggle ne touche que les ventes).
const ven = s => { const m = /· ([\d   ,]+) ventes\/an/.exec(s); return m ? parseFloat(m[1].replace(/[^\d,]/g, "").replace(",", ".")) : -1; };
console.log("\n=== Toggle Ventes strictes (secteurStrict=true) ===");
const strict = runRender(CUR, true);
const sR = strict.els["secteur-resume"]._text || "";
console.log("  brut  :", curResume);
console.log("  strict:", sR);
check("renderSecteur() ne leve pas (strict)", !strict.error);
if (strict.error) console.log("  THROW:", strict.error.message);
check(`ventes/an strict <= brut (${ven(curResume)} -> ${ven(sR)})`,
  ven(sR) >= 0 && ven(sR) <= ven(curResume));
check(`ventes/an strict < brut (effet depend. exclues)`, ven(sR) < ven(curResume));
check(`lgts INCHANGES par le toggle (${lgt(curResume)} == ${lgt(sR)})`,
  lgt(sR) === lgt(curResume));
check(`adresses INCHANGEES par le toggle (${adr(curResume)} == ${adr(sR)})`,
  adr(sR) === adr(curResume));

// ── Strict = MARCHE LIBRE (exclusion ancres social/bureaux, fusion-aware) ──
// 2026-05-31 : l'agregat strict (header/sous-total ilot) exclut les ANCRES
// taguees social/bureaux (jamais l'adresse brute fusionnee), fusion-aware.
// Le sandbox met secteurAssign:{} par defaut -> le toggle ci-dessus ne change
// PAS (aucune exclusion) -> baselines venStrict/venBrut restent vertes. Pour
// EXERCER l'exclusion on injecte un fixture peuple ciblant des cle reellement
// presentes dans le light DL ET porteuses de ventes strictes (sinon "ML <
// total" serait une egalite). 139 AV FELIX FAURE est l'ANCRE de fusion (141 FF
// s'y plie) taguee mixte -> NON exclue, elle CONSERVE les ventes pliees
// (verifie le critere "par ancre"). Le BRUT n'est jamais impacte (gate
// secteurStrict cote index.html).
if (DAUPH) {
  const ASSIGN_DL = {
    "27|AVENUE|LACASSAGNE":   { type: "social"  },  // ancre a fortes ventes -> exclue
    "128|RUE|BARABAN":        { type: "bureaux" },  // ancre a fortes ventes -> exclue
    "139|AVENUE|FELIX FAURE": { type: "mixte"   },  // ANCRE fusion (141 FF) -> NON exclue, garde ventes pliees
  };
  console.log("\n=== Strict = MARCHE LIBRE (fixture social/bureaux) ===");
  const ml = runRender(CUR, true, "", false, ASSIGN_DL);
  const mlR = ml.els["secteur-resume"]._text || "";
  console.log("  strict total (assign vide) :", sR);
  console.log("  strict marche libre        :", mlR);
  check("renderSecteur() ne leve pas (marche libre)", !ml.error);
  if (ml.error) console.log("  THROW:", ml.error.message);
  // L'exclusion ne touche QUE l'agregat ventes : les lignes social/bureaux
  // restent rendues (ventes parenthesees) -> meme nombre d'adresses.
  check(`adresses INCHANGEES par l'exclusion marche libre (${adr(sR)} == ${adr(mlR)})`,
    adr(mlR) === adr(sR));
  // Ventes/an strictes : l'exclusion des ancres social/bureaux porteuses de
  // ventes fait STRICTEMENT baisser l'agregat. (Parc secL : invariant verifie
  // par Change 1 avec assign vide ; le tag social/bureaux zero-ifie deja la
  // contribution parc, comportement existant hors-scope de cette comparaison.)
  check(`ventes/an marche libre < strict total (${ven(mlR)} < ${ven(sR)})`,
    ven(mlR) >= 0 && ven(mlR) < ven(sR));
}

// Nouveaux seuils de classement : 0–1 Figé · 1–2 Modéré · 2–3 Actif · >3 Très actif
console.log("\n=== Seuils sctClassAnnuel (nouveaux) ===");
const sb = runRender._lastSandbox;
const cl = t => vm.runInContext(`sctClassAnnuel(${t})`, sb);
[[0.5, "Figé"], [1, "Modéré"], [1.9, "Modéré"], [2, "Actif"], [2.5, "Actif"],
 [3, "Actif"], [3.01, "Très actif"], [6, "Très actif"]].forEach(([t, exp]) => {
  const got = cl(t);
  check(`sctClassAnnuel(${t}) == ${exp} (got ${got})`, got === exp);
});
// Taux secteur strict : classe self-consistante avec sctClassAnnuel
// (generique). Baseline Dauphine REBASÉE (bascule usage_principal_bdnb) :
// parc = lots RNC + hors-RNC RÉSIDENTIEL nb_log_bdnb (tertiaire/
// secondaire/dépendance/inconnu exclus) -> ~22,3k -> taux strict ~2,5%
// -> "Actif". Historique : 2,5% "Actif" (BDNB brut) -> 3,2% "Très actif"
// (RNC pur, ~17,4k) -> 2,5% "Actif" (bascule résid., ~22,3k).
const tStrict = parseFloat((/taux secteur ([\d.,]+)%/.exec(sR) || [])[1] || "NaN");
const clS = cl(tStrict);
console.log(`  taux secteur strict = ${tStrict}% -> ${clS}`);
check(`classe strict bien definie (${clS})`,
  ["Figé", "Modéré", "Actif", "Très actif"].includes(clS));
if (DAUPH) check(`Dauphine: strict ${tStrict}% classé "Actif" (bascule résid.)`,
  clS === "Actif");

// Recherche = filtre de DONNÉES : header/IRIS recalculés (non figés).
// Terme de recherche derive des donnees (secteur-agnostique) : nom de
// voie le plus frequent -> matche >=1 adresse mais pas toutes.
const _nomCnt = {};
for (const a of sd.adresses) {
  const nm = String(a.cle || "").split("|")[2] || "";
  if (nm) _nomCnt[nm] = (_nomCnt[nm] || 0) + 1;
}
const _top = Object.entries(_nomCnt).sort((x, y) => y[1] - x[1])[0];
const term = (_top ? _top[0] : "").toLowerCase();
console.log(`\n=== Filtre recherche (sctQ, terme='${term}') ===`);
const f = runRender(CUR, false, term);
const fR = f.els["secteur-resume"]._text || "";
console.log("  sans recherche :", curResume);
console.log(`  '${term}'   :`, fR);
check("renderSecteur() ne leve pas (recherche)", !f.error);
if (f.error) console.log("  THROW:", f.error.message);
check(`adresses filtrées >0 et < total (${adr(fR)} < ${adr(curResume)})`,
  adr(fR) > 0 && adr(fR) < adr(curResume));
check(`lgts recalculés sous recherche (${lgt(fR)} <= ${lgt(curResume)})`,
  lgt(fR) >= 0 && lgt(fR) <= lgt(curResume));
const f0 = runRender(CUR, false, "zzzznomatchzzzz");
check("recherche sans résultat -> 0 adresse (header cohérent)",
  adr(f0.els["secteur-resume"]._text || "") <= 0 && !f0.error);

// ── Corrections : mode strict par defaut + nom secteur dynamique ──
console.log("\n=== Mode strict par defaut + nom secteur (index.html) ===");
const idx = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
check("secteurStrict = true par defaut (toggle ON au chargement)",
  /let\s+secteurStrict\s*=\s*true\s*;/.test(idx));
check("h2 #secteur-titre present (titre dynamique)",
  /id="secteur-titre"/.test(idx));
check("loadSecteurData applique le nom (secteur-titre.textContent)",
  /secteur-titre'\)[\s\S]{0,80}textContent\s*=\s*'.*Secteur Prospector/.test(idx));
// secteurResolve : nom correct pour les 2 agences
const mfn = idx.match(/function secteurResolve\(\)\s*\{[\s\S]*?\n\}/);
check("secteurResolve() extractible", !!mfn);
if (mfn) {
  for (const [ag, exp, ville] of [
    ["dauphine-lacassagne", "Dauphiné-Lacassagne (Lyon 3e)", "Lyon 3"],
    ["motte-picquet", "Motte-Picquet (Paris 15e - 7e)", "Paris 15"]]) {
    let got;
    try {
      got = new Function("agenceId",
        mfn[0] + "\nreturn secteurResolve();")(ag);
    } catch (e) { got = ["ERR:" + e.message]; }
    const nom = Array.isArray(got) ? got[2] : undefined;
    const vl = Array.isArray(got) ? got[3] : undefined;
    check(`secteurResolve('${ag}')[2] == "${exp}" (got ${nom})`, nom === exp);
    check(`secteurResolve('${ag}')[3] ville == "${ville}" (got ${vl})`, vl === ville);
  }
  // Maps : query dynamique via secteurVille (plus de 'Lyon 3' en dur)
  check("Google Maps query utilise secteurVille (non code en dur)",
    /adrTxt \+ ' ' \+ secteurVille/.test(idx) && !/adrTxt \+ ' Lyon 3'/.test(idx));
}

// ── Change 1 (bascule) : parc = RNC + hors-RNC résidentiel BDNB ──
// secL doit = réplique EXACTE de la dedup renderSecteur : clé bg:bgid
// (RNC prioritaire, sinon hors-RNC résidentiel -> nb_log_bdnb, sinon
// 0), sinon rnc:immat, sinon adr:cle (résid. sans bgid). Tertiaire /
// secondaire / dépendance / usage inconnu -> 0.
console.log("\n=== Change 1 : parc RNC + hors-RNC résidentiel (header) ===");
const cur2 = runRender(CUR);            // brut, sans filtre, assign vide
const secL = lgt(cur2.els["secteur-resume"]._text || "");
// REBASE 2026-05-31 : replique alignee sur la logique parc renderSecteur
// post-refactor 2026-05-24 -> bgBdnbResid en 2 PASSES (Pass A = MAX
// nb_log_bdnb hors mono/social/bureaux ; Pass B = fallback getEffectiveLog),
// override _nb_lots_habitation_override, gate (rnc || getEffectiveLog>0) sur
// le path bg:. L'ancienne replique single-pass divergeait (DL -95). assign
// vide ici -> effLog = nb_log_bdnb et aucune exclusion mono/social/bureaux
// active, mais la replique les modelise pour rester fidele si assign injecte.
const RESID = { "Résidentiel collectif": 1, "Résidentiel individuel": 1 };
const uResid = a => !!(a && RESID[a.usage_principal_bdnb]);
const ASG = {};   // assign vide dans le run cur2
const effLog = a => {
  const t = (ASG[a.cle] || {}).type;
  if (t === "mono") return 1;
  if (t === "social" || t === "bureaux") return 0;
  return a.nb_log_bdnb;
};
const shown = (sd.adresses || []).filter(a =>
  !(a._fusion_auto && (a._fusion_cible || a._fusion_auto_target)));
const immatBg = {}, bgRnc = {}, bgResid = {};
// Pass commune RNC : bgRncLots / immatBg (avec override)
for (const a of shown) {
  const bg = a.batiment_groupe_id || null;
  const c = cbc[a.cle];
  const im = c ? (c.numero_immatriculation || c.cle_adresse || a.cle) : null;
  const lots = (a._nb_lots_habitation_override != null)
    ? a._nb_lots_habitation_override
    : ((c && c.nb_lots_habitation > 0) ? c.nb_lots_habitation : 0);
  if (bg && im && lots > 0) {
    if (immatBg[im] == null) immatBg[im] = bg;
    (bgRnc[immatBg[im]] = bgRnc[immatBg[im]] || {})[im] = lots;
  }
}
// Pass A bgBdnbResid : MAX nb_log_bdnb (hors-RNC resid, hors mono/social/bureaux)
for (const a of shown) {
  const bg = a.batiment_groupe_id || null;
  const c = cbc[a.cle];
  if (!bg || c || !uResid(a) || !(a.nb_log_bdnb > 0)) continue;
  const t = (ASG[a.cle] || {}).type;
  if (t === "mono" || t === "social" || t === "bureaux") continue;
  if (bgResid[bg] == null || a.nb_log_bdnb > bgResid[bg]) bgResid[bg] = a.nb_log_bdnb;
}
// Pass B bgBdnbResid : fallback getEffectiveLog si Pass A n'a rien capte
for (const a of shown) {
  const bg = a.batiment_groupe_id || null;
  const c = cbc[a.cle];
  if (!bg || c || !uResid(a) || !(a.nb_log_bdnb > 0)) continue;
  if (bgResid[bg] != null) continue;
  const e = effLog(a);
  if (e > 0) bgResid[bg] = e;
}
const bgVal = {};
new Set(Object.keys(bgRnc).concat(Object.keys(bgResid))).forEach(bg => {
  bgVal[bg] = bgRnc[bg]
    ? Object.values(bgRnc[bg]).reduce((s, v) => s + v, 0)
    : (bgResid[bg] || 0);
});
const seen = new Set(); let expected = 0;
for (const a of shown) {
  const c = cbc[a.cle];
  const rnc = !!c;
  let k = null, v = 0;
  if (a.batiment_groupe_id && bgVal[a.batiment_groupe_id] > 0
      && (rnc || effLog(a) > 0)) {
    k = "bg:" + a.batiment_groupe_id; v = bgVal[a.batiment_groupe_id] || 0;
  } else if (rnc) {
    const im = c.numero_immatriculation || c.cle_adresse || a.cle;
    if (immatBg[im]) { k = "bg:" + immatBg[im]; v = bgVal[immatBg[im]] || 0; }
    else {
      k = "rnc:" + im;
      v = (a._nb_lots_habitation_override != null)
        ? a._nb_lots_habitation_override
        : (c.nb_lots_habitation > 0 ? c.nb_lots_habitation : 0);
    }
  } else if (uResid(a) && a.nb_log_bdnb > 0) {
    k = "adr:" + a.cle; v = effLog(a);
  }
  if (k && v > 0 && !seen.has(k)) { seen.add(k); expected += v; }
}
console.log(`  secL=${secL}  attendu (réplique règle 2-passes)=${expected}  écart=${secL - expected}`);
check(`secL > 0`, secL > 0);
check(`secL == réplique EXACTE de la règle parc (${secL} == ${expected})`,
  secL === expected);

// ── Change 2 : filtre "Hors-RNC actifs" ─────────────────────────
// hors-RNC = pas de copro liée ET pas d'immat dénormalisé ; actif =
// nb_ventes_logement > 0. Doit retourner des adresses pertinentes
// (>0, < total, 0 RNC) et matcher le prédicat sur les 2 secteurs.
console.log(`\n=== Change 2 : filtre Hors-RNC actifs (secteur=${SECTEUR}) ===`);
// REBASE 2026-05-31 : "Hors-RNC actifs" n'est plus un toggle dedie
// (secteurHrActif supprime au refactor 2026-05-24) -> runRender mappe le
// param hrActif sur RNC='hors-rnc' + Ventes='avec'. Le predicat data suit :
// non-fused & hors-RNC (!copro & !immat) & nb_ventes_logement>0. L'ancien
// predicat exigeait nb_log_bdnb>1 (retire : le dropdown 'avec' ne filtre que
// sur les ventes).
const hr = runRender(CUR, false, "", true);
const hrR = hr.els["secteur-resume"]._text || "";
console.log("  resume hr-actif :", hrR);
const rncN = s => { const m = /· (\d+) RNC ·/.exec(s); return m ? +m[1] : -1; };
let predN = 0;
(sd.adresses || []).forEach(a => {
  if (a._fusion_auto && (a._fusion_cible || a._fusion_auto_target)) return;
  const horsRnc = !cbc[a.cle] && !a.numero_immatriculation;
  if (horsRnc && a.nb_ventes_logement > 0) predN++;
});
console.log(`  adresses filtrées=${adr(hrR)}  prédicat data=${predN}`
  + `  RNC affichées=${rncN(hrR)}`);
check("hr-actif : >0 adresse pertinente", adr(hrR) > 0);
check(`hr-actif : < total (${adr(hrR)} < ${adr(curResume)})`,
  adr(hrR) < adr(curResume));
check("hr-actif : 0 RNC affichée (toutes hors-RNC)", rncN(hrR) === 0);
check(`hr-actif : adresses == prédicat data (${adr(hrR)} == ${predN})`,
  adr(hrR) === predN && predN > 0);
// Cumul avec strict + sans-logements (pas d'exception, sous-ensemble)
const hrCombo = runRender(CUR, true, "", true);
const hrCR = hrCombo.els["secteur-resume"]._text || "";
console.log("  cumul strict+hr :", hrCR);
check("hr-actif cumulable strict (pas d'exception)", !hrCombo.error);
check(`cumul strict+hr <= hr seul (${adr(hrCR)} <= ${adr(hrR)})`,
  !hrCombo.error && adr(hrCR) >= 0 && adr(hrCR) <= adr(hrR));

console.log(process.exitCode ? "\nRESULTAT : ECHEC" : "\nRESULTAT : OK");
