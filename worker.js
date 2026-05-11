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
 *   GET  /conseillers/:agence          → { conseillers }
 *   POST /conseillers/:agence          → { conseillers }
 *   POST /change-password/:agence      → { oldPassword, newPassword }
 */

// ══════════════════════════════════════════════════════
//  CONFIGURATION STATIQUE DES AGENCES
//  (mots de passe stockés dans Cloudflare KV, pas ici)
// ══════════════════════════════════════════════════════

const AGENCES_CONFIG = {
  "dauphine-lacassagne": {
    nom: "Century 21 Dauphiné-Lacassagne",
    ville: "Lyon 3e",
    couleur: "#1d4ed8",
    email: "dauphine.lacassagne@century21.fr",
    dataJsonPath: "data/dauphine-lacassagne.json",
    conseillers_defaut: ["À attribuer", "Gérald", "Philippe", "Robin", "Kévin", "Yann"],
    zones: ["Dauphiné-Lacassagne", "Montchat"],
  },
  "motte-picquet": {
    nom: "Century 21 La Motte Picquet",
    ville: "Paris 15e",
    couleur: "#7c3aed",
    email: "ybufferne@century21.fr",
    dataJsonPath: "data/motte-picquet.json",
    conseillers_defaut: ["À attribuer", "Jean-Marie", "Bérénice", "Joël"],
    zones: ["La Motte Picquet"],
  },
  "pernety": {
    nom: "Century 21 Pernéty",
    ville: "Paris 14e",
    couleur: "#059669",
    email: "ybufferne@century21.fr",
    dataJsonPath: "data/pernety.json",
    conseillers_defaut: ["À attribuer", "Mathis", "Julien", "Philippe", "Fahd", "Maxime", "Cyril", "Melchior"],
    zones: ["Pernéty"],
  },
  "houlgate": {
    nom: "Century 21 Bagot — Houlgate",
    ville: "Houlgate",
    couleur: "#b45309",
    email: "marine-bagot@century21.fr",
    dataJsonPath: "data/houlgate.json",
    conseillers_defaut: ["À attribuer"],
    zones: ["Houlgate"],
  },
  "villers": {
    nom: "Century 21 Bagot — Villers-sur-Mer",
    ville: "Villers-sur-Mer",
    couleur: "#b45309",
    email: "marine-bagot@century21.fr",
    dataJsonPath: "data/villers.json",
    conseillers_defaut: ["À attribuer"],
    zones: ["Villers-sur-Mer"],
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
      const { agence, password } = body;
      if (!agence || !password) return err("agence et password requis");
      const cfg = AGENCES_CONFIG[agence];
      if (!cfg) return err("Agence inconnue", 404);

      // Mot de passe stocké en KV (hash SHA-256), fallback sur secret Wrangler
      const storedHash = await env.DPE_KV.get(`pwd:${agence}`);
      let valid = false;
      if (storedHash) {
        valid = (await hashPassword(password)) === storedHash;
      } else {
        // Premier démarrage : mot de passe depuis secrets Wrangler
        const secretKey = `PWD_${agence.toUpperCase().replace(/-/g,"_")}`;
        const plainPwd  = env[secretKey];
        if (!plainPwd) return err("Mot de passe non configuré", 500);
        if (password === plainPwd) {
          // Migrer vers KV hashé
          await env.DPE_KV.put(`pwd:${agence}`, await hashPassword(password));
          valid = true;
        }
      }
      if (!valid) return err("Mot de passe incorrect", 401);

      const token = await signJwt({ agence, exp: Date.now() + TOKEN_TTL_MS }, JWT_SECRET);

      // Charger conseillers depuis KV (ou défaut)
      const consRaw    = await env.DPE_KV.get(`conseillers:${agence}`);
      const conseillers = consRaw ? JSON.parse(consRaw) : cfg.conseillers_defaut;

      return json({
        token, agence,
        config: {
          nom:          cfg.nom,
          ville:        cfg.ville,
          couleur:      cfg.couleur,
          dataJsonPath: cfg.dataJsonPath,
          zones:        cfg.zones,
          conseillers,
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
      if (agenceId && payload.agence !== agenceId) return [null, err("Accès refusé", 403)];
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
      const [, authErr] = await requireAuth(agenceId);
      if (authErr) return authErr;

      if (method === "GET") {
        const raw = await env.DPE_KV.get(`assignments:${agenceId}`);
        return json({ assignments: raw ? JSON.parse(raw) : {} });
      }
      if (method === "POST") {
        let body; try { body = await request.json(); } catch { return err("JSON invalide"); }
        if (typeof body.assignments !== "object") return err("assignments doit être un objet");
        await env.DPE_KV.put(`assignments:${agenceId}`, JSON.stringify(body.assignments));
        return json({ ok: true, count: Object.keys(body.assignments).length });
      }
      return err("Méthode non supportée", 405);
    }

    // ── /conseillers/:agence ──────────────────────────
    const consMatch = path.match(/^\/conseillers\/([a-z0-9-]+)$/);
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

    return err("Route inconnue", 404);
  },
};
