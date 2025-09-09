-- Migration: Add organization hierarchy and bulk operations features
-- Date: 2025-01-01
-- Description: Adds support for organization hierarchy, cross-org collaboration, and bulk operations

-- Add new columns to organizations table for hierarchy support
ALTER TABLE organizations 
ADD COLUMN parent_id UUID REFERENCES organizations(id),
ADD COLUMN organization_type VARCHAR(50) DEFAULT 'standard' NOT NULL,
ADD COLUMN allow_cross_org_collaboration BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN collaboration_domains TEXT[];

-- Add check constraint for organization_type
ALTER TABLE organizations 
ADD CONSTRAINT valid_organization_type 
CHECK (organization_type IN ('standard', 'parent', 'subsidiary'));

-- Create organization_collaborations table
CREATE TABLE organization_collaborations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    partner_organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    collaboration_type VARCHAR(50) DEFAULT 'project_sharing' NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    permissions TEXT[],
    created_by UUID NOT NULL REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_collaboration_type 
        CHECK (collaboration_type IN ('project_sharing', 'resource_sharing', 'full_access')),
    CONSTRAINT valid_collaboration_status 
        CHECK (status IN ('pending', 'active', 'suspended', 'terminated')),
    CONSTRAINT no_self_collaboration 
        CHECK (organization_id != partner_organization_id),
    CONSTRAINT unique_collaboration 
        UNIQUE (organization_id, partner_organization_id)
);

-- Create bulk_user_operations table
CREATE TABLE bulk_user_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    operation_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    file_path VARCHAR(500),
    file_name VARCHAR(255),
    total_records INTEGER DEFAULT 0 NOT NULL,
    processed_records INTEGER DEFAULT 0 NOT NULL,
    successful_records INTEGER DEFAULT 0 NOT NULL,
    failed_records INTEGER DEFAULT 0 NOT NULL,
    error_details JSONB,
    result_data JSONB,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_operation_type 
        CHECK (operation_type IN ('import', 'export', 'bulk_invite', 'bulk_update', 'bulk_delete')),
    CONSTRAINT valid_operation_status 
        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled'))
);

-- Create bulk_operation_logs table
CREATE TABLE bulk_operation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bulk_operation_id UUID NOT NULL REFERENCES bulk_user_operations(id) ON DELETE CASCADE,
    record_index INTEGER NOT NULL,
    record_data JSONB,
    operation_result VARCHAR(50) NOT NULL,
    error_message TEXT,
    created_user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT valid_operation_result 
        CHECK (operation_result IN ('success', 'failed', 'skipped'))
);

-- Create organization_templates table
CREATE TABLE organization_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_type VARCHAR(50) NOT NULL,
    industry VARCHAR(100),
    configuration JSONB NOT NULL,
    default_roles JSONB,
    default_projects JSONB,
    default_workflows JSONB,
    is_public VARCHAR(10) DEFAULT 'false' NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    usage_count INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT valid_template_type 
        CHECK (template_type IN ('startup', 'agency', 'enterprise', 'custom')),
    CONSTRAINT valid_visibility 
        CHECK (is_public IN ('public', 'private', 'organization'))
);

-- Create indexes for better performance
CREATE INDEX idx_organizations_parent_id ON organizations(parent_id);
CREATE INDEX idx_organizations_type ON organizations(organization_type);
CREATE INDEX idx_org_collaborations_org_id ON organization_collaborations(organization_id);
CREATE INDEX idx_org_collaborations_partner_id ON organization_collaborations(partner_organization_id);
CREATE INDEX idx_org_collaborations_status ON organization_collaborations(status);
CREATE INDEX idx_bulk_operations_org_id ON bulk_user_operations(organization_id);
CREATE INDEX idx_bulk_operations_status ON bulk_user_operations(status);
CREATE INDEX idx_bulk_operations_type ON bulk_user_operations(operation_type);
CREATE INDEX idx_bulk_logs_operation_id ON bulk_operation_logs(bulk_operation_id);
CREATE INDEX idx_org_templates_type ON organization_templates(template_type);
CREATE INDEX idx_org_templates_public ON organization_templates(is_public);

-- Insert default organization templates
INSERT INTO organization_templates (name, description, template_type, industry, configuration, default_roles, default_projects, default_workflows, is_public, created_by) VALUES
('Startup Template', 'Perfect for small startups with basic project management needs', 'startup', 'Technology', 
 '{"max_projects": 10, "max_members": 25, "features": ["basic_kanban", "file_sharing", "basic_reporting"]}',
 '[{"role": "owner", "permissions": ["all"]}, {"role": "admin", "permissions": ["manage_projects", "manage_members"]}, {"role": "member", "permissions": ["create_tasks", "edit_own_tasks"]}, {"role": "viewer", "permissions": ["view_only"]}]',
 '[{"name": "Product Development", "description": "Main product development board", "columns": ["Backlog", "In Progress", "Review", "Done"]}]',
 '{"auto_assign": false, "require_approval": false, "time_tracking": true}',
 'public', (SELECT id FROM users LIMIT 1)),

('Agency Template', 'Designed for marketing agencies managing multiple client projects', 'agency', 'Marketing', 
 '{"max_projects": 50, "max_members": 100, "features": ["advanced_kanban", "client_portal", "time_tracking", "advanced_reporting"]}',
 '[{"role": "owner", "permissions": ["all"]}, {"role": "admin", "permissions": ["manage_projects", "manage_members", "client_access"]}, {"role": "member", "permissions": ["create_tasks", "edit_tasks", "time_tracking"]}, {"role": "viewer", "permissions": ["view_assigned"]}]',
 '[{"name": "Client Onboarding", "description": "New client setup process", "columns": ["Discovery", "Planning", "Execution", "Delivery"]}, {"name": "Campaign Management", "description": "Marketing campaign execution", "columns": ["Brief", "Creative", "Review", "Launch", "Optimize"]}]',
 '{"auto_assign": true, "require_approval": true, "time_tracking": true, "client_notifications": true}',
 'public', (SELECT id FROM users LIMIT 1)),

('Enterprise Template', 'Comprehensive template for large organizations with complex workflows', 'enterprise', 'Enterprise', 
 '{"max_projects": 500, "max_members": 1000, "features": ["enterprise_kanban", "advanced_security", "compliance", "advanced_analytics", "api_access"]}',
 '[{"role": "owner", "permissions": ["all"]}, {"role": "admin", "permissions": ["manage_projects", "manage_members", "security_settings", "compliance"]}, {"role": "member", "permissions": ["create_tasks", "edit_tasks", "time_tracking", "reporting"]}, {"role": "viewer", "permissions": ["view_assigned", "basic_reporting"]}]',
 '[{"name": "Strategic Initiatives", "description": "High-level strategic projects", "columns": ["Planning", "Approval", "Execution", "Review", "Complete"]}, {"name": "Operations", "description": "Day-to-day operational tasks", "columns": ["Queue", "In Progress", "Testing", "Done"]}, {"name": "Compliance", "description": "Regulatory and compliance tasks", "columns": ["Assessment", "Implementation", "Audit", "Approved"]}]',
 '{"auto_assign": true, "require_approval": true, "time_tracking": true, "compliance_tracking": true, "audit_trail": true}',
 'public', (SELECT id FROM users LIMIT 1));

-- Add triggers for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organization_templates_updated_at 
    BEFORE UPDATE ON organization_templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE organization_collaborations IS 'Manages cross-organization collaboration relationships';
COMMENT ON TABLE bulk_user_operations IS 'Tracks bulk user management operations like import/export';
COMMENT ON TABLE bulk_operation_logs IS 'Detailed logs for each record in bulk operations';
COMMENT ON TABLE organization_templates IS 'Pre-configured organization templates for quick setup';

COMMENT ON COLUMN organizations.parent_id IS 'Reference to parent organization for hierarchy';
COMMENT ON COLUMN organizations.organization_type IS 'Type of organization: standard, parent, or subsidiary';
COMMENT ON COLUMN organizations.allow_cross_org_collaboration IS 'Whether this organization allows collaboration with others';
COMMENT ON COLUMN organizations.collaboration_domains IS 'List of domains allowed for collaboration';
