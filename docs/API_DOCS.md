# Gateway API Docs

Tai lieu nay mo ta cac API chinh cua backend `gateway-be`.

## Docs Live

- Swagger UI: `https://gateway.plxeditor.com/api/v1/docs`
- ReDoc: `https://gateway.plxeditor.com/api/v1/redoc`
- OpenAPI JSON: `https://gateway.plxeditor.com/api/v1/openapi.json`

Staging:

- Swagger UI: `https://testgateway.plxeditor.com/api/v1/docs`
- ReDoc: `https://testgateway.plxeditor.com/api/v1/redoc`
- OpenAPI JSON: `https://testgateway.plxeditor.com/api/v1/openapi.json`

## Auth

Tat ca endpoint nghiep vu deu dung Bearer token khi `GATEWAY_AUTH_ENABLED=true`.

Dang nhap:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

Payload:

```json
{
  "username": "admin",
  "password": "GatewayAdmin@2026!"
}
```

Lay user hien tai:

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

## Vendor

Danh sach:

```http
GET /api/v1/vendors?search=&status=&offset=0&limit=20
```

Tao moi:

```http
POST /api/v1/vendors
Authorization: Bearer <admin_token>
Content-Type: application/json
```

```json
{
  "name": "Google",
  "slug": "google",
  "code": "google",
  "description": "Default vendor for Gemini integrations",
  "status": "active"
}
```

Chi tiet:

```http
GET /api/v1/vendors/{vendor_id}
```

Cap nhat:

```http
PATCH /api/v1/vendors/{vendor_id}
```

Xoa:

```http
DELETE /api/v1/vendors/{vendor_id}
```

## Pool

Danh sach:

```http
GET /api/v1/pools?vendor_id=&search=&status=&offset=0&limit=20
```

Tao moi:

```http
POST /api/v1/pools
```

```json
{
  "vendor_id": 1,
  "name": "Gemini API",
  "slug": "gemini-api",
  "code": "gemini-api",
  "description": "Google Gemini API pool",
  "status": "active",
  "config_json": {
    "provider": "google",
    "timeout_seconds": 60
  }
}
```

Chi tiet:

```http
GET /api/v1/pools/{pool_id}
```

Cap nhat:

```http
PATCH /api/v1/pools/{pool_id}
```

Xoa:

```http
DELETE /api/v1/pools/{pool_id}
```

## API Function

Danh sach:

```http
GET /api/v1/api-functions?pool_id=&search=&status=&offset=0&limit=20
```

Tao moi:

```http
POST /api/v1/api-functions
```

```json
{
  "pool_id": 1,
  "name": "Text Generation",
  "code": "text-generation",
  "description": "Generate text using Google GenAI",
  "http_method": "POST",
  "path": "/api/v1/gateway/functions/text-generation/execute",
  "provider_action": "google.genai.text_generation",
  "status": "active",
  "schema_json": {
    "type": "object"
  }
}
```

Vi du API Function cho image generation:

```json
{
  "pool_id": 2,
  "name": "Image Generation",
  "code": "image-generation",
  "description": "Generate images using Google GenAI",
  "http_method": "POST",
  "path": "/api/v1/gateway/functions/image-generation/execute",
  "provider_action": "google.genai.image_generation",
  "status": "active",
  "schema_json": {
    "type": "object"
  }
}
```

Chi tiet:

```http
GET /api/v1/api-functions/{api_function_id}
```

Cap nhat:

```http
PATCH /api/v1/api-functions/{api_function_id}
```

Xoa:

```http
DELETE /api/v1/api-functions/{api_function_id}
```

## Execute Gateway

Runtime execute:

```http
POST /api/v1/gateway/functions/{function_code}/execute
Authorization: Bearer <token>
Content-Type: application/json
```

Payload:

```json
{
  "api_key": "AIza...",
  "project_number": "123456789",
  "model": "gemini-2.5-flash",
  "prompt": "Hay viet 3 cau ngan mo ta Gateway API bang tieng Viet.",
  "input_images": [],
  "references_image": [],
  "references_video": [],
  "references_audios": []
}
```

Luu y:

- `references_image` voi luong `image-generation` se co gang fetch URL anh de gui vao provider nhu media reference thuc te. Neu fetch that bai, backend se giu URL do nhu text context.
- `references_video`, `references_audios` hien tai van duoc gui nhu URL/reference text context.
- Neu can image-to-image chac chan, uu tien dung `input_images`.
- `model` co the nhap dong, vi du:
  - `gemini-2.5-flash`
  - `gemini-3-flash-preview`
  - `gemini-3-pro-preview`

Response thanh cong:

```json
{
  "request_id": "gw_xxxxx",
  "vendor": "google",
  "pool": "gemini-api",
  "function": "text-generation",
  "model": "gemini-2.5-flash",
  "status": "success",
  "output": {
    "text": "...",
    "images": []
  },
  "usage": {
    "input_tokens": 14,
    "output_tokens": 105,
    "total_tokens": 1228
  },
  "latency_ms": 6943
}
```

Vi du image generation (text to image):

```json
{
  "api_key": "AIza...",
  "project_number": "123456789",
  "model": "nano-banana-2",
  "prompt": "Create a minimalist product photo of a bamboo water bottle on a pastel desk.",
  "input_images": [],
  "aspect_ratio": "1:1",
  "image_size": "1K"
}
```

Vi du image generation (image to image):

```json
{
  "api_key": "AIza...",
  "project_number": "123456789",
  "model": "nano-banana-pro",
  "prompt": "Restyle the input image into a clean isometric illustration.",
  "input_images": [
    {
      "mime_type": "image/png",
      "data_base64": "<BASE64_IMAGE_DATA>"
    }
  ],
  "aspect_ratio": "16:9",
  "image_size": "2K"
}
```

Response thanh cong (image generation):

```json
{
  "request_id": "gw_xxxxx",
  "vendor": "google",
  "pool": "image-generation",
  "function": "image-generation",
  "model": "gemini-3.1-flash-image-preview",
  "status": "success",
  "output": {
    "text": null,
    "images": [
      {
        "mime_type": "image/png",
        "data_base64": "<BASE64_IMAGE_DATA>"
      }
    ]
  },
  "usage": {
    "input_tokens": 120,
    "output_tokens": 0,
    "total_tokens": 120
  },
  "latency_ms": 5200
}
```

## Async Submit Gateway

Submit job de xu ly bat dong bo:

```http
POST /api/v1/gateway/functions/{function_code}/submit
X-Gateway-Api-Key: <gateway_api_key>
Content-Type: application/json
```

Payload:

```json
{
  "prompt": "Hello Gemini",
  "input_images": [],
  "references_image": [],
  "references_video": [],
  "references_audios": [],
  "max_attempts": 3,
  "webhook_url": "https://example.com/gateway/callback"
}
```

Luu y:

- Endpoint nay uu tien dung voi `Gateway API Key`.
- API se tao job va tra ngay `request_id`.
- Worker se xu ly phia sau va retry cho cac loi tam thoi nhu `429/502/503/504`.
- Retry duoc len lich qua `job_control.next_retry_at`, khong sleep trong request thread.

Response:

```json
{
  "request_id": "gw_xxxxx",
  "status": "queued",
  "function": "text-generation",
  "poll_path": "/api/v1/gateway/requests/gw_xxxxx/status",
  "webhook_url": "https://example.com/gateway/callback"
}
```

## Due Job Runner

Cho moi truong dung lau dai, nen chay runner rieng de quet cac job `queued` hoac `retrying` da den han:

```bash
python3 -m app.scripts.process_gateway_jobs
```

De xuat van hanh:

- chay bang `cron`, `systemd timer`, hoac worker process rieng
- tan suat 5-15 giay/lần tuy luong job
- endpoint `submit` chi lo nhan job nhanh
- runner lo xu ly lai cac job retry den han

## Poll Job Status

Theo doi trang thai job:

```http
GET /api/v1/gateway/requests/{request_id}/status
X-Gateway-Api-Key: <gateway_api_key>
```

Response:

```json
{
  "request_id": "gw_xxxxx",
  "function": "text-generation",
  "status": "success",
  "model": "gemini-3-flash-preview",
  "output": {
    "text": "Generated async from gateway key",
    "images": []
  },
  "error_message": null,
  "latency_ms": 1234,
  "retry_count": 0,
  "max_attempts": 3,
  "next_retry_at": null,
  "webhook_status": null
}
```

Trang thai co the gap:

- `queued`: job moi duoc tao hoac da duoc manual retry
- `processing`: worker dang xu ly
- `retrying`: da gap loi retryable va dang cho lan retry tiep theo
- `success`: hoan tat thanh cong
- `failed`: hoan tat that bai

## End-user Task Recovery

Endpoint nay danh cho client/end user khoi phuc mot task da failed tren chinh `request_id` hien tai:

```http
POST /api/v1/gateway/requests/{request_id}/retry
X-Gateway-Api-Key: <gateway_api_key>
```

Luu y:

- Chi dung cho task async tao bang endpoint `submit`.
- End user khong can submit job moi, chi khoi phuc tren task cu.
- Khong tao request moi, van giu nguyen `request_id`.
- Sau khi retry, task quay lai `queued` va client co the tiep tuc polling hoac nhan webhook.
- Neu request cu la sync `execute`, API se tra loi `422`.

Response:

```json
{
  "request_id": "gw_xxxxx",
  "function": "text-generation",
  "status": "queued",
  "model": "gemini-3-flash-preview",
  "output": {
    "text": null,
    "images": []
  },
  "error_message": null,
  "latency_ms": null,
  "retry_count": 0,
  "max_attempts": 3,
  "next_retry_at": null,
  "webhook_status": null
}
```

## Request History

Danh sach:

```http
GET /api/v1/gateway/requests?vendor_id=&pool_id=&api_function_id=&status=&search=&from_date=&to_date=&offset=0&limit=20
```

Chi tiet:

```http
GET /api/v1/gateway/requests/{id}
```

Request history luu:

- payload da mask API key
- provider request/response
- output text
- error message
- latency
- trang thai `success` hoac `failed`

## Health

```http
GET /up
```

Response:

```json
{
  "status": "ok",
  "service": "gateway-be"
}
```
