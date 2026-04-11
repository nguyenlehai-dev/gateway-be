# Gateway Backend Implementation Plan

## Tong quan

Du an backend dat ten la **Gateway** va su dung **Python** de xay dung API server.

Muc tieu giai doan dau:

- quan ly `Vendor`
- quan ly `Pool`
- quan ly `API Function`
- nhan payload goi AI
- goi Google GenAI text generation
- luu lich su request/response de theo doi va debug

Vendor dau tien:

- `Google`

Pool dau tien thuoc vendor Google:

- `Gemini API`

## Phan tich domain

Yeu cau hien tai dang co 3 lop chuc nang ro rang:

1. `Vendor`
2. `Pool`
3. `API Function`

Quan he de xuat:

- 1 `Vendor` co nhieu `Pool`
- 1 `Pool` thuoc dung 1 `Vendor`
- 1 `Pool` co nhieu `API Function`
- 1 `API Function` thuoc dung 1 `Pool`

Vi du:

- Vendor: `Google`
- Pool: `Gemini API`
- API Function: `text-generation`

## Bai toan nghiep vu

Nguoi dung vao admin Gateway se:

1. Tao `Vendor`
2. Tao `Pool` thuoc `Vendor`
3. Tao `API Function` thuoc `Pool`
4. Gui payload:
   - `api_key`
   - `project_number`
   - `model`
   - `references_image`
   - `references_video`
   - `references_audios`
5. He thong map payload vao provider adapter
6. Gateway goi Google GenAI
7. Tra ket qua ve client
8. Luu log request/response

## Luu y phan tich ky thuat

Co 1 diem can lam ro som:

- Yeu cau ghi la `text generation`, nhung payload lai co cac mang media reference.

Dieu nay hop ly neu Gateway su dung media references nhu context/input phu tro cho text generation. Vi vay backend nen tach:

- `input_text` hoac `prompt`
- `references_image[]`
- `references_video[]`
- `references_audios[]`

Neu chi giu dung cac field ma ban neu, thi van nen bo sung them `prompt` vi text generation khong nen chi dua vao references.

## Kien truc de xuat

Stack de xuat:

- Framework API: `FastAPI`
- Validation schema: `Pydantic`
- ORM: `SQLAlchemy`
- Migration: `Alembic`
- HTTP client: `httpx`
- Background jobs: co the bo sung sau bang `Celery` hoac `RQ` neu can
- Database: `PostgreSQL` cho production
- Local dev: co the bat dau bang `SQLite`, nhung production nen la `PostgreSQL`

## Cau truc thu muc de xuat

```text
gateway-be/
  app/
    api/
      v1/
        endpoints/
          vendors.py
          pools.py
          api_functions.py
          gateway_requests.py
    core/
      config.py
      security.py
    db/
      base.py
      session.py
    models/
      vendor.py
      pool.py
      api_function.py
      gateway_request.py
    schemas/
      vendor.py
      pool.py
      api_function.py
      gateway_request.py
      google_genai.py
    services/
      provider_registry.py
      google_genai_service.py
      gateway_executor.py
    repositories/
    utils/
  tests/
  alembic/
  docs/
```

## Data model de xuat

### 1. vendors

```text
id
name
slug
code
description
status
created_at
updated_at
```

Gia tri dau tien:

- `name = Google`
- `code = google`

### 2. pools

```text
id
vendor_id
name
slug
code
description
status
config_json
created_at
updated_at
```

Gia tri dau tien:

- `name = Gemini API`
- `code = gemini-api`

`config_json` dung de luu cau hinh chung cua pool, vi du:

- endpoint base
- timeout
- retry count
- rate limit

### 3. api_functions

```text
id
pool_id
name
code
description
http_method
path
provider_action
status
schema_json
created_at
updated_at
```

Gia tri dau tien:

- `name = Text Generation`
- `code = text-generation`
- `provider_action = google.genai.text_generation`

`schema_json` dung de khai bao payload contract cho FE render dong sau nay.

### 4. gateway_requests

```text
id
vendor_id
pool_id
api_function_id
request_id
model
project_number
api_key_masked
payload_json
provider_request_json
provider_response_json
output_text
status
error_message
latency_ms
created_at
updated_at
```

Bang nay dung de audit va debug.

## API contract de xuat

### CRUD quan tri

#### Vendors

- `GET /api/v1/vendors`
- `POST /api/v1/vendors`
- `GET /api/v1/vendors/{id}`
- `PUT /api/v1/vendors/{id}`
- `DELETE /api/v1/vendors/{id}`

#### Pools

- `GET /api/v1/pools`
- `POST /api/v1/pools`
- `GET /api/v1/pools/{id}`
- `PUT /api/v1/pools/{id}`
- `DELETE /api/v1/pools/{id}`

#### API Functions

- `GET /api/v1/api-functions`
- `POST /api/v1/api-functions`
- `GET /api/v1/api-functions/{id}`
- `PUT /api/v1/api-functions/{id}`
- `DELETE /api/v1/api-functions/{id}`

### Endpoint thuc thi Gateway

De xuat 1 endpoint tong quat:

- `POST /api/v1/gateway/execute`

Hoac 1 endpoint theo function:

- `POST /api/v1/gateway/functions/{function_code}/execute`

Toi uu hon la cach thu hai, vi URL ro nghia hon.

## Payload de xuat

Yeu cau hien tai:

```json
{
  "api_key": "AIza...",
  "project_number": "123456789",
  "model": "gemini-2.5-flash",
  "references_image": [],
  "references_video": [],
  "references_audios": []
}
```

De xuat bo sung bat buoc:

```json
{
  "api_key": "AIza...",
  "project_number": "123456789",
  "model": "gemini-2.5-flash",
  "prompt": "Hay tom tat noi dung tu cac references neu co",
  "references_image": [],
  "references_video": [],
  "references_audios": []
}
```

## Schema payload Python de xuat

```python
from pydantic import BaseModel, Field


class GatewayExecuteRequest(BaseModel):
    api_key: str = Field(..., min_length=10)
    project_number: str = Field(..., min_length=3)
    model: str = Field(default="gemini-2.5-flash")
    prompt: str = Field(..., min_length=1)
    references_image: list[str] = Field(default_factory=list)
    references_video: list[str] = Field(default_factory=list)
    references_audios: list[str] = Field(default_factory=list)
```

## Luong xu ly backend

1. Validate payload
2. Tim `API Function`
3. Tim `Pool`
4. Tim `Vendor`
5. Chon adapter phu hop
6. Build provider request
7. Goi Google GenAI
8. Parse response
9. Luu log vao `gateway_requests`
10. Tra output ve client

## Provider adapter pattern

Khong nen viet logic Google truc tiep trong controller. Nen tach theo adapter:

```text
Gateway Executor
  -> Provider Registry
    -> Google GenAI Service
```

Loi ich:

- sau nay de them OpenAI, Anthropic, Azure, ElevenLabs
- khong phai sua controller qua nhieu
- test don vi de hon

## Response de xuat

```json
{
  "request_id": "gw_01",
  "vendor": "google",
  "pool": "gemini-api",
  "function": "text-generation",
  "model": "gemini-2.5-flash",
  "status": "success",
  "output": {
    "text": "Noi dung sinh ra tu Gemini"
  },
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0
  },
  "latency_ms": 1200
}
```

## Bao mat

- Khong log raw `api_key`
- Chi luu `api_key_masked`
- Khong tra lai `api_key` trong response
- Them rate limit cho endpoint execute
- Them auth dashboard rieng neu day la he thong noi bo

## Validation rules

- `vendor.code` phai unique
- `pool.code` unique trong 1 vendor
- `api_function.code` unique trong 1 pool
- `model` phai thuoc danh sach cho phep hoac cho phep nhap tu do nhung co validation co ban
- Cac phan tu trong `references_*` nen la URL hop le

## Logging va monitoring

Can co:

- request log
- response log
- error log
- latency
- retry count neu co

Neu response lon, co the cat bot va chi luu phan can thiet.

## Ke hoach implement backend

### Phase 1

- Scaffold FastAPI project
- Tao model `Vendor`, `Pool`, `API Function`, `GatewayRequest`
- Tao CRUD APIs
- Seed `Google` va `Gemini API`
- Tao endpoint execute
- Tich hop Google GenAI text generation

### Phase 2

- Dashboard auth
- Search/filter/pagination
- Request history
- Retry request
- Export logs

### Phase 3

- Provider adapter mo rong
- Queue/background processing
- Rate limit theo pool
- API key vault / secret manager

## Open questions

- Co can multi-user hay chi admin noi bo?
- `project_number` dung cho routing noi bo hay bat buoc khi goi Google?
- `references_image`, `references_video`, `references_audios` la URL ngoai hay file upload?
- Co can luu file media local hay chi luu URL?
- Chuc nang text generation co can streaming response khong?

## Ket luan

Plan nay hop ly de bat dau mot AI Gateway co cau truc mo rong duoc. Diem can chot som nhat la:

- co them field `prompt`
- xac dinh `references_*` la URL hay upload
- chot FastAPI + SQLAlchemy + PostgreSQL lam stack backend mac dinh
