from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from typing import Dict, Any, Union

from models.schemas import User, ClientProfile, FreelancerProfile, ClientProfileCreate, FreelancerProfileCreate
from db.firebase_ops import get_firestore_ops_instance, FirestoreBaseModel
from routers.auth import oauth2_scheme # For dependency, might move to core.dependencies later
from core.security import decode_access_token # For decoding token

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/{user_id}", response_model=User)
async def get_user_profile(user_id: UUID):
    firestore_ops: FirestoreBaseModel = get_firestore_ops_instance()
    
    user_data = firestore_ops.get(collection_name="users", document_id=str(user_id), pydantic_model=User)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # For now, this returns the base User model.
    # Future enhancements can include fetching and merging ClientProfile or FreelancerProfile
    # based on user_data.role.
    return user_data

@router.put("/me/profile", response_model=Dict[str, Any]) # Using Dict for now, can be more specific later
async def update_user_profile(
    profile_data: Dict[str, Any], # Generic for now, can be Union[ClientProfileCreate, FreelancerProfileCreate]
    token: str = Depends(oauth2_scheme)
):
    firestore_ops: FirestoreBaseModel = get_firestore_ops_instance()
    
    user_id_from_token = decode_access_token(token)
    if not user_id_from_token:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch the current user to get their role
    current_user_data = firestore_ops.get(collection_name="users", document_id=user_id_from_token, pydantic_model=User)
    if not current_user_data:
        raise HTTPException(status_code=404, detail="Current user not found")

    user_role = current_user_data.role
    user_id_str = str(current_user_data.user_id) # Ensure it's a string for Firestore document ID

    collection_name = None
    profile_schema_create = None
    ProfileModel = None # The Pydantic model for the full profile (User + SpecificProfile)

    if user_role == "client":
        collection_name = "client_profiles"
        # In a more robust implementation, we'd validate profile_data against ClientProfileCreate
        # For now, we directly pass profile_data for update.
        # Example: profile_to_save = ClientProfileCreate(**profile_data).model_dump(exclude_unset=True)
        # And the response model might be ClientProfile
    elif user_role == "freelancer":
        collection_name = "freelancer_profiles"
        # Example: profile_to_save = FreelancerProfileCreate(**profile_data).model_dump(exclude_unset=True)
        # And the response model might be FreelancerProfile
    else:
        raise HTTPException(status_code=400, detail=f"User role '{user_role}' does not support profiles.")

    # We'll use save with document_id, which acts like upsert if the document exists or creates it.
    # FirestoreBaseModel's save method handles created_at/updated_at.
    # The profile_data should be the specific profile fields (e.g., company_name for client)
    # not the base User fields.
    
    # We should also include user_id in the profile document for reference
    data_to_save = profile_data.copy()
    data_to_save["user_id"] = current_user_data.user_id # Store UUID

    saved_profile_id = firestore_ops.save(
        collection_name=collection_name,
        data_model=data_to_save, # Pass the raw dict for now
        document_id=user_id_str
    )

    if not saved_profile_id:
        raise HTTPException(status_code=500, detail=f"Could not update/create {user_role} profile.")

    # Fetch the updated profile to return (optional, or just return success)
    # updated_profile_data = firestore_ops.get(collection_name, user_id_str)

    return {"message": f"{user_role.capitalize()} profile updated successfully", "user_id": user_id_str}
