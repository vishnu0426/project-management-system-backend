"""
Add labels column to cards table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_labels_to_cards'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('cards', sa.Column('labels', sa.JSON(), nullable=True))

def downgrade():
    op.drop_column('cards', 'labels')
