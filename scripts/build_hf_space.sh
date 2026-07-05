#!/usr/bin/env bash
# ── FreshVision AI — Assemble Hugging Face Space ───────────────────────────
#
# This script copies the backend into a ready-to-push HF Space folder.
#
# Usage:
#   bash scripts/build_hf_space.sh
#
# After running, follow the instructions printed at the end.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/hf_space"

echo "Building HF Space at: $OUT"
rm -rf "$OUT" && mkdir -p "$OUT"

# Copy backend app files
cp -r "$ROOT/backend/app"          "$OUT/app"
cp -r "$ROOT/backend/scripts"      "$OUT/scripts"
cp    "$ROOT/backend/requirements.txt" "$OUT/requirements.txt"

# HF-specific Dockerfile and README (replaces backend/Dockerfile)
cp "$ROOT/deploy/huggingface/Dockerfile" "$OUT/Dockerfile"
cp "$ROOT/deploy/huggingface/README.md"  "$OUT/README.md"

# Strip openvino from requirements (not needed on HF, saves build time)
sed -i.bak '/openvino/d' "$OUT/requirements.txt" && rm -f "$OUT/requirements.txt.bak"

echo ""
echo "✅  HF Space folder ready at: $OUT"
echo ""
echo "══════════════════════════════════════════════════════════"
echo "  Next steps:"
echo ""
echo "  1. Create a new Space on Hugging Face:"
echo "     → https://huggingface.co/new-space"
echo "     → SDK: Docker"
echo "     → Name: freshvision-backend"
echo "     → Visibility: Public"
echo ""
echo "  2. Push the hf_space/ folder to your Space:"
echo ""
echo "     git clone https://huggingface.co/spaces/YOUR_HF_USERNAME/freshvision-backend"
echo "     cp -r $OUT/* freshvision-backend/"
echo "     cd freshvision-backend"
echo "     git add . && git commit -m 'deploy' && git push"
echo ""
echo "  3. Add environment variables in Space Settings → Variables:"
echo "     FRESHVISION_JWT_SECRET  (any long random string)"
echo "     DATABASE_URL            (Supabase connection string)"
echo "     SUPABASE_URL            (Supabase project URL)"
echo "     SUPABASE_KEY            (Supabase anon key)"
echo "     CORS_ORIGINS            (your Vercel URL)"
echo ""
echo "  4. Your API will be live at:"
echo "     https://YOUR_HF_USERNAME-freshvision-backend.hf.space"
echo "══════════════════════════════════════════════════════════"
