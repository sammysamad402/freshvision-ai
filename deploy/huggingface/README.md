---
title: FreshVision AI Backend
emoji: 🌿
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: AI quality inspection API for fresh produce
---

# FreshVision AI — Backend API

FastAPI backend for the FreshVision AI produce quality inspection platform.

- **Frontend:** Deploy separately on Vercel (see main repo README)
- **Docs:** Visit `/docs` on this Space for interactive API documentation
- **Health:** `/health` endpoint

## Environment Variables (set in Space Settings → Variables and Secrets)

| Variable | Required | Description |
|---|---|---|
| `FRESHVISION_JWT_SECRET` | ✅ (Secret) | Long random string signing all login tokens. Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `ENVIRONMENT` | ✅ | Set to `production` — the app refuses to boot with the default JWT secret when this is set |
| `DATABASE_URL` | ✅ (Secret) | Supabase PostgreSQL connection string (`postgres://` or `postgresql://` both work) |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_KEY` | ✅ (Secret) | Supabase anon key |
| `CORS_ORIGINS` | ✅ | Your Vercel frontend URL |
| `ALLOW_REGISTRATION` | optional | `true` (default) lets anyone create their own private account from the Sign-up screen |
| `SEED_DEMO_USERS` | optional | Set to `false` on any public Space — leaving it `true` seeds a well-known demo admin password |

## Accounts

Sign in creates a fully private workspace per account: inspections, history,
and analytics are never shared between users. Only accounts with the
`admin` role can see everyone's data.

- **Sign-up screen** — anyone can register their own account (unless
  `ALLOW_REGISTRATION=false`).
- **Demo accounts** (`admin`/`freshvision2024`, `inspector`/`inspect123`) only
  exist if `SEED_DEMO_USERS=true`. Turn this off for any Space others can
  reach, since that password is public in this repo.
