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
const SRC = [
  slice(2046, 2050),   // ROT_COLOR + TYPE_OPTS
  slice(2072, 2074),   // esc
  slice(2076, 2080),   // secteurNorm
  slice(2094, 2134),   // sctTauxAnnuel..sctBadge (helpers de rendu)
  slice(2136, 2469),   // renderSecteur (parc RNC + hors-RNC résid. BDNB / strict / hr-actif / sctQ)
].join("\n\n");

function mkEl() {
  return {
    _html: "", _text: "",
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; },
    set textContent(v) { this._text = v; }, get textContent() { return this._text; },
    style: {},
  };
}

function runRender(jsonPath, strict, search, hrActif) {
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
    secteurFusions: {}, secteurNoms: {}, secteurAssign: {}, secteurNoLog: false,
    secteurStrict: !!strict,
    secteurHrActif: !!hrActif,        // filtre "Hors-RNC actifs"
    secteurVille: process.env.SECTEUR === "motte_picquet" ? "Paris 15" : "Lyon 3",
    document: { getElementById: (id) => els[id] || mkEl() },
    console,
  };
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
let nbVis = 0;
for (const a of injRows) if (curHtml.includes(`data-cle="${a.cle}"`)) nbVis++;
check(`toutes les lignes injectees rendues (${nbVis}/${injRows.length})`,
  nbVis === injRows.length);

// B3 : test specifique Dauphine (cle '5|RUE|MONTBRILLANT' / immat
// AA9380684) -> gate sur le secteur. Generique pour les autres.
if (DAUPH) {
  console.log("\n=== Desambiguisation B3 (5 rue Montbrillant) ===");
  const monrows = sd.adresses.filter(a => /^5\|RUE\|MONTBRILLANT/.test(a.cle));
  console.log("  lignes:", monrows.map(a =>
    a.cle + (a._bdnb_match === "immat_fix" ? " [fix]" : "")).join("  ;  "));
  check("2 lignes distinctes pour 5 rue Montbrillant", monrows.length === 2);
  check('row origine rendu (data-cle="5|RUE|MONTBRILLANT")',
    curHtml.includes('data-cle="5|RUE|MONTBRILLANT"'));
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
// .bak = etat precedent (roule a chaque apply) : on exige une evolution
// monotone (jamais de regression du parc / des adresses), pas un delta fige.
const dAdr = adr(curResume) - adr(bakResume);
check(`lgts patche >= lgts .bak (${lgt(bakResume)} -> ${lgt(curResume)})`,
  lgt(curResume) >= lgt(bakResume));
check(`adresses patche >= adresses .bak (delta ${dAdr})`, dAdr >= 0);

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
const cur2 = runRender(CUR);            // brut, sans filtre
const secL = lgt(cur2.els["secteur-resume"]._text || "");
const RESID = { "Résidentiel collectif": 1, "Résidentiel individuel": 1 };
const uResid = a => !!(a && RESID[a.usage_principal_bdnb]);
const shown = (sd.adresses || []).filter(a => !(a._fusion_auto && a._fusion_cible));
const immatBg = {}, bgRnc = {}, bgResid = {};
for (const a of shown) {
  const bg = a.batiment_groupe_id || null;
  const c = cbc[a.cle];
  const im = c ? (c.numero_immatriculation || c.cle_adresse || a.cle) : null;
  const lots = (c && c.nb_lots_habitation > 0) ? c.nb_lots_habitation : 0;
  if (bg && im && lots > 0) {
    if (immatBg[im] == null) immatBg[im] = bg;
    (bgRnc[immatBg[im]] = bgRnc[immatBg[im]] || {})[im] = lots;
  }
  if (bg && !c && uResid(a) && a.nb_log_bdnb > 0 && bgResid[bg] == null)
    bgResid[bg] = a.nb_log_bdnb;
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
  let k = null, v = 0;
  if (a.batiment_groupe_id && bgVal[a.batiment_groupe_id] > 0) {
    k = "bg:" + a.batiment_groupe_id; v = bgVal[a.batiment_groupe_id] || 0;
  } else if (c) {
    const im = c.numero_immatriculation || c.cle_adresse || a.cle;
    if (immatBg[im]) { k = "bg:" + immatBg[im]; v = bgVal[immatBg[im]] || 0; }
    else { k = "rnc:" + im; v = (c.nb_lots_habitation > 0 ? c.nb_lots_habitation : 0); }
  } else if (uResid(a) && a.nb_log_bdnb > 0) {
    k = "adr:" + a.cle; v = a.nb_log_bdnb;
  }
  if (k && v > 0 && !seen.has(k)) { seen.add(k); expected += v; }
}
console.log(`  secL=${secL}  attendu (réplique règle)=${expected}  `
  + `écart=${secL - expected}`);
check(`secL > 0`, secL > 0);
check(`secL == réplique EXACTE de la règle parc (${secL} == ${expected})`,
  secL === expected);

// ── Change 2 : filtre "Hors-RNC actifs" ─────────────────────────
// hors-RNC = pas de copro liée ET pas d'immat dénormalisé ; actif =
// nb_ventes_logement > 0. Doit retourner des adresses pertinentes
// (>0, < total, 0 RNC) et matcher le prédicat sur les 2 secteurs.
console.log(`\n=== Change 2 : filtre Hors-RNC actifs (secteur=${SECTEUR}) ===`);
const hr = runRender(CUR, false, "", true);
const hrR = hr.els["secteur-resume"]._text || "";
console.log("  resume hr-actif :", hrR);
const rncN = s => { const m = /· (\d+) RNC ·/.exec(s); return m ? +m[1] : -1; };
let predN = 0;
(sd.adresses || []).forEach(a => {
  if (a._fusion_auto && a._fusion_cible) return;
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
