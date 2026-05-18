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

// Blocs sources de index.html (cf. numeros de ligne verifies)
const SRC = [
  slice(1983, 1987),   // ROT_COLOR + TYPE_OPTS
  slice(2009, 2011),   // esc
  slice(2013, 2017),   // secteurNorm
  slice(2058, 2096),   // sctTauxAnnuel..sctBadge (helpers de rendu)
  slice(2098, 2383),   // renderSecteur
].join("\n\n");

function mkEl() {
  return {
    _html: "", _text: "",
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; },
    set textContent(v) { this._text = v; }, get textContent() { return this._text; },
    style: {},
  };
}

function runRender(jsonPath) {
  const secteurData = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
  const els = {
    "secteur-tree": mkEl(),
    "secteur-resume": mkEl(),
    "secteur-colhead": mkEl(),
  };
  const sandbox = {
    secteurData,
    secteurFusions: {}, secteurNoms: {}, secteurAssign: {}, secteurNoLog: false,
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
  return { error, els, n: secteurData.adresses.length };
}

function check(name, cond) {
  console.log(`  ${cond ? "OK  " : "FAIL"}  ${name}`);
  if (!cond) process.exitCode = 1;
}

const BAK = path.join(ROOT, "data", "secteur_dauphine_lacassagne_light.json.bak");
const CUR = path.join(ROOT, "data", "secteur_dauphine_lacassagne_light.json");

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

// Le tableau affiche l'ADRESSE (a.adresse), pas le nom de copro.
// On verifie les libelles d'adresse reellement injectes : presents
// dans le rendu patche, absents du .bak.
const sd = JSON.parse(fs.readFileSync(CUR, "utf8"));
const injRows = sd.adresses.filter(a => a._bdnb_match === "immat_fix");
console.log("\n=== Copros injectees visibles (par adresse affichee) ===");
check("42 lignes immat_fix dans le JSON", injRows.length === 42);
let nbVis = 0, nbBakAbs = 0;
for (const a of injRows) {
  const tag = `data-cle="${a.cle}"`;            // present dans nameCell
  if (curHtml.includes(tag)) nbVis++;
  if (!bakHtml.includes(`data-cle="${a.cle}"`)) nbBakAbs++;
}
check(`les 42 lignes rendues (data-cle) dans le patche (${nbVis}/42)`, nbVis === 42);
check(`les 42 cles absentes du .bak (${nbBakAbs}/42)`, nbBakAbs === 42);
// echantillon lisible
for (const adrTxt of ["2 RUE DAHLIAS", "311 RUE PAUL BERT", "76 RUE ETIENNE RICHERAND"]) {
  check(`"${adrTxt}" rendu (patche)`, curHtml.includes(adrTxt));
  check(`"${adrTxt}" absent (.bak)`, !bakHtml.includes(adrTxt));
}

// B3 : 2 lignes distinctes a la meme adresse postale, toutes deux rendues
console.log("\n=== Desambiguisation B3 (5 rue Montbrillant) ===");
const monrows = sd.adresses.filter(a => /^5\|RUE\|MONTBRILLANT/.test(a.cle));
console.log("  lignes:", monrows.map(a =>
  a.cle + (a._bdnb_match === "immat_fix" ? " [fix]" : "")).join("  ;  "));
check("2 lignes distinctes pour 5 rue Montbrillant", monrows.length === 2);
check('row origine rendu (data-cle="5|RUE|MONTBRILLANT")',
  curHtml.includes('data-cle="5|RUE|MONTBRILLANT"'));
check('row B3 injectee rendu (data-cle="5|RUE|MONTBRILLANT #AA9380684")',
  curHtml.includes('data-cle="5|RUE|MONTBRILLANT #AA9380684"'));

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
check("lgts patche > lgts .bak", lgt(curResume) > lgt(bakResume));
check("adresses patche > adresses .bak", adr(curResume) > adr(bakResume));
check("+42 adresses environ", adr(curResume) - adr(bakResume) === 42);

console.log(process.exitCode ? "\nRESULTAT : ECHEC" : "\nRESULTAT : OK");
