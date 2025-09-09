-- Migration: Add Project Sign-off and Data Protection Fields
-- Description: Adds fields to support project sign-off workflow and data protection
-- Date: 2025-01-07

-- Add sign-off and data protection fields to projects table
ALTER TABLE projects 
ADD COLUMN IF NOT EXISTS sign_off_requested BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS sign_off_requested_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS sign_off_requested_by UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS sign_off_approved BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS sign_off_approved_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS sign_off_approved_by UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS sign_off_notes TEXT,
ADD COLUMN IF NOT EXISTS data_protected BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS protection_reason VARCHAR(255),
ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS archived_by UUID REFERENCES users(id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_projects_sign_off_requested ON projects(sign_off_requested);
CREATE INDEX IF NOT EXISTS idx_projects_sign_off_approved ON projects(sign_off_approved);
CREATE INDEX IF NOT EXISTS idx_projects_data_protected ON projects(data_protected);
CREATE INDEX IF NOT EXISTS idx_projects_archived_at ON projects(archived_at);

-- Create a view for projects pending sign-off
CREATE OR REPLACE VIEW projects_pending_signoff AS
SELECT 
    p.*,
    requester.first_name || ' ' || requester.last_name AS requester_name,
    requester.email AS requester_email,
    org.name AS organization_name
FROM projects p
LEFT JOIN users requester ON p.sign_off_requested_by = requester.id
LEFT JOIN organizations org ON p.organization_id = org.id
WHERE p.sign_off_requested = TRUE 
  AND p.sign_off_approved = FALSE
  AND p.archived_at IS NULL;

-- Create a function to automatically protect data when sign-off is requested
CREATE OR REPLACE FUNCTION protect_project_data()
RETURNS TRIGGER AS $$
BEGIN
    -- When sign-off is requested, automatically protect the data
    IF NEW.sign_off_requested = TRUE AND OLD.sign_off_requested = FALSE THEN
        NEW.data_protected = TRUE;
        NEW.protection_reason = 'Automatic protection due to sign-off request';
    END IF;
    
    -- When sign-off is approved, keep data protected until explicitly unprotected
    IF NEW.sign_off_approved = TRUE AND OLD.sign_off_approved = FALSE THEN
        NEW.data_protected = TRUE;
        IF NEW.protection_reason IS NULL THEN
            NEW.protection_reason = 'Protected after sign-off approval';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically protect data
DROP TRIGGER IF EXISTS trigger_protect_project_data ON projects;
CREATE TRIGGER trigger_protect_project_data
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION protect_project_data();

-- Add comments to document the new fields
COMMENT ON COLUMN projects.sign_off_requested IS 'Whether project sign-off has been requested';
COMMENT ON COLUMN projects.sign_off_requested_at IS 'Timestamp when sign-off was requested';
COMMENT ON COLUMN projects.sign_off_requested_by IS 'User who requested the sign-off';
COMMENT ON COLUMN projects.sign_off_approved IS 'Whether project has been signed off by owner';
COMMENT ON COLUMN projects.sign_off_approved_at IS 'Timestamp when sign-off was approved';
COMMENT ON COLUMN projects.sign_off_approved_by IS 'User who approved the sign-off';
COMMENT ON COLUMN projects.sign_off_notes IS 'Notes from the approver during sign-off';
COMMENT ON COLUMN projects.data_protected IS 'Whether project data is protected from deletion';
COMMENT ON COLUMN projects.protection_reason IS 'Reason why the data is protected';
COMMENT ON COLUMN projects.archived_at IS 'Timestamp when project was archived';
COMMENT ON COLUMN projects.archived_by IS 'User who archived the project';

-- Grant necessary permissions
GRANT SELECT ON projects_pending_signoff TO PUBLIC;

-- Insert audit log entry
INSERT INTO system_logs (event_type, description, created_at) 
VALUES ('migration', 'Added project sign-off and data protection fields', NOW())
ON CONFLICT DO NOTHING;
