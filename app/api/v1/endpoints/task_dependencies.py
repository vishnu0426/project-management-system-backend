"""
Task dependency management endpoints for AI Task Management Modal
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from uuid import UUID
import uuid
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.exceptions import ValidationError, ResourceNotFoundError, InsufficientPermissionsError
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.project import Project
from app.models.board import Board
from app.models.column import Column
from app.models.card import Card

router = APIRouter()

# Pydantic models for dependency endpoints
class DependencyCreate(BaseModel):
    source_task_id: str
    target_task_id: str
    dependency_type: str = Field(pattern="^(blocks|depends_on|related_to|subtask_of)$")
    description: Optional[str] = None

class DependencyUpdate(BaseModel):
    dependency_type: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class DependencyValidationRequest(BaseModel):
    dependencies: List[DependencyCreate]
    project_id: str

class DependencyVisualizationRequest(BaseModel):
    project_id: str
    include_completed: bool = False
    max_depth: int = Field(default=3, ge=1, le=10)

class CriticalPathRequest(BaseModel):
    project_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

# In-memory storage for demo (replace with database models)
dependencies_db = {}

@router.post("/create")
async def create_dependency(
    dependency_data: DependencyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a task dependency"""
    try:
        # Validate both tasks exist and user has access
        tasks_result = await db.execute(
            select(Card)
            .options(
                selectinload(Card.column)
                .selectinload(Column.board)
                .selectinload(Board.project)
            )
            .where(Card.id.in_([dependency_data.source_task_id, dependency_data.target_task_id]))
        )
        tasks = tasks_result.scalars().all()

        if len(tasks) != 2:
            raise ResourceNotFoundError("One or both tasks not found")

        # Check if tasks are in the same project
        projects = set(task.column.board.project.id for task in tasks)
        if len(projects) > 1:
            raise ValidationError("Dependencies can only be created between tasks in the same project")

        project = tasks[0].column.board.project

        # Check user permissions
        org_member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == project.organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied to project")

        # Check for circular dependencies
        if await has_circular_dependency(dependency_data.source_task_id, dependency_data.target_task_id):
            raise ValidationError("Creating this dependency would create a circular dependency")

        # Create dependency
        dependency_id = str(uuid.uuid4())
        dependency = {
            "id": dependency_id,
            "source_task_id": dependency_data.source_task_id,
            "target_task_id": dependency_data.target_task_id,
            "dependency_type": dependency_data.dependency_type,
            "description": dependency_data.description,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "created_by": str(current_user.id),
            "project_id": project.id
        }

        dependencies_db[dependency_id] = dependency

        return {
            "success": True,
            "data": dependency,
            "message": "Dependency created successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create dependency: {str(e)}")

@router.get("/project/{project_id}")
async def get_project_dependencies(
    project_id: str,
    dependency_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all dependencies for a project"""
    try:
        # Verify project access
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise ResourceNotFoundError("Project not found")

        # Check permissions
        org_member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == project.organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
        org_member = org_member_result.scalar_one_or_none()
        if not org_member:
            raise InsufficientPermissionsError("Access denied to project")

        # Filter dependencies
        project_dependencies = [
            dep for dep in dependencies_db.values()
            if dep["project_id"] == project_id and dep["is_active"]
        ]

        if dependency_type:
            project_dependencies = [
                dep for dep in project_dependencies
                if dep["dependency_type"] == dependency_type
            ]

        return {
            "success": True,
            "data": project_dependencies,
            "message": f"Retrieved {len(project_dependencies)} dependencies"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dependencies: {str(e)}")

@router.post("/validate")
async def validate_dependencies(
    validation_data: DependencyValidationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Validate a set of dependencies for circular references and conflicts"""
    try:
        validation_results = []
        
        for dep in validation_data.dependencies:
            result = {
                "source_task_id": dep.source_task_id,
                "target_task_id": dep.target_task_id,
                "dependency_type": dep.dependency_type,
                "is_valid": True,
                "errors": []
            }

            # Check for circular dependency
            if await has_circular_dependency(dep.source_task_id, dep.target_task_id):
                result["is_valid"] = False
                result["errors"].append("Would create circular dependency")

            # Check for self-dependency
            if dep.source_task_id == dep.target_task_id:
                result["is_valid"] = False
                result["errors"].append("Task cannot depend on itself")

            # Check for duplicate dependency
            existing = await get_existing_dependency(dep.source_task_id, dep.target_task_id)
            if existing:
                result["is_valid"] = False
                result["errors"].append("Dependency already exists")

            validation_results.append(result)

        overall_valid = all(result["is_valid"] for result in validation_results)

        return {
            "success": True,
            "data": {
                "overall_valid": overall_valid,
                "validations": validation_results
            },
            "message": "Dependency validation completed"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate dependencies: {str(e)}")

@router.post("/visualization")
async def get_dependency_visualization(
    viz_data: DependencyVisualizationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dependency visualization data for a project"""
    try:
        # Verify project access
        project_result = await db.execute(
            select(Project).where(Project.id == viz_data.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise ResourceNotFoundError("Project not found")

        # Get all tasks in project
        tasks_result = await db.execute(
            select(Card)
            .options(
                selectinload(Card.column)
                .selectinload(Column.board)
            )
            .join(Column)
            .join(Board)
            .where(Board.project_id == viz_data.project_id)
        )
        tasks = tasks_result.scalars().all()

        # Get dependencies
        project_dependencies = [
            dep for dep in dependencies_db.values()
            if dep["project_id"] == viz_data.project_id and dep["is_active"]
        ]

        # Build visualization data
        nodes = []
        edges = []

        for task in tasks:
            if not viz_data.include_completed and task.status == "completed":
                continue

            nodes.append({
                "id": task.id,
                "label": task.title,
                "status": task.status,
                "priority": task.priority,
                "estimated_hours": task.estimated_hours,
                "column": task.column.name
            })

        for dep in project_dependencies:
            edges.append({
                "id": dep["id"],
                "source": dep["source_task_id"],
                "target": dep["target_task_id"],
                "type": dep["dependency_type"],
                "description": dep["description"]
            })

        return {
            "success": True,
            "data": {
                "nodes": nodes,
                "edges": edges,
                "layout": "hierarchical",
                "metadata": {
                    "total_tasks": len(nodes),
                    "total_dependencies": len(edges),
                    "max_depth": viz_data.max_depth
                }
            },
            "message": "Dependency visualization data generated"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate visualization: {str(e)}")

@router.post("/critical-path")
async def get_critical_path(
    path_data: CriticalPathRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Calculate critical path for project tasks"""
    try:
        # Verify project access
        project_result = await db.execute(
            select(Project).where(Project.id == path_data.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise ResourceNotFoundError("Project not found")

        # Get tasks and dependencies
        tasks_result = await db.execute(
            select(Card)
            .join(Column)
            .join(Board)
            .where(Board.project_id == path_data.project_id)
        )
        tasks = tasks_result.scalars().all()

        project_dependencies = [
            dep for dep in dependencies_db.values()
            if dep["project_id"] == path_data.project_id and dep["is_active"]
        ]

        # Calculate critical path using simplified algorithm
        critical_path = await calculate_critical_path(tasks, project_dependencies)

        return {
            "success": True,
            "data": {
                "critical_path": critical_path,
                "total_duration": sum(task["duration"] for task in critical_path),
                "bottlenecks": await identify_bottlenecks(tasks, project_dependencies),
                "recommendations": await generate_path_recommendations(critical_path)
            },
            "message": "Critical path calculated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate critical path: {str(e)}")

@router.delete("/{dependency_id}")
async def delete_dependency(
    dependency_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a task dependency"""
    try:
        if dependency_id not in dependencies_db:
            raise ResourceNotFoundError("Dependency not found")

        dependency = dependencies_db[dependency_id]

        # Check permissions (user must be creator or have admin rights)
        if dependency["created_by"] != str(current_user.id):
            # Check if user is admin/owner
            project_result = await db.execute(
                select(Project).where(Project.id == dependency["project_id"])
            )
            project = project_result.scalar_one_or_none()
            
            if project:
                org_member_result = await db.execute(
                    select(OrganizationMember).where(
                        OrganizationMember.organization_id == project.organization_id,
                        OrganizationMember.user_id == current_user.id,
                        OrganizationMember.role.in_(["owner", "admin"])
                    )
                )
                org_member = org_member_result.scalar_one_or_none()
                if not org_member:
                    raise InsufficientPermissionsError("Insufficient permissions to delete dependency")

        # Delete dependency
        del dependencies_db[dependency_id]

        return {
            "success": True,
            "message": "Dependency deleted successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete dependency: {str(e)}")

# Helper functions
async def has_circular_dependency(source_id: str, target_id: str) -> bool:
    """Check if creating a dependency would create a circular reference"""
    # Simple implementation - in production, use graph algorithms
    visited = set()
    
    def dfs(current_id: str, target: str) -> bool:
        if current_id == target:
            return True
        if current_id in visited:
            return False
        
        visited.add(current_id)
        
        # Find dependencies where current_id is the target
        for dep in dependencies_db.values():
            if dep["target_task_id"] == current_id and dep["is_active"]:
                if dfs(dep["source_task_id"], target):
                    return True
        
        return False
    
    return dfs(target_id, source_id)

async def get_existing_dependency(source_id: str, target_id: str) -> Optional[Dict[str, Any]]:
    """Check if dependency already exists"""
    for dep in dependencies_db.values():
        if (dep["source_task_id"] == source_id and 
            dep["target_task_id"] == target_id and 
            dep["is_active"]):
            return dep
    return None

async def calculate_critical_path(tasks: List[Card], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate critical path through tasks"""
    # Simplified critical path calculation
    # In production, implement proper CPM algorithm
    
    task_dict = {task.id: task for task in tasks}
    
    # Find tasks with no dependencies (start tasks)
    dependent_tasks = set(dep["target_task_id"] for dep in dependencies)
    start_tasks = [task for task in tasks if task.id not in dependent_tasks]
    
    # Build path from longest duration tasks
    critical_path = []
    for task in sorted(start_tasks, key=lambda t: t.estimated_hours or 0, reverse=True)[:3]:
        critical_path.append({
            "task_id": task.id,
            "title": task.title,
            "duration": task.estimated_hours or 0,
            "status": task.status
        })
    
    return critical_path

async def identify_bottlenecks(tasks: List[Card], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify potential bottlenecks in the project"""
    # Count dependencies for each task
    dependency_counts = {}
    for dep in dependencies:
        target_id = dep["target_task_id"]
        dependency_counts[target_id] = dependency_counts.get(target_id, 0) + 1
    
    # Find tasks with many dependencies
    bottlenecks = []
    for task_id, count in dependency_counts.items():
        if count >= 3:  # Threshold for bottleneck
            task = next((t for t in tasks if t.id == task_id), None)
            if task:
                bottlenecks.append({
                    "task_id": task_id,
                    "title": task.title,
                    "dependency_count": count,
                    "risk_level": "high" if count >= 5 else "medium"
                })
    
    return bottlenecks

async def generate_path_recommendations(critical_path: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations for optimizing critical path"""
    recommendations = []
    
    if len(critical_path) > 5:
        recommendations.append("Consider parallelizing some tasks to reduce overall duration")
    
    high_duration_tasks = [task for task in critical_path if task["duration"] > 40]
    if high_duration_tasks:
        recommendations.append("Break down large tasks into smaller, manageable subtasks")
    
    if any(task["status"] == "not_started" for task in critical_path):
        recommendations.append("Prioritize starting critical path tasks immediately")
    
    return recommendations
