from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime

from models.schemas import Review, ReviewCreate, User, Project, FreelancerProfile
from db.firebase_ops import get_firestore_ops_instance, FirestoreBaseModel
from routers.auth import oauth2_scheme # For dependency
from core.security import decode_access_token # For decoding token

router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("/", response_model=Review, status_code=status.HTTP_201_CREATED)
async def submit_review(
    review_in: ReviewCreate,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user (Reviewer) not found")

    # Validation: Ensure review_in.reviewer_user_id == current_user_data.user_id
    if review_in.reviewer_user_id != current_user_data.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reviewer ID in request does not match authenticated user.")

    target_project = firestore_ops.get(collection_name="projects", document_id=str(review_in.project_id), pydantic_model=Project)
    if not target_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if target_project.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reviews can only be submitted for completed projects.")

    # Reviewer/Reviewee Validation
    is_reviewer_client = (current_user_data.user_id == target_project.client_user_id)
    is_reviewer_freelancer = (target_project.freelancer_user_id and current_user_data.user_id == target_project.freelancer_user_id)

    if is_reviewer_client:
        if review_in.reviewee_user_id != target_project.freelancer_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client can only review the assigned freelancer for this project.")
    elif is_reviewer_freelancer:
        if review_in.reviewee_user_id != target_project.client_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Freelancer can only review the client for this project.")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to review this project.")

    # Prevent Duplicate Reviews
    # A review is unique by (project_id, reviewer_user_id, reviewee_user_id)
    # We can query for a review that matches all three.
    # Firestore doesn't support multiple '==' on different fields directly in a simple query without composite indexes.
    # A simpler check is to query by project_id and reviewer_user_id, then filter reviewee_user_id.
    
    existing_reviews = firestore_ops.query(
        collection_name="reviews",
        field="project_id",
        operator="==",
        value=review_in.project_id
    ) # This returns list of dicts or Pydantic models if pydantic_model is passed
    
    for rev_data in existing_reviews:
        # Assuming rev_data is a dict, if pydantic_model wasn't used or failed.
        # If firestore_ops.query returns Pydantic models directly:
        # if rev_data.reviewer_user_id == review_in.reviewer_user_id and \
        #    rev_data.reviewee_user_id == review_in.reviewee_user_id:
        
        # If rev_data is a dictionary (default from FirestoreBaseModel.query without Pydantic model)
        if rev_data.get("reviewer_user_id") == review_in.reviewer_user_id and \
           rev_data.get("reviewee_user_id") == review_in.reviewee_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already submitted a review for this user on this project.")


    review_id = uuid4()
    review_to_save = Review(
        review_id=review_id,
        **review_in.model_dump()
        # review_date has a default in the Pydantic model
    )

    saved_review_doc_id = firestore_ops.save(
        collection_name="reviews",
        data_model=review_to_save.model_dump(),
        document_id=str(review_id)
    )

    if not saved_review_doc_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save review.")

    # (Optional) Update Freelancer's Average Rating
    if is_reviewer_client and target_project.freelancer_user_id: # Review is for the freelancer
        freelancer_id_to_update = target_project.freelancer_user_id
        
        all_freelancer_reviews_data = firestore_ops.query(
            collection_name="reviews",
            field="reviewee_user_id",
            operator="==",
            value=freelancer_id_to_update
        )
        
        if all_freelancer_reviews_data:
            total_rating = sum(r.get("rating", 0) for r in all_freelancer_reviews_data)
            num_reviews = len(all_freelancer_reviews_data)
            new_average_rating = round(total_rating / num_reviews, 2) if num_reviews > 0 else 0.0
            
            # Update FreelancerProfile (assuming collection 'freelancer_profiles', doc_id is user_id)
            profile_update_success = firestore_ops.update(
                collection_name="freelancer_profiles",
                document_id=str(freelancer_id_to_update),
                updates={"average_rating": new_average_rating}
            )
            if not profile_update_success:
                # Log this error, but the review was already saved.
                print(f"Warning: Review {review_id} saved, but failed to update average rating for freelancer {freelancer_id_to_update}.")
        
    return review_to_save

@router.get("/user/{user_id}", response_model=List[Review])
async def get_reviews_for_user(user_id: UUID):
    firestore_ops: FirestoreBaseModel = get_firestore_ops_instance()

    # Fetch the user being reviewed to ensure they exist
    reviewee_user = firestore_ops.get(collection_name="users", document_id=str(user_id), pydantic_model=User)
    if not reviewee_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User (reviewee) not found")

    user_reviews = firestore_ops.query(
        collection_name="reviews",
        field="reviewee_user_id",
        operator="==",
        value=user_id,
        pydantic_model=Review
    )

    if user_reviews:
        user_reviews.sort(key=lambda rev: rev.review_date, reverse=True)
        
    return user_reviews

@router.get("/project/{project_id}", response_model=List[Review])
async def get_reviews_for_project(project_id: UUID):
    firestore_ops: FirestoreBaseModel = get_firestore_ops_instance()

    # Fetch the project to ensure it exists
    target_project = firestore_ops.get(collection_name="projects", document_id=str(project_id), pydantic_model=Project)
    if not target_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    project_reviews = firestore_ops.query(
        collection_name="reviews",
        field="project_id",
        operator="==",
        value=project_id,
        pydantic_model=Review
    )

    if project_reviews:
        project_reviews.sort(key=lambda rev: rev.review_date, reverse=True)
        
    return project_reviews
