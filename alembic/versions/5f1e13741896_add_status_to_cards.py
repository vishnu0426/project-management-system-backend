"""add_status_to_cards

Revision ID: 5f1e13741896
Revises: bf1d8b0d9ca2
Create Date: 2025-08-07 17:55:18.637004

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f1e13741896'
down_revision = 'bf1d8b0d9ca2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column to cards table
    op.add_column('cards', sa.Column('status', sa.String(20), nullable=False, server_default='todo'))


def downgrade() -> None:
    # Remove status column from cards table
    op.drop_column('cards', 'status')
