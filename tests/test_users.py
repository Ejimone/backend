import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from uuid import UUID, uuid4
from datetime import datetime

from app.main import app # FastAPI application
from app.models.schemas import User, Project, ClientProfile, FreelancerProfile 

client = TestClient(app)

@pytest.fixture
def mock_firestore_ops_users(): # Renamed to avoid conflict if moved to conftest.py later
    """
    Provides a MagicMock instance simulating FirestoreBaseModel for user-related tests.
    """
    mock_ops = MagicMock()
    # Default behaviors (can be overridden in tests)
    mock_ops.get.return_value = None
    mock_ops.query.return_value = []
    mock_ops.save.side_effect = lambda collection_name, data_model, document_id: document_id
    mock_ops.update.return_value = True
    mock_ops.delete.return_value = True
    return mock_ops

# Helper to create a mock User Pydantic model instance
def create_mock_user(user_id=None, role="client", username="testuser", email_suffix="@example.com"):
    return User(
        user_id=user_id if user_id else uuid4(),
        username=username,
        email=f"{username}{email_suffix}",
        full_name="Test User",
        role=role,
        is_active=True,
        registration_date=datetime.utcnow(),
        phone_number=None,
        profile_picture_url=None,
        last_login_date=None
    )

# Helper to create a mock Project Pydantic model instance
def create_mock_project(project_id=None, client_user_id=None, freelancer_user_id=None, status="open"):
    return Project(
        project_id=project_id if project_id else uuid4(),
        client_user_id=client_user_id if client_user_id else uuid4(),
        freelancer_user_id=freelancer_user_id,
        title="Test Project",
        description="A test project description.",
        budget=100.0,
        status=status,
        creation_date=datetime.utcnow(),
        last_updated_date=datetime.utcnow()
    )

# --- Tests for GET /users/{user_id} ---

def test_get_user_profile_success(mock_firestore_ops_users, monkeypatch):
    test_user_id = uuid4()
    mock_user = create_mock_user(user_id=test_user_id)
    mock_firestore_ops_users.get.return_value = mock_user
    
    monkeypatch.setattr("app.routers.users.get_firestore_ops_instance", lambda: mock_firestore_ops_users)
    
    response = client.get(f"/users/{test_user_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user_id)
    assert data["username"] == mock_user.username
    mock_firestore_ops_users.get.assert_called_once_with(
        collection_name="users", document_id=str(test_user_id), pydantic_model=User
    )

def test_get_user_profile_not_found(mock_firestore_ops_users, monkeypatch):
    test_user_id = uuid4()
    mock_firestore_ops_users.get.return_value = None # Simulate user not found
    
    monkeypatch.setattr("app.routers.users.get_firestore_ops_instance", lambda: mock_firestore_ops_users)
    
    response = client.get(f"/users/{test_user_id}")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
    mock_firestore_ops_users.get.assert_called_once_with(
        collection_name="users", document_id=str(test_user_id), pydantic_model=User
    )

# --- Tests for PUT /users/me/profile ---

MOCK_TOKEN_USER_ID = "mock-user-id-from-token"

@pytest.fixture
def mock_decode_token(monkeypatch):
    """Mocks decode_access_token to return a fixed user ID."""
    mock_decoder = MagicMock(return_value=MOCK_TOKEN_USER_ID)
    monkeypatch.setattr("app.routers.users.decode_access_token", mock_decoder)
    return mock_decoder

def test_update_user_profile_client_success(mock_firestore_ops_users, mock_decode_token, monkeypatch):
    mock_client_user = create_mock_user(user_id=UUID(MOCK_TOKEN_USER_ID), role="client") # Ensure UUID for model
    mock_firestore_ops_users.get.return_value = mock_client_user # For fetching current user
    
    monkeypatch.setattr("app.routers.users.get_firestore_ops_instance", lambda: mock_firestore_ops_users)
    
    client_profile_data = {"company_name": "Test Inc."}
    response = client.put(
        "/users/me/profile",
        json=client_profile_data,
        headers={"Authorization": "Bearer fake-token"} 
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Client profile updated successfully"
    assert response.json()["user_id"] == MOCK_TOKEN_USER_ID
    
    mock_firestore_ops_users.save.assert_called_once()
    args, kwargs = mock_firestore_ops_users.save.call_args
    assert kwargs['collection_name'] == 'client_profiles'
    assert kwargs['document_id'] == MOCK_TOKEN_USER_ID
    assert kwargs['data_model']['company_name'] == "Test Inc."
    assert kwargs['data_model']['user_id'] == UUID(MOCK_TOKEN_USER_ID)

def test_update_user_profile_freelancer_success(mock_firestore_ops_users, mock_decode_token, monkeypatch):
    mock_freelancer_user = create_mock_user(user_id=UUID(MOCK_TOKEN_USER_ID), role="freelancer")
    mock_firestore_ops_users.get.return_value = mock_freelancer_user # For fetching current user
    
    monkeypatch.setattr("app.routers.users.get_firestore_ops_instance", lambda: mock_firestore_ops_users)
    
    freelancer_profile_data = {"skills": ["python", "fastapi"], "hourly_rate": 50.0}
    response = client.put(
        "/users/me/profile",
        json=freelancer_profile_data,
        headers={"Authorization": "Bearer fake-token"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Freelancer profile updated successfully"
    
    mock_firestore_ops_users.save.assert_called_once()
    args, kwargs = mock_firestore_ops_users.save.call_args
    assert kwargs['collection_name'] == 'freelancer_profiles'
    assert kwargs['document_id'] == MOCK_TOKEN_USER_ID
    assert kwargs['data_model']['skills'] == ["python", "fastapi"]
    assert kwargs['data_model']['user_id'] == UUID(MOCK_TOKEN_USER_ID)

def test_update_user_profile_unsupported_role(mock_firestore_ops_users, mock_decode_token, monkeypatch):
    mock_admin_user = create_mock_user(user_id=UUID(MOCK_TOKEN_USER_ID), role="admin")
    mock_firestore_ops_users.get.return_value = mock_admin_user
    
    monkeypatch.setattr("app.routers.users.get_firestore_ops_instance", lambda: mock_firestore_ops_users)
    
    response = client.put(
        "/users/me/profile",
        json={"some_data": "value"},
        headers={"Authorization": "Bearer fake-token"}
    )
    
    assert response.status_code == 400 # Or 403, depends on implementation detail
    assert "does not support profiles" in response.json()["detail"]

def test_update_user_profile_auth_error(monkeypatch): # No firestore ops needed if auth fails first
    mock_decoder = MagicMock(return_value=None) # Simulate token decode failure
    monkeypatch.setattr("app.routers.users.decode_access_token", mock_decoder)
    
    response = client.put(
        "/users/me/profile",
        json={"company_name": "Test Inc."},
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


# --- Tests for GET /users/me/projects ---

def test_list_my_projects_client_success(mock_firestore_ops_users, mock_decode_token, monkeypatch):
    mock_client_user = create_mock_user(user_id=UUID(MOCK_TOKEN_USER_ID), role="client")
    mock_firestore_ops_users.get.return_value = mock_client_user
    
    project1_id = uuid4()
    mock_projects_list = [
        create_mock_project(project_id=project1_id, client_user_id=UUID(MOCK_TOKEN_USER_ID)),
        create_mock_project(client_user_id=UUID(MOCK_TOKEN_USER_ID))
    ]
    mock_firestore_ops_users.query.return_value = mock_projects_list
    
    monkeypatch.setattr("app.routers.users.get_firestore_ops_instance", lambda: mock_firestore_ops_users)
    
    response = client.get("/users/me/projects", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["project_id"] == str(project1_id)
    assert data[0]["client_user_id"] == MOCK_TOKEN_USER_ID
    
    mock_firestore_ops_users.query.assert_called_once_with(
        collection_name="projects",
        field="client_user_id",
        operator="==",
        value=UUID(MOCK_TOKEN_USER_ID),
        pydantic_model=Project
    )

def test_list_my_projects_freelancer_success(mock_firestore_ops_users, mock_decode_token, monkeypatch):
    mock_freelancer_user = create_mock_user(user_id=UUID(MOCK_TOKEN_USER_ID), role="freelancer")
    mock_firestore_ops_users.get.return_value = mock_freelancer_user
    
    mock_projects_list = [create_mock_project(freelancer_user_id=UUID(MOCK_TOKEN_USER_ID))]
    mock_firestore_ops_users.query.return_value = mock_projects_list
    
    monkeypatch.setattr("app.routers.users.get_firestore_ops_instance", lambda: mock_firestore_ops_users)
    
    response = client.get("/users/me/projects", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["freelancer_user_id"] == MOCK_TOKEN_USER_ID
    
    mock_firestore_ops_users.query.assert_called_once_with(
        collection_name="projects",
        field="freelancer_user_id",
        operator="==",
        value=UUID(MOCK_TOKEN_USER_ID),
        pydantic_model=Project
    )

def test_list_my_projects_no_projects(mock_firestore_ops_users, mock_decode_token, monkeypatch):
    mock_client_user = create_mock_user(user_id=UUID(MOCK_TOKEN_USER_ID), role="client")
    mock_firestore_ops_users.get.return_value = mock_client_user
    mock_firestore_ops_users.query.return_value = [] # No projects
    
    monkeypatch.setattr("app.routers.users.get_firestore_ops_instance", lambda: mock_firestore_ops_users)
    
    response = client.get("/users/me/projects", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    assert response.json() == []

def test_list_my_projects_auth_error(monkeypatch):
    mock_decoder = MagicMock(return_value=None) # Simulate token decode failure
    monkeypatch.setattr("app.routers.users.decode_access_token", mock_decoder)
    
    response = client.get("/users/me/projects", headers={"Authorization": "Bearer invalid-token"})
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"
