# Gateway Backend

Backend cho du an **Gateway** duoc xay dung bang `FastAPI`.

Trang thai hien tai:

- Da scaffold den `Phase 6` muc co ban
- Co healthcheck `/up`
- Co cau truc app, config, database session, SQLAlchemy models
- Da setup Alembic cho migration
- Da co CRUD, execute Gemini, request history, auth/rate-limit co ban, deploy skeleton
- Da co auth bai ban voi `users`, `login`, `me`, bootstrap admin

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL cho production
- SQLite cho local development

## Cau truc chinh

```text
app/
  api/
  core/
  db/
  models/
  repositories/
  schemas/
  services/
  utils/
alembic/
tests/
```

## Chay local

```bash
cd /home/vpsroot/projects/backend/gateway-be
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Luu y:

- Bien moi truong cua du an dung prefix `GATEWAY_`
- Neu may chua co `python3-venv`, co the tam thoi dung Python system de chay local
- Auth mac dinh dang tat trong local. Bat lai bang `GATEWAY_AUTH_ENABLED=true`

## Verify

```bash
curl http://127.0.0.1:8000/up
```

Ket qua mong doi:

```json
{
  "status": "ok",
  "service": "gateway-be"
}
```

## API Docs

- Swagger UI local: `http://127.0.0.1:8000/api/v1/docs`
- ReDoc local: `http://127.0.0.1:8000/api/v1/redoc`
- OpenAPI JSON local: `http://127.0.0.1:8000/api/v1/openapi.json`
- Swagger UI prod: `https://gateway.plxeditor.com/api/v1/docs`
- Swagger UI staging: `https://testgateway.plxeditor.com/api/v1/docs`
- Tai lieu markdown: `docs/API_DOCS.md`

## Testing

```bash
pytest
```

## Auth

Endpoint:

```bash
POST /api/v1/auth/login
GET /api/v1/auth/me
```

Bootstrap admin duoc tao boi:

```bash
python3 scripts/seed_auth.py
```

Env lien quan:

- `GATEWAY_AUTH_ENABLED`
- `GATEWAY_AUTH_SECRET_KEY`
- `GATEWAY_AUTH_ACCESS_TOKEN_TTL_MINUTES`
- `GATEWAY_BOOTSTRAP_ADMIN_USERNAME`
- `GATEWAY_BOOTSTRAP_ADMIN_PASSWORD`
- `GATEWAY_BOOTSTRAP_ADMIN_FULL_NAME`

Vi du login:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  --data '{"username":"admin","password":"ChangeMe123!"}'
```

## Seed du lieu mac dinh

```bash
python3 scripts/seed_phase2.py
```

Seed se tao:

- Vendor `Google`
- Pool `Gemini API`
- API Function `Text Generation`

## Execute endpoint

```bash
POST /api/v1/gateway/functions/{function_code}/execute
```

Payload:

```json
{
  "api_key": "AIza...",
  "project_number": "123456789",
  "model": "gemini-2.5-flash",
  "prompt": "Hello Gemini",
  "references_image": [],
  "references_video": [],
  "references_audios": []
}
```

## Docker deploy

```bash
docker compose up -d --build
```

Hoac:

```bash
./scripts/deploy-compose.sh staging
./scripts/deploy-compose.sh prod
```

## Phase hien tai

Da xong:

- Phase 0: scaffold project
- Phase 1: database foundation
- Phase 2: CRUD `Vendor -> Pool -> API Function`
- Phase 3: Execute Google GenAI text generation
- Phase 4: Request history co ban
- Phase 5: Auth/security co ban
- Phase 6: Docker/deploy skeleton
