from fastapi import APIRouter, HTTPException, Depends, status
from uuid import UUID, uuid4

from models.schemas import Project, ProjectCreate, User
from db.firebase_ops import get_firestore_ops_instance, FirestoreBaseModel
from routers.auth import oauth2_scheme # For dependency
from core.security import decode_access_token # For decoding token
from datetime import datetime
from typing import Any, Dict, List
router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    token: str = Depends(oauth2_scheme)
):
    firestore_ops: FirestoreBaseModel = get_firestore_ops_instance()
    
    user_id_from_token = decode_access_token(token)
    if not user_id_from_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_user_data = firestore_ops.get(collection_name="users", document_id=user_id_from_token, pydantic_model=User)
    if not current_user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user not found")

    if current_user_data.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only clients can create projects")

    project_id = uuid4()
    
    # ProjectCreate includes client_user_id, but we should ensure it matches the token user.
    # Or, more robustly, remove it from ProjectCreate and always set it from the token.
    # For now, we will overwrite it based on the token.
    
    project_data_dict = project_in.model_dump()
    project_data_dict['client_user_id'] = current_user_data.user_id # Set client_user_id from authenticated user
    
    # Create a Project Pydantic object
    # This will also set default values like creation_date, last_updated_date, project_id (if not provided)
    # and status (if defined with default in ProjectBase/Project schema)
    
    # Ensure all fields required by Project are present, including those with defaults
    # The Project schema has project_id with default_factory=uuid4, so we use our generated one.
    # creation_date and last_updated_date also have defaults.
    
    project_to_save = Project(
        project_id=project_id,
        client_user_id=current_user_data.user_id, # Ensure this is correctly assigned
        title=project_in.title,
        description=project_in.description,
        budget=project_in.budget,
        deadline=project_in.deadline,
        tags=project_in.tags,
        status=project_in.status, # This comes from ProjectCreate, which inherits from ProjectBase
        # creation_date and last_updated_date will be set by Pydantic default_factory
        # freelancer_user_id is Optional and defaults to None
    )

    # FirestoreBaseModel.save will handle created_at/updated_at based on its own logic
    # if they are part of the model it receives.
    # The Pydantic model Project already has these with defaults.
    # We can let Pydantic handle them, and FirestoreBaseModel can overwrite updated_at.
    
    saved_project_ref_id = firestore_ops.save(
        collection_name="projects", 
        data_model=project_to_save.model_dump(), # Pass the Pydantic model's dict representation
        document_id=str(project_id)
    )

    if not saved_project_ref_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create project")

    # Return the Project object. It should reflect what was saved.
    # The `project_to_save` object is already correctly populated.
    return project_to_save

@router.get("/", response_model=list[Project]) # Changed from Project to list[Project]
async def list_open_projects():
    firestore_ops: FirestoreBaseModel = get_firestore_ops_instance()
    
    # Query projects with status "open"
    open_projects = firestore_ops.query(
        collection_name="projects",
        field="status",
        operator="==",
        value="open",
        pydantic_model=Project
    )
    
    # If no projects are found, firestore_ops.query returns an empty list,
    # which is the correct response.
    return open_projects

@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: UUID,
    project_update_data: dict[str, Any], # Using Dict[str, Any] as specified
    token: str = Depends(oauth2_scheme)
):
    firestore_ops: FirestoreBaseModel = get_firestore_ops_instance()
    
    user_id_from_token = decode_access_token(token)
    if not user_id_from_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_user_data = firestore_ops.get(collection_name="users", document_id=user_id_from_token, pydantic_model=User)
    if not current_user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user not found")

    existing_project_data = firestore_ops.get(
        collection_name="projects",
        document_id=str(project_id),
        pydantic_model=Project # Fetch as Project model to easily access fields like client_user_id
    )
    if not existing_project_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if existing_project_data.client_user_id != current_user_data.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this project")

    # Ensure client_user_id and project_id are not changed by the update payload
    if "client_user_id" in project_update_data:
        del project_update_data["client_user_id"]
    if "project_id" in project_update_data:
        del project_update_data["project_id"]
    if "creation_date" in project_update_data: # Also protect creation_date
        del project_update_data["creation_date"]
        
    # The `last_updated_date` field will be automatically updated by FirestoreBaseModel.update()
    # if it's configured to do so, or by save() if using save() for updates.
    # Our FirestoreBaseModel.update() sets 'updated_at' (which matches Pydantic's last_updated_date via alias or name)

    if not project_update_data: # If payload is empty after removing protected fields
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update")

    success = firestore_ops.update(
        collection_name="projects",
        document_id=str(project_id),
        updates=project_update_data
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update project")

    # Fetch the updated project data from Firestore and return it
    updated_project = firestore_ops.get(
        collection_name="projects",
        document_id=str(project_id),
        pydantic_model=Project
    )
    if not updated_project: # Should not happen if update was successful
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found after update")
        
    return updated_project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    token: str = Depends(oauth2_scheme)
):
    from fastapi import Response # Local import for Response
    firestore_ops: FirestoreBaseModel = get_firestore_ops_instance()
    
    user_id_from_token = decode_access_token(token)
    if not user_id_from_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_user_data = firestore_ops.get(collection_name="users", document_id=user_id_from_token, pydantic_model=User)
    if not current_user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user not found")

    existing_project_data = firestore_ops.get(
        collection_name="projects",
        document_id=str(project_id),
        pydantic_model=Project # Fetch as Project model for authorization check
    )
    if not existing_project_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if existing_project_data.client_user_id != current_user_data.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this project")

    success = firestore_ops.delete(collection_name="projects", document_id=str(project_id))

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete project")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/{project_id}", response_model=Project)
async def get_project_details(project_id: UUID):
    firestore_ops: FirestoreBaseModel = get_firestore_ops_instance()
    
    project_data = firestore_ops.get(
        collection_name="projects",
        document_id=str(project_id),
        pydantic_model=Project
    )
    
    if not project_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    return project_data
