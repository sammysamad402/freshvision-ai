#!/usr/bin/env bash
# ── FreshVision AI — Generate self-signed TLS certificate ─────────────────
# For production use Let's Encrypt (see README).
# For local / hackathon demo this gives you working HTTPS in < 5 seconds.
#
# Usage:
#   bash scripts/gen_selfsigned_cert.sh
#   bash scripts/gen_selfsigned_cert.sh yourdomain.com   # with custom CN

set -euo pipefail

DOMAIN="${1:-localhost}"
OUT_DIR="$(cd "$(dirname "$0")/../nginx/ssl" && pwd)"
mkdir -p "$OUT_DIR"

echo "Generating self-signed cert for: $DOMAIN"
echo "Output dir: $OUT_DIR"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$OUT_DIR/privkey.pem" \
  -out    "$OUT_DIR/fullchain.pem" \
  -subj   "/C=US/ST=State/L=City/O=FreshVision AI/CN=$DOMAIN" \
  -addext "subjectAltName=DNS:$DOMAIN,DNS:www.$DOMAIN,IP:127.0.0.1"

echo ""
echo "✅  Certificate written to:"
echo "    $OUT_DIR/fullchain.pem"
echo "    $OUT_DIR/privkey.pem"
echo ""
echo "⚠️   Browsers will show a security warning for self-signed certs."
echo "    For production: run scripts/letsencrypt.sh to get a trusted cert."
