"""create ocr uploads

Revision ID: 20260224_0011
Revises: 20260224_0010
Create Date: 2026-02-24 07:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260224_0011"
down_revision: Union[str, None] = "20260224_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ocr_source_type = sa.Enum("MONITOR", "VENT", "MED_LABEL", "DOCUMENT", "OTHER", name="ocr_source_type")
    ocr_source_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ocr_uploads",
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", ocr_source_type, nullable=False),
        sa.Column("s3_object_key", sa.String(length=512), nullable=False),
        sa.Column("image_sha256", sa.String(length=128), nullable=False),
        sa.Column("extracted_json_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("approved_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_to_entity_type", sa.String(length=64), nullable=True),
        sa.Column("applied_to_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ocr_uploads_tenant_id"), "ocr_uploads", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ocr_uploads_tenant_id"), table_name="ocr_uploads")
    op.drop_table("ocr_uploads")
