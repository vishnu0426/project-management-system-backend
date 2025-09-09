# Role-Based Task Assignment & AI Checklist API Documentation

## Overview

This document describes the new API endpoints for role-based task assignment restrictions and AI-powered checklist generation features.

## Authentication

All endpoints require authentication via Bearer token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Role-Based Permissions

### Role Hierarchy
- **Viewer**: Can only assign tasks to themselves, cannot create tasks
- **Member**: Can only assign tasks to themselves, can create and edit own tasks
- **Admin**: Can assign tasks to any team member, full task management within projects
- **Owner**: Can assign tasks to any organization member, full permissions

### Assignment Scopes
- **Self**: Can only assign to themselves (Viewer, Member)
- **Project**: Can assign within project scope (Admin)
- **Organization**: Can assign to any organization member (Owner)

## Checklist & AI Endpoints

### 1. Generate AI Checklist

**POST** `/api/v1/checklist/cards/{card_id}/checklist/ai-generate`

Generate AI-powered checklist items for a card.

**Request Body:**
```json
{
  "title": "Implement user authentication",
  "description": "Create login and registration system with JWT",
  "priority": "high",
  "project_type": "api"
}
```

**Response:**
```json
{
  "success": true,
  "items": [
    {
      "text": "Review requirements and acceptance criteria",
      "completed": false,
      "position": 0,
      "ai_generated": true,
      "confidence": 85,
      "metadata": {
        "task_type": "development",
        "generated_at": "2024-01-01T12:00:00Z",
        "priority": "high"
      }
    }
  ],
  "metadata": {
    "task_type": "development",
    "confidence": 82,
    "generated_at": "2024-01-01T12:00:00Z",
    "item_count": 6
  }
}
```

### 2. Create Checklist Items

**POST** `/api/v1/checklist/cards/{card_id}/checklist`

Create multiple checklist items for a card.

**Request Body:**
```json
{
  "items": [
    {
      "text": "Set up development environment",
      "position": 0,
      "ai_generated": true,
      "confidence": 90,
      "metadata": {"source": "ai_generation"}
    }
  ]
}
```

### 3. Get Checklist Items

**GET** `/api/v1/checklist/cards/{card_id}/checklist`

Retrieve all checklist items for a card.

**Response:**
```json
[
  {
    "id": "uuid",
    "card_id": "uuid",
    "text": "Review requirements",
    "completed": false,
    "position": 0,
    "ai_generated": true,
    "confidence": 85,
    "metadata": {},
    "created_by": "uuid",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
]
```

### 4. Update Checklist Item

**PUT** `/api/v1/checklist/checklist/{item_id}`

Update a specific checklist item.

**Request Body:**
```json
{
  "text": "Updated item text",
  "completed": true,
  "position": 1
}
```

### 5. Delete Checklist Item

**DELETE** `/api/v1/checklist/checklist/{item_id}`

Delete a checklist item.

**Response:**
```json
{
  "success": true,
  "message": "Checklist item deleted successfully"
}
```

### 6. Get Checklist Progress

**GET** `/api/v1/checklist/cards/{card_id}/checklist/progress`

Get progress statistics for a card's checklist.

**Response:**
```json
{
  "total_items": 8,
  "completed_items": 3,
  "progress_percentage": 37.5,
  "ai_generated_count": 6
}
```

### 7. Get Checklist Suggestions

**GET** `/api/v1/checklist/checklist/suggestions/{task_type}`

Get suggested checklist items for a specific task type.

**Response:**
```json
{
  "suggestions": [
    "Set up CI/CD pipeline",
    "Perform security review",
    "Optimize performance"
  ],
  "task_type": "development"
}
```

## Role-Based Assignment Endpoints

### 1. Validate Task Assignment

**POST** `/api/v1/checklist/assignments/validate?organization_id={org_id}`

Validate if current user can assign tasks to specified users.

**Request Body:**
```json
{
  "assigned_to": ["user_id_1", "user_id_2"]
}
```

**Response:**
```json
{
  "valid": true
}
```

**Error Response:**
```json
{
  "valid": false,
  "error": "Members can only assign tasks to themselves",
  "error_code": "INVALID_ASSIGNMENT",
  "invalid_users": ["user_id_2"]
}
```

### 2. Get Assignable Members

**GET** `/api/v1/checklist/organizations/{organization_id}/assignable-members`

Get list of members current user can assign tasks to.

**Response:**
```json
{
  "members": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "member",
      "avatar_url": "https://..."
    }
  ],
  "total_count": 1,
  "user_role": "member",
  "assignment_scope": "self"
}
```

### 3. Get Role Permissions

**GET** `/api/v1/checklist/permissions/role/{role}`

Get detailed permissions for a specific role.

**Response:**
```json
{
  "can_assign_tasks_to_self": true,
  "can_assign_tasks_to_others": false,
  "can_create_tasks": true,
  "can_edit_own_tasks": true,
  "can_edit_other_tasks": false,
  "can_delete_tasks": false,
  "assignment_scope": "self",
  "restriction_message": "Members can only assign tasks to themselves"
}
```

## Enhanced Card Endpoints

### Create Card with Checklist

**POST** `/api/v1/cards/{column_id}/cards`

Create a card with optional AI-generated checklist.

**Request Body:**
```json
{
  "title": "Implement user authentication",
  "description": "Create login system",
  "position": 0,
  "priority": "high",
  "assigned_to": ["user_id"],
  "checklist": [
    {
      "text": "Set up authentication middleware",
      "position": 0,
      "ai_generated": true,
      "confidence": 90
    }
  ]
}
```

## Error Codes

- `NOT_ORGANIZATION_MEMBER`: User is not a member of the organization
- `INVALID_ASSIGNMENT`: Assignment violates role-based restrictions
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `VALIDATION_ERROR`: Request data validation failed

## Rate Limiting

- AI checklist generation: 10 requests per minute per user
- Other endpoints: 100 requests per minute per user

## Examples

### Frontend Integration

```javascript
// Validate assignment before creating card
const validateAssignment = async (organizationId, userIds) => {
  const response = await fetch(`/api/v1/checklist/assignments/validate?organization_id=${organizationId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ assigned_to: userIds })
  });
  return response.json();
};

// Generate AI checklist
const generateChecklist = async (cardId, taskData) => {
  const response = await fetch(`/api/v1/checklist/cards/${cardId}/checklist/ai-generate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(taskData)
  });
  return response.json();
};
```

## Database Schema

### checklist_items Table
```sql
CREATE TABLE checklist_items (
    id UUID PRIMARY KEY,
    card_id UUID REFERENCES cards(id),
    text TEXT NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    position INTEGER NOT NULL,
    ai_generated BOOLEAN DEFAULT FALSE,
    confidence INTEGER CHECK (confidence >= 0 AND confidence <= 100),
    metadata JSONB,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Role Validation Function
```sql
CREATE FUNCTION validate_task_assignment(
    assigner_user_id UUID,
    target_user_id UUID,
    organization_id UUID
) RETURNS BOOLEAN;
```
