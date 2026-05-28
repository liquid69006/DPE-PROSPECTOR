#!/usr/bin/env python3
"""Sign a fresh JWT for DPE-PROSPECTOR worker (role=patron, 1 agence).

Le secret est lu depuis la variable d'environnement WORKER_JWT_SECRET.
Ne contient AUCUN secret. N'ecrit rien sur disque (ni JWT ni secret).
Affiche le JWT sur stdout une seule fois.

Reproduit exactement la signature du worker (worker.js l163 signJwt) :
  - HMAC-SHA256
  - b64url (URL-safe base64 sans padding)
  - payload {agence, agences, role, exp} ; exp = ms epoch (Date.now() style)
  - TTL par defaut 24h (TOKEN_TTL_MS du worker)

Usage (PowerShell 5.1) :
  $sec = Read-Host "JWT_SECRET" -AsSecureString
  $env:WORKER_JWT_SECRET = `
      [System.Net.NetworkCredential]::new('', $sec).Password
  python scripts/sign_jwt_dpe.py
  # Copier le JWT affiche, puis :
  $env:DPE_JWT = '<jwt-copie>'
  Remove-Item Env:\WORKER_JWT_SECRET    # imperatif : enlever le secret

Options :
  --agence <id>    defaut : dauphine-lacassagne (slug racine du payload)
  --agences <csv>  optionnel : liste CSV de slugs (override payload.agences)
                   ex : --agences dauphine-lacassagne,motte-picquet,pernety
                   si absent : payload.agences = [args.agence]
  --role <r>       defaut : patron
  --ttl-hours <h>  defaut : 24 (= TOKEN_TTL_MS worker)
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time


def b64url(data):
    """URL-safe base64 sans padding, comme worker.js b64url()."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def sign_jwt(payload, secret):
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"},
                               separators=(",", ":")))
    body = b64url(json.dumps(payload, separators=(",", ":")))
    data = f"{header}.{body}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), data, hashlib.sha256).digest()
    return f"{header}.{body}.{b64url(sig)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agence", default="dauphine-lacassagne")
    ap.add_argument("--agences",
                    help="Liste CSV de slugs (ex: dauphine-lacassagne,"
                         "motte-picquet). Si fournie, override "
                         "payload.agences. Sinon defaut = [--agence].")
    ap.add_argument("--role", default="patron")
    ap.add_argument("--ttl-hours", type=int, default=24)
    args = ap.parse_args()

    secret = os.environ.get("WORKER_JWT_SECRET")
    if not secret:
        sys.exit("[abort] env var WORKER_JWT_SECRET absente. "
                 "Set la avant le run (cf docstring du script).")

    exp_ms = int(time.time() * 1000) + args.ttl_hours * 3600 * 1000

    # agences[] : si --agences fourni, parse CSV ; sinon defaut = [--agence]
    if args.agences:
        agences_list = [s.strip() for s in args.agences.split(",")
                        if s.strip()]
    else:
        agences_list = [args.agence]

    payload = {
        "agence":   args.agence,
        "agences":  agences_list,
        "role":     args.role,
        "exp":      exp_ms,
    }

    token = sign_jwt(payload, secret)

    # Affichage stdout (1 ligne, sans retour multiple, pour copy facile)
    sys.stdout.write(token)
    sys.stdout.write("\n")

    # Note d'info sur stderr (ne pollue pas le copier-coller du token)
    sys.stderr.write(
        f"\n[info] role={args.role}  agence={args.agence}  "
        f"agences={agences_list}  "
        f"ttl={args.ttl_hours}h  exp_ms={exp_ms}\n"
        "[info] ce JWT n'est PAS ecrit sur disque. Copie-le maintenant.\n"
    )


if __name__ == "__main__":
    main()
