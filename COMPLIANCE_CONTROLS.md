# Compliance Controls (Technical)

- Tenant isolation enforced from JWT-derived context.
- Audit entries store changed field names only; no PHI values.
- Mutation endpoints require optimistic concurrency version checks.
