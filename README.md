# gateway-be

Backend scaffold for the profile management and automation platform.

## Stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- Playwright-ready automation service layer

## Features in this scaffold

- Profile management for `grok`, `flow`, `dreamina`
- Proxy management
- API key management
- Cookie import from `txt` and `json`
- Basic anti-detect profile fields
- Automation job queue model with Playwright launch previews

## Quick start

1. Copy env:

```bash
cp .env.example .env
```

2. Start PostgreSQL:

```bash
docker compose up -d
```

3. Create venv and install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

4. Run API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Main endpoints

- `GET /health`
- `GET /api/dashboard`
- `GET/POST /api/profiles`
- `POST /api/profiles/{id}/cookies`
- `GET/POST /api/proxies`
- `GET/POST /api/api-keys`
- `GET/POST /api/jobs`
- `GET /api/jobs/preview/{profile_id}`
