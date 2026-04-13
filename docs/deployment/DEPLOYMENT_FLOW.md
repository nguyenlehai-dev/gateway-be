# Video Processing Service BE Deployment Flow

## Domain Mapping

- `staging` branch -> `https://test.plxeditor.com/api/`
- `prod` branch -> `https://plxeditor.com/api/`

Production API entrypoint from frontend:

- `https://plxeditor.com/api/...`

## Source Model

- Chi co **1 source goc** de phat trien backend:
  - `/home/vpsroot/projects/backend/video-processing-service`
- Khong deploy bang cach copy tay file le len server.
- Chi promote release qua branch:
  - `main` cho phat trien
  - `staging` cho test
  - `prod` cho production

## Release Flow

1. Develop trong source repo `/home/vpsroot/projects/backend/video-processing-service`
2. Commit va push branch lam viec
3. Promote commit can test len `staging`
4. Deploy backend tu branch `staging`
5. Validate API qua `https://test.plxeditor.com/api/...`
6. Promote commit da validate len `prod`
7. Deploy backend tu branch `prod`
8. Smoke test qua `https://plxeditor.com/api/...`

Short form:

- `source -> staging -> deploy test -> validate -> promote -> prod -> deploy prod`

## SOP

1. Sua code trong `/home/vpsroot/projects/backend/video-processing-service`
2. Kiem tra `git status`
3. Chay test/build local theo stack backend thuc te cua repo
4. Commit thay doi
5. Push branch hien tai
6. Promote len `staging`
7. Checkout `staging` tren moi truong deploy va pull ban moi nhat
8. Rebuild/restart backend theo stack thuc te
9. QA tren `https://test.plxeditor.com/api/...`
10. Promote `staging -> prod`
11. Checkout `prod` tren moi truong deploy va pull ban moi nhat
12. Rebuild/restart backend production
13. Smoke test `https://plxeditor.com/api/...`

Lenh thuong dung:

```bash
cd /home/vpsroot/projects/backend/video-processing-service
git status
git add .
git commit -m "feat: mo ta thay doi"
git push origin HEAD
./scripts/promote-branch.sh staging prod
```

## Runtime Notes

- Repo hien tai moi duoc bootstrap branch flow, chua co stack runtime co dinh.
- Khi backend duoc scaffold day du, can bo sung them:
  - tai lieu deploy runtime
  - script deploy staging/prod
  - file env mau
  - healthcheck endpoint
- Khuyen nghi quy uoc API:
  - test: `https://test.plxeditor.com/api/`
  - prod: `https://plxeditor.com/api/`

## Verify

Sau khi backend co runtime that su, it nhat can verify:

```bash
curl -I https://test.plxeditor.com/api/
curl -I https://plxeditor.com/api/
```

## Rules

- Khong deploy production truc tiep tu `main`
- Chi promote release `staging -> prod` bang git history
- Khong copy tay source giua test va production
- Khi backend co database migration, chi chay migration o moi truong duoc chi dinh ro rang
