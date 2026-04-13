# Video Processing Service BE Branching Setup

Muc tieu la chuan hoa release flow cho repo backend:

- `main`: branch phat trien
- `staging`: branch test cho `test.plxeditor.com`
- `prod`: branch production cho `plxeditor.com`

## Cau truc thu muc

- Source repo:
  - `/home/vpsroot/projects/backend/video-processing-service`

## Thiet lap branch

```bash
cd /home/vpsroot/projects/backend/video-processing-service
git checkout main
git pull --ff-only origin main
git checkout -b staging
git push -u origin staging
git checkout main
git checkout -b prod
git push -u origin prod
git checkout main
```

## Promote release

```bash
cd /home/vpsroot/projects/backend/video-processing-service
./scripts/promote-branch.sh staging prod
```

## Domain mapping

- `staging` -> `https://test.plxeditor.com/api/`
- `prod` -> `https://plxeditor.com/api/`
