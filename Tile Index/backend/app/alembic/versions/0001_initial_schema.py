"""initial production schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-15
"""

from alembic import op
from app.models import Base


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
