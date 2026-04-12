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
4. GitHub Actions deploy len `testgateway`
5. QA/UAT xac nhan
6. Promote `staging` -> `prod`
7. GitHub Actions deploy len `gateway`

## GitHub Secrets can co

### Backend repo secrets

- `DEV_SSH_HOST`
- `DEV_SSH_USER`
- `DEV_SSH_KEY`
- `DEV_BE_PATH`
- `PROD_SSH_HOST`
- `PROD_SSH_USER`
- `PROD_SSH_KEY`
- `PROD_BE_PATH`

### Frontend repo secrets

- `DEV_SSH_HOST`
- `DEV_SSH_USER`
- `DEV_SSH_KEY`
- `DEV_FE_PATH`
- `PROD_SSH_HOST`
- `PROD_SSH_USER`
- `PROD_SSH_KEY`
- `PROD_FE_PATH`

## Gia tri path hien tai

### VM dev

- Backend: `/home/vpsroot/apps/gateway-staging/be`
- Frontend: `/home/vpsroot/apps/gateway-staging/fe`

### VM pro

- Backend: `/home/vpsroot/apps/gateway-prod/be`
- Frontend: `/home/vpsroot/apps/gateway-prod/fe`

## Luu y quan trong

Frontend repo `prod` branch hien tai can duoc dong bo source day du voi `staging`/`main` truoc khi bat auto deploy prod. Neu branch `prod` chi co file toi thieu thi workflow prod se khong build duoc.

## Deploy scripts

- Backend: `scripts/deploy-compose.sh`
- Frontend: `scripts/deploy-static.sh`

## Khuyen nghi team

- Bat branch protection cho `staging` va `prod`
- Chi merge qua PR
- Bat required review
- Bat required checks neu can them test/lint ve sau
