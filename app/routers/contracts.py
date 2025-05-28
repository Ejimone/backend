from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any # Added Dict, Any
from uuid import UUID

from app.models.schemas import Contract, User
from app.db.firebase_ops import get_firestore_ops_instance, FirestoreBaseModel
from app.routers.auth import oauth2_scheme # For dependency
from app.core.security import decode_access_token # For decoding token

router = APIRouter(prefix="/contracts", tags=["Contracts"])

@router.get("/", response_model=List[Contract])
async def list_my_contracts(token: str = Depends(oauth2_scheme)):
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

    user_contracts = []
    id_field_to_query = None

    if current_user_data.role == "client":
        id_field_to_query = "client_id"
    elif current_user_data.role == "freelancer":
        id_field_to_query = "freelancer_id"
    else:
        # If user is not a client or freelancer, they would not have contracts in these roles.
        # Admins might have different logic, but that's out of scope for this endpoint.
        return [] 

    if id_field_to_query:
        user_contracts = firestore_ops.query(
            collection_name="contracts",
            field=id_field_to_query,
            operator="==",
            value=current_user_data.user_id, # Query by the UUID
            pydantic_model=Contract
        )
        
    return user_contracts

@router.get("/{contract_id}", response_model=Contract)
async def get_contract_details(
    contract_id: UUID,
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

    target_contract = firestore_ops.get(collection_name="contracts", document_id=str(contract_id), pydantic_model=Contract)
    if not target_contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    # Authorization check
    is_client = (current_user_data.user_id == target_contract.client_id)
    is_freelancer = (current_user_data.user_id == target_contract.freelancer_id)

    if not (is_client or is_freelancer):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this contract")
        
    return target_contract

VALID_CONTRACT_STATUSES = ["active", "completed", "terminated", "disputed"]

@router.put("/{contract_id}/status", response_model=Contract)
async def update_contract_status(
    contract_id: UUID,
    status_update: Dict[str, str], # Expects {"status": "new_status_value"}
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

    target_contract = firestore_ops.get(collection_name="contracts", document_id=str(contract_id), pydantic_model=Contract)
    if not target_contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    # Authorization check
    is_client = (current_user_data.user_id == target_contract.client_id)
    is_freelancer = (current_user_data.user_id == target_contract.freelancer_id)

    if not (is_client or is_freelancer):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this contract's status")

    new_status = status_update.get("status")
    if not new_status or new_status not in VALID_CONTRACT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid or missing status in request body. Valid statuses are: {', '.join(VALID_CONTRACT_STATUSES)}."
        )

    # Update the contract's status
    success = firestore_ops.update(
        collection_name="contracts",
        document_id=str(contract_id),
        updates={"status": new_status, "last_updated_date": datetime.utcnow()} # Explicitly set last_updated_date for Pydantic model
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update contract status")

    # Fetch the updated contract to return
    updated_contract = firestore_ops.get(collection_name="contracts", document_id=str(contract_id), pydantic_model=Contract)
    if not updated_contract: # Should not happen if update was successful
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found after update")
        
    return updated_contract
