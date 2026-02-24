"""create coding reference tables

Revision ID: 20260224_0003
Revises: 20260223_0001
Create Date: 2026-02-24 00:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260224_0003"
down_revision: Union[str, None] = "20260223_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "icd10_codes",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("short_description", sa.String(length=255), nullable=False),
        sa.Column("long_description", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), server_onupdate=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_icd10_codes_code", "icd10_codes", ["code"], unique=False)
    op.create_index("ix_icd10_codes_short_description", "icd10_codes", ["short_description"], unique=False)

    op.create_table(
        "rxnorm_codes",
        sa.Column("rxcui", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("tty", sa.String(length=32), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rxcui"),
    )
    op.create_index("ix_rxnorm_codes_rxcui", "rxnorm_codes", ["rxcui"], unique=False)
    op.create_index("ix_rxnorm_codes_name", "rxnorm_codes", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rxnorm_codes_name", table_name="rxnorm_codes")
    op.drop_index("ix_rxnorm_codes_rxcui", table_name="rxnorm_codes")
    op.drop_table("rxnorm_codes")

    op.drop_index("ix_icd10_codes_short_description", table_name="icd10_codes")
    op.drop_index("ix_icd10_codes_code", table_name="icd10_codes")
    op.drop_table("icd10_codes")
