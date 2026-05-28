/**
 * DPE Prospector — Cloudflare Worker v2
 * API backend centralisé multi-agences
 *
 * Routes :
 *   GET  /health
 *   POST /login                        → { agence, password } → { token, agence, config }
 *   POST /forgot-password              → { agence } → envoie email reset
 *   POST /reset-password               → { token, newPassword }
 *   GET  /assignments/:agence          → { assignments }
 *   POST /assignments/:agence          → { assignments }
 *   GET  /sci-assignments/:agence      → { assignments }
 *   POST /sci-assignments/:agence      → { assignments }
 *   GET  /conseillers/:agence          → { conseillers }
 *   POST /conseillers/:agence          → { conseillers }
 *   POST /change-password/:agence      → { oldPassword, newPassword }
 */

// ══════════════════════════════════════════════════════
//  TABLE IDENTIFIANTS → AGENCES (confidentiel côté serveur)
// ══════════════════════════════════════════════════════

const IDENTIFIANTS = {
  // Patrons (mono ou multi-agence) — valeur = id agence (composite ou simple)
  "bufferne":  "dauphine-lacassagne",
  "bagot":     "bagot",        // composite houlgate + villers
  "lopez":     "lopez",        // composite motte-picquet + pernety (inchangé)
  // Identifiants courts (fallbacks)
  "dauphine":  "dauphine-lacassagne",
  "motte":     "motte-picquet",
  "pernety":   "pernety",
  "houlgate":  "houlgate",
  "villers":   "villers",
};

// ══════════════════════════════════════════════════════
//  CONFIGURATION STATIQUE DES AGENCES
//  (mots de passe stockés dans Cloudflare KV, pas ici)
// ══════════════════════════════════════════════════════

const AGENCES_CONFIG = {
  "dauphine-lacassagne": {
    nom: "Century 21 Dauphiné-Lacassagne",
    ville: "Lyon 3e",
    couleur: "#1d4ed8",
    email: "ybufferne@century21.fr",
    dataJsonPath: "data/dauphine-lacassagne.json",
    conseillers_defaut: ["À attribuer", "Gérald", "Philippe", "Robin", "Kévin", "Yann"],
    zones: ["Dauphiné-Lacassagne", "Montchat"],
    sci_enabled: true,
    secteur_enabled: true,
  },
  "motte-picquet": {
    nom: "Century 21 La Motte Picquet",
    ville: "Paris 15e",
    couleur: "#7c3aed",
    email: "ybufferne@century21.fr",
    dataJsonPath: "data/motte-picquet.json",
    conseillers_defaut: ["À attribuer", "Jean-Marie", "Bérénice", "Joël"],
    zones: ["La Motte Picquet"],
    sci_enabled: true,
    secteur_enabled: true,
  },
  "pernety": {
    nom: "Century 21 Pernéty",
    ville: "Paris 14e",
    couleur: "#059669",
    email: "ybufferne@century21.fr",
    dataJsonPath: "data/pernety.json",
    conseillers_defaut: ["À attribuer", "Mathis", "Julien", "Philippe", "Fahd", "Maxime", "Cyril", "Melchior"],
    zones: ["Pernéty"],
    sci_enabled: false,
    secteur_enabled: false,
  },
  "houlgate": {
    nom: "Century 21 Bagot — Houlgate",
    ville: "Houlgate",
    couleur: "#b45309",
    email: "marine-bagot@century21.fr",
    dataJsonPath: "data/houlgate.json",
    conseillers_defaut: ["À attribuer"],
    zones: ["14510", "14160", "14430"],
    sci_enabled: false,
    secteur_enabled: false,
  },
  "villers": {
    nom: "Century 21 Bagot — Villers-sur-Mer",
    ville: "Villers-sur-Mer",
    couleur: "#b45309",
    email: "marine-bagot@century21.fr",
    dataJsonPath: "data/villers.json",
    conseillers_defaut: ["À attribuer"],
    zones: ["14910", "14640"],
    sci_enabled: false,
    secteur_enabled: false,
  },
  "lopez": {
    nom: "Century 21 Lopez",
    ville: "Paris 14e & 15e",
    couleur: "#7c3aed",
    email: "ybufferne@century21.fr",
    // lopez n'a pas de dataJsonPath unique — les données DPE viennent de motte-picquet + pernety
    dataJsonPath: "data/motte-picquet.json",   // utilisé comme fallback, surchargé côté dashboard
    conseillers_defaut: ["À attribuer", "Jean-Marie", "Bérénice", "Joël", "Mathis", "Julien", "Philippe", "Fahd", "Maxime", "Cyril", "Melchior"],
    zones: ["La Motte Picquet", "Pernéty"],
    sci_enabled: true,
    secteur_enabled: false,  // PAS d'accès Secteur motte (restreint à la session motte-picquet)
    // Agences DPE dont lopez agrège les assignments
    dpe_agences: ["motte-picquet", "pernety"],
    // Agences SCI dont lopez agrège les données
    sci_agences: ["motte-picquet", "pernety"],
  },
  "bagot": {
    nom: "Century 21 Bagot",
    ville: "Houlgate & Villers-sur-Mer",
    couleur: "#b45309",
    email: "marine-bagot@century21.fr",
    // bagot n'a pas de JSON propre — données DPE depuis houlgate + villers
    dataJsonPath: "data/houlgate.json",   // fallback, surchargé côté dashboard
    conseillers_defaut: ["À attribuer"],
    zones: ["14510", "14160", "14430", "14910", "14640"],
    sci_enabled: false,
    // Agences DPE dont bagot agrège les assignments
    dpe_agences: ["houlgate", "villers"],
    // Agences SCI dont bagot agrège les données
    sci_agences: ["houlgate", "villers"],
  },
};

const ADMIN_EMAIL    = "ybufferne@century21.fr";
const TOKEN_TTL_MS   = 24 * 60 * 60 * 1000;      // 24h
const RESET_TTL_MS   =      60 * 60 * 1000;       // 1h

// ══════════════════════════════════════════════════════
//  DESTINATAIRES NOTIF. IDENTIFIANTS CONSEILLERS
//  Clé = agence RÉELLE du conseiller créé (résolue côté serveur),
//  PAS la session connectée. Composite lopez → motte-picquet|pernety.
//  Hors liste → CONSEILLER_NOTIFY_FALLBACK.
// ══════════════════════════════════════════════════════

const CONSEILLER_NOTIFY_EMAIL = {
  "dauphine-lacassagne": "ybufferne@century21.fr",
  "bufferne":            "ybufferne@century21.fr",
  "motte-picquet":       "laurent.lopez@century21.fr",
  "lopez":               "laurent.lopez@century21.fr",
  "pernety":             "laurent.lopez@century21.fr",
  "houlgate":            "marine-bagot@century21.fr",
  "villers":             "marine-bagot@century21.fr",
};
const CONSEILLER_NOTIFY_FALLBACK = "ybufferne@century21.fr";

// ══════════════════════════════════════════════════════
//  JWT (HMAC-SHA256 Web Crypto)
// ══════════════════════════════════════════════════════

function b64url(str) {
  return btoa(str).replace(/=/g,"").replace(/\+/g,"-").replace(/\//g,"_");
}
function fromb64url(str) {
  return atob(str.replace(/-/g,"+").replace(/_/g,"/"));
}

async function signJwt(payload, secret) {
  const header = b64url(JSON.stringify({ alg:"HS256", typ:"JWT" }));
  const body   = b64url(JSON.stringify(payload));
  const data   = `${header}.${body}`;
  const key    = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret),
    { name:"HMAC", hash:"SHA-256" }, false, ["sign"]
  );
  const sig    = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data));
  const sigB64 = b64url(String.fromCharCode(...new Uint8Array(sig)));
  return `${data}.${sigB64}`;
}

async function verifyJwt(token, secret) {
  try {
    const [header, body, sig] = token.split(".");
    if (!header || !body || !sig) return null;
    const data    = `${header}.${body}`;
    const key     = await crypto.subtle.importKey(
      "raw", new TextEncoder().encode(secret),
      { name:"HMAC", hash:"SHA-256" }, false, ["verify"]
    );
    const sigBytes = Uint8Array.from(fromb64url(sig), c => c.charCodeAt(0));
    const valid   = await crypto.subtle.verify("HMAC", key, sigBytes, new TextEncoder().encode(data));
    if (!valid) return null;
    const payload = JSON.parse(fromb64url(body));
    if (payload.exp && Date.now() > payload.exp) return null;
    return payload;
  } catch { return null; }
}

// ══════════════════════════════════════════════════════
//  HASH MOT DE PASSE (SHA-256)
// ══════════════════════════════════════════════════════

async function hashPassword(pwd) {
  const buf  = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(pwd));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,"0")).join("");
}

// ══════════════════════════════════════════════════════
//  LOGIN CONSEILLER (slug sans accents + suffixe agence)
//  Source unique de vérité partagée par /create et /sessions.
// ══════════════════════════════════════════════════════

function conseillerLoginFor(agenceId, prenom) {
  const shortName = agenceId.split("-")[0];
  const slug = (prenom || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return slug ? `${slug}.${shortName}` : null;
}

// Suffixe d'un login conseiller → agence réelle (même résolution que /login).
//  "marie.motte"   → "motte-picquet"
//  "joel.pernety"  → "pernety"
//  "robin.dauphine"→ "dauphine-lacassagne"
function agenceFromLogin(login) {
  if (!login || !login.includes(".")) return null;
  const suffix = login.slice(login.lastIndexOf(".") + 1);
  return IDENTIFIANTS[suffix] || (AGENCES_CONFIG[suffix] ? suffix : null);
}

// Pour un compte composite (lopez/bagot), déterminer la sous-agence réelle
// d'un conseiller. Pour un compte simple, renvoie agenceId tel quel.
//  1) hint explicite (body.agence) s'il appartient aux sous-agences
//  2) sinon : scan des listes conseillers:<sous-agence> par prénom
//  3) sinon : null → l'appelant renvoie une erreur 400 propre
async function resolveConseillerAgence(env, agenceId, cfg, prenom, hint) {
  const subs = Array.isArray(cfg.dpe_agences) ? cfg.dpe_agences : null;
  if (!subs) return agenceId;                       // compte simple
  if (hint && subs.includes(hint)) return hint;     // agence explicite
  const norm = s => (s || "").trim().toLowerCase();
  for (const ag of subs) {
    const raw = await env.DPE_KV.get(`conseillers:${ag}`);
    let liste;
    try { liste = raw ? JSON.parse(raw) : (AGENCES_CONFIG[ag]?.conseillers_defaut || []); }
    catch { liste = AGENCES_CONFIG[ag]?.conseillers_defaut || []; }
    if (Array.isArray(liste) && liste.some(c => norm(c) === norm(prenom))) return ag;
  }
  return null;
}

// ══════════════════════════════════════════════════════
//  HELPERS RÉPONSE
// ══════════════════════════════════════════════════════

const CORS = {
  "Access-Control-Allow-Origin":  "*",
  "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

const json = (data, status=200) =>
  new Response(JSON.stringify(data), { status, headers:{...CORS,"Content-Type":"application/json"} });

const err = (msg, status=400) => json({ error: msg }, status);
const ok  = (data)            => json(data, 200);

// ══════════════════════════════════════════════════════
//  EMAIL BREVO
// ══════════════════════════════════════════════════════

async function sendEmail(env, to, subject, html) {
  const resp = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "api-key": env.BREVO_API_KEY,
    },
    body: JSON.stringify({
      sender:  { name:"DPE Prospector", email:"alerte_dpe@outlook.com" },
      to:      [{ email: to }],
      subject,
      htmlContent: html,
    }),
  });
  return resp.ok;
}

function htmlReset(agenceNom, resetUrl) {
  return `<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;background:#f1f5f9;padding:32px;">
<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:40px;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
  <div style="font-size:28px;font-weight:700;margin-bottom:8px;">DPE Prospector</div>
  <div style="font-size:14px;color:#6b7280;margin-bottom:32px;">Réinitialisation du mot de passe</div>
  <p style="color:#374151;line-height:1.6;margin-bottom:24px;">
    Une demande de réinitialisation du mot de passe a été reçue pour l'agence <strong>${agenceNom}</strong>.
    Ce lien est valable <strong>1 heure</strong>.
  </p>
  <a href="${resetUrl}" style="display:inline-block;background:#1d4ed8;color:#fff;text-decoration:none;border-radius:8px;padding:14px 28px;font-weight:600;font-size:15px;">
    Réinitialiser le mot de passe →
  </a>
  <p style="margin-top:24px;font-size:12px;color:#9ca3af;">
    Si vous n'avez pas fait cette demande, ignorez cet email.
  </p>
</div>
</body></html>`;
}

// ══════════════════════════════════════════════════════
//  HANDLER PRINCIPAL
// ══════════════════════════════════════════════════════

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    try {
      return await handleRequest(request, env);
    } catch(e) {
      // Toujours renvoyer CORS même sur erreur 500
      return new Response(JSON.stringify({ error: e.message }), {
        status: 500,
        headers: { ...CORS, "Content-Type": "application/json" }
      });
    }
  }
};

async function handleRequest(request, env) {
    const url    = new URL(request.url);
    const path   = url.pathname.replace(/\/$/, "");
    const method = request.method;
    const JWT_SECRET = env.JWT_SECRET || "dev-secret-change-me";

    // ── GET /health ───────────────────────────────────
    if (path === "/health" && method === "GET") {
      return json({ ok:true, ts:new Date().toISOString(), agences: Object.keys(AGENCES_CONFIG) });
    }

    // ── POST /login ───────────────────────────────────
    if (path === "/login" && method === "POST") {
      let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
      const { agence: identifiant, password } = body;
      if (!identifiant || !password) return err("identifiant et password requis");

      const idLower = identifiant.toLowerCase().trim();

      // ── Résolution identifiant → agence ────────────────────────
      //  1) identifiant patron connu (court "dauphine" ou direct "lopez")
      //  2) login conseiller "prenom.shortname" → agence déduite du suffixe
      //  Erreur générique pour ne pas révéler quels identifiants existent.
      let agence = null;
      let isConseillerLogin = false;
      if (IDENTIFIANTS[idLower]) {
        agence = IDENTIFIANTS[idLower];
      } else if (AGENCES_CONFIG[idLower]) {
        agence = idLower;
      } else if (idLower.includes(".")) {
        const suffix   = idLower.slice(idLower.lastIndexOf(".") + 1);
        const resolved = IDENTIFIANTS[suffix] || (AGENCES_CONFIG[suffix] ? suffix : null);
        if (resolved && AGENCES_CONFIG[resolved]) { agence = resolved; isConseillerLogin = true; }
      }
      const cfg = agence ? AGENCES_CONFIG[agence] : null;
      if (!cfg) return err("Identifiant ou mot de passe incorrect", 401);

      // ── Rôle : 'conseiller' si role:<agence>:<login> === 'conseiller' ──
      const roleVal = await env.DPE_KV.get(`role:${agence}:${idLower}`);
      const role    = (roleVal === "conseiller") ? "conseiller" : "patron";

      // Un login "prenom.xxx" doit correspondre à une session conseiller existante
      if (isConseillerLogin && role !== "conseiller") {
        return err("Identifiant ou mot de passe incorrect", 401);
      }

      // ── Vérification mot de passe ──────────────────────────────
      //  conseiller : pwd:<login>  |  patron : pwd:<agence> (+ fallback secret)
      let valid = false;
      if (role === "conseiller") {
        const storedHash = await env.DPE_KV.get(`pwd:${idLower}`);
        if (storedHash) valid = (await hashPassword(password)) === storedHash;
      } else {
        const storedHash = await env.DPE_KV.get(`pwd:${agence}`);
        if (storedHash) {
          valid = (await hashPassword(password)) === storedHash;
        } else {
          // Premier démarrage : mot de passe depuis secrets Wrangler
          const secretKey = `PWD_${agence.toUpperCase().replace(/-/g,"_")}`;
          const plainPwd  = env[secretKey];
          if (!plainPwd) return err("Mot de passe non configuré", 500);
          if (password === plainPwd) {
            await env.DPE_KV.put(`pwd:${agence}`, await hashPassword(password));
            valid = true;
          }
        }
      }
      if (!valid) return err("Mot de passe incorrect", 401);

      // Agences accessibles : sous-agences si composite, sinon l'agence seule
      const agences = (Array.isArray(cfg.dpe_agences) && cfg.dpe_agences.length)
        ? cfg.dpe_agences
        : [agence];

      const token = await signJwt(
        { agence, agences, role, exp: Date.now() + TOKEN_TTL_MS },
        JWT_SECRET
      );

      // Charger conseillers depuis KV (ou défaut)
      const consRaw    = await env.DPE_KV.get(`conseillers:${agence}`);
      const conseillers = consRaw ? JSON.parse(consRaw) : cfg.conseillers_defaut;

      return json({
        token, agence, role, agences,
        config: {
          nom:          cfg.nom,
          ville:        cfg.ville,
          couleur:      cfg.couleur,
          dataJsonPath: cfg.dataJsonPath,
          zones:        cfg.zones,
          conseillers,
          sci_enabled:  cfg.sci_enabled || false,
          secteur_enabled: cfg.secteur_enabled || false,
          dpe_agences:  cfg.dpe_agences || null,   // null = agence simple, array = agence composite
          sci_agences:  cfg.sci_agences || null,
          role,
        },
      });
    }

    // ── POST /forgot-password ─────────────────────────
    if (path === "/forgot-password" && method === "POST") {
      let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
      const { agence } = body;
      const cfg = AGENCES_CONFIG[agence];
      if (!cfg) return err("Agence inconnue", 404);

      // Générer token de reset (UUID-like)
      const resetToken = crypto.randomUUID();
      await env.DPE_KV.put(
        `reset:${resetToken}`,
        JSON.stringify({ agence, exp: Date.now() + RESET_TTL_MS }),
        { expirationTtl: 3600 }
      );

      const origin   = request.headers.get("Origin") || "https://liquid69006.github.io";
      const resetUrl = `${origin}/dpe-prospector/?reset=${resetToken}`;

      await sendEmail(
        env,
        ADMIN_EMAIL,
        `🔑 Réinitialisation mot de passe — ${cfg.nom}`,
        htmlReset(cfg.nom, resetUrl)
      );

      // Réponse générique (sécurité : ne pas confirmer si l'agence existe)
      return json({ ok: true, message: "Email envoyé si l'agence est valide." });
    }

    // ── POST /reset-password ──────────────────────────
    if (path === "/reset-password" && method === "POST") {
      let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
      const { token, newPassword } = body;
      if (!token || !newPassword) return err("token et newPassword requis");
      if (newPassword.length < 8) return err("Le mot de passe doit faire au moins 8 caractères");

      const raw = await env.DPE_KV.get(`reset:${token}`);
      if (!raw) return err("Lien invalide ou expiré", 401);

      const { agence, exp } = JSON.parse(raw);
      if (Date.now() > exp) {
        await env.DPE_KV.delete(`reset:${token}`);
        return err("Lien expiré", 401);
      }

      await env.DPE_KV.put(`pwd:${agence}`, await hashPassword(newPassword));
      await env.DPE_KV.delete(`reset:${token}`);
      return json({ ok: true });
    }

    // ── Middleware JWT pour routes protégées ──────────
    async function requireAuth(agenceId) {
      const authHeader = request.headers.get("Authorization") || "";
      const token = authHeader.replace(/^Bearer\s+/i, "");
      if (!token) return [null, err("Token manquant", 401)];
      const payload = await verifyJwt(token, JWT_SECRET);
      if (!payload) return [null, err("Token invalide ou expiré", 401)];
      // Agences autorisées : l'agence du token, ses sous-agences (composite
      // lopez/bagot) et toute agence listée dans payload.agences.
      const composite = AGENCES_CONFIG[payload.agence];
      const allowed   = new Set([payload.agence]);
      if (Array.isArray(payload.agences))            payload.agences.forEach(a => allowed.add(a));
      if (composite && Array.isArray(composite.dpe_agences)) composite.dpe_agences.forEach(a => allowed.add(a));
      if (agenceId && !allowed.has(agenceId)) return [null, err("Accès refusé", 403)];
      return [payload, null];
    }

    // ── POST /change-password/:agence ─────────────────
    const chgPwdMatch = path.match(/^\/change-password\/([a-z0-9-]+)$/);
    if (chgPwdMatch && method === "POST") {
      const agenceId = chgPwdMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;

      let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
      const { oldPassword, newPassword } = body;
      if (!oldPassword || !newPassword) return err("oldPassword et newPassword requis");
      if (newPassword.length < 8) return err("Le mot de passe doit faire au moins 8 caractères");

      // Vérifier l'ancien mot de passe
      const storedHash = await env.DPE_KV.get(`pwd:${agenceId}`);
      let oldValid = false;
      if (storedHash) {
        oldValid = (await hashPassword(oldPassword)) === storedHash;
      } else {
        const secretKey = `PWD_${agenceId.toUpperCase().replace(/-/g,"_")}`;
        oldValid = oldPassword === env[secretKey];
      }
      if (!oldValid) return err("Ancien mot de passe incorrect", 401);

      await env.DPE_KV.put(`pwd:${agenceId}`, await hashPassword(newPassword));
      return json({ ok: true });
    }

    // ── /assignments/:agence ──────────────────────────
    const assignMatch = path.match(/^\/assignments\/([a-z0-9-]+)$/);
    if (assignMatch) {
      const agenceId = assignMatch[1];
      const [payload, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;

      // Lopez agrège les assignments de motte-picquet + pernety
      const isLopez = payload.agence === "lopez";
      const lopezAgences = AGENCES_CONFIG["lopez"].dpe_agences;

      if (method === "GET") {
        if (isLopez) {
          // Fusionner les assignments des deux agences
          let merged = {};
          for (const ag of lopezAgences) {
            const raw = await env.DPE_KV.get(`assignments:${ag}`);
            if (raw) Object.assign(merged, JSON.parse(raw));
          }
          return json({ assignments: merged });
        }
        const raw = await env.DPE_KV.get(`assignments:${agenceId}`);
        return json({ assignments: raw ? JSON.parse(raw) : {} });
      }

      if (method === "POST") {
        let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
        if (typeof body.assignments !== "object") return err("assignments doit être un objet");

        if (isLopez) {
          // Répartir les assignments dans les bonnes clés KV selon la zone du DPE
          // Le dashboard envoie tous les assignments fusionnés — on les re-dispatche
          // en lisant les assignments existants de chaque agence pour savoir à qui appartient chaque DPE
          const motteCurrent = JSON.parse(await env.DPE_KV.get(`assignments:motte-picquet`) || "{}");
          const pernetyCurrent = JSON.parse(await env.DPE_KV.get(`assignments:pernety`) || "{}");
          const motteNew = {};
          const pernetyNew = {};

          for (const [dpeId, val] of Object.entries(body.assignments)) {
            // Si la clé existait déjà dans motte → reste dans motte
            // Si la clé existait déjà dans pernety → reste dans pernety
            // Si nouvelle clé → on utilise la zone indiquée dans val.zone
            if (dpeId in motteCurrent || val?.zone === "La Motte Picquet") {
              motteNew[dpeId] = val;
            } else {
              pernetyNew[dpeId] = val;
            }
          }
          await env.DPE_KV.put(`assignments:motte-picquet`, JSON.stringify(motteNew));
          await env.DPE_KV.put(`assignments:pernety`, JSON.stringify(pernetyNew));
          return json({ ok: true, count: Object.keys(body.assignments).length });
        }

        await env.DPE_KV.put(`assignments:${agenceId}`, JSON.stringify(body.assignments));
        return json({ ok: true, count: Object.keys(body.assignments).length });
      }
      return err("Méthode non supportée", 405);
    }

    // ── /sci-assignments/:agence ──────────────────────
    const sciAssignMatch = path.match(/^\/sci-assignments\/([a-z0-9-]+)$/);
    if (sciAssignMatch) {
      const agenceId = sciAssignMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;

      if (method === "GET") {
        const raw = await env.DPE_KV.get(`sci-assignments:${agenceId}`);
        return json({ assignments: raw ? JSON.parse(raw) : {} });
      }
      if (method === "POST") {
        let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
        if (typeof body.assignments !== "object") return err("assignments doit être un objet");
        await env.DPE_KV.put(`sci-assignments:${agenceId}`, JSON.stringify(body.assignments));
        return json({ ok: true, count: Object.keys(body.assignments).length });
      }
      return err("Méthode non supportée", 405);
    }

    // ── /secteur-assignments/:agence ── ilots + qualifications ────────
    const secteurAssignMatch = path.match(/^\/secteur-assignments\/([a-z0-9-]+)$/);
    if (secteurAssignMatch) {
      const agenceId = secteurAssignMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;

      if (method === "GET") {
        const raw = await env.DPE_KV.get(`secteur_assignments:${agenceId}`);
        let parsed = raw ? JSON.parse(raw) : {};
        // Retro-compat : ancien format = objet d'assignations a plat.
        // Nouveau format = { assignments:{...}, fusions:{...} }.
        const isWrapped = parsed && (parsed.assignments !== undefined
          || parsed.fusions !== undefined || parsed.noms !== undefined);
        const assignments = isWrapped ? (parsed.assignments || {}) : parsed;
        const fusions = isWrapped ? (parsed.fusions || {}) : {};
        const noms = isWrapped ? (parsed.noms || {}) : {};
        return json({ assignments, fusions, noms });
      }
      if (method === "POST") {
        let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
        if (typeof body.assignments !== "object" || body.assignments === null)
          return err("assignments doit être un objet");
        const fusions = (body.fusions && typeof body.fusions === "object") ? body.fusions : {};
        const noms = (body.noms && typeof body.noms === "object") ? body.noms : {};
        await env.DPE_KV.put(`secteur_assignments:${agenceId}`,
          JSON.stringify({ assignments: body.assignments, fusions, noms }));
        return json({ ok: true, assignments: Object.keys(body.assignments).length,
                      fusions: Object.keys(fusions).length, noms: Object.keys(noms).length });
      }
      return err("Méthode non supportée", 405);
    }

    // ── /secteur-repartition/:agence ── génération de secteurs conseillers ─
    // KV : secteur_repartition:{agenceId} -> { adresse_agence, agence_lat,
    // agence_lng, conseillers:[{id,nom,couleur}], repartition:{ilotId:{
    // conseillerId, locked}} }. GET renvoie {} si absent (frontend traite
    // comme état vierge). POST écrase tout. PATCH /ilot met à jour 1 entrée.
    const secteurRepartMatch = path.match(/^\/secteur-repartition\/([a-z0-9-]+)$/);
    if (secteurRepartMatch) {
      const agenceId = secteurRepartMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;

      if (method === "GET") {
        const raw = await env.DPE_KV.get(`secteur_repartition:${agenceId}`);
        return json(raw ? JSON.parse(raw) : {});
      }
      if (method === "POST") {
        let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
        if (typeof body !== "object" || body === null) return err("body doit être un objet");
        const payload = {
          adresse_agence: typeof body.adresse_agence === "string" ? body.adresse_agence : "",
          agence_lat: typeof body.agence_lat === "number" ? body.agence_lat : null,
          agence_lng: typeof body.agence_lng === "number" ? body.agence_lng : null,
          conseillers: Array.isArray(body.conseillers) ? body.conseillers : [],
          repartition: (body.repartition && typeof body.repartition === "object") ? body.repartition : {},
          updated_at: new Date().toISOString(),
        };
        await env.DPE_KV.put(`secteur_repartition:${agenceId}`, JSON.stringify(payload));
        return json({ ok: true, ilots: Object.keys(payload.repartition).length,
                      conseillers: payload.conseillers.length });
      }
      // PATCH partiel : merge des champs envoyes. Sert au front pour
      // persister l'adresse de l'agence des le geocode (sans toucher
      // a conseillers/repartition qui restent gouvernes par le Save).
      if (method === "PATCH") {
        let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
        if (typeof body !== "object" || body === null) return err("body doit être un objet");
        const raw = await env.DPE_KV.get(`secteur_repartition:${agenceId}`);
        const obj = raw ? JSON.parse(raw) : {};
        if (typeof body.adresse_agence === "string") obj.adresse_agence = body.adresse_agence;
        if (typeof body.agence_lat === "number")     obj.agence_lat     = body.agence_lat;
        if (typeof body.agence_lng === "number")     obj.agence_lng     = body.agence_lng;
        if (Array.isArray(body.conseillers))         obj.conseillers    = body.conseillers;
        if (body.repartition && typeof body.repartition === "object") obj.repartition = body.repartition;
        obj.updated_at = new Date().toISOString();
        await env.DPE_KV.put(`secteur_repartition:${agenceId}`, JSON.stringify(obj));
        return json({ ok: true, merged: Object.keys(body).length });
      }
      return err("Méthode non supportée", 405);
    }

    // ── /secteur-attribution/:agence ── attribution secteurs -> conseillers ─
    // KV : secteur_attribution:{agenceId} -> { conseillers:[{id,nom}],
    //   attribution:{secId: conseillerId|null}, updated_at }.
    // GET renvoie {} si absent. POST ecrase tout. Pattern identique a
    // /secteur-repartition. Pour l'etape 2 du wizard "Reattribuer secteurs".
    const secteurAttribMatch = path.match(/^\/secteur-attribution\/([a-z0-9-]+)$/);
    if (secteurAttribMatch) {
      const agenceId = secteurAttribMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;
      if (method === "GET") {
        const raw = await env.DPE_KV.get(`secteur_attribution:${agenceId}`);
        return json(raw ? JSON.parse(raw) : {});
      }
      if (method === "POST") {
        let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
        if (typeof body !== "object" || body === null) return err("body doit être un objet");
        const payload = {
          conseillers: Array.isArray(body.conseillers) ? body.conseillers : [],
          attribution: (body.attribution && typeof body.attribution === "object") ? body.attribution : {},
          updated_at: new Date().toISOString(),
        };
        await env.DPE_KV.put(`secteur_attribution:${agenceId}`, JSON.stringify(payload));
        return json({ ok: true, attribution: Object.keys(payload.attribution).length,
                      conseillers: payload.conseillers.length });
      }
      return err("Méthode non supportée", 405);
    }

    // ── PATCH /secteur-repartition/:agence/ilot ── update partiel 1 îlot ──
    const secteurRepartIlotMatch = path.match(/^\/secteur-repartition\/([a-z0-9-]+)\/ilot$/);
    if (secteurRepartIlotMatch && method === "PATCH") {
      const agenceId = secteurRepartIlotMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;
      let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
      const ilotId = body.ilotId != null ? String(body.ilotId) : "";
      if (!ilotId) return err("ilotId requis");

      const raw = await env.DPE_KV.get(`secteur_repartition:${agenceId}`);
      const obj = raw ? JSON.parse(raw) : {};
      if (!obj.repartition || typeof obj.repartition !== "object") obj.repartition = {};

      const prev = obj.repartition[ilotId] || {};
      obj.repartition[ilotId] = {
        conseillerId: body.conseillerId !== undefined ? body.conseillerId : prev.conseillerId,
        locked: body.locked !== undefined ? !!body.locked : !!prev.locked,
      };
      obj.updated_at = new Date().toISOString();
      await env.DPE_KV.put(`secteur_repartition:${agenceId}`, JSON.stringify(obj));
      return json({ ok: true, ilot: obj.repartition[ilotId] });
    }

    // ── /map-a0/* ── generation de carte A0 via GitHub Actions ───────
    //  POST /map-a0/generate/:agence  -> declenche workflow
    //  GET  /map-a0/status/:agence    -> dernier run du workflow
    //  GET  /map-a0/artifact/:runId   -> resout l'archive_download_url
    //                                     en signed URL S3 directe, que
    //                                     le front passe a window.open()
    //                                     (pas d'auth necessaire, l'URL
    //                                     est signee + expire en ~1 min).
    //  Auth : requireAuth(agenceId) sauf /artifact qui accepte aussi
    //  ?token=... pour permettre window.open() cote front.
    //  Necessite env.GH_PAT (Cloudflare secret).
    // Auth GitHub : "token <PAT>" pour les PAT classiques (compatible avec
    // tous les endpoints REST + artifacts/zip). "Bearer" cassait le download
    // d'artifact (401 sur archive_download_url).
    const ghHeaders = () => ({
      "Authorization": `token ${env.GH_PAT}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "dpe-prospector-api",
    });
    const GH_REPO = "liquid69006/DPE-PROSPECTOR";

    const mapA0GenMatch = path.match(/^\/map-a0\/generate\/([a-z0-9-]+)$/);
    if (mapA0GenMatch && method === "POST") {
      const agenceId = mapA0GenMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;
      if (!env.GH_PAT) return err("GH_PAT non configuré côté Worker", 500);
      let body; try { body = await request.json(); } catch { return err("JSON invalide"); }

      const ghResp = await fetch(
        `https://api.github.com/repos/${GH_REPO}/actions/workflows/generate-map-a0.yml/dispatches`,
        {
          method: "POST",
          headers: { ...ghHeaders(), "Content-Type": "application/json" },
          body: JSON.stringify({
            ref: "main",
            inputs: {
              repartition_json: JSON.stringify(body),
              agence_id: agenceId,
            },
          }),
        }
      );
      if (!ghResp.ok) {
        const txt = await ghResp.text();
        return err(`Échec GitHub Actions (${ghResp.status}) : ${txt}`, 502);
      }
      return json({ ok: true, message: "Workflow déclenché" });
    }

    const mapA0StatusMatch = path.match(/^\/map-a0\/status\/([a-z0-9-]+)$/);
    if (mapA0StatusMatch && method === "GET") {
      const agenceId = mapA0StatusMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;
      if (!env.GH_PAT) return err("GH_PAT non configuré côté Worker", 500);

      const ghResp = await fetch(
        `https://api.github.com/repos/${GH_REPO}/actions/workflows/generate-map-a0.yml/runs?per_page=1`,
        { headers: ghHeaders() }
      );
      if (!ghResp.ok) {
        const txt = await ghResp.text();
        return err(`Échec GitHub Actions (${ghResp.status}) : ${txt}`, 502);
      }
      const data = await ghResp.json();
      const run = (data.workflow_runs || [])[0];
      if (!run) return json({ status: "unknown", conclusion: null, run_id: null, artifact_url: null });
      return json({
        status: run.status,                   // queued | in_progress | completed
        conclusion: run.conclusion,           // success | failure | null
        run_id: run.id,
        artifact_url: null,                   // a recup via /artifact/:runId
      });
    }

    const mapA0ArtifactMatch = path.match(/^\/map-a0\/artifact\/(\d+)$/);
    if (mapA0ArtifactMatch && method === "GET") {
      // Auth : Authorization header OU ?token=... (UX window.open).
      const urlObj = new URL(request.url);
      const tokenQ = urlObj.searchParams.get("token");
      const tokenH = (request.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
      const token = tokenQ || tokenH;
      if (!token) return err("Token manquant", 401);
      const payload = await verifyJwt(token, JWT_SECRET);
      if (!payload) return err("Token invalide ou expiré", 401);
      if (!env.GH_PAT) return err("GH_PAT non configuré côté Worker", 500);

      const runId = mapA0ArtifactMatch[1];
      // 1) Liste les artifacts du run (on n'en uploade qu'un seul).
      const ghResp = await fetch(
        `https://api.github.com/repos/${GH_REPO}/actions/runs/${runId}/artifacts`,
        { headers: ghHeaders() }
      );
      if (!ghResp.ok) {
        const txt = await ghResp.text();
        return err(`Échec GitHub Actions (${ghResp.status}) : ${txt}`, 502);
      }
      const data = await ghResp.json();
      const art = (data.artifacts || [])[0];
      if (!art) return json({ download_url: null, message: "Aucun artifact" });

      // 2) Resout archive_download_url -> signed URL S3 (redirect manual).
      //    La signed URL n'accepte PAS Authorization (S3 rejette), donc on
      //    la retourne directement au front qui la passe a window.open().
      //    Elle expire en ~1 min, ce qui est suffisant pour un download
      //    declenche immediatement par le navigateur.
      const redirResp = await fetch(art.archive_download_url, {
        headers: ghHeaders(),
        redirect: "manual",
      });
      const signedUrl = redirResp.headers.get("Location");
      if (!signedUrl) {
        const txt = await redirResp.text().catch(() => "");
        return err(
          `Pas de Location header (status ${redirResp.status}) : ${txt.slice(0, 200)}`,
          502
        );
      }

      return json({
        download_url: signedUrl,
        name: art.name,
        size: art.size_in_bytes,
      });
    }

    // ── POST /conseillers/:agence/create ── créer une session conseiller ──
    const consCreateMatch = path.match(/^\/conseillers\/([a-z0-9-]+)\/create$/);
    if (consCreateMatch && method === "POST") {
      const agenceId = consCreateMatch[1];
      const [payload, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;
      if (payload.role === "conseiller") return err("Réservé au patron", 403);

      const cfg = AGENCES_CONFIG[agenceId];
      if (!cfg) return err("Agence inconnue", 404);

      let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
      const prenom = (body.prenom || "").trim();
      if (!prenom) return err("prenom requis", 400);

      // Compte composite (lopez/bagot) : le conseiller appartient à une
      // sous-agence réelle (motte-picquet/pernety, houlgate/villers), JAMAIS
      // au compte composite lui-même. C'est cette agence qui forme le login.
      const realAgence = await resolveConseillerAgence(env, agenceId, cfg, prenom, body.agence);
      if (!realAgence) {
        return err("Agence du conseiller introuvable — ajoutez-le à la liste avant de créer la session", 400);
      }

      const login = conseillerLoginFor(realAgence, prenom);
      if (!login) return err("prenom invalide", 400);

      // Mot de passe : 8 caractères alphanumériques (alphabet sans ambiguïté)
      const ALPHA = "abcdefghijkmnpqrstuvwxyz23456789";
      const rnd   = crypto.getRandomValues(new Uint8Array(8));
      let password = "";
      for (let i = 0; i < 8; i++) password += ALPHA[rnd[i] % ALPHA.length];

      try {
        await env.DPE_KV.put(`pwd:${login}`, await hashPassword(password));
        await env.DPE_KV.put(`role:${realAgence}:${login}`, "conseiller");
      } catch (e) {
        return err("Erreur création session (KV) : " + e.message, 500);
      }

      // ── Notification e-mail (login + password) ───────────────────────
      //  Destinataire = agence RÉELLE du conseiller (realAgence), JAMAIS la
      //  session connectée — important pour lopez (→ motte-picquet/pernety).
      //  Fiable : tout échec Brevo est loggé, jamais ignoré en silence ;
      //  les identifiants restent renvoyés en JSON (pas de perte d'accès).
      const realCfg  = AGENCES_CONFIG[realAgence] || cfg;
      const notifyTo = CONSEILLER_NOTIFY_EMAIL[realAgence] || CONSEILLER_NOTIFY_FALLBACK;
      const htmlMail = `<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;background:#f1f5f9;padding:32px;">
<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:40px;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
  <div style="font-size:24px;font-weight:700;margin-bottom:16px;">Nouveau conseiller — ${prenom}</div>
  <p style="color:#374151;line-height:1.6;">Une session a été créée pour <strong>${prenom}</strong> (${realCfg.nom}).</p>
  <p style="color:#374151;line-height:1.6;">
    Identifiant : <strong>${login}</strong><br>
    Mot de passe : <strong>${password}</strong>
  </p>
  <p style="font-size:13px;color:#6b7280;line-height:1.6;">
    Communiquez ces accès au conseiller. Il est recommandé de changer le mot de passe
    après la première connexion.
  </p>
</div></body></html>`;

      let emailSent = false;
      try {
        emailSent = await sendEmail(env, notifyTo, `Nouveau conseiller — ${prenom}`, htmlMail);
        if (!emailSent) {
          console.error(`[create] Échec Brevo identifiants conseiller ${login} → ${notifyTo} (agence ${realAgence})`);
        }
      } catch (e) {
        console.error(`[create] Exception Brevo identifiants conseiller ${login} → ${notifyTo} : ${e.message}`);
      }

      return ok({ ok: true, login, password, agence: realAgence, emailSent, notifyTo });
    }

    // ── GET /conseillers/:agence/sessions ── état des sessions conseillers ──
    const consSessMatch = path.match(/^\/conseillers\/([a-z0-9-]+)\/sessions$/);
    if (consSessMatch && method === "GET") {
      const agenceId = consSessMatch[1];
      const [payload, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;
      if (payload.role === "conseiller") return err("Réservé au patron", 403);

      const cfg = AGENCES_CONFIG[agenceId];
      if (!cfg) return err("Agence inconnue", 404);

      // Liste {nom, agence} des conseillers. Pour un compte composite, chaque
      // conseiller porte sa sous-agence réelle (motte-picquet/pernety…) ;
      // c'est elle qui forme le login, pas le compte composite.
      const subs = Array.isArray(cfg.dpe_agences) ? cfg.dpe_agences : null;
      const entries = [];
      if (subs) {
        const seen = new Set();
        for (const ag of subs) {
          const raw = await env.DPE_KV.get(`conseillers:${ag}`);
          let liste;
          try { liste = raw ? JSON.parse(raw) : (AGENCES_CONFIG[ag]?.conseillers_defaut || []); }
          catch { liste = AGENCES_CONFIG[ag]?.conseillers_defaut || []; }
          (Array.isArray(liste) ? liste : [])
            .filter(c => c && c !== "À attribuer")
            .forEach(c => { if (!seen.has(c)) { seen.add(c); entries.push({ nom: c, agence: ag }); } });
        }
      } else {
        const raw = await env.DPE_KV.get(`conseillers:${agenceId}`);
        let liste;
        try { liste = raw ? JSON.parse(raw) : (cfg.conseillers_defaut || []); }
        catch { liste = cfg.conseillers_defaut || []; }
        (Array.isArray(liste) ? liste : [])
          .filter(c => c && c !== "À attribuer")
          .forEach(c => entries.push({ nom: c, agence: agenceId }));
      }

      const sessions = {};
      for (const { nom, agence } of entries) {
        const login = conseillerLoginFor(agence, nom);
        if (!login) continue;
        const v = await env.DPE_KV.get(`role:${agence}:${login}`);
        sessions[login] = v === "conseiller";
      }
      return ok({ sessions });
    }

    // ── DELETE /conseillers/:agence/:login ── supprimer une session ──
    const consDelMatch = path.match(/^\/conseillers\/([a-z0-9-]+)\/([a-z0-9.-]+)$/);
    if (consDelMatch && method === "DELETE") {
      const agenceId = consDelMatch[1];
      const login    = consDelMatch[2];
      const [payload, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;
      if (payload.role === "conseiller") return err("Réservé au patron", 403);

      const cfg = AGENCES_CONFIG[agenceId];
      if (!cfg) return err("Agence inconnue", 404);

      // L'agence réelle du conseiller est portée par le suffixe du login
      // (ex. "marie.motte" → motte-picquet). Pour un compte composite, ce
      // n'est PAS agenceId (= "lopez") : viser la bonne clé role:.
      const roleAgence = agenceFromLogin(login) || agenceId;
      const realCfg    = AGENCES_CONFIG[roleAgence] || cfg;

      try {
        await env.DPE_KV.delete(`pwd:${login}`);
        await env.DPE_KV.delete(`role:${roleAgence}:${login}`);
        // Compat : purge aussi une éventuelle ancienne clé mal formée
        // (role:lopez:nom.lopez créée avant le correctif).
        if (roleAgence !== agenceId) {
          await env.DPE_KV.delete(`role:${agenceId}:${login}`);
        }
      } catch (e) {
        return err("Erreur suppression session (KV) : " + e.message, 500);
      }

      // Email best-effort : son échec ne doit pas faire échouer la suppression.
      try {
        const htmlMail = `<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;background:#f1f5f9;padding:32px;">
<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:40px;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
  <div style="font-size:24px;font-weight:700;margin-bottom:16px;">Session supprimée — ${login}</div>
  <p style="color:#374151;line-height:1.6;">
    La session conseiller <strong>${login}</strong> (${realCfg.nom}) a été supprimée.
    Cet identifiant ne permet plus de se connecter.
  </p>
</div></body></html>`;
        await sendEmail(env, realCfg.email || cfg.email, `Session supprimée — ${login}`, htmlMail);
      } catch (e) { /* email non critique */ }

      return ok({ ok: true });
    }

    // ── /conseillers/:agence ──────────────────────────
    const consMatch = path.match(/^\/conseillers\/([a-z0-9-]+)$/);
    if (consMatch) {
      const agenceId = consMatch[1];
      const [payload, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;
      const cfg = AGENCES_CONFIG[agenceId];
      const isLopez = payload.agence === "lopez";
      const lopezAgences = AGENCES_CONFIG["lopez"].dpe_agences;
      const isBagot = payload.agence === "bagot";
      const bagotAgences = AGENCES_CONFIG["bagot"].dpe_agences;

      if (method === "GET") {
        if (isLopez) {
          let merged = [{ nom: "À attribuer", agence: null }];
          for (const ag of lopezAgences) {
            const raw = await env.DPE_KV.get(`conseillers:${ag}`);
            const liste = raw ? JSON.parse(raw) : (AGENCES_CONFIG[ag]?.conseillers_defaut || []);
            liste.filter(c => c && c !== "À attribuer").forEach(c => {
              if (!merged.find(m => m.nom === c)) merged.push({ nom: c, agence: ag });
            });
          }
          return json({ conseillers: merged.map(m => m.nom), conseillers_detail: merged });
        }
        if (isBagot) {
          let merged = [{ nom: "À attribuer", agence: null }];
          for (const ag of bagotAgences) {
            const raw = await env.DPE_KV.get(`conseillers:${ag}`);
            const liste = raw ? JSON.parse(raw) : (AGENCES_CONFIG[ag]?.conseillers_defaut || []);
            liste.filter(c => c && c !== "À attribuer").forEach(c => {
              if (!merged.find(m => m.nom === c)) merged.push({ nom: c, agence: ag });
            });
          }
          return json({ conseillers: merged.map(m => m.nom), conseillers_detail: merged });
        }
        const raw = await env.DPE_KV.get(`conseillers:${agenceId}`);
        const conseillers = raw ? JSON.parse(raw) : (cfg?.conseillers_defaut || ["À attribuer"]);
        return json({ conseillers });
      }

      if (method === "POST") {
        let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
        if (!Array.isArray(body.conseillers)) return err("conseillers doit être un tableau");

        if (isLopez) {
          if (!Array.isArray(body.conseillers_detail)) return err("conseillers_detail requis pour lopez", 400);
          const motteList = ["À attribuer"];
          const pernetyList = ["À attribuer"];
          for (const item of body.conseillers_detail) {
            if (!item.nom || item.nom === "À attribuer") continue;
            if (item.agence === "motte-picquet") motteList.push(item.nom);
            else if (item.agence === "pernety") pernetyList.push(item.nom);
          }
          await env.DPE_KV.put(`conseillers:motte-picquet`, JSON.stringify(motteList));
          await env.DPE_KV.put(`conseillers:pernety`, JSON.stringify(pernetyList));
          return json({ ok: true, conseillers: [...motteList, ...pernetyList.filter(c => c !== "À attribuer")] });
        }

        if (isBagot) {
          if (!Array.isArray(body.conseillers_detail)) return err("conseillers_detail requis pour bagot", 400);
          const houlgateList = ["À attribuer"];
          const villersList = ["À attribuer"];
          for (const item of body.conseillers_detail) {
            if (!item.nom || item.nom === "À attribuer") continue;
            if (item.agence === "houlgate") houlgateList.push(item.nom);
            else if (item.agence === "villers") villersList.push(item.nom);
          }
          await env.DPE_KV.put(`conseillers:houlgate`, JSON.stringify(houlgateList));
          await env.DPE_KV.put(`conseillers:villers`, JSON.stringify(villersList));
          return json({ ok: true, conseillers: [...houlgateList, ...villersList.filter(c => c !== "À attribuer")] });
        }

        const list = ["À attribuer", ...body.conseillers.filter(c => c && c !== "À attribuer")];
        await env.DPE_KV.put(`conseillers:${agenceId}`, JSON.stringify(list));
        return json({ ok: true, conseillers: list });
      }
      return err("Méthode non supportée", 405);
    }
    if (consMatch) {
      const agenceId = consMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;
      const cfg = AGENCES_CONFIG[agenceId];

      if (method === "GET") {
        const raw = await env.DPE_KV.get(`conseillers:${agenceId}`);
        const conseillers = raw ? JSON.parse(raw) : (cfg?.conseillers_defaut || ["À attribuer"]);
        return json({ conseillers });
      }
      if (method === "POST") {
        let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
        if (!Array.isArray(body.conseillers)) return err("conseillers doit être un tableau");
        // Toujours garder "À attribuer" en premier
        const list = ["À attribuer", ...body.conseillers.filter(c => c && c !== "À attribuer")];
        await env.DPE_KV.put(`conseillers:${agenceId}`, JSON.stringify(list));
        return json({ ok: true, conseillers: list });
      }
      return err("Méthode non supportée", 405);
    }

    // ── /msb-key/:agence ── clé API MySendingBox par agence ──────────────
    const msbKeyMatch = path.match(/^\/msb-key\/([a-z0-9-]+)$/);
    if (msbKeyMatch) {
      const agenceId = msbKeyMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;

      if (method === 'GET') {
        const key = await env.DPE_KV.get(`msb_key:${agenceId}`);
        // On retourne juste si une clé existe, pas la clé elle-même
        return ok({ configured: !!key, preview: key ? key.slice(0,6) + '...' : null });
      }

      if (method === 'POST') {
        const body = await request.json();
        const { api_key } = body;
        if (!api_key || api_key.trim().length < 10) return err('Clé API invalide', 400);
        await env.DPE_KV.put(`msb_key:${agenceId}`, api_key.trim());
        return ok({ saved: true });
      }

      if (method === 'DELETE') {
        await env.DPE_KV.delete(`msb_key:${agenceId}`);
        return ok({ deleted: true });
      }
    }

        // ── /msb-send/:agence ── envoi courrier via MySendingBox ──────────────
    const msbSendMatch = path.match(/^\/msb-send\/([a-z0-9-]+)$/);
    if (msbSendMatch && method === 'POST') {
      const agenceId = msbSendMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;

      // Récupérer la clé API stockée
      const msbKey = await env.DPE_KV.get(`msb_key:${agenceId}`);
      if (!msbKey) return err('Clé API MySendingBox non configurée', 400);

      const body = await request.json();
      const { html, docx_base64, to, postage_type, color, both_sides, siren } = body;
      if ((!html && !docx_base64) || !to) return err('Paramètres manquants', 400);

      // Récupérer l'expéditeur stocké
      const fromRaw = await env.DPE_KV.get(`msb_from:${agenceId}`);
      const from = fromRaw ? JSON.parse(fromRaw) : {
        name: 'CENTURY 21 Dauphiné-Lacassagne',
        address_line1: '224 rue Paul Bert',
        zip_code: '69003',
        city: 'Lyon',
        country: 'France',
      };

      try {
        const toMSB = {
          name:               (to.name        || '').slice(0, 45),
          address_line1:      (to.address_line1 || '').slice(0, 45),
          address_city:       (to.city         || '').slice(0, 35),
          address_postalcode: (to.zip_code     || '').slice(0, 10),
          address_country:    'France',
        };
        const fromMSB = {
          name:               (from.name        || '').slice(0, 45),
          address_line1:      (from.address_line1 || '').slice(0, 45),
          address_city:       (from.city         || '').slice(0, 35),
          address_postalcode: (from.zip_code     || '').slice(0, 10),
          address_country:    'France',
        };
        const colorVal   = color || 'color';
        const postageVal = postage_type || 'ecopli';
        const bothVal    = (both_sides === true || both_sides === 'true');

        // [DEBUG] Trace clef MSB avant la requete HTTP (clef + Authorization
        // masquees au milieu). Visible via `wrangler tail` ou Cloudflare
        // Workers Logs. Cle: 5 premiers + 4 derniers caracteres. Header
        // Authorization: 10 premiers + 6 derniers caracteres.
        const _keyLen     = msbKey ? msbKey.length : 0;
        const _keyMasked  = (_keyLen > 9)
          ? msbKey.slice(0, 5) + '...' + msbKey.slice(-4)
          : '(short_key)';
        const _authHeader = 'Basic ' + btoa(msbKey + ':');
        const _authLen    = _authHeader.length;
        const _authMasked = (_authLen > 16)
          ? _authHeader.slice(0, 10) + '***' + _authHeader.slice(-6)
          : _authHeader;
        console.log('[MSB] agence=' + agenceId
          + ' key=' + _keyMasked + ' keyLen=' + _keyLen
          + ' auth=' + _authMasked + ' authLen=' + _authLen);

        let msbResp;
        if (docx_base64) {
          // MSB exige multipart/form-data quand source_file_type = 'file'
          const bin   = atob(docx_base64);
          const bytes = new Uint8Array(bin.length);
          for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
          const blob  = new Blob([bytes], {
            type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          });

          const fd = new FormData();
          fd.append('source_file', blob, 'courrier.docx');
          fd.append('source_file_type', 'file');
          fd.append('to[name]',               toMSB.name);
          fd.append('to[address_line1]',      toMSB.address_line1);
          fd.append('to[address_postalcode]', toMSB.address_postalcode);
          fd.append('to[address_city]',       toMSB.address_city);
          fd.append('to[address_country]',    toMSB.address_country);
          fd.append('from[name]',               fromMSB.name);
          fd.append('from[address_line1]',      fromMSB.address_line1);
          fd.append('from[address_postalcode]', fromMSB.address_postalcode);
          fd.append('from[address_city]',       fromMSB.address_city);
          fd.append('from[address_country]',    fromMSB.address_country);
          fd.append('color', colorVal);
          fd.append('postage_type', postageVal);
          fd.append('both_sides', String(bothVal));
          fd.append('address_placement', 'insert_blank_page');

          // NE PAS définir Content-Type : fetch ajoute la boundary multipart
          msbResp = await fetch('https://api.mysendingbox.fr/letters', {
            method: 'POST',
            headers: { 'Authorization': 'Basic ' + btoa(msbKey + ':') },
            body: fd,
          });
        } else {
          msbResp = await fetch('https://api.mysendingbox.fr/letters', {
            method: 'POST',
            headers: {
              'Authorization': 'Basic ' + btoa(msbKey + ':'),
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              to:   toMSB,
              from: fromMSB,
              source_file: html,
              source_file_type: 'html',
              color: colorVal,
              postage_type: postageVal,
              both_sides: bothVal,
              address_placement: 'insert_blank_page',
            }),
          });
        }
        const msbData = await msbResp.json();
        if (!msbResp.ok) return err(`MSB ${msbResp.status}: ${JSON.stringify(msbData)}`, 502);

        // Tracer uniquement les envois réels (clé live), jamais les tests.
        // MSB renvoie mode: "live"|"test" (string), pas live_mode: bool.
        if (msbData.mode === 'live' && siren) {
          await env.DPE_KV.put(`dernierCourrier:${agenceId}:${siren}`, new Date().toISOString());
        }

        return ok({ id: msbData._id, status: msbData.status?.name, live_mode: msbData.mode === 'live', file_for_corus: msbData.file_for_corus, file: msbData.file });
      } catch(e) {
        return err('Erreur réseau MySendingBox', 502);
      }
    }

    // ── GET /dernierCourrier/:agence ── date du dernier courrier réel par SCI ──
    const dcMatch = path.match(/^\/dernierCourrier\/([a-z0-9-]+)$/);
    if (dcMatch && method === 'GET') {
      const agenceId = dcMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;

      const prefix = `dernierCourrier:${agenceId}:`;
      const dates  = {};
      let cursor;
      do {
        const listed = await env.DPE_KV.list({ prefix, cursor });
        for (const k of listed.keys) {
          const siren = k.name.slice(prefix.length);
          const v = await env.DPE_KV.get(k.name);
          if (v) dates[siren] = v;
        }
        cursor = listed.list_complete ? null : listed.cursor;
      } while (cursor);

      return ok({ dates });
    }

    // ── GET /msb-history/:agence ── diagnostic temporaire ─────────────────
    // Liste les courriers MSB envoyés (route GET https://api.mysendingbox.fr/letters).
    // Retourne le JSON MSB brut pour identifier le nom exact du champ mode/live.
    // Params: ?limit=N (defaut 25, cap 100) &offset=N (defaut 0).
    const mhMatch = path.match(/^\/msb-history\/([a-z0-9-]+)$/);
    if (mhMatch && method === 'GET') {
      const agenceId = mhMatch[1];
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;

      const msbKey = await env.DPE_KV.get(`msb_key:${agenceId}`);
      if (!msbKey) return err('Cle API MySendingBox non configuree', 400);

      const u = new URL(request.url);
      let limit  = parseInt(u.searchParams.get('limit')  || '25', 10);
      let offset = parseInt(u.searchParams.get('offset') || '0',  10);
      if (!Number.isFinite(limit)  || limit  < 1) limit  = 25;
      if (limit > 100) limit = 100;
      if (!Number.isFinite(offset) || offset < 0) offset = 0;

      try {
        const msbResp = await fetch(
          `https://api.mysendingbox.fr/letters?limit=${limit}&offset=${offset}`,
          { headers: { 'Authorization': 'Basic ' + btoa(msbKey + ':') } }
        );
        const msbData = await msbResp.json();
        if (!msbResp.ok) return err(`MSB ${msbResp.status}: ${JSON.stringify(msbData).slice(0, 400)}`, 502);
        return ok(msbData);
      } catch (e) {
        return err('Erreur reseau MySendingBox', 502);
      }
    }

        // ── /lib/:file ── proxy GitHub Raw pour libs JS (évite CSP sandbox) ──
    const libMatch = path.match(/^\/lib\/([a-z0-9._-]+\.(?:js))$/);
    if (libMatch && method === "GET") {
      const fileName = libMatch[1];
      const githubUrl = `https://raw.githubusercontent.com/liquid69006/DPE-PROSPECTOR/main/lib/${fileName}`;
      try {
        const resp = await fetch(githubUrl);
        if (!resp.ok) return err("Lib introuvable", 404);
        const text = await resp.text();
        return new Response(text, {
          headers: {
            ...CORS,
            "Content-Type": "application/javascript; charset=utf-8",
            "Cache-Control": "public, max-age=86400",
          },
        });
      } catch {
        return err("Erreur proxy lib", 502);
      }
    }

    // ── /data/:agence/:file ── proxy GitHub Raw (évite CSP sandbox) ──
    const dataMatch = path.match(/^\/data\/([a-z0-9-]+)\/([a-z0-9._-]+\.json)$/);
    if (dataMatch && method === "GET") {
      const agenceId = dataMatch[1];
      const fileName = dataMatch[2];
      const cfg = AGENCES_CONFIG[agenceId];
      if (!cfg) return err("Agence inconnue", 404);

      // Construire le chemin GitHub depuis dataJsonPath de l'agence
      const basePath = cfg.dataJsonPath.replace(/[^/]+\.json$/, "");
      const githubUrl = `https://raw.githubusercontent.com/liquid69006/DPE-PROSPECTOR/main/${basePath}${fileName}`;

      try {
        const resp = await fetch(githubUrl);
        if (!resp.ok) return err("Fichier introuvable", 404);
        const text = await resp.text();
        return new Response(text, {
          headers: {
            ...CORS,
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-cache",
          },
        });
      } catch {
        return err("Erreur proxy GitHub", 502);
      }
    }

    return err("Route inconnue", 404);
}
