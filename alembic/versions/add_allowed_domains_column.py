"""Add allowed_domains column to organizations table

Revision ID: add_allowed_domains
Revises: add_org_contact_fields
Create Date: 2025-08-02 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_allowed_domains'
down_revision = 'add_org_contact_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Add allowed_domains column to organizations table for domain validation"""
    # Add allowed_domains column as an array of strings
    op.add_column('organizations', 
                  sa.Column('allowed_domains', 
                           postgresql.ARRAY(sa.String(255)), 
                           nullable=True,
                           comment='List of allowed email domains for this organization'))
    
    # Update existing organizations with default allowed domains
    # This is a safe operation that sets reasonable defaults
    op.execute("""
        UPDATE organizations 
        SET allowed_domains = ARRAY['agnoshin.com', 'agno.com'] 
        WHERE allowed_domains IS NULL
    """)


def downgrade():
    """Remove allowed_domains column from organizations table"""
    op.drop_column('organizations', 'allowed_domains')
