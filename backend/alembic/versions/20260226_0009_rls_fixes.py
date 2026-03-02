"""Fix RLS: add policies for tenant_provisioning_events, tenant_subscriptions;
add system-tenant bypass policy for lob_webhook_receipts and stripe_webhook_receipts

Revision ID: 20260226_0009
Revises: 20260226_0008
Create Date: 2026-02-26
"""

from __future__ import annotations

from alembic import op

revision = "20260226_0009"
down_revision = "20260226_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # tenant_provisioning_events — missed from RLS loop in 0008
    # This is an append-only audit log; readers are scoped by tenant,
    # but writes are done by internal service accounts (no RLS bypass
    # needed for writes since service accounts use SECURITY DEFINER procs
    # or superuser roles). A standard read policy is sufficient.
    # ------------------------------------------------------------------
    op.execute('ALTER TABLE "tenant_provisioning_events" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        'CREATE POLICY "tenant_provisioning_events_tenant_isolation" '
        'ON "tenant_provisioning_events" '
        "USING (tenant_id = current_setting('app.tenant_id', true)::uuid);"
    )

    # ------------------------------------------------------------------
    # tenant_subscriptions — missed from RLS loop in 0008
    # One row per tenant; the unique tenant_id constraint already limits
    # cross-tenant access, but RLS enforces it at the query level too.
    # ------------------------------------------------------------------
    op.execute('ALTER TABLE "tenant_subscriptions" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        'CREATE POLICY "tenant_subscriptions_tenant_isolation" '
        'ON "tenant_subscriptions" '
        "USING (tenant_id = current_setting('app.tenant_id', true)::uuid);"
    )

    # ------------------------------------------------------------------
    # lob_webhook_receipts — add system-tenant INSERT bypass policy.
    #
    # Webhook receipts are written by the /webhooks/lob HTTP handler using
    # the system_tenant_id (a deterministic UUID configured per environment).
    # The existing tenant_isolation USING policy blocks reads from other
    # tenants but also blocks INSERT when app.tenant_id is not set (Lambda /
    # background workers do not set it). A separate WITH CHECK policy allows
    # INSERT/UPDATE from the system tenant UUID without needing to set
    # app.tenant_id in the Lambda execution context.
    #
    # The SYSTEM_TENANT_ID value must be set as a Postgres parameter:
    #   ALTER DATABASE fusionems SET app.system_tenant_id = '<uuid>';
    # or injected per-connection before the INSERT.
    # ------------------------------------------------------------------
    op.execute(
        "CREATE POLICY lob_webhook_receipts_system_write "
        "ON lob_webhook_receipts "
        "FOR INSERT "
        "WITH CHECK ("
        "  tenant_id = current_setting('app.system_tenant_id', true)::uuid"
        ");"
    )

    # ------------------------------------------------------------------
    # stripe_webhook_receipts — same system-tenant INSERT bypass policy.
    # stripe_webhook_receipts RLS was enabled in migration 0004 via
    # _create_tenant_json_table(); the bypass policy is added here.
    # ------------------------------------------------------------------
    op.execute(
        "CREATE POLICY stripe_webhook_receipts_system_write "
        "ON stripe_webhook_receipts "
        "FOR INSERT "
        "WITH CHECK ("
        "  tenant_id = current_setting('app.system_tenant_id', true)::uuid"
        ");"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS stripe_webhook_receipts_system_write ON stripe_webhook_receipts;"
    )
    op.execute("DROP POLICY IF EXISTS lob_webhook_receipts_system_write ON lob_webhook_receipts;")
    op.execute(
        'DROP POLICY IF EXISTS "tenant_subscriptions_tenant_isolation" ON "tenant_subscriptions";'
    )
    op.execute('ALTER TABLE "tenant_subscriptions" DISABLE ROW LEVEL SECURITY;')
    op.execute(
        'DROP POLICY IF EXISTS "tenant_provisioning_events_tenant_isolation" ON "tenant_provisioning_events";'
    )
    op.execute('ALTER TABLE "tenant_provisioning_events" DISABLE ROW LEVEL SECURITY;')
