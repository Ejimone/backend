from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any # Added Dict, Any
from uuid import UUID, uuid4

from models.schemas import Bid, BidCreate, User, Project, Contract # Added Contract
from db.firebase_ops import get_firestore_ops_instance, FirestoreBaseModel
from routers.auth import oauth2_scheme # For dependency
from core.security import decode_access_token # For decoding token
from datetime import datetime # For bid_date default

router = APIRouter(tags=["Bids"]) # No prefix here, paths will be specific
# Example paths to implement:
# POST /project/{project_id}/submit-bid
# GET /project/{project_id}/list-bids

@router.post("/project/{project_id}/submit-bid", response_model=Bid, status_code=status.HTTP_201_CREATED)
async def submit_bid_for_project(
    project_id: UUID,
    bid_in: BidCreate,
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

    if current_user_data.role != "freelancer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only freelancers can submit bids")

    target_project = firestore_ops.get(collection_name="projects", document_id=str(project_id), pydantic_model=Project)
    if not target_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if target_project.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is not open for bids.")

    # Check if this freelancer has already bid on this project
    existing_bids = firestore_ops.query(
        collection_name="bids",
        field="project_id", # Query by project_id first
        operator="==",
        value=project_id,
        pydantic_model=Bid 
    )
    for bid in existing_bids:
        if bid.freelancer_user_id == current_user_data.user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already submitted a bid for this project.")


    bid_id = uuid4()
    
    # BidCreate contains project_id and freelancer_user_id. We should ensure they are correctly set.
    # The schema for BidCreate: proposal, amount, estimated_completion_time, project_id, freelancer_user_id
    # The path provides project_id. The token provides freelancer_user_id.
    # bid_in should primarily provide proposal, amount, estimated_completion_time.
    # We will overwrite project_id and freelancer_user_id from bid_in with trusted sources.

    bid_to_save = Bid(
        bid_id=bid_id,
        project_id=project_id, # From path
        freelancer_user_id=current_user_data.user_id, # From token
        proposal=bid_in.proposal,
        amount=bid_in.amount,
        estimated_completion_time=bid_in.estimated_completion_time,
        # bid_date and status have defaults in the Bid Pydantic model
    )

    saved_bid_doc_id = firestore_ops.save(
        collection_name="bids",
        data_model=bid_to_save.model_dump(),
        document_id=str(bid_id)
    )

    if not saved_bid_doc_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not submit bid")

    return bid_to_save

@router.get("/project/{project_id}/list-bids", response_model=List[Bid])
async def list_bids_for_project(
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

    # Authorization: Only the client who owns the project should see all bids.
    if target_project.client_user_id != current_user_data.user_id:
        # Additional check: if the user is a freelancer, they should not be able to list all bids either,
        # unless they have a bid on this project (which is not the purpose of this endpoint).
        # This endpoint is primarily for the project owner (client).
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view bids for this project")

    project_bids = firestore_ops.query(
        collection_name="bids",
        field="project_id",
        operator="==",
        value=project_id, # Query by the UUID
        pydantic_model=Bid
    )
    
    return project_bids

from typing import Dict, Any # Added for Dict and Any

@router.get("/bids/{bid_id}", response_model=Bid)
async def get_bid_details(
    bid_id: UUID,
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

    target_bid = firestore_ops.get(collection_name="bids", document_id=str(bid_id), pydantic_model=Bid)
    if not target_bid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found")

    target_project = firestore_ops.get(collection_name="projects", document_id=str(target_bid.project_id), pydantic_model=Project)
    if not target_project:
        # This case might indicate data inconsistency if a bid exists for a non-existent project
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated project not found")

    # Authorization check
    is_bid_owner = (current_user_data.user_id == target_bid.freelancer_user_id)
    is_project_owner = (current_user_data.user_id == target_project.client_user_id)

    if not (is_bid_owner or is_project_owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this bid")
        
    return target_bid

@router.put("/bids/{bid_id}", response_model=Bid)
async def update_bid(
    bid_id: UUID,
    bid_update_data: Dict[str, Any],
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

    target_bid = firestore_ops.get(collection_name="bids", document_id=str(bid_id), pydantic_model=Bid)
    if not target_bid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found")

    # Authorization: Only the freelancer who made the bid can update/withdraw it.
    if current_user_data.user_id != target_bid.freelancer_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this bid")

    target_project = firestore_ops.get(collection_name="projects", document_id=str(target_bid.project_id), pydantic_model=Project)
    if not target_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated project not found")

    # Condition: Bid can only be updated/withdrawn if the project is still 'open' and the bid status is 'pending'.
    if target_project.status != "open" or target_bid.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bid cannot be modified at this stage. Project must be 'open' and bid 'pending'.")

    # Sanitize bid_update_data
    allowed_updates = {}
    for key, value in bid_update_data.items():
        if key in ["proposal", "amount", "estimated_completion_time", "status"]: # Add other updatable fields if any
            # Special handling for 'status': only 'withdrawn' is allowed by freelancer through this endpoint for now.
            if key == "status" and value != "withdrawn":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only 'withdrawn' status is allowed for self-update.")
            allowed_updates[key] = value
    
    if not allowed_updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update or invalid status value.")

    # The `updated_at` field will be handled by FirestoreBaseModel's update method.
    success = firestore_ops.update(
        collection_name="bids",
        document_id=str(bid_id),
        updates=allowed_updates
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update bid")

    updated_bid = firestore_ops.get(collection_name="bids", document_id=str(bid_id), pydantic_model=Bid)
    if not updated_bid: # Should not happen if update was successful
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found after update")
        
    return updated_bid

@router.post("/project/{project_id}/bid/{bid_id}/accept", response_model=Dict[str, str])
async def accept_bid(
    project_id: UUID,
    bid_id: UUID,
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

    # Authorization: Ensure current_user_data.user_id == target_project.client_user_id
    if current_user_data.user_id != target_project.client_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to accept bids for this project")

    target_bid = firestore_ops.get(collection_name="bids", document_id=str(bid_id), pydantic_model=Bid)
    if not target_bid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found")

    # Validation: Ensure target_bid.project_id == project_id
    if target_bid.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bid does not belong to this project.")

    # Validation: Ensure target_project.status == "open"
    if target_project.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is not open for new bids or is already in progress.")

    # Validation: Ensure target_bid.status == "pending"
    if target_bid.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bid is not in a pending state.")

    # Update Bid Status
    bid_update_success = firestore_ops.update(
        collection_name="bids",
        document_id=str(bid_id),
        updates={"status": "accepted"}
    )
    if not bid_update_success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update bid status.")

    # Update Project Status and Assign Freelancer
    project_update_success = firestore_ops.update(
        collection_name="projects",
        document_id=str(project_id),
        updates={
            "status": "in_progress",
            "freelancer_user_id": target_bid.freelancer_user_id
        }
    )
    if not project_update_success:
        # Attempt to revert bid status if project update fails
        firestore_ops.update(collection_name="bids", document_id=str(bid_id), updates={"status": "pending"})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update project status. Bid acceptance has been reverted.")

    # Optional: Reject other pending bids for this project
    other_bids = firestore_ops.query(
        collection_name="bids",
        field="project_id",
        operator="==",
        value=project_id,
        pydantic_model=Bid
    )
    for bid in other_bids:
        if bid.bid_id != bid_id and bid.status == "pending":
            firestore_ops.update(
                collection_name="bids",
                document_id=str(bid.bid_id),
                updates={"status": "rejected"}
            )
            # Failure to reject other bids is not critical enough to fail the whole operation,
            # but it could be logged.

    # 2. Create Contract Record
    contract_id = uuid4()
    now = datetime.utcnow()

    # Populate Contract object
    contract_to_save = Contract(
        contract_id=contract_id,
        project_id=target_project.project_id,
        client_id=target_project.client_user_id,
        freelancer_id=target_bid.freelancer_user_id,
        terms="Details as per project description and bid proposal.", # Default terms
        agreed_amount=target_bid.amount,
        start_date=now, # Or target_project.last_updated_date which should be recent
        end_date=None,  # Can be enhanced later
        status="active",
        # creation_date will be set by Pydantic model default_factory
    )

    saved_contract_doc_id = firestore_ops.save(
        collection_name="contracts",
        data_model=contract_to_save.model_dump(),
        document_id=str(contract_id)
    )

    if not saved_contract_doc_id:
        # If contract creation fails, the bid and project are already updated.
        # This is a partial failure. Log it and raise an error.
        # For now, we'll raise an HTTPException that indicates the main part succeeded but contract failed.
        # A more complex rollback isn't required for this subtask.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bid accepted and project updated, but failed to create contract record. Please check system logs."
        )

    return {"message": "Bid accepted, project in progress, and contract created."}
