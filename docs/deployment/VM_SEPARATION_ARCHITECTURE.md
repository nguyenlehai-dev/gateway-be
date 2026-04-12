# Gateway VM Separation Architecture

## Muc tieu

Tach rieng `DEV` va `PROD` thanh 2 Ubuntu VM doc lap:

- `VM dev` chi chay `staging/dev`
- `VM pro` chi chay `production`
- public ingress va reverse proxy tap trung tai `VM pro`

## Hien trang sau khi tach

### VM dev

Hostname: `dev`
IP noi bo: `192.168.100.67`

Chay:

- `gateway-staging-gateway-be-1`
- `gateway-staging-gateway-job-worker-1`
- `project_dev_web`
- `nginx_proxy_manager`

Ports:

- `18082` -> Gateway staging backend
- `8081` -> Gateway staging frontend
- `80/443` -> reverse proxy local/tam thoi

Cloudflared:

- Da tat tren `VM dev`

### VM pro

Hostname: `pro`
IP noi bo: `192.168.100.68`

Chay:

- `gateway-prod-gateway-be-1`
- `gateway-prod-gateway-job-worker-1`
- `project_prod_web`
- `nginx_proxy_manager`

Ports:

- `18081` -> Gateway production backend
- `8082` -> Gateway production frontend
- `80/443` -> reverse proxy public

Cloudflared:

- Chay bang `systemd`
- Service: `cloudflared.service`

## Domain routing

Public domains:

- `gateway.plxeditor.com`
- `testgateway.plxeditor.com`

Current ingress model:

- Cloudflare/Cloudflared vao `VM pro`
- Reverse proxy tren `VM pro` route:
  - `gateway.plxeditor.com` -> `192.168.100.68:8082`
  - `testgateway.plxeditor.com` -> `192.168.100.67:8081`

## Data separation

### DEV

- App path: `/home/vpsroot/apps/gateway-staging`
- DB staging: `/home/vpsroot/apps/gateway-staging/be/deploy/staging/gateway-staging.db`
- Env staging: `/home/vpsroot/apps/gateway-staging/be/deploy/staging/.env`

### PROD

- App path: `/home/vpsroot/apps/gateway-prod`
- DB prod: `/home/vpsroot/apps/gateway-prod/be/deploy/prod/gateway-prod.db`
- Env prod: `/home/vpsroot/apps/gateway-prod/be/deploy/prod/.env`
- Backup dir: `/home/vpsroot/backups/gateway-prod`

## Backup prod

Script:

- `/home/vpsroot/apps/gateway-prod/be/scripts/backup-prod-db.sh`

Cron tren `VM pro`:

```cron
0 2 * * * /home/vpsroot/apps/gateway-prod/be/scripts/backup-prod-db.sh >/home/vpsroot/logs/backup-prod-db.log 2>&1
```

## Restore prod

Script:

- `/home/vpsroot/apps/gateway-prod/be/scripts/restore-prod-db.sh`

Nguyen tac:

- stop backend/worker prod
- backup nhanh ban hien tai truoc khi restore
- copy DB backup vao vi tri runtime
- xoa file `-wal/-shm`
- start lai backend/worker prod

## Van hanh chuan

1. Code va test tren `VM dev`
2. Verify `testgateway.plxeditor.com`
3. Promote code sang `VM pro`
4. Verify `gateway.plxeditor.com`
5. Backup dinh ky tren `VM pro`

## Health checks nhanh

### VM dev

```bash
docker ps
curl -s http://127.0.0.1:18082/up
curl -I -s https://testgateway.plxeditor.com/
```

### VM pro

```bash
docker ps
curl -s http://127.0.0.1:18081/up
curl -I -s https://gateway.plxeditor.com/
systemctl status cloudflared --no-pager
```
