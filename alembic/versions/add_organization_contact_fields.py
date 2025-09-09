"""Add contact and address fields to organizations

Revision ID: add_org_contact_fields
Revises: 
Create Date: 2025-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_org_contact_fields'
down_revision = None  # Update this with the actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """Add contact information and address fields to organizations table"""
    # Add contact information columns
    op.add_column('organizations', sa.Column('contact_email', sa.String(255), nullable=True))
    op.add_column('organizations', sa.Column('contact_phone', sa.String(50), nullable=True))
    
    # Add address columns
    op.add_column('organizations', sa.Column('address_line1', sa.String(255), nullable=True))
    op.add_column('organizations', sa.Column('address_line2', sa.String(255), nullable=True))
    op.add_column('organizations', sa.Column('city', sa.String(100), nullable=True))
    op.add_column('organizations', sa.Column('state', sa.String(100), nullable=True))
    op.add_column('organizations', sa.Column('postal_code', sa.String(20), nullable=True))
    op.add_column('organizations', sa.Column('country', sa.String(100), nullable=True))
    
    # Add organization category column
    op.add_column('organizations', sa.Column('organization_category', sa.String(100), nullable=True))


def downgrade():
    """Remove contact information and address fields from organizations table"""
    # Remove organization category column
    op.drop_column('organizations', 'organization_category')
    
    # Remove address columns
    op.drop_column('organizations', 'country')
    op.drop_column('organizations', 'postal_code')
    op.drop_column('organizations', 'state')
    op.drop_column('organizations', 'city')
    op.drop_column('organizations', 'address_line2')
    op.drop_column('organizations', 'address_line1')
    
    # Remove contact information columns
    op.drop_column('organizations', 'contact_phone')
    op.drop_column('organizations', 'contact_email')
