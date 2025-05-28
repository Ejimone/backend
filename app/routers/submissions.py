from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Any, Dict
from uuid import UUID, uuid4

from models.schemas import WorkSubmission, WorkSubmissionCreate, User, Project, Contract
from db.firebase_ops import get_firestore_ops_instance, FirestoreBaseModel
from routers.auth import oauth2_scheme # For dependency
from core.security import decode_access_token # For decoding token
from datetime import datetime # For submission_date default

router = APIRouter(prefix="/projects/{project_id}/submissions", tags=["Work Submissions"])

@router.post("/", response_model=WorkSubmission, status_code=status.HTTP_201_CREATED)
async def submit_work_for_project(
    project_id: UUID,
    submission_in: WorkSubmissionCreate,
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

    target_project = firestore_ops.get(collection_name="projects", document_id=str(project_id), pydantic_model=Project)
    if not target_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Authorization
    if not target_project.freelancer_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project has no assigned freelancer.")
    if current_user_data.user_id != target_project.freelancer_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not the assigned freelancer for this project.")

    # Validation
    if target_project.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is not in progress.")

    # Optional: Check for active contract (basic check by existence)
    contracts = firestore_ops.query(
        collection_name="contracts",
        field="project_id",
        operator="==",
        value=project_id
    )
    active_contract_exists = any(c.get("freelancer_id") == target_project.freelancer_user_id and c.get("status") == "active" for c in contracts)
    if not active_contract_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active contract found for this project and freelancer.")


    submission_id = uuid4()
    
    # WorkSubmissionCreate schema: project_id, freelancer_id, files, notes
    # Path provides project_id. Token provides freelancer_id.
    # submission_in should provide files, notes.
    # We overwrite project_id and freelancer_id from submission_in with trusted sources.
    
    # Determine version number (simple increment based on existing submissions for this project)
    existing_submissions = firestore_ops.query(
        collection_name="submissions",
        field="project_id",
        operator="==",
        value=project_id,
        pydantic_model=WorkSubmission
    )
    current_version = 1
    if existing_submissions:
        current_version = max(sub.version for sub in existing_submissions if sub.version is not None) + 1


    submission_to_save = WorkSubmission(
        submission_id=submission_id,
        project_id=project_id, # From path
        freelancer_id=current_user_data.user_id, # From token
        files=submission_in.files,
        notes=submission_in.notes,
        version=current_version,
        # submission_date has a default in the Pydantic model
    )

    saved_submission_doc_id = firestore_ops.save(
        collection_name="submissions",
        data_model=submission_to_save.model_dump(),
        document_id=str(submission_id)
    )

    if not saved_submission_doc_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save work submission")

    # Update Project Status to 'awaiting_review'
    project_update_success = firestore_ops.update(
        collection_name="projects",
        document_id=str(project_id),
        updates={"status": "awaiting_review"}
    )
    if not project_update_success:
        # If project update fails, this is a partial success. Log and raise error.
        # A more complex rollback for submission isn't required by subtask.
        # For now, we'll let the submission be saved and raise an error for project update.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Work submitted successfully, but failed to update project status to 'awaiting_review'. Please notify admin."
        )
        
    return submission_to_save

@router.get("/", response_model=List[WorkSubmission])
async def list_submissions_for_project(
    project_id: UUID,
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

    target_project = firestore_ops.get(collection_name="projects", document_id=str(project_id), pydantic_model=Project)
    if not target_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Authorization
    is_client_owner = (current_user_data.user_id == target_project.client_user_id)
    is_assigned_freelancer = (target_project.freelancer_user_id and current_user_data.user_id == target_project.freelancer_user_id)

    if not (is_client_owner or is_assigned_freelancer):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view submissions for this project")

    project_submissions = firestore_ops.query(
        collection_name="submissions",
        field="project_id",
        operator="==",
        value=project_id,
        pydantic_model=WorkSubmission
    )
    
    # Firestore returns documents in an undefined order unless an `order_by` clause is used.
    # For simplicity, we'll sort them in Python if needed, or rely on client-side sorting.
    # Sorting by version:
    if project_submissions:
        project_submissions.sort(key=lambda sub: (sub.version is None, sub.version)) # Handles None versions

    return project_submissions

@router.post("/{submission_id}/approve", response_model=Dict[str, str])
async def approve_submission(
    project_id: UUID,
    submission_id: UUID,
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

    target_project = firestore_ops.get(collection_name="projects", document_id=str(project_id), pydantic_model=Project)
    if not target_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    target_submission = firestore_ops.get(collection_name="submissions", document_id=str(submission_id), pydantic_model=WorkSubmission)
    if not target_submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    # Authorization
    if current_user_data.user_id != target_project.client_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the project owner can approve submissions.")

    # Validation
    if target_submission.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submission does not belong to this project.")
    
    if target_project.status != "awaiting_review":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is not awaiting review.")

    # Update Project Status
    project_update_success = firestore_ops.update(
        collection_name="projects",
        document_id=str(project_id),
        updates={"status": "completed"}
    )
    if not project_update_success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update project status to 'completed'.")

    # Optional: Update Contract Status
    # Find active contract for this project involving the project's freelancer
    if target_project.freelancer_user_id: # Ensure freelancer is assigned
        contracts = firestore_ops.query(
            collection_name="contracts",
            field="project_id",
            operator="==",
            value=project_id,
            pydantic_model=Contract # Fetch as Contract to check fields
        )
        active_contract_for_freelancer = None
        for contract in contracts:
            if contract.freelancer_id == target_project.freelancer_user_id and contract.status == "active":
                active_contract_for_freelancer = contract
                break
        
        if active_contract_for_freelancer:
            contract_update_success = firestore_ops.update(
                collection_name="contracts",
                document_id=str(active_contract_for_freelancer.contract_id),
                updates={"status": "completed"}
            )
            if not contract_update_success:
                # Log this error, but the main operation (project completion) already succeeded.
                print(f"Warning: Project {project_id} completed, but failed to update contract {active_contract_for_freelancer.contract_id} status.")

    return {"message": "Submission approved. Project marked as completed."}
