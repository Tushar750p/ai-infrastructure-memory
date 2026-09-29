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

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

For containerized deployment and production configuration, see [DEPLOYMENT.md](./DEPLOYMENT.md).

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
