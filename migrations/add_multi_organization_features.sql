-- Migration: Add Multi-Organization Features
-- Description: Add tables for enhanced multi-organization management

-- Organization Settings Table
CREATE TABLE IF NOT EXISTS organization_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Project creation permissions
    allow_admin_create_projects BOOLEAN NOT NULL DEFAULT TRUE,
    allow_member_create_projects BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Meeting permissions
    allow_admin_schedule_meetings BOOLEAN NOT NULL DEFAULT TRUE,
    allow_member_schedule_meetings BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Invitation settings
    require_domain_match BOOLEAN NOT NULL DEFAULT TRUE,
    allowed_invitation_domains JSONB,
    
    -- Notification settings
    enable_task_notifications BOOLEAN NOT NULL DEFAULT TRUE,
    enable_meeting_notifications BOOLEAN NOT NULL DEFAULT TRUE,
    enable_role_change_notifications BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Dashboard customization
    dashboard_config JSONB,
    
    -- Security settings
    require_email_verification BOOLEAN NOT NULL DEFAULT TRUE,
    password_policy JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_org_settings UNIQUE (organization_id)
);

-- User Organization Context Table
CREATE TABLE IF NOT EXISTS user_organization_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    last_switched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    preferences JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_user_context UNIQUE (user_id)
);

-- Invitation Tokens Table
CREATE TABLE IF NOT EXISTS invitation_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    invited_role VARCHAR(20) NOT NULL CHECK (invited_role IN ('admin', 'member')),
    temporary_password VARCHAR(255) NOT NULL,
    
    -- Invitation details
    invited_by UUID NOT NULL REFERENCES users(id),
    invitation_message TEXT,
    
    -- Status and expiry
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Meeting Schedules Table
CREATE TABLE IF NOT EXISTS meeting_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Meeting details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    meeting_type VARCHAR(50) NOT NULL DEFAULT 'team' CHECK (meeting_type IN ('team', 'individual', 'project')),
    
    -- Scheduling
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    
    -- Meeting link/details
    meeting_link VARCHAR(500),
    meeting_platform VARCHAR(50) NOT NULL DEFAULT 'zoom' CHECK (meeting_platform IN ('zoom', 'teams', 'meet', 'custom')),
    
    -- Participants
    organizer_id UUID NOT NULL REFERENCES users(id),
    participants JSONB,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'started', 'completed', 'cancelled')),
    
    -- Notifications
    reminder_sent BOOLEAN NOT NULL DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_organization_settings_org_id ON organization_settings(organization_id);
CREATE INDEX IF NOT EXISTS idx_user_org_contexts_user_id ON user_organization_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_org_contexts_current_org ON user_organization_contexts(current_organization_id);
CREATE INDEX IF NOT EXISTS idx_invitation_tokens_token ON invitation_tokens(token);
CREATE INDEX IF NOT EXISTS idx_invitation_tokens_email ON invitation_tokens(email);
CREATE INDEX IF NOT EXISTS idx_invitation_tokens_org_id ON invitation_tokens(organization_id);
CREATE INDEX IF NOT EXISTS idx_invitation_tokens_expires ON invitation_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_meeting_schedules_org_id ON meeting_schedules(organization_id);
CREATE INDEX IF NOT EXISTS idx_meeting_schedules_project_id ON meeting_schedules(project_id);
CREATE INDEX IF NOT EXISTS idx_meeting_schedules_organizer ON meeting_schedules(organizer_id);
CREATE INDEX IF NOT EXISTS idx_meeting_schedules_scheduled_at ON meeting_schedules(scheduled_at);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organization_settings_updated_at 
    BEFORE UPDATE ON organization_settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_organization_contexts_updated_at 
    BEFORE UPDATE ON user_organization_contexts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_meeting_schedules_updated_at 
    BEFORE UPDATE ON meeting_schedules 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default settings for existing organizations (only if they don't exist)
INSERT INTO organization_settings (
    id, organization_id, allow_admin_create_projects, allow_member_create_projects,
    allow_admin_schedule_meetings, allow_member_schedule_meetings, require_domain_match,
    enable_task_notifications, enable_meeting_notifications, enable_role_change_notifications,
    require_email_verification
)
SELECT
    gen_random_uuid(),
    o.id,
    TRUE,  -- allow_admin_create_projects
    FALSE, -- allow_member_create_projects
    TRUE,  -- allow_admin_schedule_meetings
    FALSE, -- allow_member_schedule_meetings
    TRUE,  -- require_domain_match
    TRUE,  -- enable_task_notifications
    TRUE,  -- enable_meeting_notifications
    TRUE,  -- enable_role_change_notifications
    TRUE   -- require_email_verification
FROM organizations o
WHERE NOT EXISTS (
    SELECT 1 FROM organization_settings os
    WHERE os.organization_id = o.id
);

-- Create default user contexts for existing users (only if they don't exist)
INSERT INTO user_organization_contexts (id, user_id, current_organization_id)
SELECT gen_random_uuid(),
       DISTINCT_OM.user_id,
       (SELECT organization_id FROM organization_members om2
        WHERE om2.user_id = DISTINCT_OM.user_id
        ORDER BY joined_at ASC LIMIT 1) as first_org
FROM (SELECT DISTINCT user_id FROM organization_members) DISTINCT_OM
WHERE NOT EXISTS (
    SELECT 1 FROM user_organization_contexts uoc
    WHERE uoc.user_id = DISTINCT_OM.user_id
);

COMMENT ON TABLE organization_settings IS 'Organization-specific settings and permissions';
COMMENT ON TABLE user_organization_contexts IS 'Track users current organization context for multi-org switching';
COMMENT ON TABLE invitation_tokens IS 'Temporary invitation tokens for organization/project invitations';
COMMENT ON TABLE meeting_schedules IS 'Meeting scheduling system for organizations and projects';
