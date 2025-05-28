import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Dict, Any, Optional # Added Optional

from app.main import app # FastAPI application
from app.models.schemas import Project, User, ProjectCreate 

client = TestClient(app)

MOCK_PROJECTS_TOKEN_USER_ID = "mock-projects-user-id"

@pytest.fixture
def mock_firestore_ops_projects():
    mock_ops = MagicMock()
    mock_ops.get.return_value = None
    mock_ops.query.return_value = []
    mock_ops.save.side_effect = lambda collection_name, data_model, document_id: document_id
    mock_ops.update.return_value = True
    mock_ops.delete.return_value = True
    return mock_ops

@pytest.fixture
def mock_decode_token_projects(monkeypatch):
    """Mocks decode_access_token for project routes to return a fixed user ID."""
    mock_decoder = MagicMock(return_value=MOCK_PROJECTS_TOKEN_USER_ID)
    monkeypatch.setattr("app.routers.projects.decode_access_token", mock_decoder)
    return mock_decoder

# Helper functions (can be copied from test_users.py or moved to a conftest.py)
def create_mock_user_projects(user_id_str: str, role="client", username_prefix="user"):
    # Ensure user_id is UUID if the model expects it, but MOCK_PROJECTS_TOKEN_USER_ID is a string
    # For User model, user_id is UUID.
    try:
        uid = UUID(user_id_str)
    except ValueError:
        # If user_id_str is not a valid UUID string, generate one.
        # This might happen if MOCK_PROJECTS_TOKEN_USER_ID is not UUID-like.
        # However, for consistency, the token should represent a valid UUID string if it's used as such.
        # For this mock, we'll assume it can be converted or is used as a string ID where appropriate.
        # The User model itself requires user_id: UUID.
        uid = uuid4() # Fallback, but ideally MOCK_PROJECTS_TOKEN_USER_ID is a string form of a UUID

    return User(
        user_id=uid, # If MOCK_PROJECTS_TOKEN_USER_ID is used for document ID, it's string. User model needs UUID.
        username=f"{username_prefix}_{user_id_str[:8]}", # Ensure username is somewhat unique
        email=f"{username_prefix}_{user_id_str[:8]}@example.com",
        full_name=f"Test User {user_id_str[:8]}",
        role=role,
        is_active=True,
        registration_date=datetime.utcnow(),
        phone_number=None,
        profile_picture_url=None,
        last_login_date=None
    )

def create_mock_project_projects(
    project_id: Optional[UUID] = None, 
    client_user_id: Optional[UUID] = None, 
    freelancer_user_id: Optional[UUID] = None, 
    status="open",
    title="Test Project"
):
    return Project(
        project_id=project_id if project_id else uuid4(),
        client_user_id=client_user_id if client_user_id else uuid4(),
        freelancer_user_id=freelancer_user_id,
        title=title,
        description="A test project description.",
        budget=100.0,
        status=status,
        creation_date=datetime.utcnow(),
        last_updated_date=datetime.utcnow(),
        tags=["test", "mock"]
    )

# --- Tests for POST /projects/ ---

def test_create_project_success(mock_firestore_ops_projects, mock_decode_token_projects, monkeypatch):
    monkeypatch.setattr("app.routers.projects.get_firestore_ops_instance", lambda: mock_firestore_ops_projects)

    mock_client_user = create_mock_user_projects(MOCK_PROJECTS_TOKEN_USER_ID, role="client")
    mock_firestore_ops_projects.get.return_value = mock_client_user # Mock fetching the current user

    project_data = {
        "title": "New Test Project",
        "description": "A new description",
        "budget": 200.0,
        "status": "open", # From ProjectBase
        "client_user_id": str(mock_client_user.user_id) # Part of ProjectCreate, will be overwritten
    }

    response = client.post("/projects/", json=project_data, headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == project_data["title"]
    assert data["client_user_id"] == str(mock_client_user.user_id) # Assert it's set from token user
    assert data["status"] == "open"
    
    mock_firestore_ops_projects.save.assert_called_once()
    args, kwargs = mock_firestore_ops_projects.save.call_args
    assert kwargs['collection_name'] == 'projects'
    assert kwargs['data_model']['client_user_id'] == mock_client_user.user_id # Check UUID object
    assert kwargs['data_model']['title'] == project_data['title']

def test_create_project_auth_forbidden_freelancer(mock_firestore_ops_projects, mock_decode_token_projects, monkeypatch):
    monkeypatch.setattr("app.routers.projects.get_firestore_ops_instance", lambda: mock_firestore_ops_projects)
    
    mock_freelancer_user = create_mock_user_projects(MOCK_PROJECTS_TOKEN_USER_ID, role="freelancer")
    mock_firestore_ops_projects.get.return_value = mock_freelancer_user # Mock fetching the current user

    project_data = {"title": "Freelancer Project", "description": "...", "client_user_id": MOCK_PROJECTS_TOKEN_USER_ID}
    response = client.post("/projects/", json=project_data, headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Only clients can create projects"

def test_create_project_auth_invalid_token(monkeypatch):
    # Mock decode_access_token to return None for this specific test
    monkeypatch.setattr("app.routers.projects.decode_access_token", lambda token: None)
    
    project_data = {"title": "Project With Invalid Token", "description": "...", "client_user_id": "some-id"}
    response = client.post("/projects/", json=project_data, headers={"Authorization": "Bearer invalid-token"})
    
    assert response.status_code == 401 # Or 403 depending on how Depends handles it
    assert "Could not validate credentials" in response.json()["detail"]


# --- Tests for GET /projects/ ---

def test_list_open_projects_success(mock_firestore_ops_projects, monkeypatch):
    monkeypatch.setattr("app.routers.projects.get_firestore_ops_instance", lambda: mock_firestore_ops_projects)
    
    mock_project_list = [
        create_mock_project_projects(status="open", title="Open Project 1"),
        create_mock_project_projects(status="open", title="Open Project 2")
    ]
    mock_firestore_ops_projects.query.return_value = mock_project_list
    
    response = client.get("/projects/")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Open Project 1"
    assert data[1]["status"] == "open"
    
    mock_firestore_ops_projects.query.assert_called_once_with(
        collection_name="projects", field="status", operator="==", value="open", pydantic_model=Project
    )

def test_list_open_projects_empty(mock_firestore_ops_projects, monkeypatch):
    monkeypatch.setattr("app.routers.projects.get_firestore_ops_instance", lambda: mock_firestore_ops_projects)
    mock_firestore_ops_projects.query.return_value = []
    
    response = client.get("/projects/")
    
    assert response.status_code == 200
    assert response.json() == []

# --- Tests for GET /projects/{project_id} ---

def test_get_project_details_success(mock_firestore_ops_projects, monkeypatch):
    monkeypatch.setattr("app.routers.projects.get_firestore_ops_instance", lambda: mock_firestore_ops_projects)
    
    test_project_id = uuid4()
    mock_project = create_mock_project_projects(project_id=test_project_id)
    mock_firestore_ops_projects.get.return_value = mock_project
    
    response = client.get(f"/projects/{test_project_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == str(test_project_id)
    assert data["title"] == mock_project.title
    
    mock_firestore_ops_projects.get.assert_called_once_with(
        collection_name="projects", document_id=str(test_project_id), pydantic_model=Project
    )

def test_get_project_details_not_found(mock_firestore_ops_projects, monkeypatch):
    monkeypatch.setattr("app.routers.projects.get_firestore_ops_instance", lambda: mock_firestore_ops_projects)
    
    test_project_id = uuid4()
    mock_firestore_ops_projects.get.return_value = None # Simulate not found
    
    response = client.get(f"/projects/{test_project_id}")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"

# --- Tests for PUT /projects/{project_id} ---

def test_update_project_success(mock_firestore_ops_projects, mock_decode_token_projects, monkeypatch):
    monkeypatch.setattr("app.routers.projects.get_firestore_ops_instance", lambda: mock_firestore_ops_projects)
    
    client_user_id_obj = UUID(MOCK_PROJECTS_TOKEN_USER_ID) # Ensure UUID for model
    mock_client_user = create_mock_user_projects(MOCK_PROJECTS_TOKEN_USER_ID, role="client")
    
    test_project_id = uuid4()
    original_project = create_mock_project_projects(project_id=test_project_id, client_user_id=client_user_id_obj)
    
    # Mock the .get calls:
    # 1. For fetching current user
    # 2. For fetching existing project
    # 3. For fetching project after update
    updated_project_data_dict = original_project.model_dump()
    updated_project_data_dict["title"] = "Updated Title"
    updated_project_data_dict["last_updated_date"] = datetime.utcnow() # Simulate update
    
    mock_firestore_ops_projects.get.side_effect = [
        mock_client_user,          # Call 1: Get current user
        original_project,          # Call 2: Get existing project
        Project(**updated_project_data_dict) # Call 3: Get project after update
    ]
    mock_firestore_ops_projects.update.return_value = True

    update_payload = {"title": "Updated Title", "description": "New Description"}
    response = client.put(f"/projects/{test_project_id}", json=update_payload, headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["project_id"] == str(test_project_id)
    
    mock_firestore_ops_projects.update.assert_called_once()
    args, kwargs = mock_firestore_ops_projects.update.call_args
    assert kwargs['collection_name'] == 'projects'
    assert kwargs['document_id'] == str(test_project_id)
    assert kwargs['updates']['title'] == "Updated Title"
    assert "client_user_id" not in kwargs['updates'] # Ensure protected fields are not in update
    assert "project_id" not in kwargs['updates']
    assert "creation_date" not in kwargs['updates']

def test_update_project_forbidden_not_owner(mock_firestore_ops_projects, mock_decode_token_projects, monkeypatch):
    monkeypatch.setattr("app.routers.projects.get_firestore_ops_instance", lambda: mock_firestore_ops_projects)

    # Authenticated user (from token)
    auth_user_id_obj = UUID(MOCK_PROJECTS_TOKEN_USER_ID)
    mock_auth_user = create_mock_user_projects(MOCK_PROJECTS_TOKEN_USER_ID, role="client")
    
    # Project owned by a different client
    owner_client_id = uuid4() 
    test_project_id = uuid4()
    existing_project = create_mock_project_projects(project_id=test_project_id, client_user_id=owner_client_id)
    
    mock_firestore_ops_projects.get.side_effect = [mock_auth_user, existing_project]

    response = client.put(f"/projects/{test_project_id}", json={"title": "Attempted Update"}, headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update this project"

def test_update_project_not_found(mock_firestore_ops_projects, mock_decode_token_projects, monkeypatch):
    monkeypatch.setattr("app.routers.projects.get_firestore_ops_instance", lambda: mock_firestore_ops_projects)
    
    mock_client_user = create_mock_user_projects(MOCK_PROJECTS_TOKEN_USER_ID, role="client")
    
    mock_firestore_ops_projects.get.side_effect = [
        mock_client_user, # Get current user
        None              # Project not found
    ]
    
    test_project_id = uuid4()
    response = client.put(f"/projects/{test_project_id}", json={"title": "Update NonExistent"}, headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"

def test_update_project_auth_invalid_token(monkeypatch):
    monkeypatch.setattr("app.routers.projects.decode_access_token", lambda token: None)
    response = client.put(f"/projects/{uuid4()}", json={"title": "Update"}, headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401

# --- Tests for DELETE /projects/{project_id} ---

def test_delete_project_success(mock_firestore_ops_projects, mock_decode_token_projects, monkeypatch):
    monkeypatch.setattr("app.routers.projects.get_firestore_ops_instance", lambda: mock_firestore_ops_projects)

    client_user_id_obj = UUID(MOCK_PROJECTS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_projects(MOCK_PROJECTS_TOKEN_USER_ID, role="client")
    
    test_project_id = uuid4()
    existing_project = create_mock_project_projects(project_id=test_project_id, client_user_id=client_user_id_obj)
    
    mock_firestore_ops_projects.get.side_effect = [mock_client_user, existing_project]
    mock_firestore_ops_projects.delete.return_value = True
    
    response = client.delete(f"/projects/{test_project_id}", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 204
    mock_firestore_ops_projects.delete.assert_called_once_with(collection_name="projects", document_id=str(test_project_id))

def test_delete_project_forbidden_not_owner(mock_firestore_ops_projects, mock_decode_token_projects, monkeypatch):
    monkeypatch.setattr("app.routers.projects.get_firestore_ops_instance", lambda: mock_firestore_ops_projects)
    
    mock_auth_user = create_mock_user_projects(MOCK_PROJECTS_TOKEN_USER_ID, role="client")
    owner_client_id = uuid4()
    test_project_id = uuid4()
    existing_project = create_mock_project_projects(project_id=test_project_id, client_user_id=owner_client_id)
    
    mock_firestore_ops_projects.get.side_effect = [mock_auth_user, existing_project]
    
    response = client.delete(f"/projects/{test_project_id}", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to delete this project"

def test_delete_project_not_found(mock_firestore_ops_projects, mock_decode_token_projects, monkeypatch):
    monkeypatch.setattr("app.routers.projects.get_firestore_ops_instance", lambda: mock_firestore_ops_projects)
    
    mock_client_user = create_mock_user_projects(MOCK_PROJECTS_TOKEN_USER_ID, role="client")
    mock_firestore_ops_projects.get.side_effect = [mock_client_user, None] # Project not found
    
    test_project_id = uuid4()
    response = client.delete(f"/projects/{test_project_id}", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"

def test_delete_project_auth_invalid_token(monkeypatch):
    monkeypatch.setattr("app.routers.projects.decode_access_token", lambda token: None)
    response = client.delete(f"/projects/{uuid4()}", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
