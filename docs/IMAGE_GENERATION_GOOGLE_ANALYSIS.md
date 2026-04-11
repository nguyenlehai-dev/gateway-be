# Google Image Generation Analysis

## Muc tieu

Tai lieu nay phan tich viec bo sung chuc nang `image-generation` cho du an `gateway-be`.

Phan tich nay bo qua case `503` truoc do va tap trung vao feature moi ma khach dang muon:

- them `API Function` moi thuoc vendor `Google`
- ho tro `text-to-image`
- ho tro `image-to-image`
- cho phep gui anh tham chieu
- dung cac model image generation cua Gemini

Tai lieu tham chieu chinh thuc:

- Image generation docs: https://ai.google.dev/gemini-api/docs/image-generation
- Image understanding docs: https://ai.google.dev/gemini-api/docs/vision
- Gemini models overview: https://ai.google.dev/models/gemini

## Ket luan nhanh

Feature nay lam duoc, nhung khong phai chi "them 1 pool" la xong.

Gateway hien tai moi support duy nhat `text_generation` cho Google. De support `image-generation`, can mo rong:

- `provider registry`
- `request/response schema`
- `Google service`
- `gateway executor`
- `gateway request logging`
- `API docs`
- `tests`

Neu muon giao nhanh, nen lam theo huong MVP:

1. giu nguyen endpoint `/api/v1/gateway/functions/{function_code}/execute`
2. them `provider_action = google.genai.image_generation`
3. bo sung request schema cho prompt + image inputs
4. tra response co ca `text` va danh sach anh sinh ra
5. logging du metadata va provider response de debug

## Trang thai hien tai cua codebase

Gateway hien tai dang co cac gioi han ro rang:

### 1. Provider registry chi map text generation

File: `app/services/provider_registry.py`

He thong hien tai chi resolve:

- `vendor_code = google`
- `provider_action = google.genai.text_generation`

Nghia la neu tao `API Function` moi voi action khac, runtime se fail ngay.

### 2. Google service hien tai chi goi `generateContent` va parse text

File: `app/services/google_genai_service.py`

Service hien tai:

- build request tu `prompt`
- them `references_image`, `references_video`, `references_audios` nhu text context
- goi `.../models/{model}:generateContent`
- doc `response.candidates[0].content.parts[*].text`

Diem quan trong:

- `references_image` hien tai chi la URL/reference string, chua phai binary image input thuc su
- response hien tai khong parse `inline_data`/`inlineData` cho image output

### 3. Schema hien tai la schema text-centric

File: `app/schemas/google_genai.py`

`GatewayExecuteRequest` hien tai co:

- `prompt`
- `references_image`
- `references_video`
- `references_audios`

`GatewayExecuteResponse` hien tai chi co:

- `output.text`
- `usage`
- `latency_ms`

Nghia la response contract hien tai chua co cho:

- danh sach anh output
- mime type
- base64 data
- image metadata

### 4. Gateway request log hien tai van co the tai su dung, nhung chua toi uu cho image

File: `app/models/gateway_request.py`

Bang log hien tai da co:

- `payload_json`
- `provider_request_json`
- `provider_response_json`
- `output_text`

Day la diem tot vi khong can tao bang moi ngay lap tuc.

Tuy nhien:

- `output_text` la chua du neu response chinh la image
- nen can nhac bo sung metadata tong hop cho image output sau nay

## Doc yeu cau tu khach

Khach dang muon:

- them tinh nang tao anh
- dung docs image generation cua Google
- dat ten function la `image-generation`
- thuoc vendor `Google`
- generate anh bang `Nano Banana` va `Nano Banana Pro`
- co anh tham chieu
- co `text to image`
- co `image to image`

Tu docs chinh thuc cua Google, cach goi hop ly nhat hien nay la:

- `gemini-3.1-flash-image-preview` (Nano Banana 2)
- `gemini-3-pro-image-preview` (Nano Banana Pro)

Ten "Nano Banana" va "Nano Banana Pro" la ten goi capability/marketing.
Trong API request, can dung model code o tren.

## Muc tieu nghiep vu de xuat

De tranh mo feature qua rong ngay tu dau, nen chia theo 2 phase:

### Phase 1: MVP

Support:

- `text-to-image`
- `image-to-image`
- 1 hoac nhieu anh dau vao dang `inline data`
- response tra ve danh sach anh output dang base64
- co the co them text output neu provider tra kem

Khong support trong MVP:

- upload file lon qua Files API
- luu image artifact ra storage rieng
- streaming
- image mask/chinh sua theo region
- video/image mixed workflow

### Phase 2: Nang cao

Support them:

- luu image output vao object storage
- response tra URL thay vi base64
- file upload flow cho input image lon
- selection strategy theo model/pool key
- policy/guardrail rieng cho image generation

## Thay doi can co trong domain hien tai

## 1. API Function moi

Can them 1 `API Function` moi trong admin:

- `name = Image Generation`
- `code = image-generation`
- `path = /api/v1/gateway/functions/image-generation/execute`
- `provider_action = google.genai.image_generation`

Neu muon tach ro model cap:

- co the tao them:
  - `image-generation-flash`
  - `image-generation-pro`

Nhung de gian cho FE va client, 1 function voi `model` truyen dong la hop ly hon.

## 2. Request schema moi

Schema hien tai khong du de mo ta anh input dung nghia.

Nen doi sang cau truc ro hon:

```json
{
  "gateway_api_key": "gw_...",
  "api_key": "AIza...",
  "project_number": "123456789",
  "model": "gemini-2.5-flash-image",
  "prompt": "Create a clean ecommerce photo of this product on a stone table",
  "input_images": [
    {
      "mime_type": "image/png",
      "data_base64": "..."
    }
  ]
}
```

Ly do:

- `references_image` dang la list string, khong du de goi image generation thuc su
- image generation cua Google can prompt + image bytes hoac inline data
- neu tiep tuc dung `references_image: list[str]`, backend se kho phan biet URL text reference voi binary image input

De giam pha vo backward compatibility, co 2 cach:

### Cach A: Mo rong schema hien tai

Them field moi:

- `input_images: list[GatewayInputImage] = []`

Va van giu:

- `references_image`
- `references_video`
- `references_audios`

Uu diem:

- it pha vo code hien tai
- text generation khong bi anh huong

Nhuoc diem:

- schema execute se bat dau "phinh"

### Cach B: Tach schema theo provider action

Khi `provider_action = google.genai.image_generation`, dung schema rieng.

Uu diem:

- nghiep vu sach hon

Nhuoc diem:

- gateway executor va admin schema renderer se phuc tap hon

De giao nhanh, nen chon **Cach A**.

## 3. Response schema moi

Hien tai response chi co `output.text`.

Can doi sang output da modality:

```json
{
  "request_id": "gw_xxx",
  "vendor": "google",
  "pool": "gemini-api",
  "function": "image-generation",
  "model": "gemini-2.5-flash-image",
  "status": "success",
  "output": {
    "text": "Here is the generated image.",
    "images": [
      {
        "mime_type": "image/png",
        "data_base64": "..."
      }
    ]
  },
  "usage": {
    "input_tokens": 123,
    "output_tokens": 456,
    "total_tokens": 579
  },
  "latency_ms": 3200
}
```

Can bo sung:

- `images[]`
- `mime_type`
- `data_base64`

Neu muon an toan hon cho payload lon:

- co the them config de tra `images` toi da bao nhieu item
- va canh bao kich thuoc response

## 4. Google service moi cho image generation

Can bo sung service hoac mo rong service hien tai:

- `GoogleGenAIImageService`
hoac
- them method `generate_image(...)` vao `GoogleGenAIService`

Huong de xuat:

- giu `GoogleGenAIService` nhung tach ro:
  - `generate_text(...)`
  - `generate_image(...)`
  - helper parse parts chung

Tai sao:

- cung vendor `google`
- cung su dung `generateContent`
- khac nhau chu yeu o request parts va response parsing

## 5. Provider registry can map action moi

Can bo sung:

- `google.genai.image_generation`

Neu khong co buoc nay thi function moi tao trong admin se khong chay duoc.

## 6. Gateway executor can support output da loai

Hien tai `GatewayExecutor.execute()` dang assume response thanh cong se co:

- `provider_request`
- `provider_response`
- `output_text`

Can doi thanh mot contract trung gian ro hon, vi du:

```python
{
  "provider_request": {...},
  "provider_response": {...},
  "output_text": "...",
  "output_images": [
    {"mime_type": "image/png", "data_base64": "..."}
  ]
}
```

Neu khong doi contract trung gian, image generation se bi ep vao text-only flow va kho mo rong tiep.

## De xuat thiet ke ky thuat

## Option 1: Tien hoa tu flow hien tai

Mo rong code hien tai theo chieu doc:

- `GatewayExecuteRequest` them `input_images`
- `GatewayExecuteOutput` them `images`
- `ProviderRegistry` them action moi
- `GoogleGenAIService` them `generate_image`
- `GatewayExecutor` xu ly response da modality

Uu diem:

- thay doi vua phai
- it file moi
- de review

Nhuoc diem:

- `google_genai.py` va `gateway_executor.py` se "phinh" hon

## Option 2: Tach provider capability layer

Tao them abstraction theo capability:

- `TextGenerationResult`
- `ImageGenerationResult`
- `BaseProviderResult`

Uu diem:

- mo rong dai han tot hon

Nhuoc diem:

- qua tay so voi MVP

**Kien nghi:** chon `Option 1` cho lan dau.

## De xuat API contract MVP

## Request

```json
{
  "gateway_api_key": "gw_xxx",
  "model": "gemini-2.5-flash-image",
  "prompt": "Generate a premium lifestyle product photo",
  "input_images": [
    {
      "mime_type": "image/jpeg",
      "data_base64": "..."
    }
  ]
}
```

Rule:

- `prompt` bat buoc
- `model` bat buoc cho image generation hoac lay default tu pool
- `input_images = []` thi la `text-to-image`
- `input_images != []` thi la `image-to-image`

## Response

```json
{
  "request_id": "gw_xxx",
  "vendor": "google",
  "pool": "gemini-api",
  "function": "image-generation",
  "model": "gemini-2.5-flash-image",
  "status": "success",
  "output": {
    "text": "Generated 1 image.",
    "images": [
      {
        "mime_type": "image/png",
        "data_base64": "..."
      }
    ]
  },
  "usage": {
    "input_tokens": 123,
    "output_tokens": 456,
    "total_tokens": 579
  },
  "latency_ms": 3200
}
```

## Logging va database

MVP co the giu nguyen bang `gateway_requests`.

Nhung nen note ro:

- `payload_json` co the chua `input_images`
- khong nen log full base64 input neu payload qua lon

De xuat:

- chi log metadata input image:
  - `mime_type`
  - `byte_size`
  - `sha256_prefix`
- khong log full `data_base64` vao `payload_json`

Ly do:

- tranh DB phinh nhanh
- tranh ro ri du lieu
- de log van doc duoc

Cho `provider_request_json` va `provider_response_json`:

- co the can sanitize tuong tu
- neu provider response chua image binary base64 lon, can nhac cat gon

Neu khong sanitize, DB se to ra rat nhanh.

Day la diem can chot som truoc khi implement.

## Anh huong toi FE admin Gateway

Repo FE admin hien tai la `frontend/gateway-fe`.

De tao function moi trong admin, FE co the da du de:

- tao `Api Function`
- chon `provider_action`
- nhap `schema_json`

Nhung neu muon Playground/execute tren FE admin:

- se can UI upload image
- doc file base64
- gui `input_images`
- render image output tu `data_base64`

Neu MVP chi target backend runtime, FE admin co the cap nhat sau.

## Anh huong toi API docs

Can cap nhat `docs/API_DOCS.md` va OpenAPI docs cho:

- example request moi
- example response moi
- `provider_action = google.genai.image_generation`
- model examples:
  - `gemini-2.5-flash-image`
  - `gemini-3-pro-image-preview`

## Rui ro ky thuat

## 1. Payload lon

Image base64 lam request va response rat lon.

He qua:

- tang latency
- tang memory
- tang kich thuoc DB neu log nguyen van
- de vuot gioi han reverse proxy

Can xem lai:

- nginx body size
- uvicorn/gunicorn settings
- max request payload

## 2. Logging qua nhieu binary

Neu luu full `data_base64` vao DB:

- database phinh nhanh
- query list log cham
- backup phinh

Nen sanitize metadata thay vi luu full.

## 3. Backward compatibility

Neu sua truc tiep `GatewayExecuteResponse.output` theo huong them `images`, can dam bao client text generation cu khong bi vo.

Huong an toan:

- giu `output.text`
- them `output.images` la optional

## 4. Validation input image

Can validate:

- `mime_type`
- `data_base64` hop le
- gioi han so luong anh
- gioi han kich thuoc moi anh
- tong kich thuoc payload

## 5. Security

Can tranh:

- upload file gia mao mime type
- request payload qua lon de lam nghen service
- luu binary nhay cam vao logs

## De xuat validation MVP

- toi da `4` input images
- moi image toi da `10MB` raw data
- chi chap nhan:
  - `image/png`
  - `image/jpeg`
  - `image/webp`
- tong payload image toi da `20MB`

Con so nay can chot lai theo ha tang that.

## De xuat cac thay doi code

## Backend files chac chan se dung toi

- `app/schemas/google_genai.py`
- `app/services/provider_registry.py`
- `app/services/google_genai_service.py`
- `app/services/gateway_executor.py`
- `app/api/v1/endpoints/gateway.py`
- `docs/API_DOCS.md`
- `tests/test_phase3_execute.py`
- `tests/test_gateway_api_key_flow.py`

## Co the can tao them file moi

- `app/schemas/media.py`
hoac
- tiep tuc de chung trong `google_genai.py`

MVP khong bat buoc tach file moi.

## Roadmap implement de xuat

### Buoc 1

Cap nhat schema request/response:

- them `input_images`
- them `output.images`

### Buoc 2

Cap nhat provider registry:

- map `google.genai.image_generation`

### Buoc 3

Mo rong Google service:

- build image parts dung `inline_data`
- parse response parts gom text va image

### Buoc 4

Cap nhat gateway executor:

- nhan ket qua da modality
- log metadata an toan
- tra response image generation

### Buoc 5

Cap nhat tests:

- text-to-image success
- image-to-image success
- invalid mime type
- payload qua lon

### Buoc 6

Cap nhat docs va example trong admin

## Recommendation cuoi cung

Nen chot pham vi nhu sau:

- them `API Function` moi: `image-generation`
- thuoc vendor `Google`
- `provider_action = google.genai.image_generation`
- support `text-to-image` va `image-to-image`
- request dung `input_images[]` thay vi tai su dung `references_image[]`
- response them `output.images[]`
- khong luu full base64 vao DB logs

Neu can giao nhanh, day la pham vi MVP hop ly nhat va it lam vo flow text generation hien tai.

## Ghi chu ve model names

Theo docs chinh thuc hien tai cua Google:

- `gemini-2.5-flash-image`
- `gemini-3-pro-image-preview`

Tai lieu marketing goi chung capability nay la:

- `Nano Banana`
- `Nano Banana Pro`

Day la suy ra tu docs chinh thuc cua Google AI Developers, va can uu tien dung model code o tren trong backend/API docs.
