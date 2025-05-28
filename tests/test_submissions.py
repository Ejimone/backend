import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, call
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.main import app # FastAPI application
from app.models.schemas import WorkSubmission, User, Project, Contract, WorkSubmissionCreate

client = TestClient(app)

MOCK_SUBMISSIONS_TOKEN_USER_ID = "mock-submissions-user-id"

@pytest.fixture
def mock_firestore_ops_submissions():
    mock_ops = MagicMock()
    mock_ops.get.return_value = None
    mock_ops.query.return_value = []
    mock_ops.save.side_effect = lambda collection_name, data_model, document_id: document_id
    mock_ops.update.return_value = True
    return mock_ops

@pytest.fixture
def mock_decode_token_submissions(monkeypatch):
    """Mocks decode_access_token for submission routes to return a fixed user ID."""
    mock_decoder = MagicMock(return_value=MOCK_SUBMISSIONS_TOKEN_USER_ID)
    monkeypatch.setattr("app.routers.submissions.decode_access_token", mock_decoder)
    return mock_decoder

# Helper functions
def create_mock_user_submissions(user_id_str: str, role="client", username_prefix="user"):
    try:
        uid = UUID(user_id_str)
    except ValueError:
        uid = uuid4() 
    return User(
        user_id=uid,
        username=f"{username_prefix}_{user_id_str[:8]}",
        email=f"{username_prefix}_{user_id_str[:8]}@example.com",
        full_name=f"Test User {user_id_str[:8]}",
        role=role,
        is_active=True,
        registration_date=datetime.utcnow(),
        phone_number=None,
        profile_picture_url=None,
        last_login_date=None
    )

def create_mock_project_submissions(
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

def create_mock_submission_submissions(
    submission_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    freelancer_id: Optional[UUID] = None,
    version: int = 1
):
    return WorkSubmission(
        submission_id=submission_id if submission_id else uuid4(),
        project_id=project_id if project_id else uuid4(),
        freelancer_id=freelancer_id if freelancer_id else uuid4(),
        files=[{"filename": "test.zip", "url": "http://example.com/test.zip"}],
        notes="Test submission notes.",
        submission_date=datetime.utcnow(),
        version=version
    )

def create_mock_contract_submissions(
    contract_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    client_id: Optional[UUID] = None,
    freelancer_id: Optional[UUID] = None,
    status: str = "active"
):
    return Contract(
        contract_id=contract_id if contract_id else uuid4(),
        project_id=project_id if project_id else uuid4(),
        client_id=client_id if client_id else uuid4(),
        freelancer_id=freelancer_id if freelancer_id else uuid4(),
        terms="Test contract terms",
        agreed_amount=100.0,
        start_date=datetime.utcnow(),
        status=status,
        creation_date=datetime.utcnow()
    )

# --- Tests for POST /projects/{project_id}/submissions/ ---

def test_submit_work_success(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)

    freelancer_user_id_obj = UUID(MOCK_SUBMISSIONS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="freelancer")
    
    test_project_id = uuid4()
    mock_project = create_mock_project_submissions(project_id=test_project_id, freelancer_user_id=freelancer_user_id_obj, status="in_progress")
    mock_active_contract = create_mock_contract_submissions(project_id=test_project_id, freelancer_id=freelancer_user_id_obj, status="active")

    # Mock sequence for .get: user, project
    # Mock sequence for .query: active contract, existing submissions (for versioning)
    mock_firestore_ops_submissions.get.side_effect = [mock_freelancer_user, mock_project]
    mock_firestore_ops_submissions.query.side_effect = [[mock_active_contract], []] # Active contract found, no previous submissions
    mock_firestore_ops_submissions.save.return_value = str(uuid4()) # Submission save
    mock_firestore_ops_submissions.update.return_value = True # Project status update

    submission_data = {
        "files": [{"filename": "final_work.pdf", "url": "http://example.com/final.pdf"}],
        "notes": "Here is my completed work."
    } # project_id and freelancer_id are from path/token

    response = client.post(f"/projects/{test_project_id}/submissions/", json=submission_data, headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == str(test_project_id)
    assert data["freelancer_id"] == MOCK_SUBMISSIONS_TOKEN_USER_ID
    assert data["version"] == 1
    assert data["notes"] == submission_data["notes"]
    
    mock_firestore_ops_submissions.save.assert_called_once()
    args_save, kwargs_save = mock_firestore_ops_submissions.save.call_args
    assert kwargs_save['collection_name'] == 'submissions'
    
    mock_firestore_ops_submissions.update.assert_called_once_with(
        collection_name="projects", document_id=str(test_project_id), updates={"status": "awaiting_review"}
    )

def test_submit_work_not_assigned_freelancer(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    
    # Authenticated user is different from project's freelancer
    mock_auth_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="freelancer")
    test_project_id = uuid4()
    assigned_freelancer_id = uuid4() # Different freelancer
    mock_project = create_mock_project_submissions(project_id=test_project_id, freelancer_user_id=assigned_freelancer_id, status="in_progress")

    mock_firestore_ops_submissions.get.side_effect = [mock_auth_user, mock_project]
    
    submission_data = {"files": [], "notes": "Trying to submit"}
    response = client.post(f"/projects/{test_project_id}/submissions/", json=submission_data, headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 403
    assert response.json()["detail"] == "You are not the assigned freelancer for this project."

def test_submit_work_project_not_in_progress(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    freelancer_user_id_obj = UUID(MOCK_SUBMISSIONS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="freelancer")
    test_project_id = uuid4()
    mock_project = create_mock_project_submissions(project_id=test_project_id, freelancer_user_id=freelancer_user_id_obj, status="completed") # Not 'in_progress'

    mock_firestore_ops_submissions.get.side_effect = [mock_freelancer_user, mock_project]
    
    submission_data = {"files": [], "notes": "Late submission"}
    response = client.post(f"/projects/{test_project_id}/submissions/", json=submission_data, headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Project is not in progress."

def test_submit_work_no_active_contract(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    freelancer_user_id_obj = UUID(MOCK_SUBMISSIONS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="freelancer")
    test_project_id = uuid4()
    mock_project = create_mock_project_submissions(project_id=test_project_id, freelancer_user_id=freelancer_user_id_obj, status="in_progress")

    mock_firestore_ops_submissions.get.side_effect = [mock_freelancer_user, mock_project]
    mock_firestore_ops_submissions.query.return_value = [] # No active contract

    submission_data = {"files": [], "notes": "Submission without contract"}
    response = client.post(f"/projects/{test_project_id}/submissions/", json=submission_data, headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "No active contract found for this project and freelancer."

def test_submit_work_project_not_found(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    mock_freelancer_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="freelancer")
    mock_firestore_ops_submissions.get.side_effect = [mock_freelancer_user, None] # Project not found

    test_project_id = uuid4()
    submission_data = {"files": [], "notes": "Submission for non-existent project"}
    response = client.post(f"/projects/{test_project_id}/submissions/", json=submission_data, headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"

# --- Tests for GET /projects/{project_id}/submissions/ ---

def test_list_submissions_client_owner_success(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    client_user_id_obj = UUID(MOCK_SUBMISSIONS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="client")
    test_project_id = uuid4()
    mock_project = create_mock_project_submissions(project_id=test_project_id, client_user_id=client_user_id_obj)
    
    mock_firestore_ops_submissions.get.side_effect = [mock_client_user, mock_project]
    
    mock_submissions_list = [
        create_mock_submission_submissions(project_id=test_project_id, version=2),
        create_mock_submission_submissions(project_id=test_project_id, version=1)
    ]
    mock_firestore_ops_submissions.query.return_value = mock_submissions_list
    
    response = client.get(f"/projects/{test_project_id}/submissions/", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["version"] == 1 # Check sorting
    assert data[1]["version"] == 2
    
    mock_firestore_ops_submissions.query.assert_called_once_with(
        collection_name="submissions", field="project_id", operator="==", value=test_project_id, pydantic_model=WorkSubmission
    )

def test_list_submissions_assigned_freelancer_success(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    freelancer_user_id_obj = UUID(MOCK_SUBMISSIONS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="freelancer")
    test_project_id = uuid4()
    mock_project = create_mock_project_submissions(project_id=test_project_id, freelancer_user_id=freelancer_user_id_obj)
    
    mock_firestore_ops_submissions.get.side_effect = [mock_freelancer_user, mock_project]
    mock_firestore_ops_submissions.query.return_value = [create_mock_submission_submissions(project_id=test_project_id)]
    
    response = client.get(f"/projects/{test_project_id}/submissions/", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_list_submissions_unauthorized(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    # User is neither client owner nor assigned freelancer
    mock_unauthorized_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="client") 
    test_project_id = uuid4()
    mock_project = create_mock_project_submissions(project_id=test_project_id, client_user_id=uuid4(), freelancer_user_id=uuid4()) # Different users
    
    mock_firestore_ops_submissions.get.side_effect = [mock_unauthorized_user, mock_project]
    
    response = client.get(f"/projects/{test_project_id}/submissions/", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to view submissions for this project"

def test_list_submissions_project_not_found(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    mock_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID)
    mock_firestore_ops_submissions.get.side_effect = [mock_user, None] # Project not found
    
    test_project_id = uuid4()
    response = client.get(f"/projects/{test_project_id}/submissions/", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"

# --- Tests for POST /projects/{project_id}/submissions/{submission_id}/approve ---

def test_approve_submission_success(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)

    client_user_id_obj = UUID(MOCK_SUBMISSIONS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="client")
    
    test_project_id = uuid4()
    assigned_freelancer_id = uuid4()
    mock_project = create_mock_project_submissions(project_id=test_project_id, client_user_id=client_user_id_obj, freelancer_user_id=assigned_freelancer_id, status="awaiting_review")
    
    test_submission_id = uuid4()
    mock_submission = create_mock_submission_submissions(submission_id=test_submission_id, project_id=test_project_id, freelancer_id=assigned_freelancer_id)
    
    mock_active_contract = create_mock_contract_submissions(project_id=test_project_id, client_id=client_user_id_obj, freelancer_id=assigned_freelancer_id, status="active")

    # Mock .get calls: user, project, submission
    # Mock .query for contract
    # Mock .update for project and contract
    mock_firestore_ops_submissions.get.side_effect = [mock_client_user, mock_project, mock_submission]
    mock_firestore_ops_submissions.query.return_value = [mock_active_contract]
    mock_firestore_ops_submissions.update.return_value = True

    response = client.post(f"/projects/{test_project_id}/submissions/{test_submission_id}/approve", headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 200
    assert response.json()["message"] == "Submission approved. Project marked as completed."
    
    expected_updates = [
        call(collection_name="projects", document_id=str(test_project_id), updates={"status": "completed"}),
        call(collection_name="contracts", document_id=str(mock_active_contract.contract_id), updates={"status": "completed"})
    ]
    mock_firestore_ops_submissions.update.assert_has_calls(expected_updates, any_order=False)

def test_approve_submission_not_client_owner(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    mock_not_owner_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="freelancer") # Not client owner
    test_project_id = uuid4()
    mock_project = create_mock_project_submissions(project_id=test_project_id, client_user_id=uuid4()) # Different client
    mock_firestore_ops_submissions.get.side_effect = [mock_not_owner_user, mock_project] # Submission get won't be called
    
    response = client.post(f"/projects/{test_project_id}/submissions/{uuid4()}/approve", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Only the project owner can approve submissions."

def test_approve_submission_project_not_awaiting_review(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    client_user_id_obj = UUID(MOCK_SUBMISSIONS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="client")
    test_project_id = uuid4()
    mock_project = create_mock_project_submissions(project_id=test_project_id, client_user_id=client_user_id_obj, status="in_progress") # Not awaiting_review
    test_submission_id = uuid4()
    mock_submission = create_mock_submission_submissions(submission_id=test_submission_id, project_id=test_project_id)
    mock_firestore_ops_submissions.get.side_effect = [mock_client_user, mock_project, mock_submission]
    
    response = client.post(f"/projects/{test_project_id}/submissions/{test_submission_id}/approve", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Project is not awaiting review."

def test_approve_submission_mismatch(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    client_user_id_obj = UUID(MOCK_SUBMISSIONS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="client")
    
    path_project_id = uuid4() # Project ID in path
    submission_project_id = uuid4() # Different project ID in submission
    
    mock_project_in_path = create_mock_project_submissions(project_id=path_project_id, client_user_id=client_user_id_obj, status="awaiting_review")
    test_submission_id = uuid4()
    mock_submission = create_mock_submission_submissions(submission_id=test_submission_id, project_id=submission_project_id)
    
    mock_firestore_ops_submissions.get.side_effect = [mock_client_user, mock_project_in_path, mock_submission]
    
    response = client.post(f"/projects/{path_project_id}/submissions/{test_submission_id}/approve", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Submission does not belong to this project."

def test_approve_submission_submission_not_found(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    client_user_id_obj = UUID(MOCK_SUBMISSIONS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID, role="client")
    test_project_id = uuid4()
    mock_project = create_mock_project_submissions(project_id=test_project_id, client_user_id=client_user_id_obj, status="awaiting_review")
    
    mock_firestore_ops_submissions.get.side_effect = [mock_client_user, mock_project, None] # Submission not found
    
    test_submission_id = uuid4()
    response = client.post(f"/projects/{test_project_id}/submissions/{test_submission_id}/approve", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Submission not found"

def test_approve_submission_project_not_found(mock_firestore_ops_submissions, mock_decode_token_submissions, monkeypatch):
    monkeypatch.setattr("app.routers.submissions.get_firestore_ops_instance", lambda: mock_firestore_ops_submissions)
    mock_user = create_mock_user_submissions(MOCK_SUBMISSIONS_TOKEN_USER_ID)
    mock_firestore_ops_submissions.get.side_effect = [mock_user, None] # Project not found
    
    response = client.post(f"/projects/{uuid4()}/submissions/{uuid4()}/approve", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"
