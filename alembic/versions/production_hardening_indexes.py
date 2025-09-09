"""Production hardening - add missing indexes and constraints

Revision ID: production_hardening
Revises: bf1d8b0d9ca2
Create Date: 2025-01-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'production_hardening'
down_revision = 'bf1d8b0d9ca2'
branch_labels = None
depends_on = None

def upgrade():
    """Add production-ready indexes and constraints"""
    
    # Add indexes for frequent queries and foreign keys
    
    # Card indexes for performance
    op.create_index('idx_cards_column_id', 'cards', ['column_id'])
    op.create_index('idx_cards_created_by', 'cards', ['created_by'])
    op.create_index('idx_cards_status', 'cards', ['status'])
    op.create_index('idx_cards_priority', 'cards', ['priority'])
    op.create_index('idx_cards_due_date', 'cards', ['due_date'])
    op.create_index('idx_cards_created_at', 'cards', ['created_at'])
    
    # Column indexes
    op.create_index('idx_columns_board_id', 'columns', ['board_id'])
    op.create_index('idx_columns_position', 'columns', ['position'])
    
    # Board indexes
    op.create_index('idx_boards_project_id', 'boards', ['project_id'])
    op.create_index('idx_boards_created_by', 'boards', ['created_by'])
    
    # Project indexes
    op.create_index('idx_projects_organization_id', 'projects', ['organization_id'])
    op.create_index('idx_projects_created_by', 'projects', ['created_by'])
    op.create_index('idx_projects_status', 'projects', ['status'])
    op.create_index('idx_projects_created_at', 'projects', ['created_at'])
    
    # Organization member indexes (if not already exist)
    op.create_index('idx_org_members_user_id', 'organization_members', ['user_id'], if_not_exists=True)
    op.create_index('idx_org_members_org_id', 'organization_members', ['organization_id'], if_not_exists=True)
    op.create_index('idx_org_members_role', 'organization_members', ['role'], if_not_exists=True)
    
    # User session indexes for auth performance
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_user_sessions_expires_at', 'user_sessions', ['expires_at'])
    op.create_index('idx_user_sessions_is_active', 'user_sessions', ['is_active'])
    
    # Checklist item indexes
    op.create_index('idx_checklist_items_card_id', 'checklist_items', ['card_id'])
    op.create_index('idx_checklist_items_created_by', 'checklist_items', ['created_by'])
    op.create_index('idx_checklist_items_position', 'checklist_items', ['position'])
    
    # Card assignment indexes
    op.create_index('idx_card_assignments_card_id', 'card_assignments', ['card_id'])
    op.create_index('idx_card_assignments_user_id', 'card_assignments', ['user_id'])
    op.create_index('idx_card_assignments_assigned_by', 'card_assignments', ['assigned_by'])
    
    # Comment indexes
    op.create_index('idx_comments_card_id', 'comments', ['card_id'])
    op.create_index('idx_comments_user_id', 'comments', ['user_id'])
    op.create_index('idx_comments_created_at', 'comments', ['created_at'])
    
    # Attachment indexes
    op.create_index('idx_attachments_card_id', 'attachments', ['card_id'])
    op.create_index('idx_attachments_uploaded_by', 'attachments', ['uploaded_by'])
    
    # Registration indexes for admin queries
    op.create_index('idx_registrations_email', 'registrations', ['email'])
    op.create_index('idx_registrations_status', 'registrations', ['status'])
    op.create_index('idx_registrations_created_at', 'registrations', ['created_at'])
    
    # Composite indexes for common query patterns
    op.create_index('idx_cards_column_position', 'cards', ['column_id', 'position'])
    op.create_index('idx_cards_status_priority', 'cards', ['status', 'priority'])
    op.create_index('idx_org_members_user_org', 'organization_members', ['user_id', 'organization_id'])


def downgrade():
    """Remove production indexes"""
    
    # Drop all indexes created in upgrade
    op.drop_index('idx_cards_column_id', 'cards')
    op.drop_index('idx_cards_created_by', 'cards')
    op.drop_index('idx_cards_status', 'cards')
    op.drop_index('idx_cards_priority', 'cards')
    op.drop_index('idx_cards_due_date', 'cards')
    op.drop_index('idx_cards_created_at', 'cards')
    
    op.drop_index('idx_columns_board_id', 'columns')
    op.drop_index('idx_columns_position', 'columns')
    
    op.drop_index('idx_boards_project_id', 'boards')
    op.drop_index('idx_boards_created_by', 'boards')
    
    op.drop_index('idx_projects_organization_id', 'projects')
    op.drop_index('idx_projects_created_by', 'projects')
    op.drop_index('idx_projects_status', 'projects')
    op.drop_index('idx_projects_created_at', 'projects')
    
    op.drop_index('idx_org_members_user_id', 'organization_members')
    op.drop_index('idx_org_members_org_id', 'organization_members')
    op.drop_index('idx_org_members_role', 'organization_members')
    
    op.drop_index('idx_user_sessions_user_id', 'user_sessions')
    op.drop_index('idx_user_sessions_expires_at', 'user_sessions')
    op.drop_index('idx_user_sessions_is_active', 'user_sessions')
    
    op.drop_index('idx_checklist_items_card_id', 'checklist_items')
    op.drop_index('idx_checklist_items_created_by', 'checklist_items')
    op.drop_index('idx_checklist_items_position', 'checklist_items')
    
    op.drop_index('idx_card_assignments_card_id', 'card_assignments')
    op.drop_index('idx_card_assignments_user_id', 'card_assignments')
    op.drop_index('idx_card_assignments_assigned_by', 'card_assignments')
    
    op.drop_index('idx_comments_card_id', 'comments')
    op.drop_index('idx_comments_user_id', 'comments')
    op.drop_index('idx_comments_created_at', 'comments')
    
    op.drop_index('idx_attachments_card_id', 'attachments')
    op.drop_index('idx_attachments_uploaded_by', 'attachments')
    
    op.drop_index('idx_registrations_email', 'registrations')
    op.drop_index('idx_registrations_status', 'registrations')
    op.drop_index('idx_registrations_created_at', 'registrations')
    
    op.drop_index('idx_cards_column_position', 'cards')
    op.drop_index('idx_cards_status_priority', 'cards')
    op.drop_index('idx_org_members_user_org', 'organization_members')
