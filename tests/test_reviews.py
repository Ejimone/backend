import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, call
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.main import app # FastAPI application
from app.models.schemas import Review, User, Project, FreelancerProfile, ReviewCreate

client = TestClient(app)

MOCK_REVIEWS_TOKEN_USER_ID = "mock-reviews-user-id"

@pytest.fixture
def mock_firestore_ops_reviews():
    mock_ops = MagicMock()
    mock_ops.get.return_value = None
    mock_ops.query.return_value = []
    mock_ops.save.side_effect = lambda collection_name, data_model, document_id: document_id
    mock_ops.update.return_value = True
    return mock_ops

@pytest.fixture
def mock_decode_token_reviews(monkeypatch):
    """Mocks decode_access_token for review routes to return a fixed user ID."""
    mock_decoder = MagicMock(return_value=MOCK_REVIEWS_TOKEN_USER_ID)
    monkeypatch.setattr("app.routers.reviews.decode_access_token", mock_decoder)
    return mock_decoder

# Helper functions
def create_mock_user_reviews(user_id_str: str, role="client", username_prefix="revuser"):
    try:
        uid = UUID(user_id_str)
    except ValueError:
        # Fallback for cases where MOCK_REVIEWS_TOKEN_USER_ID might not be a perfect UUID string
        # although it should be for consistency with User model's user_id: UUID
        uid = uuid4() 
    return User(
        user_id=uid,
        username=f"{username_prefix}_{user_id_str[:8]}",
        email=f"{username_prefix}_{user_id_str[:8]}@example.com",
        full_name=f"Test User {user_id_str[:8]}",
        role=role,
        is_active=True,
        registration_date=datetime.now(timezone.utc),
    )

def create_mock_project_reviews(
    project_id: Optional[UUID] = None, 
    client_user_id: Optional[UUID] = None, 
    freelancer_user_id: Optional[UUID] = None, 
    status="completed", # Default to completed for review tests
    title="Test Project for Reviews"
):
    return Project(
        project_id=project_id if project_id else uuid4(),
        client_user_id=client_user_id if client_user_id else uuid4(),
        freelancer_user_id=freelancer_user_id,
        title=title,
        description="A test project description for reviews.",
        budget=100.0,
        status=status,
        creation_date=datetime.now(timezone.utc),
        last_updated_date=datetime.now(timezone.utc),
        tags=["review", "test"]
    )

def create_mock_review_reviews(
    review_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    reviewer_user_id: Optional[UUID] = None,
    reviewee_user_id: Optional[UUID] = None,
    rating: int = 5,
    comment: str = "Excellent work!"
):
    return Review(
        review_id=review_id if review_id else uuid4(),
        project_id=project_id if project_id else uuid4(),
        reviewer_user_id=reviewer_user_id if reviewer_user_id else uuid4(),
        reviewee_user_id=reviewee_user_id if reviewee_user_id else uuid4(),
        rating=rating,
        comment=comment,
        review_date=datetime.now(timezone.utc)
    )

def create_mock_freelancer_profile_reviews(
    user_id: Optional[UUID] = None,
    average_rating: Optional[float] = None
):
    return FreelancerProfile(
        user_id=user_id if user_id else uuid4(),
        skills=["testing"],
        average_rating=average_rating
    )

# --- Tests for POST /reviews/ (Submit Review) ---

def test_submit_review_client_reviews_freelancer_success(mock_firestore_ops_reviews, mock_decode_token_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)

    client_id_obj = UUID(MOCK_REVIEWS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_reviews(MOCK_REVIEWS_TOKEN_USER_ID, role="client")
    
    freelancer_id_obj = uuid4()
    # mock_freelancer_user = create_mock_user_reviews(str(freelancer_id_obj), role="freelancer", username_prefix="freelance")
    
    test_project_id = uuid4()
    mock_project = create_mock_project_reviews(project_id=test_project_id, client_user_id=client_id_obj, freelancer_user_id=freelancer_id_obj, status="completed")

    mock_firestore_ops_reviews.get.side_effect = [mock_client_user, mock_project] # User, then Project
    mock_firestore_ops_reviews.query.side_effect = [
        [], # No existing review by this client for this freelancer on this project
        [{"rating": 5}, {"rating": 3}] # Mock reviews for average rating calculation
    ]
    mock_firestore_ops_reviews.save.return_value = str(uuid4()) # New review_id
    mock_firestore_ops_reviews.update.return_value = True # Freelancer profile update

    review_data = ReviewCreate(
        project_id=test_project_id,
        reviewer_user_id=client_id_obj,
        reviewee_user_id=freelancer_id_obj,
        rating=5,
        comment="Great job by freelancer!"
    )

    response = client.post("/reviews/", json=review_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 201
    data = response.json()
    assert data["reviewer_user_id"] == MOCK_REVIEWS_TOKEN_USER_ID
    assert data["reviewee_user_id"] == str(freelancer_id_obj)
    assert data["rating"] == 5
    
    mock_firestore_ops_reviews.save.assert_called_once()
    args_save, kwargs_save = mock_firestore_ops_reviews.save.call_args
    assert kwargs_save['collection_name'] == 'reviews'
    assert kwargs_save['data_model']['rating'] == 5
    
    # Check freelancer profile update for average rating
    mock_firestore_ops_reviews.update.assert_called_once()
    args_update, kwargs_update = mock_firestore_ops_reviews.update.call_args
    assert kwargs_update['collection_name'] == 'freelancer_profiles'
    assert kwargs_update['document_id'] == str(freelancer_id_obj)
    assert "average_rating" in kwargs_update['updates']
    # Based on mocked reviews of [5, 3] and new review of 5, the new average would be (5+3+5)/3 = 4.33...
    # The endpoint logic for query is: all_freelancer_reviews_data = firestore_ops.query(field="reviewee_user_id")
    # This query mock was for the second query call: `[{"rating": 5}, {"rating": 3}]`
    # The new review (5) is added to this in calculation logic if it's part of the query result, or considered separately.
    # The code is: sum(r.get("rating", 0) for r in all_freelancer_reviews_data)
    # If the new review is not in all_freelancer_reviews_data, then it's (5+3)/2 = 4.0.
    # Let's adjust the mock to include the current review in the query for average rating.
    # The logic in submit_review queries for *all* reviews for the reviewee.
    # So, if save happens first, the query for avg rating should include the new review.
    # If query for avg rating happens conceptually "after" this review is considered submitted,
    # then the number of reviews would be 2 (from mock) + 1 (current).
    # Let's assume the query for average calculation gets all reviews including the current one.
    # To simplify, let's say the query returns reviews that *would* exist if this one is added.
    # The code gets all reviews for the reviewee.
    # If the current review is already saved before calculating, the query will pick it up.
    # If not, the current review's rating needs to be manually included.
    # The code queries all reviews for the reviewee_user_id. This will include the one just saved.
    # So, if query mock is `[{"rating": 5}, {"rating": 3}]` and new is 5, sum is 13, count is 3. avg = 4.33
    # If query mock `[{"rating": 5}, {"rating": 3}]` *doesn't include the current review*, then sum is 8, count is 2, avg is 4.
    # Let's assume query returns all *previously existing* reviews. The new one isn't there yet.
    # The current code for avg rating: queries *all* reviews for reviewee_user_id.
    # This means the just-saved review IS part of `all_freelancer_reviews_data`.
    # So, if query returns [{"rating":5}, {"rating":3}] *before* the new review is added by the query,
    # then the code's logic for average rating will be based on those + the current.
    # This is tricky. Let's assume the query for avg rating gets all reviews *including* the one just saved.
    # So if mock_firestore_ops.query returns `[new_review_dict, old_review1_dict, old_review2_dict]`
    # For this test, let's say the query for avg rating returns the newly saved review + others.
    # `all_freelancer_reviews_data` will contain the new review.
    # If previous reviews were rating 4, and new is 5. Total 2 reviews. Avg (4+5)/2 = 4.5
    # If `query.side_effect` for `all_freelancer_reviews_data` returns `[{"rating": 4, ...}, {"rating": 5, ...}]` (this new one + one old one)
    # total_rating = 9, num_reviews = 2, new_average_rating = 4.5
    assert kwargs_update['updates']['average_rating'] == 4.0 # (5+3)/2 because the query mock for avg rating is just those two.


def test_submit_review_freelancer_reviews_client_success(mock_firestore_ops_reviews, mock_decode_token_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)

    freelancer_id_obj = UUID(MOCK_REVIEWS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_reviews(MOCK_REVIEWS_TOKEN_USER_ID, role="freelancer")
    
    client_id_obj = uuid4()
    test_project_id = uuid4()
    mock_project = create_mock_project_reviews(project_id=test_project_id, client_user_id=client_id_obj, freelancer_user_id=freelancer_id_obj, status="completed")

    mock_firestore_ops_reviews.get.side_effect = [mock_freelancer_user, mock_project]
    mock_firestore_ops_reviews.query.return_value = [] # No existing review

    review_data = ReviewCreate(
        project_id=test_project_id,
        reviewer_user_id=freelancer_id_obj,
        reviewee_user_id=client_id_obj,
        rating=4,
        comment="Good client!"
    )
    response = client.post("/reviews/", json=review_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 201
    data = response.json()
    assert data["reviewer_user_id"] == MOCK_REVIEWS_TOKEN_USER_ID
    assert data["reviewee_user_id"] == str(client_id_obj)
    
    mock_firestore_ops_reviews.save.assert_called_once()
    mock_firestore_ops_reviews.update.assert_not_called() # No client average rating update

def test_submit_review_reviewer_id_mismatch(mock_firestore_ops_reviews, mock_decode_token_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)
    mock_user = create_mock_user_reviews(MOCK_REVIEWS_TOKEN_USER_ID) # Token user
    mock_firestore_ops_reviews.get.return_value = mock_user

    review_data = ReviewCreate(project_id=uuid4(), reviewer_user_id=uuid4(), reviewee_user_id=uuid4(), rating=5) # Different reviewer_id
    response = client.post("/reviews/", json=review_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert "Reviewer ID in request does not match authenticated user" in response.json()["detail"]

def test_submit_review_project_not_completed(mock_firestore_ops_reviews, mock_decode_token_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)
    user_id_obj = UUID(MOCK_REVIEWS_TOKEN_USER_ID)
    mock_user = create_mock_user_reviews(MOCK_REVIEWS_TOKEN_USER_ID)
    mock_project = create_mock_project_reviews(status="in_progress") # Not completed
    mock_firestore_ops_reviews.get.side_effect = [mock_user, mock_project]

    review_data = ReviewCreate(project_id=mock_project.project_id, reviewer_user_id=user_id_obj, reviewee_user_id=uuid4(), rating=5)
    response = client.post("/reviews/", json=review_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert "Reviews can only be submitted for completed projects" in response.json()["detail"]

def test_submit_review_invalid_reviewee_client(mock_firestore_ops_reviews, mock_decode_token_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)
    client_id_obj = UUID(MOCK_REVIEWS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_reviews(MOCK_REVIEWS_TOKEN_USER_ID, role="client")
    mock_project = create_mock_project_reviews(client_user_id=client_id_obj, freelancer_user_id=uuid4()) # Freelancer A
    mock_firestore_ops_reviews.get.side_effect = [mock_client_user, mock_project]

    review_data = ReviewCreate(project_id=mock_project.project_id, reviewer_user_id=client_id_obj, reviewee_user_id=uuid4(), rating=5) # Reviewing Freelancer B
    response = client.post("/reviews/", json=review_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert "Client can only review the assigned freelancer" in response.json()["detail"]
    
def test_submit_review_invalid_reviewee_freelancer(mock_firestore_ops_reviews, mock_decode_token_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)
    freelancer_id_obj = UUID(MOCK_REVIEWS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_reviews(MOCK_REVIEWS_TOKEN_USER_ID, role="freelancer")
    mock_project = create_mock_project_reviews(client_user_id=uuid4(), freelancer_user_id=freelancer_id_obj) # Client A
    mock_firestore_ops_reviews.get.side_effect = [mock_freelancer_user, mock_project]

    review_data = ReviewCreate(project_id=mock_project.project_id, reviewer_user_id=freelancer_id_obj, reviewee_user_id=uuid4(), rating=5) # Reviewing Client B
    response = client.post("/reviews/", json=review_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert "Freelancer can only review the client" in response.json()["detail"]

def test_submit_review_not_involved_in_project(mock_firestore_ops_reviews, mock_decode_token_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)
    reviewer_id_obj = UUID(MOCK_REVIEWS_TOKEN_USER_ID)
    mock_reviewer_user = create_mock_user_reviews(MOCK_REVIEWS_TOKEN_USER_ID, role="client") # A client, but not of this project
    mock_project = create_mock_project_reviews(client_user_id=uuid4(), freelancer_user_id=uuid4()) # Project by others
    mock_firestore_ops_reviews.get.side_effect = [mock_reviewer_user, mock_project]

    review_data = ReviewCreate(project_id=mock_project.project_id, reviewer_user_id=reviewer_id_obj, reviewee_user_id=mock_project.freelancer_user_id, rating=5)
    response = client.post("/reviews/", json=review_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert "Not authorized to review this project" in response.json()["detail"]

def test_submit_review_duplicate_review(mock_firestore_ops_reviews, mock_decode_token_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)
    client_id_obj = UUID(MOCK_REVIEWS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_reviews(MOCK_REVIEWS_TOKEN_USER_ID, role="client")
    freelancer_id_obj = uuid4()
    mock_project = create_mock_project_reviews(client_user_id=client_id_obj, freelancer_user_id=freelancer_id_obj)
    
    mock_firestore_ops_reviews.get.side_effect = [mock_client_user, mock_project]
    # Simulate existing review
    existing_review = create_mock_review_reviews(project_id=mock_project.project_id, reviewer_user_id=client_id_obj, reviewee_user_id=freelancer_id_obj)
    mock_firestore_ops_reviews.query.return_value = [existing_review.model_dump()] # Query returns it as dict

    review_data = ReviewCreate(
        project_id=mock_project.project_id,
        reviewer_user_id=client_id_obj,
        reviewee_user_id=freelancer_id_obj,
        rating=3, comment="Another try"
    )
    response = client.post("/reviews/", json=review_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert "You have already submitted a review for this user on this project" in response.json()["detail"]

# --- Tests for GET /reviews/user/{user_id} ---

def test_get_reviews_for_user_success(mock_firestore_ops_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)
    
    reviewee_id = uuid4()
    mock_reviewee_user = create_mock_user_reviews(str(reviewee_id))
    mock_firestore_ops_reviews.get.return_value = mock_reviewee_user # For user existence check
    
    reviews_list = [
        create_mock_review_reviews(reviewee_user_id=reviewee_id, review_date=datetime.now(timezone.utc) - timedelta(days=1)),
        create_mock_review_reviews(reviewee_user_id=reviewee_id, review_date=datetime.now(timezone.utc))
    ]
    mock_firestore_ops_reviews.query.return_value = reviews_list
    
    response = client.get(f"/reviews/user/{reviewee_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["review_id"] == str(reviews_list[1].review_id) # Sorted desc by date
    
    mock_firestore_ops_reviews.query.assert_called_once_with(
        collection_name="reviews", field="reviewee_user_id", operator="==", value=reviewee_id, pydantic_model=Review
    )

def test_get_reviews_for_user_not_found(mock_firestore_ops_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)
    mock_firestore_ops_reviews.get.return_value = None # User not found
    
    response = client.get(f"/reviews/user/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "User (reviewee) not found"

def test_get_reviews_for_user_no_reviews(mock_firestore_ops_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)
    reviewee_id = uuid4()
    mock_reviewee_user = create_mock_user_reviews(str(reviewee_id))
    mock_firestore_ops_reviews.get.return_value = mock_reviewee_user
    mock_firestore_ops_reviews.query.return_value = [] # No reviews
    
    response = client.get(f"/reviews/user/{reviewee_id}")
    assert response.status_code == 200
    assert response.json() == []

# --- Tests for GET /reviews/project/{project_id} ---

def test_get_reviews_for_project_success(mock_firestore_ops_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)
    
    test_project_id = uuid4()
    mock_project = create_mock_project_reviews(project_id=test_project_id)
    mock_firestore_ops_reviews.get.return_value = mock_project # Project exists
    
    reviews_list = [
        create_mock_review_reviews(project_id=test_project_id, review_date=datetime.now(timezone.utc) - timedelta(hours=1)),
        create_mock_review_reviews(project_id=test_project_id, review_date=datetime.now(timezone.utc))
    ]
    mock_firestore_ops_reviews.query.return_value = reviews_list
    
    response = client.get(f"/reviews/project/{test_project_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["review_id"] == str(reviews_list[1].review_id) # Sorted desc
    
    mock_firestore_ops_reviews.query.assert_called_once_with(
        collection_name="reviews", field="project_id", operator="==", value=test_project_id, pydantic_model=Review
    )

def test_get_reviews_for_project_not_found(mock_firestore_ops_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)
    mock_firestore_ops_reviews.get.return_value = None # Project not found
    
    response = client.get(f"/reviews/project/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"

def test_get_reviews_for_project_no_reviews(mock_firestore_ops_reviews, monkeypatch):
    monkeypatch.setattr("app.routers.reviews.get_firestore_ops_instance", lambda: mock_firestore_ops_reviews)
    test_project_id = uuid4()
    mock_project = create_mock_project_reviews(project_id=test_project_id)
    mock_firestore_ops_reviews.get.return_value = mock_project
    mock_firestore_ops_reviews.query.return_value = [] # No reviews
    
    response = client.get(f"/reviews/project/{test_project_id}")
    assert response.status_code == 200
    assert response.json() == []

from datetime import timedelta # Add timedelta for time manipulation in tests
