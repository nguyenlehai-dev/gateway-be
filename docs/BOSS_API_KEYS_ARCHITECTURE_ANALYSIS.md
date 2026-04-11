# Boss API Keys Architecture Analysis

## Muc tieu

Tai lieu nay phan tich bo sung moi cua sep cho du an Gateway.

Huong moi can dat:

- giu `Vendor`
- giu `Pool`
- bo sung lop `API Keys` rieng thuoc `Pool`
- giu `Gateway API Key` la lop khac, dung cho client goi vao Gateway

Noi ngan gon:

- `API Keys` = provider keys noi bo
- `Gateway API Key` = client key de goi Gateway

Hai loai key nay khong duoc tron vao nhau.

## Van de cua co che hien tai

He thong hien tai dang co cac diem gay roi:

1. `Pool` vua chua metadata vua chua provider key
2. `Gateway API Key` dang xuat hien trong runtime flow qua som
3. user phai nghi qua nhieu thu:
   - provider key
   - project number
   - gateway key
   - verify
   - generate
4. cau truc hien tai chua phan tach ro:
   - key noi bo cua provider
   - key public cua Gateway

He qua:

- khach thay flow phuc tap
- kho giai thich nghiep vu
- kho mo rong rotation va best-key selection
- sau nay muon them nhieu provider key cho cung 1 pool se vuong

## Huong kien truc sep chot

Sep dang chot lai domain nhu sau:

1. `Vendor`
2. `Pool`
3. `API Keys`
4. `Gateway API Key`

Vi du:

- Vendor: `Google`
- Pool: `gemini-api`
- API Keys: danh sach Google AI Studio keys cua pool do
- Gateway API Key: key prefix `gw_...` de client goi Gateway

## Y nghia tung lop

### 1. Vendor

Dai dien cho nha cung cap AI.

Vi du:

- `google`
- sau nay co the them `openai`, `anthropic`, `xai`

### 2. Pool

Dai dien cho 1 nhom cau hinh va chien luoc goi provider.

Vi du:

- `gemini-api`

Pool khong nen bi coi la noi chua dung 1 provider key duy nhat nua.
Pool nen la "container" chua nhieu `API Keys`.

### 3. API Keys

Day la danh sach provider keys noi bo thuoc 1 pool.

Moi record can chua toi thieu:

- `id`
- `pool_id`
- `name`
- `provider_api_key`
- `project_number`
- `status`

Nen bo sung them:

- `priority`
- `weight`
- `last_used_at`
- `last_error_at`
- `fail_count`
- `success_count`
- `cooldown_until`

Day la lop phuc vu:

- rotation
- round robin
- failover
- best key selection
- throttle tung key

### 4. Gateway API Key

Day la client key de goi vao Gateway.

Tinh chat:

- khac voi provider key
- prefix `gw_...`
- cap cho client hoac ung dung goi Gateway
- co scope gan voi `Pool` hoac nhieu `Pool`

Client chi nen thay va dung loai key nay.

## Luong xu ly moi

Luong mong muon theo y sep:

1. Admin tao `Vendor`
2. Admin tao `Pool`
3. Admin them nhieu `API Keys` vao pool
4. Admin cap `Gateway API Key` cho client
5. Client goi Gateway bang `Gateway API Key`
6. Gateway resolve duoc `Pool`
7. Gateway chon 1 `API Key` phu hop trong danh sach cua pool
8. Gateway lay:
   - `provider_api_key`
   - `project_number`
9. Gateway goi `Google GenAI text generation`
10. Gateway tra response cho client

Client khong can:

- nhap `provider api key`
- nhap `project number`
- hieu rotation
- hieu provider key nao dang duoc dung

## Thay doi tu duy nghiep vu

Can doi cach hieu tu:

- "Pool luu 1 key"

sang:

- "Pool quan ly nhieu provider keys"

Va tu:

- "user verify/generate key trong runtime"

sang:

- "client duoc cap Gateway API Key de dung"

Noi cach khac:

- provider key la internal configuration
- gateway key la external access credential

## Data model de xuat

### Bang `vendors`

Giu nguyen.

### Bang `pools`

Nen giu metadata chung:

- `vendor_id`
- `name`
- `slug`
- `code`
- `description`
- `status`
- `config_json`

`config_json` tu nay chi nen giu:

- `timeout_seconds`
- `provider`
- `selection_strategy`
- `default_model`
- `rate_limit`

Khong nen tiep tuc nhet `provider_api_key` vao `config_json` theo kieu 1 key duy nhat.

### Bang moi `pool_api_keys`

De xuat:

```text
id
pool_id
name
provider_api_key_hash
provider_api_key_masked
project_number
status
priority
weight
last_used_at
last_error_at
fail_count
success_count
cooldown_until
created_at
updated_at
```

Luu y:

- khong nen luu plain `provider_api_key` neu co the tranh duoc
- neu can dung key that de goi provider, can can nhac:
  - ma hoa reversible
  - hoac su dung secret store
- neu chua co secret manager, co the tam luu encrypted value trong DB

### Bang `gateway_api_keys`

Bang nay da co mot phan, nhung can dinh nghia lai ro scope.

De xuat:

```text
id
name
user_id
pool_id
key_hash
key_masked
status
last_used_at
expires_at
created_at
updated_at
```

Bang nay la public access key cua Gateway, khong lien quan truc tiep toi provider key.

## Selection strategy cho API Keys

Gateway khi nhan request can chon 1 provider key trong pool.

Thu tu de xuat:

### Phase dau

- chon key `active` dau tien theo `priority asc`, `id asc`

### Phase tiep theo

- `round robin`
- `weighted round robin`
- bo qua key dang cooldown
- uu tien key co `fail_count` thap

### Rule co ban

Khong duoc chon key:

- `inactive`
- dang cooldown
- fail lien tiep qua nguong

Neu key dang duoc chon bi loi provider:

- tang `fail_count`
- cap nhat `last_error_at`
- dua vao cooldown neu can
- thu key tiep theo trong pool neu chinh sach cho phep

## API contract de xuat

### CRUD Vendor

Giu nguyen.

### CRUD Pool

Can don gian lai:

- `Pool` khong con bat buoc nhap provider key o muc metadata chinh
- metadata chung cua pool nen nhe hon

### CRUD API Keys moi

Can bo sung:

- `GET /api/v1/pools/{pool_id}/api-keys`
- `POST /api/v1/pools/{pool_id}/api-keys`
- `PATCH /api/v1/pools/{pool_id}/api-keys/{id}`
- `DELETE /api/v1/pools/{pool_id}/api-keys/{id}`

Hoac co the tach:

- `GET /api/v1/api-keys`
- `POST /api/v1/api-keys`

Nhung ve mat nghiep vu, nested duoi `Pool` de hieu hon.

### Gateway API Keys

Can giu nhung can giai thich ro:

- day la key cap cho client
- day khong phai provider key

### Execute API

Request can don gian:

```json
{
  "model": "gemini-3-flash-preview",
  "prompt": "Hello",
  "references_image": [],
  "references_video": [],
  "references_audios": []
}
```

Authentication:

- qua header `X-Gateway-Api-Key: gw_...`

Backend tu lam:

- resolve `Gateway API Key`
- tim `Pool`
- chon `API Key` provider tu pool
- lay `project_number`
- goi provider

Client khong phai gui:

- `api_key`
- `project_number`

## Tac dong den backend

Backend can refactor cac phan sau:

1. model moi `pool_api_keys`
2. migration DB
3. CRUD endpoint cho `API Keys`
4. service chon key trong pool
5. `gateway_executor` phai doi:
   - khong lay provider key chinh tu `pool.config_json`
   - lay tu `pool_api_keys`
6. request log nen luu them:
   - `selected_api_key_id`
   - `selected_api_key_name`

## Tac dong den frontend

Frontend can doi:

1. menu moi `API Keys`
2. trong man `Pool`, bo cam giac "nhap 1 key duy nhat"
3. `Playground` khong hien:
   - provider api key
   - project number
4. `System Auth` neu con giu lai thi chi dung cho `Gateway API Key`

Muc tieu UX:

- admin quan ly provider keys o man hinh rieng
- client chi thay `Gateway API Key`
- runtime flow ngan hon

## Migration strategy

Can co giai doan chuyen doi de khong vo he thong hien tai.

### Buoc 1

Them bang `pool_api_keys`.

### Buoc 2

Viet script migrate du lieu cu:

- doc `provider_api_key`
- doc `provider_project_number`
- doc `default_model`
tu `pool.config_json`

Tao 1 record `pool_api_keys` dau tien cho moi pool neu co cau hinh cu.

### Buoc 3

Cap nhat `gateway_executor` uu tien `pool_api_keys`.

### Buoc 4

Sau khi on dinh, bo dan phu thuoc vao `provider_api_key` trong `config_json`.

## Rui ro can luu y

1. Secret management

- neu luu provider key dang plain text thi rui ro cao
- can co chien luoc hash/encrypt ro rang

2. Rotation logic

- neu lam qua som se tang do phuc tap
- phase dau nen de rule chon key don gian

3. Backward compatibility

- he thong hien tai dang dung `pool.config_json`
- can migration nhe de tranh vo flow dang chay

4. Scope cua Gateway API Key

- can chot ro key gan voi:
  - 1 pool
  - hay nhieu pools

Hien tai de don gian nen giu:

- 1 `Gateway API Key` thuoc 1 `Pool`

## Open questions can chot voi sep

1. `Gateway API Key` thuoc 1 pool hay co the thuoc nhieu pools?
2. `API Keys` provider co can `weight/priority` ngay phase dau khong?
3. co can `auto retry` sang key tiep theo khi key dau tien loi khong?
4. provider key co bat buoc ma hoa reversible trong DB ngay phase dau khong?
5. ai duoc tao `Gateway API Key`:
   - admin
   - customer
   - ca hai?

## Ket luan

Bo sung cua sep la dung huong va hop ly hon co che hien tai.

Huong nen theo la:

- `Vendor`
- `Pool`
- `API Keys` thuoc `Pool`
- `Gateway API Key` la lop rieng

Day la mot refactor kien truc nghiep vu, khong phai chi la chinh UI.

Neu lam dung huong nay:

- flow se de giai thich hon
- khach de dung hon
- backend san sang cho rotation/failover
- phan tach ro internal provider keys va external gateway key

## De xuat phase moi

1. Phase A: Bo sung bang `pool_api_keys` va CRUD backend
2. Phase B: Them menu `API Keys` tren frontend
3. Phase C: Refactor `gateway_executor` sang selection theo pool
4. Phase D: Migrate du lieu cu tu `pool.config_json`
5. Phase E: Don gian hoa `Playground` va `System Auth`

