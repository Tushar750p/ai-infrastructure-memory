# AI Infrastructure Memory (AIME)

> **AI that remembers every cloud resource, change, incident, and verified fix.**

AI Infrastructure Memory (AIME) is an infrastructure intelligence and SRE memory platform designed to help engineering teams understand **what changed, what broke, why it broke, whether it has happened before, and what fixed it**.

AIME brings infrastructure inventory, change intelligence, incident memory, infrastructure relationships, and operational knowledge into one system.

## What AIME Does

- **Infrastructure Memory** — remembers infrastructure state, changes, incidents, and resolutions.
- **Change Intelligence** — correlates infrastructure changes with operational impact.
- **Incident Intelligence** — builds incident timelines and surfaces relevant signals.
- **Verified Fix Memory** — stores previously verified fixes for future incidents.
- **Infrastructure Graph** — maps relationships between resources and services.
- **AI SRE Copilot** — provides a natural-language interface for infrastructure knowledge.
- **AWS Intelligence** — supports AWS inventory, CloudTrail events, and CloudWatch telemetry.
- **Operational Console** — provides monitoring, incident management, search, reports, and infrastructure views.

## The AIME Memory Loop

```text
What changed?
      ↓
What broke?
      ↓
Why did it break?
      ↓
Have we seen this before?
      ↓
What fixed it?
      ↓
Remember the verified solution
```

The goal is to turn operational history into reusable engineering knowledge.

## Architecture

The repository contains the production-oriented AIME platform plus the merged AIME Console codebase:

```text
ai-infrastructure-memory/
├── backend/          # FastAPI production backend
├── frontend/         # Next.js production frontend
├── infrastructure/   # AWS + Terraform infrastructure
├── console/          # Merged AIME Console capabilities
├── nginx/             # Reverse proxy configuration
├── docs/              # Product and technical documentation
├── .github/           # CI/CD workflows
└── DEPLOYMENT.md      # Deployment documentation
```

## Technology

**Backend**
- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Alembic

**Frontend**
- Next.js
- React
- TypeScript

**Infrastructure**
- AWS
- ECS/Fargate
- RDS PostgreSQL
- ElastiCache Redis
- ECR
- ALB
- CloudWatch
- CloudTrail
- Terraform

**Operations**
- Docker
- Nginx
- GitHub Actions
- AWS OIDC deployment

## Repository Status

This is the **master repository** for AI Infrastructure Memory.

The previous AIME Console codebase has been consolidated under `/console` so the project can evolve as a single platform instead of maintaining two separate repositories.

## Demo

AIME includes a buyer-facing interactive demo in the production frontend:

- Product overview: `/demo`
- Interactive buyer demo: `/demo/experience`
- Live console: `/`

The interactive demo uses a clearly labeled simulated environment for product demonstration.

## Local Development

The lightweight root `docker-compose.yml` starts **only PostgreSQL and Redis**. Run the Python API and Next.js frontend directly on the host to keep local resource usage lower. Do not use `docker-compose.prod.yml` for everyday laptop development.

### Requirements

- Docker Desktop with the WSL 2 backend (Windows) or Docker Engine (Linux)
- Python 3.12 recommended
- Node.js 22 LTS (Node.js 20.9 or newer is required by the installed Next.js version)
- Git

### 1. Start the local dependencies

From the repository root:

```bash
docker compose up -d
docker compose ps
```

PostgreSQL is available on `localhost:5432`; Redis is available on `localhost:6379`. The database is persisted in the `aime_pgdata` Docker volume. The default database password is for local development only. Set `AIME_DB_PASSWORD` before starting Compose if you want a different local password.

### 2. Configure the backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

- Linux / WSL: `source .venv/bin/activate`
- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`

Then install dependencies and create the local environment file:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

On Windows PowerShell, use `Copy-Item .env.example .env` instead of `cp`. Put the generated Fernet key into `CREDENTIALS_ENCRYPTION_KEY` in `.env`. Set these local values:

```dotenv
DATABASE_URL=postgresql+psycopg2://postgres:aime_local_dev_only@localhost:5432/infra_memory
REDIS_URL=redis://localhost:6379/0
CORS_ALLOWED_ORIGINS=http://localhost:3000
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_NAME=aime_session
```

If you changed `AIME_DB_PASSWORD` for Compose, use the same password in `DATABASE_URL`. Keep `.env` private; never commit it.

Run database migrations and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start the frontend

In a second terminal:

```bash
cd frontend
npm ci
```

Linux / WSL:

```bash
AIME_BACKEND_URL=http://localhost:8000 npm run dev
```

Windows PowerShell:

```powershell
$env:AIME_BACKEND_URL="http://localhost:8000"
npm run dev
```

Open:

- Frontend: http://localhost:3000
- API documentation: http://localhost:8000/docs
- Liveness check: http://localhost:8000/health/live
- Database readiness check: http://localhost:8000/health/ready

The local SMTP values in `.env.example` are placeholders. Email verification and password-reset delivery require a real SMTP provider; they are not configured by this local setup.

For containerized production deployment and production configuration, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## Security

AIME is designed with production security in mind, including:

- Secure password hashing
- HttpOnly authentication cookies
- Session-based authentication
- Organization-level RBAC
- Password reset and email verification flows
- Redis-backed authentication rate limiting
- AWS IAM task roles
- GitHub Actions → AWS OIDC authentication
- Private RDS and Redis deployment in production infrastructure

Never commit production secrets, credentials, private keys, or `.env` files.

## Roadmap

- Deeper AWS resource coverage
- Expanded Kubernetes and Docker discovery
- More advanced change-to-incident correlation
- Multi-cloud infrastructure memory
- Richer infrastructure knowledge graph
- More automated remediation workflows
- Enterprise integrations and governance
- Production-grade AI reasoning over infrastructure history

## Vision

**Infrastructure should remember.**

AIME is being built to give SRE, DevOps, cloud, and platform teams a persistent operational memory layer — so every incident can make the next incident easier to understand and resolve.

---

**AI Infrastructure Memory (AIME)**  
*SRE Memory Engine for modern cloud infrastructure.*
