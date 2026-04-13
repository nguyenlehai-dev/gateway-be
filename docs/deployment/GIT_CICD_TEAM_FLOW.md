# Git + CI/CD Team Flow

## Muc tieu

Khong SSH tay len server de deploy moi lan. Team lam viec thong qua Git:

1. Tao branch feature
2. Mo Pull Request
3. Merge vao `staging`
4. GitHub Actions tu deploy len `VM dev`
5. Sau khi test on dinh, promote sang `prod`
6. GitHub Actions tu deploy len `VM pro`

## Branches

## Git remotes su dung

- Backend repo: `https://github.com/nguyenlehai-dev/video-processing-service`
- Frontend repo: `https://github.com/nguyenlehai-dev/video-processing-service-fe.git`

### Backend

- `staging` -> auto deploy `VM dev`
- `prod` -> auto deploy `VM pro`

### Frontend

- `staging` -> auto deploy `VM dev`
- `prod` -> auto deploy `VM pro`

## Workflow de xuat cho member

1. Tao branch moi tu `staging`
2. Push code va mo PR vao `staging`
3. Sau khi review xong, merge PR
4. GitHub Actions deploy len `test.plxeditor.com`
5. QA/UAT xac nhan
6. Promote `staging` -> `prod`
7. GitHub Actions deploy len `plxeditor.com`

## Runner model

- Khong can repo secrets cho deploy nua
- Moi repo dung self-hosted runner tren tung VM
- Label dang dung:
  - `gateway-dev` cho branch `staging`
  - `gateway-prod` cho branch `prod`

### Runner services hien tai

- `VM dev`
  - `actions.runner.nguyenlehai-dev-video-processing-service.video-processing-service-dev.service`
  - `actions.runner.nguyenlehai-dev-video-processing-service-fe.video-processing-service-fe-dev.service`
- `VM pro`
  - `actions.runner.nguyenlehai-dev-video-processing-service.video-processing-service-prod.service`
  - `actions.runner.nguyenlehai-dev-video-processing-service-fe.video-processing-service-fe-prod.service`

## Gia tri path hien tai

### VM dev

- Backend: `/home/vpsroot/apps/gateway-staging/be`
- Frontend: `/home/vpsroot/apps/gateway-staging/fe`

### VM pro

- Backend: `/home/vpsroot/apps/gateway-prod/be`
- Frontend: `/home/vpsroot/apps/gateway-prod/fe`

## Luu y quan trong

- Frontend `prod` branch da duoc promote day du tu `staging`, co the build/deploy tu dong
- Workflow deploy dung `git reset --hard origin/<branch>` tren repo server, vi day la working tree chuyen dung cho deploy
- Frontend co fallback build bang Docker `node:20-bookworm` neu host khong co `npm`

## Deploy scripts

- Backend: `scripts/deploy-compose.sh`
- Frontend: `scripts/deploy-static.sh`

## Khuyen nghi team

- Bat branch protection cho `staging` va `prod`
- Chi merge qua PR
- Bat required review
- Bat required checks neu can them test/lint ve sau
