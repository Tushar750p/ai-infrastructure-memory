# Production Deployment

AIME is deployed as a small container stack:

- Nginx: public HTTP entry point / reverse proxy
- Next.js: frontend
- FastAPI/Uvicorn: backend
- PostgreSQL 16: persistent application database
- Redis 7: sessions/rate limiting/cache
- Alembic: one-shot database migration service

## Required secrets

Copy `docker-compose.prod.env.example` to `.env` and replace every placeholder.

Generate the Fernet encryption key with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Never commit `.env` or real credentials.

## First deployment

```bash
docker compose --env-file .env -f docker-compose.prod.yml build
docker compose --env-file .env -f docker-compose.prod.yml up -d postgres redis
docker compose --env-file .env -f docker-compose.prod.yml run --rm migrate
docker compose --env-file .env -f docker-compose.prod.yml up -d backend frontend nginx
```

The migration is deliberately a separate one-shot step so multiple backend replicas do not race to run schema migrations.

## Health checks

- `GET /health/live` confirms the process is running.
- `GET /health/ready` confirms PostgreSQL connectivity.

## HTTPS

The included Nginx config is the internal reverse proxy and listens on port 80. For public production traffic, terminate TLS at a cloud load balancer, managed ingress, or a host-level reverse proxy and forward traffic to Nginx. Set:

```env
AUTH_COOKIE_SECURE=true
CORS_ALLOWED_ORIGINS=https://your-real-domain.example
PASSWORD_RESET_URL=https://your-real-domain.example/reset-password
EMAIL_VERIFICATION_URL=https://your-real-domain.example/verify-email
```

Do not expose PostgreSQL or Redis directly to the internet.

## Scaling

Run database migrations once per release before rolling out new backend replicas. PostgreSQL should use managed backups in a real production environment. Redis can be replaced by a managed Redis-compatible service by changing `REDIS_URL`.

The current FastAPI process also starts the CloudTrail collector worker. If the backend is scaled horizontally, move collection into a dedicated worker service or enforce a distributed single-worker lease to avoid duplicate collection.


## AWS ECS/Fargate production

The repository also contains an AWS production stack under `infrastructure/terraform/prod`.

See `infrastructure/terraform/prod/README.md` for the GitHub OIDC bootstrap, required GitHub secrets, and first deployment procedure.

Production runtime secrets are injected from AWS Secrets Manager. The RDS master password is managed by Amazon RDS rather than stored in GitHub or Terraform variables.
