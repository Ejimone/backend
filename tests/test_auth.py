import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock # patch can also be used

from app.main import app # FastAPI application
from app.models.schemas import User # For type hinting or validation if needed
# from app.db.firebase_ops import get_firestore_ops_instance, FirestoreBaseModel # Not directly used here due to mocking strategy

# Initialize TestClient
client = TestClient(app)

@pytest.fixture
def mock_firestore_ops():
    """
    Provides a MagicMock instance simulating FirestoreBaseModel.
    This mock is configured for general successful operations unless overridden in a test.
    """
    mock_ops_instance = MagicMock()
    
    # Default behavior for query (no user exists)
    mock_ops_instance.query.return_value = [] 
    
    # Default behavior for save (successful save returns the document_id passed to it)
    # This mimics the behavior of FirestoreBaseModel.save when document_id is provided.
    mock_ops_instance.save.side_effect = lambda collection_name, data_model, document_id: document_id
    
    return mock_ops_instance

def test_register_user_success(mock_firestore_ops, monkeypatch): # Fixture is passed directly
    """Test successful user registration."""
    # Replace the actual get_firestore_ops_instance with a lambda that returns our mock
    monkeypatch.setattr("app.routers.auth.get_firestore_ops_instance", lambda: mock_firestore_ops)
    
    response = client.post(
        "/auth/register", # Path as defined in app.routers.auth
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User",
            "role": "client" 
        },
    )
    assert response.status_code == 200 # Default status code for POST in FastAPI unless specified
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "user_id" in data
    assert "hashed_password" not in data # Ensure hashed_password is not returned
    
    # Verify that save was called.
    # Check the call arguments if necessary, e.g., document_id based on user_id from response
    # For a more detailed check:
    # mock_firestore_ops.save.assert_called_once()
    # args, kwargs = mock_firestore_ops.save.call_args
    # assert kwargs['collection_name'] == 'users'
    # assert kwargs['document_id'] == data['user_id']
    # assert kwargs['data_model']['email'] == "test@example.com"

def test_register_user_duplicate_email(mock_firestore_ops, monkeypatch):
    """Test registration with a duplicate email."""
    # Configure the mock's query method to simulate finding an existing user by email
    # The side_effect needs to handle different query calls (email vs username)
    def query_side_effect(collection_name, field, operator, value):
        if field == "email" and value == "test@example.com":
            return [{"email": "test@example.com", "username": "existinguser"}] # Simulate user found
        return [] # No user found for other queries (e.g., username check)
    
    mock_firestore_ops.query.side_effect = query_side_effect
    monkeypatch.setattr("app.routers.auth.get_firestore_ops_instance", lambda: mock_firestore_ops)

    response = client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "email": "test@example.com", # Duplicate email
            "password": "password123",
            "full_name": "New User",
            "role": "client"
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"
        
def test_register_user_duplicate_username(mock_firestore_ops, monkeypatch):
    """Test registration with a duplicate username."""
    # Configure the mock's query method to simulate finding an existing user by username
    def query_side_effect(collection_name, field, operator, value):
        if field == "username" and value == "testuser":
            return [{"email": "other@example.com", "username": "testuser"}] # Simulate user found
        return [] # No user found for other queries (e.g., email check)

    mock_firestore_ops.query.side_effect = query_side_effect
    monkeypatch.setattr("app.routers.auth.get_firestore_ops_instance", lambda: mock_firestore_ops)

    response = client.post(
        "/auth/register",
        json={
            "username": "testuser", # Duplicate username
            "email": "newemail@example.com",
            "password": "password123",
            "full_name": "Another User",
            "role": "client"
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already taken"

# Note: The /auth/register endpoint in the provided code for app.routers.auth
# returns status 200 OK by default for FastAPI POST operations.
# If it were changed to 201 Created, the assertions would need adjustment.
# The `hashed_password` is not returned in the response as per the `User` response_model.
# The `get_password_hash` function is part of the tested endpoint's internal logic.
# We are testing the endpoint's behavior based on its interaction with the database mock.
# The mock_firestore_ops fixture is reset for each test function.I have already created the `tests/` directory and `tests/__init__.py` in the previous overall task. I have also just created the `tests/test_auth.py` file with the specified test cases for user registration in the current turn.

**Summary of actions taken based on the subtask description:**

1.  **Create Test Directory and Files (Partially done previously, completed now):**
    *   `tests/` directory and `tests/__init__.py` were created in the previous turn.
    *   `tests/test_auth.py` was created in the current turn with the test content.

2.  **Install `pytest` and `requests`:**
    *   This is a conceptual step noted in the prompt. I cannot execute installations, but the tests are written assuming `pytest` and `fastapi.testclient.TestClient` (which uses `requests`) are available.

3.  **Write tests in `tests/test_auth.py` (Completed in the current turn):**
    *   Imported `pytest`, `TestClient`, `MagicMock`.
    *   Imported `app` from `app.main`.
    *   Defined a `TestClient` instance: `client = TestClient(app)`.
    *   **`mock_firestore_ops` fixture:**
        *   Created using `MagicMock()`.
        *   Default `query.return_value` set to `[]` (no user found).
        *   Default `save.side_effect` set to `lambda collection_name, data_model, document_id: document_id` to mimic successful save returning the provided document ID.
    *   **`test_register_user_success`:**
        *   Used `monkeypatch.setattr("app.routers.auth.get_firestore_ops_instance", lambda: mock_firestore_ops)` to inject the mock.
        *   Sent a POST request to `/auth/register` with valid user data.
        *   Asserted status code `200`.
        *   Asserted response data fields (`email`, `username`, `user_id`).
        *   Asserted `hashed_password` is not in the response.
    *   **`test_register_user_duplicate_email`:**
        *   Configured `mock_firestore_ops.query.side_effect` to simulate an existing user when queried by email.
        *   Used `monkeypatch` to inject the mock.
        *   Sent a POST request with a duplicate email.
        *   Asserted status code `400` and the correct error detail.
    *   **`test_register_user_duplicate_username`:**
        *   Configured `mock_firestore_ops.query.side_effect` to simulate an existing user when queried by username.
        *   Used `monkeypatch` to inject the mock.
        *   Sent a POST request with a duplicate username.
        *   Asserted status code `400` and the correct error detail.
    *   **Important Notes Addressed:**
        *   The `monkeypatch.setattr` path used is `"app.routers.auth.get_firestore_ops_instance"`, assuming `get_firestore_ops_instance` is imported directly into `app.routers.auth`'s namespace. This matches the typical pattern from previous endpoint implementations.
        *   The status code `200` is asserted, matching FastAPI's default for POST.
        *   The `save.side_effect` correctly mimics returning the `document_id`.

All specified actions for creating the basic unit tests for the user registration endpoint have been completed.

from datetime import datetime # For checking last_login_date update
from uuid import UUID, uuid4 # For user_id in User model

# Tests for POST /auth/login

def test_login_success(mock_firestore_ops, monkeypatch):
    """Test successful user login."""
    user_id_for_token = "user_document_id_123"
    # Configure query to return a user
    mock_firestore_ops.query.return_value = [
        {
            "id": user_id_for_token, # Document ID from Firestore query result
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "hashed_password123", # Matches verify_password("password123", ...)
            "user_id": uuid4(), # Actual UUID field in the document
            "role": "client",
            "full_name": "Test User",
            "is_active": True,
            "registration_date": datetime.utcnow(), # Use datetime object
        }
    ]
    # Configure update to simulate success
    mock_firestore_ops.update.return_value = True
    
    monkeypatch.setattr("app.routers.auth.get_firestore_ops_instance", lambda: mock_firestore_ops)

    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "password123"}, # Use data for form
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["access_token"] == f"fake-jwt-token-for-{user_id_for_token}" # Based on current create_access_token
    assert data["token_type"] == "bearer"
    
    # Verify that update was called for last_login_date
    mock_firestore_ops.update.assert_called_once()
    args, kwargs = mock_firestore_ops.update.call_args
    assert kwargs['collection_name'] == 'users'
    assert kwargs['document_id'] == user_id_for_token
    assert "last_login_date" in kwargs['updates']
    # Ensure the value is a datetime object or a string representation of it
    assert isinstance(kwargs['updates']['last_login_date'], datetime)


def test_login_incorrect_username(mock_firestore_ops, monkeypatch):
    """Test login with an incorrect username."""
    mock_firestore_ops.query.return_value = [] # Simulate user not found
    monkeypatch.setattr("app.routers.auth.get_firestore_ops_instance", lambda: mock_firestore_ops)

    response = client.post(
        "/auth/login",
        data={"username": "wronguser", "password": "password123"},
    )
    assert response.status_code == 400 # Endpoint uses 400 for incorrect username/password
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_incorrect_password(mock_firestore_ops, monkeypatch):
    """Test login with an incorrect password."""
    user_id_for_token = "user_document_id_456"
    mock_firestore_ops.query.return_value = [
        {
            "id": user_id_for_token,
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "hashed_wrongpassword", # Does not match "password123"
            "user_id": uuid4(),
            "role": "client",
            "full_name": "Test User",
            "is_active": True,
            "registration_date": datetime.utcnow(),
        }
    ]
    monkeypatch.setattr("app.routers.auth.get_firestore_ops_instance", lambda: mock_firestore_ops)

    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "password123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect username or password"

# Tests for GET /auth/me

def test_read_users_me_success(mock_firestore_ops, monkeypatch):
    """Test successful retrieval of current user's details."""
    user_id_from_token = "test-user-id-from-token" # Must be valid for UUID conversion if needed by User model
    
    # Ensure user_id_from_token is a valid UUID string representation for the User model
    # If user_id_from_token is arbitrary, ensure User model instantiation can handle it,
    # or make user_id_from_token a valid UUID string. For simplicity, assume User model handles str to UUID.
    # Create an instance of User model to be returned by the mock
    mock_user_instance = User(
        user_id=uuid4(), # Generate a real UUID for the model instance
        username="currentuser",
        email="current@example.com",
        full_name="Current User",
        role="freelancer",
        is_active=True,
        registration_date=datetime.utcnow(), 
        phone_number=None,
        profile_picture_url=None,
        last_login_date=None,
    )
    # The `get` method in FirestoreBaseModel with `pydantic_model=User` will return an instance of User.
    mock_firestore_ops.get.return_value = mock_user_instance

    monkeypatch.setattr("app.routers.auth.get_firestore_ops_instance", lambda: mock_firestore_ops)

    # Token should be "fake-jwt-token-for-{user_id_from_token}"
    # The user_id_from_token is what decode_access_token will return.
    # This returned user_id_from_token is then used as document_id in firestore_ops.get
    # So, the mock_firestore_ops.get should be configured to expect this user_id_from_token.
    
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer fake-jwt-token-for-{user_id_from_token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == mock_user_instance.username
    assert data["email"] == mock_user_instance.email
    assert data["user_id"] == str(mock_user_instance.user_id) # Response user_id is string

    # Verify that firestore_ops.get was called with the correct document_id
    mock_firestore_ops.get.assert_called_once_with(
        collection_name="users",
        document_id=user_id_from_token, # This is what decode_access_token returns
        pydantic_model=User
    )


def test_read_users_me_invalid_token(monkeypatch): 
    """Test /auth/me with an invalid token format."""
    # No need to mock Firestore if token decoding fails early
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token-format"},
    )
    assert response.status_code == 401 
    assert response.json()["detail"] == "Could not validate credentials"

def test_read_users_me_user_not_found(mock_firestore_ops, monkeypatch):
    """Test /auth/me when token is valid but user is not found in DB."""
    user_id_from_token = "non-existent-user-id"
    mock_firestore_ops.get.return_value = None # Simulate user not found
    monkeypatch.setattr("app.routers.auth.get_firestore_ops_instance", lambda: mock_firestore_ops)

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer fake-jwt-token-for-{user_id_from_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
