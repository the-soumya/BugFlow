from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectRequest
from app.exceptions import ResourceNotFound, DuplicateKey

def create_project(db: Session, request: ProjectRequest, creator: User) -> Project:
    # Validate unique key
    existing_project = db.query(Project).filter(Project.project_key == request.project_key).first()
    if existing_project:
        raise DuplicateKey(f"Project key '{request.project_key}' is already taken")

    project = Project(
        name=request.name,
        description=request.description,
        project_key=request.project_key.upper(),
        active=True,
        created_by_id=creator.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

def get_projects(db: Session, active_only: bool = True) -> List[Project]:
    query = db.query(Project)
    if active_only:
        query = query.filter(Project.active == True)
    return query.all()

def get_project(db: Session, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ResourceNotFound(f"Project with ID {project_id} not found")
    return project

def update_project(db: Session, project_id: int, request: ProjectRequest) -> Project:
    project = get_project(db, project_id)
    
    # If key changed, validate uniqueness
    if project.project_key != request.project_key.upper():
        existing_project = db.query(Project).filter(Project.project_key == request.project_key.upper()).first()
        if existing_project:
            raise DuplicateKey(f"Project key '{request.project_key}' is already taken")
    
    project.name = request.name
    project.description = request.description
    project.project_key = request.project_key.upper()
    
    db.commit()
    db.refresh(project)
    return project

def delete_project(db: Session, project_id: int) -> Project:
    project = get_project(db, project_id)
    project.active = False  # Soft delete as requested
    db.commit()
    db.refresh(project)
    return project
