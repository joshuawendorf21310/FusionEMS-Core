# FusionEMS Quantum — Core Platform

**Enterprise-grade EMS operations platform** built on FastAPI, Next.js, and Terraform-managed AWS infrastructure.

## Architecture

| Layer | Stack |
|-------|-------|
| **Frontend** | Next.js 14 · React 18 · Tailwind CSS · Radix UI |
| **Backend** | FastAPI · SQLAlchemy 2 · PostgreSQL (PostGIS) · Redis |
| **Infrastructure** | Terraform (multi-env) · ECS Fargate · CloudFront · WAF |
| **Observability** | OpenTelemetry · Prometheus · Grafana |
| **Security** | OIDC · OPA policies · Checkov · Cognito |

## Quick Start (Local Development)

```bash
docker compose up -d
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Grafana**: http://localhost:3001

## Project Structure

```
backend/       FastAPI application and core business logic
frontend/      Next.js frontend application
infra/         Terraform modules and environment configs
  terraform/
    modules/   Reusable infrastructure modules
    environments/  dev · staging · prod · dr
opa/           Open Policy Agent policies
otel/          OpenTelemetry collector config
prometheus/    Prometheus scrape configuration
grafana/       Grafana dashboard provisioning
schemas/       Data schemas and validation
scripts/       Utility and deployment scripts
```

## Deployment

See [`README_DEPLOY.md`](README_DEPLOY.md) for the full deployment runbook.
