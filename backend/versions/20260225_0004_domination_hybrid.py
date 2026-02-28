"""domination hybrid tables + RLS + postgis

Revision ID: 20260225_0004
Revises: 20260224_0003
Create Date: 2026-02-25 00:00:00.000000
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy import inspect

revision: str = "20260225_0004"
down_revision: Union[str, None] = "20260224_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn: Connection, name: str) -> bool:
    return inspect(conn).has_table(name)


def _enable_rls(conn: Connection, table: str) -> None:
    conn.execute(text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
    # Create policy only if not exists
    conn.execute(text(f'''
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = '{table}' AND policyname = '{table}_tenant_isolation'
      ) THEN
        EXECUTE 'CREATE POLICY {table}_tenant_isolation ON "{table}" USING (tenant_id = current_setting(''app.tenant_id'', true)::uuid)';
      END IF;
    END$$;
    '''))


def upgrade() -> None:
    conn = op.get_bind()

    # Extensions needed for UUID defaults and PostGIS points
    conn.execute(text('CREATE EXTENSION IF NOT EXISTS pgcrypto'))
    conn.execute(text('CREATE EXTENSION IF NOT EXISTS postgis'))

    # Ensure core identity tables exist (tenants, users, audit_logs)
    if not _has_table(conn, 'tenants'):
        op.create_table(
            'tenants',
            sa.Column('tenant_key', sa.String(length=128), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )
        op.create_index('ix_tenants_tenant_key', 'tenants', ['tenant_key'], unique=True)

    if not _has_table(conn, 'users'):
        op.create_table(
            'users',
            sa.Column('email', sa.String(length=320), nullable=False),
            sa.Column('hashed_password', sa.String(length=255), nullable=False),
            sa.Column('role', sa.String(length=64), nullable=False),
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
            sa.UniqueConstraint('tenant_id', 'email', name='uq_users_tenant_email'),
        )
        op.create_index('ix_users_tenant_id', 'users', ['tenant_id'], unique=False)

    if not _has_table(conn, 'audit_logs'):
        op.create_table(
        'audit_logs',
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=128), nullable=False),
        sa.Column('entity_name', sa.String(length=128), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_changes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('correlation_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index('ix_audit_logs_tenant_created', 'audit_logs', ['tenant_id', 'created_at'], unique=False)


    # Helper columns for tenant-scoped domination tables
    base_cols = [
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
    ]

    # Create tenant tables
    for name in ['devices', 'support_sessions', 'feature_flags', 'calls', 'call_intake_answers', 'dispatch_decisions', 'units', 'unit_status_events', 'unit_locations', 'crew_members', 'crew_assignments', 'shifts', 'shift_instances', 'availability_blocks', 'time_off_requests', 'bid_cycles', 'shift_bids', 'coverage_rulesets', 'credentials', 'credential_requirements', 'schedule_audit_events', 'pages', 'page_targets', 'page_responses', 'escalation_policies', 'on_call_rotations', 'mdt_sessions', 'mdt_offline_queue_items', 'obd_readings', 'fleet_alerts', 'camera_events', 'maintenance_items', 'inspection_checklists', 'weather_tiles_cache', 'weather_alerts', 'aviation_weather_reports', 'facilities', 'facility_users', 'facility_requests', 'recurring_request_rules', 'request_documents', 'documents', 'document_extractions', 'missing_document_tasks', 'signature_requests', 'signatures', 'fax_jobs', 'fax_events', 'billing_cases', 'claims', 'edi_artifacts', 'eras', 'denials', 'appeals', 'billing_jobs', 'pricing_plans', 'usage_records', 'stripe_webhook_receipts', 'patient_payment_links', 'import_batches', 'import_mappings', 'import_errors', 'export_jobs', 'export_artifacts', 'ai_runs', 'ai_policies', 'fire_incidents', 'fire_reports', 'fire_statements', 'fire_apparatus', 'fire_personnel_assignments', 'fire_losses', 'fire_actions_taken', 'nemsis_export_jobs', 'nemsis_validation_results', 'neris_export_jobs', 'neris_validation_results', 'governance_scores']:
        if _has_table(conn, name):
            continue
        if name == 'unit_locations':
            op.create_table(
                'unit_locations',
                sa.Column('unit_id', postgresql.UUID(as_uuid=True), nullable=False),
                sa.Column('location', postgresql.GEOGRAPHY(geometry_type='POINT', srid=4326), nullable=False),
                sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                *base_cols,
            )
            op.create_index('ix_unit_locations_tenant_recorded', 'unit_locations', ['tenant_id', 'recorded_at'], unique=False)
        elif name == 'calls':
            op.create_table(
                'calls',
                sa.Column('call_number', sa.String(length=64), nullable=False),
                sa.Column('status', sa.String(length=64), nullable=False, server_default='new'),
                sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
                *base_cols,
                sa.UniqueConstraint('tenant_id', 'call_number', name='uq_calls_tenant_number'),
            )
            op.create_index('ix_calls_tenant_received', 'calls', ['tenant_id', 'received_at'], unique=False)
        elif name == 'units':
            op.create_table(
                'units',
                sa.Column('name', sa.String(length=64), nullable=False),
                sa.Column('unit_type', sa.String(length=32), nullable=False, server_default='ambulance'),
                sa.Column('status', sa.String(length=32), nullable=False, server_default='available'),
                *base_cols,
                sa.UniqueConstraint('tenant_id', 'name', name='uq_units_tenant_name'),
            )
        elif name == 'claims':
            op.create_table(
                'claims',
                sa.Column('billing_case_id', postgresql.UUID(as_uuid=True), nullable=True),
                sa.Column('status', sa.String(length=32), nullable=False, server_default='draft'),
                sa.Column('amount_cents', sa.Integer(), nullable=True),
                *base_cols,
            )
            op.create_index('ix_claims_tenant_status', 'claims', ['tenant_id', 'status'], unique=False)
        elif name == 'documents':
            op.create_table(
                'documents',
                sa.Column('s3_key', sa.String(length=1024), nullable=True),
                sa.Column('doc_type', sa.String(length=64), nullable=True),
                sa.Column('sha256', sa.String(length=64), nullable=True),
                *base_cols,
            )
            op.create_index('ix_documents_tenant_type', 'documents', ['tenant_id', 'doc_type'], unique=False)
        else:
            op.create_table(name, *base_cols)
            op.create_index('ix_builders_rulesets_tenant_id', name, ['tenant_id'], unique=False)

        # Enable RLS and tenant isolation policy
        _enable_rls(conn, name)

    # Global ICD10 tables (no tenant_id)
    if not _has_table(conn, 'icd10_versions'):
        op.create_table(
            'icd10_versions',
            sa.Column('year', sa.Integer(), primary_key=True),
            sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        )

    if not _has_table(conn, 'icd10_codes'):
        op.create_table(
            'icd10_codes',
            sa.Column('code', sa.String(length=16), primary_key=True),
            sa.Column('year', sa.Integer(), nullable=False),
            sa.Column('short_desc', sa.String(length=255), nullable=True),
            sa.Column('long_desc', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['year'], ['icd10_versions.year']),
        )
        op.create_index('ix_icd10_codes_year', 'icd10_codes', ['year'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    # Drop in reverse where safe (leave tenants/users/audit_logs if pre-existing in some env)
    for name in reversed(['devices', 'support_sessions', 'feature_flags', 'calls', 'call_intake_answers', 'dispatch_decisions', 'units', 'unit_status_events', 'unit_locations', 'crew_members', 'crew_assignments', 'shifts', 'shift_instances', 'availability_blocks', 'time_off_requests', 'bid_cycles', 'shift_bids', 'coverage_rulesets', 'credentials', 'credential_requirements', 'schedule_audit_events', 'pages', 'page_targets', 'page_responses', 'escalation_policies', 'on_call_rotations', 'mdt_sessions', 'mdt_offline_queue_items', 'obd_readings', 'fleet_alerts', 'camera_events', 'maintenance_items', 'inspection_checklists', 'weather_tiles_cache', 'weather_alerts', 'aviation_weather_reports', 'facilities', 'facility_users', 'facility_requests', 'recurring_request_rules', 'request_documents', 'documents', 'document_extractions', 'missing_document_tasks', 'signature_requests', 'signatures', 'fax_jobs', 'fax_events', 'billing_cases', 'claims', 'edi_artifacts', 'eras', 'denials', 'appeals', 'billing_jobs', 'pricing_plans', 'usage_records', 'stripe_webhook_receipts', 'patient_payment_links', 'import_batches', 'import_mappings', 'import_errors', 'export_jobs', 'export_artifacts', 'ai_runs', 'ai_policies', 'fire_incidents', 'fire_reports', 'fire_statements', 'fire_apparatus', 'fire_personnel_assignments', 'fire_losses', 'fire_actions_taken', 'nemsis_export_jobs', 'nemsis_validation_results', 'neris_export_jobs', 'neris_validation_results', 'governance_scores']):
        if _has_table(conn, name):
            op.drop_table(name)
    if _has_table(conn, 'icd10_codes'):
        op.drop_index('ix_icd10_codes_year', table_name='icd10_codes')
        op.drop_table('icd10_codes')
    if _has_table(conn, 'icd10_versions'):
        op.drop_table('icd10_versions')
