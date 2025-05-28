from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel

from models.schemas import Transaction, TransactionCreate, User, Project
from db.firebase_ops import get_firestore_ops_instance, FirestoreBaseModel
from routers.auth import oauth2_scheme # For dependency
from core.security import decode_access_token # For decoding token

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/checkout/project/{project_id}", response_model=Transaction, status_code=status.HTTP_201_CREATED)
async def checkout_project_payment(
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user (payer) not found")

    target_project = firestore_ops.get(collection_name="projects", document_id=str(project_id), pydantic_model=Project)
    if not target_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Authorization
    if current_user_data.user_id != target_project.client_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the project client can make this payment.")

    # Validation
    if target_project.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is not marked as completed.")
    
    if not target_project.freelancer_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project has no assigned freelancer to pay.")

    # Optional: Check for existing payment (simple check by project_id and type)
    existing_transactions = firestore_ops.query(
        collection_name="transactions",
        field="project_id",
        operator="==",
        value=project_id
    )
    for tr in existing_transactions:
        if tr.get("transaction_type") == "project_payment" and tr.get("status") == "completed":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment for this project has already been processed.")

    # Determine amount
    amount = target_project.budget
    if amount is None or amount <= 0:
        # Fallback: If budget is not set or invalid, try to find accepted bid amount.
        accepted_bid = None
        bids_for_project = firestore_ops.query(
            collection_name="bids",
            field="project_id",
            operator="==",
            value=project_id
        )
        for bid_data in bids_for_project:
            if bid_data.get("status") == "accepted" and bid_data.get("freelancer_user_id") == target_project.freelancer_user_id:
                accepted_bid = bid_data
                break
        
        if accepted_bid and accepted_bid.get("amount") is not None and accepted_bid.get("amount") > 0:
            amount = accepted_bid.get("amount")
        else:
            # If no valid budget on project and no accepted bid amount, raise error or use placeholder
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project budget is not set or invalid, and no accepted bid amount found.")
            # Or: amount = 0.0 # Placeholder if absolutely necessary, but better to error

    transaction_id = uuid4()

    transaction_to_save = Transaction(
        transaction_id=transaction_id,
        project_id=project_id,
        payer_user_id=current_user_data.user_id,
        payee_user_id=target_project.freelancer_user_id,
        amount=amount,
        currency="USD", # Default as per schema
        transaction_type="project_payment",
        status="completed", # Mocked successful payment
        # transaction_date will be set by Pydantic default_factory
    )

    saved_transaction_doc_id = firestore_ops.save(
        collection_name="transactions",
        data_model=transaction_to_save.model_dump(),
        document_id=str(transaction_id)
    )

    if not saved_transaction_doc_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not process payment transaction.")

    # Optional: Update project payment status (if a field like `payment_status` exists on Project model)
    # firestore_ops.update(
    #     collection_name="projects",
    #     document_id=str(project_id),
    #     updates={"payment_status": "paid"} # Example
    # )
        
    return transaction_to_save

@router.get("/history", response_model=List[Transaction])
async def get_payment_history(token: str = Depends(oauth2_scheme)):
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

    # Query 1: Transactions where the user is the payer
    payer_transactions = firestore_ops.query(
        collection_name="transactions",
        field="payer_user_id",
        operator="==",
        value=current_user_data.user_id,
        pydantic_model=Transaction
    )

    # Query 2: Transactions where the user is the payee
    payee_transactions = firestore_ops.query(
        collection_name="transactions",
        field="payee_user_id",
        operator="==",
        value=current_user_data.user_id,
        pydantic_model=Transaction
    )

    # Combine and de-duplicate results
    combined_transactions: Dict[UUID, Transaction] = {}
    for tx in payer_transactions:
        combined_transactions[tx.transaction_id] = tx
    for tx in payee_transactions:
        combined_transactions[tx.transaction_id] = tx # Overwrites if duplicate, which is fine

    all_user_transactions = list(combined_transactions.values())

    # Sort the combined list by transaction_date (descending)
    all_user_transactions.sort(key=lambda tx: tx.transaction_date, reverse=True)

    return all_user_transactions

class WithdrawalRequest(BaseModel): # Using Pydantic BaseModel for request body
    amount: float

@router.post("/withdraw", response_model=Transaction, status_code=status.HTTP_201_CREATED)
async def withdraw_funds(
    withdrawal_request: WithdrawalRequest, # Use the Pydantic model
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

    # Authorization
    if current_user_data.role != "freelancer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only freelancers can withdraw funds.")

    # Extract amount
    amount = withdrawal_request.amount
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or missing withdrawal amount.")

    # (Optional) Balance Check - Skipped for this mocked version

    transaction_id = uuid4()

    # Create Transaction Pydantic object
    # payer_user_id is None as the platform is paying out.
    # This is allowed because we made payer_user_id Optional[UUID] in Transaction schemas.
    transaction_to_save = Transaction(
        transaction_id=transaction_id,
        project_id=None, # Not tied to a specific project
        payer_user_id=None, # Platform is the payer
        payee_user_id=current_user_data.user_id, # Freelancer receiving funds
        amount=amount,
        currency="USD",
        transaction_type="withdrawal",
        status="pending", # Withdrawals often require processing
        # transaction_date will be set by Pydantic default_factory
    )

    saved_transaction_doc_id = firestore_ops.save(
        collection_name="transactions",
        data_model=transaction_to_save.model_dump(),
        document_id=str(transaction_id)
    )

    if not saved_transaction_doc_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not process withdrawal request.")
        
    return transaction_to_save
