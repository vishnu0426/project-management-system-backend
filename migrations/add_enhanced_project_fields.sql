-- Migration: Add enhanced project fields for advanced project management
-- Date: 2024-08-05
-- Description: Adds JSON fields to support enhanced project creation wizard data

-- Add enhanced project fields to projects table
ALTER TABLE projects 
ADD COLUMN IF NOT EXISTS configuration JSONB,
ADD COLUMN IF NOT EXISTS overview JSONB,
ADD COLUMN IF NOT EXISTS tech_stack JSONB,
ADD COLUMN IF NOT EXISTS workflow JSONB,
ADD COLUMN IF NOT EXISTS tasks JSONB,
ADD COLUMN IF NOT EXISTS notifications JSONB,
ADD COLUMN IF NOT EXISTS launch_options JSONB,
ADD COLUMN IF NOT EXISTS finalized_at TIMESTAMP WITH TIME ZONE;

-- Create indexes for better query performance on JSON fields
CREATE INDEX IF NOT EXISTS idx_projects_configuration ON projects USING GIN (configuration);
CREATE INDEX IF NOT EXISTS idx_projects_overview ON projects USING GIN (overview);
CREATE INDEX IF NOT EXISTS idx_projects_tech_stack ON projects USING GIN (tech_stack);
CREATE INDEX IF NOT EXISTS idx_projects_workflow ON projects USING GIN (workflow);
CREATE INDEX IF NOT EXISTS idx_projects_tasks ON projects USING GIN (tasks);
CREATE INDEX IF NOT EXISTS idx_projects_finalized_at ON projects (finalized_at);

-- Add comments for documentation
COMMENT ON COLUMN projects.configuration IS 'Project configuration data including budget, duration, team size, methodology, resources, tools, and features';
COMMENT ON COLUMN projects.overview IS 'Project overview data including objectives, deliverables, KPIs, timeline, stakeholders, risk assessment, and success criteria';
COMMENT ON COLUMN projects.tech_stack IS 'Technology stack data including frontend, backend, database, cloud, and tools selections';
COMMENT ON COLUMN projects.workflow IS 'Workflow and phases data including project phases, tasks, dependencies, and timeline';
COMMENT ON COLUMN projects.tasks IS 'Enhanced tasks data including detailed task information, subtasks, dependencies, and progress tracking';
COMMENT ON COLUMN projects.notifications IS 'Notification preferences for email, push, Slack, Teams, etc.';
COMMENT ON COLUMN projects.launch_options IS 'Launch configuration options for repository creation, CI/CD setup, staging deployment, etc.';
COMMENT ON COLUMN projects.finalized_at IS 'Timestamp when the project was finalized and launched';

-- Create a view for enhanced project data
CREATE OR REPLACE VIEW enhanced_projects AS
SELECT 
    p.*,
    u.first_name || ' ' || u.last_name AS creator_name,
    u.email AS creator_email,
    o.name AS organization_name,
    CASE 
        WHEN p.finalized_at IS NOT NULL THEN 'finalized'
        WHEN p.configuration IS NOT NULL OR p.overview IS NOT NULL THEN 'configured'
        ELSE 'basic'
    END AS project_type,
    CASE 
        WHEN p.tasks IS NOT NULL THEN jsonb_array_length(p.tasks)
        ELSE 0
    END AS task_count,
    CASE 
        WHEN p.workflow IS NOT NULL AND p.workflow ? 'phases' THEN jsonb_array_length(p.workflow->'phases')
        ELSE 0
    END AS phase_count
FROM projects p
LEFT JOIN users u ON p.created_by = u.id
LEFT JOIN organizations o ON p.organization_id = o.id;

-- Grant permissions
GRANT SELECT ON enhanced_projects TO PUBLIC;

-- Create function to validate project configuration
CREATE OR REPLACE FUNCTION validate_project_configuration(config JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Basic validation for configuration structure
    IF config IS NULL THEN
        RETURN TRUE;
    END IF;
    
    -- Check if budget is a positive number if present
    IF config ? 'budget' AND (config->>'budget')::NUMERIC <= 0 THEN
        RETURN FALSE;
    END IF;
    
    -- Check if duration is a positive integer if present
    IF config ? 'duration' AND (config->>'duration')::INTEGER <= 0 THEN
        RETURN FALSE;
    END IF;
    
    -- Check if team_size is a positive integer if present
    IF config ? 'team_size' AND (config->>'team_size')::INTEGER <= 0 THEN
        RETURN FALSE;
    END IF;
    
    -- Check if priority is valid if present
    IF config ? 'priority' AND (config->>'priority') NOT IN ('low', 'medium', 'high', 'urgent') THEN
        RETURN FALSE;
    END IF;
    
    -- Check if methodology is valid if present
    IF config ? 'methodology' AND (config->>'methodology') NOT IN ('agile', 'waterfall', 'kanban', 'hybrid') THEN
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to validate configuration on insert/update
CREATE OR REPLACE FUNCTION trigger_validate_project_configuration()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT validate_project_configuration(NEW.configuration) THEN
        RAISE EXCEPTION 'Invalid project configuration data';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists and create new one
DROP TRIGGER IF EXISTS validate_project_config_trigger ON projects;
CREATE TRIGGER validate_project_config_trigger
    BEFORE INSERT OR UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION trigger_validate_project_configuration();

-- Create function to get project statistics
CREATE OR REPLACE FUNCTION get_project_statistics(project_id UUID)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
    project_data RECORD;
BEGIN
    SELECT * INTO project_data FROM projects WHERE id = project_id;
    
    IF NOT FOUND THEN
        RETURN '{"error": "Project not found"}'::JSONB;
    END IF;
    
    result := jsonb_build_object(
        'project_id', project_data.id,
        'name', project_data.name,
        'status', project_data.status,
        'priority', project_data.priority,
        'created_at', project_data.created_at,
        'is_enhanced', CASE WHEN project_data.configuration IS NOT NULL THEN true ELSE false END,
        'is_finalized', CASE WHEN project_data.finalized_at IS NOT NULL THEN true ELSE false END,
        'task_count', CASE WHEN project_data.tasks IS NOT NULL THEN jsonb_array_length(project_data.tasks) ELSE 0 END,
        'phase_count', CASE WHEN project_data.workflow IS NOT NULL AND project_data.workflow ? 'phases' THEN jsonb_array_length(project_data.workflow->'phases') ELSE 0 END,
        'has_tech_stack', CASE WHEN project_data.tech_stack IS NOT NULL THEN true ELSE false END,
        'budget', CASE WHEN project_data.configuration ? 'budget' THEN (project_data.configuration->>'budget')::NUMERIC ELSE NULL END,
        'duration_weeks', CASE WHEN project_data.configuration ? 'duration' THEN (project_data.configuration->>'duration')::INTEGER ELSE NULL END
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_projects_status_priority ON projects (status, priority);
CREATE INDEX IF NOT EXISTS idx_projects_created_by_status ON projects (created_by, status);
CREATE INDEX IF NOT EXISTS idx_projects_organization_status ON projects (organization_id, status);

-- Update existing projects to have empty JSON objects for new fields if needed
UPDATE projects 
SET 
    configuration = '{}'::JSONB,
    overview = '{}'::JSONB,
    tech_stack = '{}'::JSONB,
    workflow = '{}'::JSONB,
    tasks = '[]'::JSONB,
    notifications = '{}'::JSONB,
    launch_options = '{}'::JSONB
WHERE 
    configuration IS NULL 
    OR overview IS NULL 
    OR tech_stack IS NULL 
    OR workflow IS NULL 
    OR tasks IS NULL 
    OR notifications IS NULL 
    OR launch_options IS NULL;

-- Create partial indexes for enhanced projects
CREATE INDEX IF NOT EXISTS idx_enhanced_projects ON projects (id) WHERE configuration IS NOT NULL AND configuration != '{}'::JSONB;
CREATE INDEX IF NOT EXISTS idx_finalized_projects ON projects (finalized_at) WHERE finalized_at IS NOT NULL;

COMMIT;
