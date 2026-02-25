# FusionEMS Quantum — Founder Command Platform (Build Directive)

This repository includes:
- Backend: FastAPI (existing FusionEMS-Core) extended with Founder Command endpoints, Systems Registry, and Realtime SSE.
- Frontend: Next.js Founder Command Center + platform landing + system gating UI.
- Infra: CloudFormation nested-stack skeleton (requires completion for full ECS/RDS/Redis/CloudFront production deploy).

## Local Run (Zero-error dev)
### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .
uvicorn core_app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
cp .env.example .env.local
# edit BACKEND_URL if needed
npm install
npm run dev
```

Open http://localhost:3000

## Founder Command Center
- Visit `/founder`
- Save keys + founder email
- Generate Word/Excel/Invoice files

## Realtime
- SSE endpoint: `/api/v1/realtime/sse`
- Events are PHI-safe (IDs only). Clients must fetch details via REST.

## Certification Readiness
- NEMSIS/NERIS readiness endpoints are scaffolded for integration:
  - Add NEMSIS v3.5.1 C&S test cases under `backend/compliance/nemsis/v3.5.1/cs/`
  - Implement export/validate pipelines and produce deterministic artifacts for CI.

## Telnyx/AI
- Telnyx, AI voice/phone tree, fax, Stripe, LOB are represented in Founder settings.
- Production integrations should be implemented behind service interfaces with audited actions and explicit user confirmation.

## CloudFormation
Templates under `infra/cloudformation/` are syntactically valid skeletons. For production, extend:
- network.yml: subnets, IGW, NAT, route tables, ALB SGs
- data.yml: RDS Postgres, ElastiCache Redis, KMS, S3 docs
- compute.yml: ECS cluster/services, ALB, autoscaling, health checks
- edge.yml: CloudFront + WAF + ACM (us-east-1)

