"""create_registration_table

Revision ID: 2c7527da8955
Revises: 5f1e13741896
Create Date: 2025-08-07 18:10:53.790963

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = '2c7527da8955'
down_revision = '5f1e13741896'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create registrations table
    op.create_table(
        'registrations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),

        # Personal Information
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone_number', sa.String(20), nullable=True),

        # Organization Information
        sa.Column('organization_name', sa.String(255), nullable=False),
        sa.Column('organization_domain', sa.String(255), nullable=True),
        sa.Column('organization_size', sa.String(50), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),

        # Role and Access
        sa.Column('requested_role', sa.String(50), nullable=False, server_default='owner'),
        sa.Column('assigned_role', sa.String(50), nullable=True),

        # Additional Information
        sa.Column('job_title', sa.String(100), nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('company_website', sa.String(255), nullable=True),

        # Registration Context
        sa.Column('registration_source', sa.String(50), nullable=False, server_default='web'),
        sa.Column('referral_source', sa.String(100), nullable=True),
        sa.Column('marketing_consent', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('terms_accepted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('privacy_policy_accepted', sa.Boolean, nullable=False, server_default='false'),

        # System Information
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('browser_info', JSON, nullable=True),

        # Status and Processing
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('approval_notes', sa.Text, nullable=True),
        sa.Column('processed_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),

        # Linked Records
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Additional metadata
        sa.Column('form_metadata', JSON, nullable=True)
    )

    # Create indexes
    op.create_index('ix_registrations_email', 'registrations', ['email'])
    op.create_index('ix_registrations_status', 'registrations', ['status'])
    op.create_index('ix_registrations_created_at', 'registrations', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_registrations_created_at', 'registrations')
    op.drop_index('ix_registrations_status', 'registrations')
    op.drop_index('ix_registrations_email', 'registrations')

    # Drop table
    op.drop_table('registrations')
