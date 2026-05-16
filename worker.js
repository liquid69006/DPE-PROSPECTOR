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
  },
  "motte-picquet": {
    nom: "Century 21 La Motte Picquet",
    ville: "Paris 15e",
    couleur: "#7c3aed",
    email: "ybufferne@century21.fr",
    dataJsonPath: "data/motte-picquet.json",
    conseillers_defaut: ["À attribuer", "Jean-Marie", "Bérénice", "Joël"],
    zones: ["La Motte Picquet"],
    sci_enabled: false,
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

// ══════════════════════════════════════════════════════
//  HELPERS RÉPONSE
// ══════════════════════════════════════════════════════

const CORS = {
  "Access-Control-Allow-Origin":  "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
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

      const login = conseillerLoginFor(agenceId, prenom);
      if (!login) return err("prenom invalide", 400);

      // Mot de passe : 8 caractères alphanumériques (alphabet sans ambiguïté)
      const ALPHA = "abcdefghijkmnpqrstuvwxyz23456789";
      const rnd   = crypto.getRandomValues(new Uint8Array(8));
      let password = "";
      for (let i = 0; i < 8; i++) password += ALPHA[rnd[i] % ALPHA.length];

      await env.DPE_KV.put(`pwd:${login}`, await hashPassword(password));
      await env.DPE_KV.put(`role:${agenceId}:${login}`, "conseiller");

      const htmlMail = `<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;background:#f1f5f9;padding:32px;">
<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:40px;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
  <div style="font-size:24px;font-weight:700;margin-bottom:16px;">Nouveau conseiller — ${prenom}</div>
  <p style="color:#374151;line-height:1.6;">Une session a été créée pour <strong>${prenom}</strong> (${cfg.nom}).</p>
  <p style="color:#374151;line-height:1.6;">
    Identifiant : <strong>${login}</strong><br>
    Mot de passe : <strong>${password}</strong>
  </p>
  <p style="font-size:13px;color:#6b7280;line-height:1.6;">
    Communiquez ces accès au conseiller. Il est recommandé de changer le mot de passe
    après la première connexion.
  </p>
</div></body></html>`;
      await sendEmail(env, cfg.email, `Nouveau conseiller — ${prenom}`, htmlMail);

      return ok({ ok: true, login, password });
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

      // Liste des prénoms de conseillers (même source que GET /conseillers/:agence)
      let noms;
      if (agenceId === "lopez") {
        const merged = new Set();
        for (const ag of (AGENCES_CONFIG["lopez"].dpe_agences || [])) {
          const raw = await env.DPE_KV.get(`conseillers:${ag}`);
          const liste = raw ? JSON.parse(raw) : (AGENCES_CONFIG[ag]?.conseillers_defaut || []);
          liste.filter(c => c && c !== "À attribuer").forEach(c => merged.add(c));
        }
        noms = [...merged];
      } else if (agenceId === "bagot") {
        const merged = new Set();
        for (const ag of (AGENCES_CONFIG["bagot"].dpe_agences || [])) {
          const raw = await env.DPE_KV.get(`conseillers:${ag}`);
          const liste = raw ? JSON.parse(raw) : (AGENCES_CONFIG[ag]?.conseillers_defaut || []);
          liste.filter(c => c && c !== "À attribuer").forEach(c => merged.add(c));
        }
        noms = [...merged];
      } else {
        const raw = await env.DPE_KV.get(`conseillers:${agenceId}`);
        const liste = raw ? JSON.parse(raw) : (cfg.conseillers_defaut || []);
        noms = liste.filter(c => c && c !== "À attribuer");
      }

      const sessions = {};
      for (const nom of noms) {
        const login = conseillerLoginFor(agenceId, nom);
        if (!login) continue;
        const v = await env.DPE_KV.get(`role:${agenceId}:${login}`);
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

      await env.DPE_KV.delete(`pwd:${login}`);
      await env.DPE_KV.delete(`role:${agenceId}:${login}`);

      const htmlMail = `<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;background:#f1f5f9;padding:32px;">
<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:40px;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
  <div style="font-size:24px;font-weight:700;margin-bottom:16px;">Session supprimée — ${login}</div>
  <p style="color:#374151;line-height:1.6;">
    La session conseiller <strong>${login}</strong> (${cfg.nom}) a été supprimée.
    Cet identifiant ne permet plus de se connecter.
  </p>
</div></body></html>`;
      await sendEmail(env, cfg.email, `Session supprimée — ${login}`, htmlMail);

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
      const { html, docx_base64, to, postage_type, color, both_sides } = body;
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
        return ok({ id: msbData._id, status: msbData.status?.name, file_for_corus: msbData.file_for_corus, file: msbData.file });
      } catch(e) {
        return err('Erreur réseau MySendingBox', 502);
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
