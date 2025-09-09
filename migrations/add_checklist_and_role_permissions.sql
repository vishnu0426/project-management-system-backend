-- Migration: Add checklist support and role-based permissions
-- Date: 2024-01-01
-- Description: Adds checklist_items table and updates existing tables for role-based task assignment

-- Create checklist_items table
CREATE TABLE IF NOT EXISTS checklist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    completed BOOLEAN DEFAULT FALSE NOT NULL,
    position INTEGER NOT NULL,
    ai_generated BOOLEAN DEFAULT FALSE NOT NULL,
    confidence INTEGER CHECK (confidence >= 0 AND confidence <= 100),
    metadata JSONB,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create indexes for checklist_items
CREATE INDEX IF NOT EXISTS idx_checklist_items_card_id ON checklist_items(card_id);
CREATE INDEX IF NOT EXISTS idx_checklist_items_position ON checklist_items(card_id, position);
CREATE INDEX IF NOT EXISTS idx_checklist_items_ai_generated ON checklist_items(ai_generated);
CREATE INDEX IF NOT EXISTS idx_checklist_items_completed ON checklist_items(completed);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_checklist_items_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_checklist_items_updated_at
    BEFORE UPDATE ON checklist_items
    FOR EACH ROW
    EXECUTE FUNCTION update_checklist_items_updated_at();

-- Update organization_members table to ensure role column exists with proper constraints
DO $$
BEGIN
    -- Check if role column exists, if not add it
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'organization_members' AND column_name = 'role'
    ) THEN
        ALTER TABLE organization_members ADD COLUMN role VARCHAR(20) DEFAULT 'member' NOT NULL;
    END IF;
    
    -- Add check constraint for valid roles
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints 
        WHERE constraint_name = 'chk_organization_members_role'
    ) THEN
        ALTER TABLE organization_members 
        ADD CONSTRAINT chk_organization_members_role 
        CHECK (role IN ('viewer', 'member', 'admin', 'owner'));
    END IF;
END $$;

-- Create index on organization_members role
CREATE INDEX IF NOT EXISTS idx_organization_members_role ON organization_members(role);

-- Update card_assignments table to include assigned_by tracking
DO $$
BEGIN
    -- Check if assigned_by column exists, if not add it
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'card_assignments' AND column_name = 'assigned_by'
    ) THEN
        ALTER TABLE card_assignments ADD COLUMN assigned_by UUID REFERENCES users(id);
    END IF;
    
    -- Check if assigned_at column exists, if not add it
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'card_assignments' AND column_name = 'assigned_at'
    ) THEN
        ALTER TABLE card_assignments ADD COLUMN assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL;
    END IF;
END $$;

-- Create indexes for card_assignments
CREATE INDEX IF NOT EXISTS idx_card_assignments_assigned_by ON card_assignments(assigned_by);
CREATE INDEX IF NOT EXISTS idx_card_assignments_assigned_at ON card_assignments(assigned_at);

-- Create a view for role-based assignment permissions
CREATE OR REPLACE VIEW v_user_assignment_permissions AS
SELECT 
    u.id as user_id,
    u.email,
    u.first_name,
    u.last_name,
    om.organization_id,
    om.role,
    CASE 
        WHEN om.role IN ('admin', 'owner') THEN true
        ELSE false
    END as can_assign_to_others,
    CASE 
        WHEN om.role IN ('member', 'admin', 'owner') THEN true
        ELSE false
    END as can_assign_to_self,
    CASE 
        WHEN om.role = 'owner' THEN 'organization'
        WHEN om.role = 'admin' THEN 'project'
        ELSE 'self'
    END as assignment_scope
FROM users u
JOIN organization_members om ON u.id = om.user_id
WHERE om.status = 'active';

-- Create a function to validate task assignments
CREATE OR REPLACE FUNCTION validate_task_assignment(
    assigner_user_id UUID,
    target_user_id UUID,
    organization_id UUID
) RETURNS BOOLEAN AS $$
DECLARE
    assigner_role VARCHAR(20);
    target_exists BOOLEAN;
BEGIN
    -- Get assigner's role
    SELECT role INTO assigner_role
    FROM organization_members
    WHERE user_id = assigner_user_id AND organization_id = organization_id AND status = 'active';
    
    -- Check if assigner exists in organization
    IF assigner_role IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Check if target user exists in organization
    SELECT EXISTS(
        SELECT 1 FROM organization_members
        WHERE user_id = target_user_id AND organization_id = organization_id AND status = 'active'
    ) INTO target_exists;
    
    IF NOT target_exists THEN
        RETURN FALSE;
    END IF;
    
    -- Self-assignment is always allowed
    IF assigner_user_id = target_user_id THEN
        RETURN TRUE;
    END IF;
    
    -- Role-based assignment rules
    CASE assigner_role
        WHEN 'viewer' THEN
            RETURN FALSE; -- Viewers can only assign to themselves
        WHEN 'member' THEN
            RETURN FALSE; -- Members can only assign to themselves
        WHEN 'admin' THEN
            RETURN TRUE; -- Admins can assign to anyone in the organization
        WHEN 'owner' THEN
            RETURN TRUE; -- Owners can assign to anyone in the organization
        ELSE
            RETURN FALSE;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Create a function to get assignable members for a user
CREATE OR REPLACE FUNCTION get_assignable_members(
    user_id UUID,
    organization_id UUID
) RETURNS TABLE (
    member_id UUID,
    email VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    role VARCHAR,
    avatar_url VARCHAR
) AS $$
DECLARE
    user_role VARCHAR(20);
BEGIN
    -- Get user's role
    SELECT om.role INTO user_role
    FROM organization_members om
    WHERE om.user_id = user_id AND om.organization_id = organization_id AND om.status = 'active';
    
    -- Return assignable members based on role
    CASE user_role
        WHEN 'viewer', 'member' THEN
            -- Can only assign to themselves
            RETURN QUERY
            SELECT u.id, u.email, u.first_name, u.last_name, om.role, u.avatar_url
            FROM users u
            JOIN organization_members om ON u.id = om.user_id
            WHERE u.id = user_id AND om.organization_id = organization_id AND om.status = 'active';
        
        WHEN 'admin', 'owner' THEN
            -- Can assign to anyone in the organization
            RETURN QUERY
            SELECT u.id, u.email, u.first_name, u.last_name, om.role, u.avatar_url
            FROM users u
            JOIN organization_members om ON u.id = om.user_id
            WHERE om.organization_id = organization_id AND om.status = 'active'
            ORDER BY u.first_name, u.last_name;
        
        ELSE
            -- No access
            RETURN;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Insert some sample data for testing (optional)
-- This can be removed in production
DO $$
BEGIN
    -- Update existing organization members to have proper roles if they don't
    UPDATE organization_members 
    SET role = 'owner' 
    WHERE role IS NULL OR role = '' 
    AND id IN (
        SELECT id FROM organization_members 
        ORDER BY created_at 
        LIMIT 1
    );
    
    UPDATE organization_members 
    SET role = 'member' 
    WHERE role IS NULL OR role = '';
END $$;

-- Add comments for documentation
COMMENT ON TABLE checklist_items IS 'Stores checklist items for cards with AI generation support';
COMMENT ON COLUMN checklist_items.ai_generated IS 'Indicates if the item was generated by AI';
COMMENT ON COLUMN checklist_items.confidence IS 'AI confidence score (0-100) for generated items';
COMMENT ON COLUMN checklist_items.metadata IS 'Additional metadata for AI-generated items';
COMMENT ON FUNCTION validate_task_assignment IS 'Validates if a user can assign a task to another user based on roles';
COMMENT ON FUNCTION get_assignable_members IS 'Returns list of members a user can assign tasks to based on their role';
COMMENT ON VIEW v_user_assignment_permissions IS 'Provides role-based assignment permissions for users';
