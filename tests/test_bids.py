import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, call # Import call for checking multiple calls
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.main import app # FastAPI application
from app.models.schemas import Bid, User, Project, BidCreate, Contract # Added Contract

client = TestClient(app)

MOCK_BIDS_TOKEN_USER_ID = "mock-bids-user-id"

@pytest.fixture
def mock_firestore_ops_bids():
    mock_ops = MagicMock()
    mock_ops.get.return_value = None
    mock_ops.query.return_value = []
    # Ensure save returns the document_id for consistency if tests rely on it
    mock_ops.save.side_effect = lambda collection_name, data_model, document_id: document_id
    mock_ops.update.return_value = True
    mock_ops.delete.return_value = True
    return mock_ops

@pytest.fixture
def mock_decode_token_bids(monkeypatch):
    """Mocks decode_access_token for bid routes to return a fixed user ID."""
    mock_decoder = MagicMock(return_value=MOCK_BIDS_TOKEN_USER_ID)
    monkeypatch.setattr("app.routers.bids.decode_access_token", mock_decoder)
    return mock_decoder

# Helper functions (can be adjusted or moved to conftest.py)
def create_mock_user_bids(user_id_str: str, role="client", username_prefix="user"):
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

def create_mock_project_bids(
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

def create_mock_bid_bids(
    bid_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    freelancer_user_id: Optional[UUID] = None,
    status: str = "pending",
    amount: float = 100.0
):
    return Bid(
        bid_id=bid_id if bid_id else uuid4(),
        project_id=project_id if project_id else uuid4(),
        freelancer_user_id=freelancer_user_id if freelancer_user_id else uuid4(),
        proposal="Test bid proposal",
        amount=amount,
        estimated_completion_time="1 week",
        bid_date=datetime.utcnow(),
        status=status
    )

# --- Tests for POST /project/{project_id}/submit-bid ---

def test_submit_bid_success(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)

    freelancer_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="freelancer")
    
    test_project_id = uuid4()
    mock_project = create_mock_project_bids(project_id=test_project_id, status="open")

    mock_firestore_ops_bids.get.side_effect = [mock_freelancer_user, mock_project]
    mock_firestore_ops_bids.query.return_value = [] # No existing bids by this freelancer

    bid_data = {"proposal": "My new bid", "amount": 150.0, "project_id": str(test_project_id), "freelancer_user_id": MOCK_BIDS_TOKEN_USER_ID} # these last two will be ignored by endpoint

    response = client.post(f"/project/{test_project_id}/submit-bid", json=bid_data, headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 201
    data = response.json()
    assert data["proposal"] == bid_data["proposal"]
    assert data["freelancer_user_id"] == MOCK_BIDS_TOKEN_USER_ID
    assert data["project_id"] == str(test_project_id)
    assert data["status"] == "pending"
    
    mock_firestore_ops_bids.save.assert_called_once()
    args, kwargs = mock_firestore_ops_bids.save.call_args
    assert kwargs['collection_name'] == 'bids'
    assert kwargs['data_model']['freelancer_user_id'] == freelancer_user_id_obj

def test_submit_bid_not_freelancer(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    mock_client_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="client")
    mock_firestore_ops_bids.get.return_value = mock_client_user

    test_project_id = uuid4()
    bid_data = {"proposal": "Bid by client", "amount": 100.0, "project_id": str(test_project_id), "freelancer_user_id": MOCK_BIDS_TOKEN_USER_ID}
    
    response = client.post(f"/project/{test_project_id}/submit-bid", json=bid_data, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Only freelancers can submit bids"

def test_submit_bid_project_not_found(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    mock_freelancer_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="freelancer")
    mock_firestore_ops_bids.get.side_effect = [mock_freelancer_user, None] # Project not found

    test_project_id = uuid4()
    bid_data = {"proposal": "Bid for non-existent project", "amount": 100.0, "project_id": str(test_project_id), "freelancer_user_id": MOCK_BIDS_TOKEN_USER_ID}
    
    response = client.post(f"/project/{test_project_id}/submit-bid", json=bid_data, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"

def test_submit_bid_project_not_open(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    mock_freelancer_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="freelancer")
    test_project_id = uuid4()
    mock_project = create_mock_project_bids(project_id=test_project_id, status="in_progress")
    mock_firestore_ops_bids.get.side_effect = [mock_freelancer_user, mock_project]

    bid_data = {"proposal": "Bid for in-progress project", "amount": 100.0, "project_id": str(test_project_id), "freelancer_user_id": MOCK_BIDS_TOKEN_USER_ID}
    
    response = client.post(f"/project/{test_project_id}/submit-bid", json=bid_data, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Project is not open for bids."

def test_submit_bid_already_exists(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    
    freelancer_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="freelancer")
    
    test_project_id = uuid4()
    mock_project = create_mock_project_bids(project_id=test_project_id, status="open")
    
    mock_firestore_ops_bids.get.side_effect = [mock_freelancer_user, mock_project]
    # Simulate existing bid
    mock_firestore_ops_bids.query.return_value = [create_mock_bid_bids(project_id=test_project_id, freelancer_user_id=freelancer_user_id_obj)]

    bid_data = {"proposal": "Another bid", "amount": 120.0, "project_id": str(test_project_id), "freelancer_user_id": MOCK_BIDS_TOKEN_USER_ID}
    
    response = client.post(f"/project/{test_project_id}/submit-bid", json=bid_data, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "You have already submitted a bid for this project."

# --- Tests for GET /project/{project_id}/list-bids ---

def test_list_bids_for_project_client_owner_success(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)

    client_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="client")
    
    test_project_id = uuid4()
    mock_project = create_mock_project_bids(project_id=test_project_id, client_user_id=client_user_id_obj)
    
    mock_firestore_ops_bids.get.side_effect = [mock_client_user, mock_project]
    
    mock_bids_list = [
        create_mock_bid_bids(project_id=test_project_id),
        create_mock_bid_bids(project_id=test_project_id)
    ]
    mock_firestore_ops_bids.query.return_value = mock_bids_list
    
    response = client.get(f"/project/{test_project_id}/list-bids", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["project_id"] == str(test_project_id)
    mock_firestore_ops_bids.query.assert_called_once_with(
        collection_name="bids", field="project_id", operator="==", value=test_project_id, pydantic_model=Bid
    )

def test_list_bids_for_project_not_client_owner(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)

    other_user_id = uuid4()
    mock_other_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="freelancer") # Authenticated user is a freelancer
    
    test_project_id = uuid4()
    project_owner_id = uuid4() # Different user owns the project
    mock_project = create_mock_project_bids(project_id=test_project_id, client_user_id=project_owner_id)
    
    mock_firestore_ops_bids.get.side_effect = [mock_other_user, mock_project]
    
    response = client.get(f"/project/{test_project_id}/list-bids", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to view bids for this project"

def test_list_bids_for_project_not_found(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    mock_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="client")
    mock_firestore_ops_bids.get.side_effect = [mock_user, None] # Project not found

    test_project_id = uuid4()
    response = client.get(f"/project/{test_project_id}/list-bids", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"

# --- Tests for GET /bids/{bid_id} ---

def test_get_bid_details_freelancer_owner_success(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)

    freelancer_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="freelancer")
    
    test_project_id = uuid4()
    test_bid_id = uuid4()
    mock_bid = create_mock_bid_bids(bid_id=test_bid_id, project_id=test_project_id, freelancer_user_id=freelancer_user_id_obj)
    mock_project = create_mock_project_bids(project_id=test_project_id) # Associated project

    mock_firestore_ops_bids.get.side_effect = [mock_freelancer_user, mock_bid, mock_project]
    
    response = client.get(f"/bids/{test_bid_id}", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["bid_id"] == str(test_bid_id)
    assert data["freelancer_user_id"] == MOCK_BIDS_TOKEN_USER_ID

def test_get_bid_details_client_owner_success(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)

    client_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="client")
    
    test_project_id = uuid4()
    test_bid_id = uuid4()
    mock_bid = create_mock_bid_bids(bid_id=test_bid_id, project_id=test_project_id)
    mock_project = create_mock_project_bids(project_id=test_project_id, client_user_id=client_user_id_obj)

    mock_firestore_ops_bids.get.side_effect = [mock_client_user, mock_bid, mock_project]
    
    response = client.get(f"/bids/{test_bid_id}", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["bid_id"] == str(test_bid_id)

def test_get_bid_details_unauthorized(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)

    unauthorized_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_unauthorized_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="client") # Or any role
    
    test_project_id = uuid4()
    test_bid_id = uuid4()
    # Bid owned by another freelancer, project by another client
    mock_bid = create_mock_bid_bids(bid_id=test_bid_id, project_id=test_project_id, freelancer_user_id=uuid4())
    mock_project = create_mock_project_bids(project_id=test_project_id, client_user_id=uuid4())

    mock_firestore_ops_bids.get.side_effect = [mock_unauthorized_user, mock_bid, mock_project]
    
    response = client.get(f"/bids/{test_bid_id}", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to view this bid"

def test_get_bid_details_bid_not_found(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    mock_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID)
    mock_firestore_ops_bids.get.side_effect = [mock_user, None] # Bid not found

    test_bid_id = uuid4()
    response = client.get(f"/bids/{test_bid_id}", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Bid not found"

# --- Tests for PUT /bids/{bid_id} ---

def test_update_bid_success(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)

    freelancer_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="freelancer")
    
    test_project_id = uuid4()
    test_bid_id = uuid4()
    original_bid = create_mock_bid_bids(bid_id=test_bid_id, project_id=test_project_id, freelancer_user_id=freelancer_user_id_obj, status="pending")
    mock_project = create_mock_project_bids(project_id=test_project_id, status="open")
    
    updated_bid_data_dict = original_bid.model_dump()
    updated_bid_data_dict["amount"] = 200.0
    
    mock_firestore_ops_bids.get.side_effect = [mock_freelancer_user, original_bid, mock_project, Bid(**updated_bid_data_dict)]
    mock_firestore_ops_bids.update.return_value = True

    update_payload = {"amount": 200.0, "proposal": "Updated proposal"}
    response = client.put(f"/bids/{test_bid_id}", json=update_payload, headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 200.0
    
    mock_firestore_ops_bids.update.assert_called_once()
    args, kwargs = mock_firestore_ops_bids.update.call_args
    assert kwargs['updates']['amount'] == 200.0

def test_update_bid_withdraw_success(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    freelancer_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="freelancer")
    test_project_id = uuid4()
    test_bid_id = uuid4()
    original_bid = create_mock_bid_bids(bid_id=test_bid_id, project_id=test_project_id, freelancer_user_id=freelancer_user_id_obj, status="pending")
    mock_project = create_mock_project_bids(project_id=test_project_id, status="open")
    
    updated_bid_data_dict = original_bid.model_dump()
    updated_bid_data_dict["status"] = "withdrawn"
    
    mock_firestore_ops_bids.get.side_effect = [mock_freelancer_user, original_bid, mock_project, Bid(**updated_bid_data_dict)]
    
    response = client.put(f"/bids/{test_bid_id}", json={"status": "withdrawn"}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"
    mock_firestore_ops_bids.update.assert_called_once_with(collection_name="bids", document_id=str(test_bid_id), updates={"status": "withdrawn"})

def test_update_bid_forbidden_not_owner(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    mock_other_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="client") # Not the bid owner
    test_bid_id = uuid4()
    mock_bid = create_mock_bid_bids(bid_id=test_bid_id, freelancer_user_id=uuid4()) # Owned by someone else
    mock_firestore_ops_bids.get.side_effect = [mock_other_user, mock_bid]
    
    response = client.put(f"/bids/{test_bid_id}", json={"amount": 250.0}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update this bid"

def test_update_bid_project_not_open(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    freelancer_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="freelancer")
    test_project_id = uuid4()
    test_bid_id = uuid4()
    mock_bid = create_mock_bid_bids(bid_id=test_bid_id, project_id=test_project_id, freelancer_user_id=freelancer_user_id_obj, status="pending")
    mock_project = create_mock_project_bids(project_id=test_project_id, status="completed") # Not open
    mock_firestore_ops_bids.get.side_effect = [mock_freelancer_user, mock_bid, mock_project]

    response = client.put(f"/bids/{test_bid_id}", json={"amount": 250.0}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert "Project must be 'open' and bid 'pending'" in response.json()["detail"]

def test_update_bid_bid_not_pending(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    freelancer_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="freelancer")
    test_project_id = uuid4()
    test_bid_id = uuid4()
    mock_bid = create_mock_bid_bids(bid_id=test_bid_id, project_id=test_project_id, freelancer_user_id=freelancer_user_id_obj, status="accepted") # Not pending
    mock_project = create_mock_project_bids(project_id=test_project_id, status="open")
    mock_firestore_ops_bids.get.side_effect = [mock_freelancer_user, mock_bid, mock_project]

    response = client.put(f"/bids/{test_bid_id}", json={"amount": 250.0}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert "Project must be 'open' and bid 'pending'" in response.json()["detail"]

def test_update_bid_invalid_status_update(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    freelancer_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="freelancer")
    test_project_id = uuid4()
    test_bid_id = uuid4()
    mock_bid = create_mock_bid_bids(bid_id=test_bid_id, project_id=test_project_id, freelancer_user_id=freelancer_user_id_obj, status="pending")
    mock_project = create_mock_project_bids(project_id=test_project_id, status="open")
    mock_firestore_ops_bids.get.side_effect = [mock_freelancer_user, mock_bid, mock_project]

    response = client.put(f"/bids/{test_bid_id}", json={"status": "accepted"}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Only 'withdrawn' status is allowed for self-update."


# --- Tests for POST /project/{project_id}/bid/{bid_id}/accept ---

def test_accept_bid_success(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)

    client_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="client")
    
    freelancer_to_be_accepted_id = uuid4()
    test_project_id = uuid4()
    test_bid_id = uuid4()

    mock_project = create_mock_project_bids(project_id=test_project_id, client_user_id=client_user_id_obj, status="open")
    mock_bid_to_accept = create_mock_bid_bids(bid_id=test_bid_id, project_id=test_project_id, freelancer_user_id=freelancer_to_be_accepted_id, status="pending")
    
    # Mock other pending bids for the same project
    other_bid_id = uuid4()
    mock_other_pending_bid = create_mock_bid_bids(bid_id=other_bid_id, project_id=test_project_id, status="pending")
    
    mock_firestore_ops_bids.get.side_effect = [mock_client_user, mock_project, mock_bid_to_accept]
    mock_firestore_ops_bids.query.return_value = [mock_bid_to_accept, mock_other_pending_bid] # Bids for the project
    mock_firestore_ops_bids.update.return_value = True # All updates succeed
    mock_firestore_ops_bids.save.return_value = str(uuid4()) # Contract save succeeds

    response = client.post(f"/project/{test_project_id}/bid/{test_bid_id}/accept", headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 200 # Endpoint returns 200 for this, not 201
    assert response.json()["message"] == "Bid accepted, project in progress, and contract created."

    # Check updates: bid accepted, project updated, other bid rejected, contract created
    expected_calls = [
        call(collection_name='bids', document_id=str(test_bid_id), updates={'status': 'accepted'}),
        call(collection_name='projects', document_id=str(test_project_id), updates={'status': 'in_progress', 'freelancer_user_id': freelancer_to_be_accepted_id}),
        call(collection_name='bids', document_id=str(other_bid_id), updates={'status': 'rejected'})
    ]
    mock_firestore_ops_bids.update.assert_has_calls(expected_calls, any_order=False) # Order matters for these updates
    mock_firestore_ops_bids.save.assert_called_once() # For contract
    args_save, kwargs_save = mock_firestore_ops_bids.save.call_args
    assert kwargs_save['collection_name'] == 'contracts'
    assert kwargs_save['data_model']['project_id'] == test_project_id
    assert kwargs_save['data_model']['freelancer_id'] == freelancer_to_be_accepted_id

def test_accept_bid_forbidden_not_client_owner(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    mock_non_owner_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="freelancer") # Not client owner
    test_project_id = uuid4()
    mock_project = create_mock_project_bids(project_id=test_project_id, client_user_id=uuid4()) # Different client owner
    mock_firestore_ops_bids.get.side_effect = [mock_non_owner_user, mock_project]

    response = client.post(f"/project/{test_project_id}/bid/{uuid4()}/accept", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to accept bids for this project"

def test_accept_bid_project_not_open(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    client_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="client")
    test_project_id = uuid4()
    mock_project = create_mock_project_bids(project_id=test_project_id, client_user_id=client_user_id_obj, status="completed") # Not open
    test_bid_id = uuid4()
    mock_bid = create_mock_bid_bids(bid_id=test_bid_id, project_id=test_project_id, status="pending")
    mock_firestore_ops_bids.get.side_effect = [mock_client_user, mock_project, mock_bid]

    response = client.post(f"/project/{test_project_id}/bid/{test_bid_id}/accept", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert "Project is not open" in response.json()["detail"]

def test_accept_bid_bid_not_pending(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    client_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="client")
    test_project_id = uuid4()
    mock_project = create_mock_project_bids(project_id=test_project_id, client_user_id=client_user_id_obj, status="open")
    test_bid_id = uuid4()
    mock_bid = create_mock_bid_bids(bid_id=test_bid_id, project_id=test_project_id, status="accepted") # Not pending
    mock_firestore_ops_bids.get.side_effect = [mock_client_user, mock_project, mock_bid]

    response = client.post(f"/project/{test_project_id}/bid/{test_bid_id}/accept", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Bid is not in a pending state."

def test_accept_bid_bid_project_mismatch(mock_firestore_ops_bids, mock_decode_token_bids, monkeypatch):
    monkeypatch.setattr("app.routers.bids.get_firestore_ops_instance", lambda: mock_firestore_ops_bids)
    client_user_id_obj = UUID(MOCK_BIDS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_bids(MOCK_BIDS_TOKEN_USER_ID, role="client")
    
    path_project_id = uuid4() # Project ID in the path
    bid_project_id = uuid4()  # Different project ID associated with the bid
    
    mock_project_in_path = create_mock_project_bids(project_id=path_project_id, client_user_id=client_user_id_obj, status="open")
    test_bid_id = uuid4()
    mock_bid = create_mock_bid_bids(bid_id=test_bid_id, project_id=bid_project_id, status="pending") # Bid belongs to different project
    
    mock_firestore_ops_bids.get.side_effect = [mock_client_user, mock_project_in_path, mock_bid]

    response = client.post(f"/project/{path_project_id}/bid/{test_bid_id}/accept", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Bid does not belong to this project."
