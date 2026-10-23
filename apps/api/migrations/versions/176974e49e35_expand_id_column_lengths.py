"""expand_id_column_lengths

Revision ID: 176974e49e35
Revises: 86db0305b294
Create Date: 2026-10-23 13:19:34.252809

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '176974e49e35'
down_revision: Union[str, Sequence[str], None] = '86db0305b294'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema using batch mode for SQLite & PostgreSQL compatibility."""
    with op.batch_alter_table('organizations', schema=None) as batch_op:
        batch_op.alter_column('org_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)

    with op.batch_alter_table('facilities', schema=None) as batch_op:
        batch_op.alter_column('facility_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)
        batch_op.alter_column('org_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)

    with op.batch_alter_table('material_lots', schema=None) as batch_op:
        batch_op.alter_column('lot_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)
        batch_op.alter_column('org_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)
        batch_op.alter_column('facility_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)

    with op.batch_alter_table('evidence_records', schema=None) as batch_op:
        batch_op.alter_column('evidence_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)
        batch_op.alter_column('org_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)
        batch_op.alter_column('lot_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=True)

    with op.batch_alter_table('investigations', schema=None) as batch_op:
        batch_op.alter_column('investigation_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)
        batch_op.alter_column('org_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)
        batch_op.alter_column('lot_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)

    with op.batch_alter_table('qualification_assessments', schema=None) as batch_op:
        batch_op.alter_column('assessment_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)
        batch_op.alter_column('investigation_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=True)
        batch_op.alter_column('lot_id',
                   existing_type=sa.VARCHAR(length=36),
                   type_=sa.String(length=64),
                   existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema using batch mode for SQLite & PostgreSQL compatibility."""
    with op.batch_alter_table('qualification_assessments', schema=None) as batch_op:
        batch_op.alter_column('lot_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)
        batch_op.alter_column('investigation_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=True)
        batch_op.alter_column('assessment_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)

    with op.batch_alter_table('investigations', schema=None) as batch_op:
        batch_op.alter_column('lot_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)
        batch_op.alter_column('org_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)
        batch_op.alter_column('investigation_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)

    with op.batch_alter_table('evidence_records', schema=None) as batch_op:
        batch_op.alter_column('lot_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=True)
        batch_op.alter_column('org_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)
        batch_op.alter_column('evidence_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)

    with op.batch_alter_table('material_lots', schema=None) as batch_op:
        batch_op.alter_column('facility_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)
        batch_op.alter_column('org_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)
        batch_op.alter_column('lot_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)

    with op.batch_alter_table('facilities', schema=None) as batch_op:
        batch_op.alter_column('org_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)
        batch_op.alter_column('facility_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)

    with op.batch_alter_table('organizations', schema=None) as batch_op:
        batch_op.alter_column('org_id',
                   existing_type=sa.String(length=64),
                   type_=sa.VARCHAR(length=36),
                   existing_nullable=False)
