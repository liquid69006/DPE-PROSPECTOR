/**
 * _assign_a_envoyer.js
 *
 * Marque statut='À envoyer' pour les 316 SCI du CSV de relance, dans la map
 * consolidée sci-assignments:lopez (merge, pas clobber).
 *
 * Workflow :
 *   1) toi    : wrangler kv key get -> data/_sci_assignments_lopez.json
 *   2) ce script : merge -> data/_sci_assignments_lopez_merged.json (+ backup + log)
 *   3) toi    : wrangler kv key put data/_sci_assignments_lopez_merged.json
 *
 * Règles de merge :
 *   - SIREN absent                          -> { statut:'À envoyer', conseiller:'' }
 *   - SIREN présent, statut PROTEGE          -> skip + log  (Déjà client / Ne plus contacter)
 *   - SIREN présent, autre statut            -> statut='À envoyer', conseiller PRESERVE
 *
 * Usage : node scripts/_assign_a_envoyer.js
 *   [--csv data/_sci_mp_a_relancer_2026-05-29.csv]
 *   [--in  data/_sci_assignments_lopez.json]
 *   [--out data/_sci_assignments_lopez_merged.json]
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
function arg(n, d) { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; }
const CSV_PATH = arg('--csv', 'data/_sci_mp_a_relancer_2026-05-29.csv');
const IN_PATH  = arg('--in', 'data/_sci_assignments_lopez.json');
const OUT_PATH = arg('--out', 'data/_sci_assignments_lopez_merged.json');
const NEW_STATUT = 'À envoyer';
const PROTECTED = new Set(['Déjà client', 'Ne plus contacter']);

// lecture tolérante (BOM UTF-8/UTF-16, ANSI wrangler, junk avant/après le JSON)
function readTextTolerant(file) {
  const buf = fs.readFileSync(file);
  let txt;
  if (buf.length >= 2 && buf[0] === 0xFF && buf[1] === 0xFE)      txt = buf.toString('utf16le');
  else if (buf.length >= 2 && buf[0] === 0xFE && buf[1] === 0xFF) txt = buf.swap16().toString('utf16le');
  else                                                            txt = buf.toString('utf8');
  return txt.replace(/^﻿/, '').replace(/\x1b\[[0-9;]*m/g, '');
}
function parseAssignments(file) {
  if (!fs.existsSync(path.join(ROOT, file))) return {};
  let t = readTextTolerant(path.join(ROOT, file)).trim();
  if (!t || t === 'null') return {};
  if (t[0] !== '{') { const a = t.indexOf('{'), b = t.lastIndexOf('}'); if (a >= 0 && b > a) t = t.slice(a, b + 1); }
  const obj = JSON.parse(t);
  return (obj && typeof obj === 'object') ? obj : {};
}

// CSV reliquat : UTF-8 BOM, séparateur ';', 1re colonne = sci_siren
function readSirens(file) {
  const txt = readTextTolerant(path.join(ROOT, file));
  const lines = txt.split(/\r?\n/).filter(l => l.trim() !== '');
  const out = [];
  for (let i = 1; i < lines.length; i++) {           // skip entête
    const siren = lines[i].split(';')[0].replace(/^"|"$/g, '').trim();
    if (siren) out.push(siren);
  }
  return out;
}

// ── charge ──────────────────────────────────────────────────────────────
const sirens = readSirens(CSV_PATH);
const assignments = parseAssignments(IN_PATH);
const beforeKeys = Object.keys(assignments).length;

// ── backup horodaté de l'entrée (sécurité) ───────────────────────────────
if (fs.existsSync(path.join(ROOT, IN_PATH))) {
  const d = new Date();
  const z = n => String(n).padStart(2, '0');
  const stamp = `${d.getFullYear()}${z(d.getMonth() + 1)}${z(d.getDate())}_${z(d.getHours())}${z(d.getMinutes())}${z(d.getSeconds())}`;
  const bak = `data/_sci_assignments_lopez_backup_${stamp}.json`;
  fs.copyFileSync(path.join(ROOT, IN_PATH), path.join(ROOT, bak));
  console.log('🛟 Backup entrée : ' + bak);
}

// ── merge ─────────────────────────────────────────────────────────────────
let marquees = 0, ajoutes = 0, ecrases = 0;
const skippees = [];
for (const siren of sirens) {
  const cur = assignments[siren];
  if (cur && cur.statut && PROTECTED.has(cur.statut)) {
    skippees.push({ siren, statut: cur.statut, conseiller: cur.conseiller || '' });
    continue;
  }
  if (cur) {
    cur.statut = NEW_STATUT;                 // conseiller préservé tel quel
    marquees++; ecrases++;
  } else {
    assignments[siren] = { statut: NEW_STATUT, conseiller: '' };
    marquees++; ajoutes++;
  }
}

fs.writeFileSync(path.join(ROOT, OUT_PATH), JSON.stringify(assignments), 'utf8');

// ── sortie ──────────────────────────────────────────────────────────────
console.log('');
console.log('=== Assignation statut "À envoyer" (sci-assignments:lopez) ===');
console.log('SIREN dans le CSV de relance      : ' + sirens.length);
console.log('Clés dans la map AVANT            : ' + beforeKeys);
console.log('Clés dans la map APRÈS            : ' + Object.keys(assignments).length);
console.log('');
console.log(marquees + ' SCI marquées À envoyer (' + ajoutes + ' ajouts + ' + ecrases + ' écrasements), ' + skippees.length + ' skippées (déjà client/NPC)');
if (skippees.length) {
  console.log('');
  console.log('— SCI skippées (statut métier protégé) —');
  for (const s of skippees) console.log('  - ' + s.siren + '  [' + s.statut + ']' + (s.conseiller ? ' / ' + s.conseiller : ''));
}
console.log('');
console.log('✅ Fichier prêt à uploader : ' + OUT_PATH);
