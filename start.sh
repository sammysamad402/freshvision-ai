#!/usr/bin/env bash
# ── FreshVision AI — Start Script ──────────────────────────────────────────
# Usage:
#   bash start.sh             # HTTP mode (default, port 80)
#   bash start.sh --https     # HTTPS mode (needs nginx/ssl/*.pem)
#   bash start.sh --seed      # Seed 30 days of demo data after start
#   bash start.sh --https --seed
#   bash start.sh --stop      # Stop all containers
#   bash start.sh --logs      # Follow logs

set -euo pipefail
cd "$(dirname "$0")"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

info()  { echo -e "${GREEN}[FreshVision]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARNING]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

HTTPS=false; SEED=false; STOP=false; LOGS=false
for arg in "$@"; do
  case $arg in
    --https) HTTPS=true ;;
    --seed)  SEED=true  ;;
    --stop)  STOP=true  ;;
    --logs)  LOGS=true  ;;
    *) warn "Unknown argument: $arg" ;;
  esac
done

# ── Stop ─────────────────────────────────────────────────────────────────────
if $STOP; then
  info "Stopping FreshVision AI..."
  docker compose down
  info "Stopped."
  exit 0
fi

# ── Logs ─────────────────────────────────────────────────────────────────────
if $LOGS; then
  docker compose logs -f
  exit 0
fi

# ── Pre-flight checks ─────────────────────────────────────────────────────────
info "FreshVision AI — starting up"

if ! command -v docker &>/dev/null; then
  error "Docker not found. Install Docker Desktop or Docker Engine first."
  exit 1
fi

if ! docker compose version &>/dev/null; then
  error "docker compose not found. Update Docker to v2.x."
  exit 1
fi

# ── .env check ────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    # Generate a random JWT secret automatically
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || \
             cat /dev/urandom | tr -dc 'a-f0-9' | head -c 64)
    sed -i.bak "s/CHANGE-ME-IN-PRODUCTION/$SECRET/" .env && rm -f .env.bak
    info ".env created with auto-generated JWT secret."
  else
    error ".env.example not found. Cannot create .env."
    exit 1
  fi
fi

# ── TLS cert check (HTTPS mode) ───────────────────────────────────────────────
if $HTTPS; then
  if [ ! -f nginx/ssl/fullchain.pem ] || [ ! -f nginx/ssl/privkey.pem ]; then
    warn "TLS certificates not found. Generating self-signed cert..."
    bash scripts/gen_selfsigned_cert.sh
  fi
  PROFILE_ARGS="--profile https"
  info "Starting in HTTPS mode on :443"
else
  PROFILE_ARGS=""
  info "Starting in HTTP mode on :80"
fi

# ── Build + start ─────────────────────────────────────────────────────────────
info "Building images (first run downloads ~300 MB, subsequent runs are fast)..."
docker compose $PROFILE_ARGS up --build -d

info "Waiting for backend health check..."
for i in $(seq 1 24); do
  if docker compose exec -T backend python3 -c \
      "import urllib.request; urllib.request.urlopen('http://localhost:8000/health',timeout=3)" \
      &>/dev/null; then
    info "Backend is healthy ✓"
    break
  fi
  if [ "$i" -eq 24 ]; then
    error "Backend did not become healthy in 120s. Check: docker compose logs backend"
    exit 1
  fi
  echo -n "."
  sleep 5
done

# ── Seed demo data ────────────────────────────────────────────────────────────
if $SEED; then
  info "Seeding 30 days of demo data (this takes ~60s on i3)..."
  docker compose exec backend python -m scripts.seed_demo_data --days 30
  info "Demo data seeded ✓"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        FreshVision AI is running!                   ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
if $HTTPS; then
echo -e "${GREEN}║  Dashboard:  https://localhost                       ║${NC}"
echo -e "${GREEN}║  API Docs:   https://localhost/docs                  ║${NC}"
else
echo -e "${GREEN}║  Dashboard:  http://localhost                        ║${NC}"
echo -e "${GREEN}║  API Docs:   http://localhost/docs                   ║${NC}"
fi
echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Login:  admin / freshvision2024                    ║${NC}"
echo -e "${GREEN}║          inspector / inspect123                     ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Logs:   bash start.sh --logs                       ║${NC}"
echo -e "${GREEN}║  Stop:   bash start.sh --stop                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
