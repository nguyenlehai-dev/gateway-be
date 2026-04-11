# Gateway Backend Deploy

## Domain mapping

- `staging` -> `https://testgateway.plxeditor.com/api/`
- `prod` -> `https://gateway.plxeditor.com/api/`

## Runtime

- Container port: `8000`
- Suggested host port staging: `8080`
- Suggested host port prod: `8081`
- Co them worker service `gateway-job-worker` de quet job async va retry den han

## Local compose deploy

```bash
cd /home/vpsroot/projects/backend/gateway-be
cp deploy/staging/.env.example deploy/staging/.env
./scripts/deploy-compose.sh staging
```

Hoac production:

```bash
cd /home/vpsroot/projects/backend/gateway-be
cp deploy/prod/.env.example deploy/prod/.env
./scripts/deploy-compose.sh prod
```

## Verify

```bash
curl http://127.0.0.1:8080/up
curl http://127.0.0.1:8081/up
```

Kiem tra worker:

```bash
docker compose --env-file deploy/staging/.env -f docker-compose.yml -p gateway-staging ps
docker logs gateway-staging-gateway-job-worker-1 --tail 50
```
