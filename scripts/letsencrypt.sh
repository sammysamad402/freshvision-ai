#!/usr/bin/env bash
# ── FreshVision AI — Let's Encrypt certificate via Certbot ────────────────
# Free, trusted TLS cert. Requires:
#   • A public domain pointing to this server (A/AAAA record)
#   • Port 80 open to the internet (for ACME challenge)
#   • Docker + docker compose running
#
# Usage:
#   bash scripts/letsencrypt.sh yourdomain.com admin@yourdomain.com

set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain> <email>}"
EMAIL="${2:?Usage: $0 <domain> <email>}"
SSL_DIR="$(cd "$(dirname "$0")/../nginx/ssl" && pwd)"

echo "Requesting Let's Encrypt certificate for $DOMAIN..."

# Certbot standalone mode — temporarily uses port 80
docker run --rm \
  -v "$SSL_DIR:/etc/letsencrypt/live/$DOMAIN" \
  -v "/var/www/certbot:/var/www/certbot" \
  -p "80:80" \
  certbot/certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    -d "$DOMAIN" \
    --cert-path  "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" \
    --key-path   "/etc/letsencrypt/live/$DOMAIN/privkey.pem"

echo ""
echo "✅  Certificate saved to $SSL_DIR"
echo ""
echo "Add to crontab for auto-renewal (runs at 3am daily):"
echo "  0 3 * * * bash $(realpath "$0") $DOMAIN $EMAIL >> /var/log/certbot_renew.log 2>&1"
