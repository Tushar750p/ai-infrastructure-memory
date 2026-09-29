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


## Recommended low-cost public deployment

For the AIME MVP/demo, AWS is optional. The application can run with:

- **Supabase** for managed PostgreSQL
- **Render** for the FastAPI backend (the repository includes `render.yaml`)
- **Vercel** for the Next.js frontend
- **Upstash Redis** for Redis-backed sessions, rate limiting, and cache

### Supabase

Create a Supabase project and copy its PostgreSQL connection string into Render as `DATABASE_URL`. Run the existing Alembic migrations from the backend against that database before using the application.

### Upstash

Create a Redis database and copy its TLS connection URL into Render as `REDIS_URL`. The application already uses Redis for authentication rate limiting and session/cache functionality.

### Render

Connect the GitHub repository to Render as a Blueprint. The repository's `render.yaml` creates the FastAPI service. Set the secret environment variables shown in that file. Generate `CREDENTIALS_ENCRYPTION_KEY` with the Fernet command above.

Set `CORS_ALLOWED_ORIGINS` to the final Vercel URL. Set `PASSWORD_RESET_URL` and `EMAIL_VERIFICATION_URL` to the corresponding Vercel routes when email verification/reset emails are configured.

After the backend is live, note its Render URL, for example `https://aime-api.onrender.com`.

### Vercel

Import the same GitHub repository into Vercel and set the **Root Directory** to `frontend`. Add:

```text
AIME_BACKEND_URL=https://YOUR-RENDER-SERVICE.onrender.com
```

The Next.js configuration proxies `/api/*` and `/health/*` through Vercel to Render. This keeps the browser-facing API on the same origin as the frontend and preserves the existing session-cookie authentication flow.

The current frontend can therefore use its existing default:

```text
NEXT_PUBLIC_API_URL=
```

After Vercel gives you the final URL, update Render's `CORS_ALLOWED_ORIGINS` to that exact origin and redeploy the backend.

### Database migration

Run the existing Alembic migration once against Supabase:

```bash
cd backend
DATABASE_URL='YOUR_SUPABASE_POSTGRES_URL' alembic upgrade head
```

Do not commit the connection string or any other secret.

### AWS remains optional

AIME's AWS connector code is still included. A customer can later connect an AWS account through the AIME UI. AWS credentials are encrypted by the application; the AIME hosting stack itself does not require an AWS account.

The existing `infrastructure/terraform/prod` and AWS deployment workflow are retained as an optional enterprise deployment path. The AWS workflow is manual-only so a missing AWS OIDC secret does not break normal GitHub pushes for the Supabase/Vercel/Render deployment path.
