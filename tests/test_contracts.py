import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.main import app # FastAPI application
from app.models.schemas import Contract, User

client = TestClient(app)

MOCK_CONTRACTS_TOKEN_USER_ID = "mock-contracts-user-id"

@pytest.fixture
def mock_firestore_ops_contracts():
    mock_ops = MagicMock()
    mock_ops.get.return_value = None
    mock_ops.query.return_value = []
    mock_ops.save.side_effect = lambda collection_name, data_model, document_id: document_id
    mock_ops.update.return_value = True
    mock_ops.delete.return_value = True
    return mock_ops

@pytest.fixture
def mock_decode_token_contracts(monkeypatch):
    """Mocks decode_access_token for contract routes to return a fixed user ID."""
    mock_decoder = MagicMock(return_value=MOCK_CONTRACTS_TOKEN_USER_ID)
    monkeypatch.setattr("app.routers.contracts.decode_access_token", mock_decoder)
    return mock_decoder

# Helper functions
def create_mock_user_contracts(user_id_str: str, role="client", username_prefix="user"):
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

def create_mock_contract_contracts(
    contract_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    client_id: Optional[UUID] = None,
    freelancer_id: Optional[UUID] = None,
    status: str = "active",
    agreed_amount: float = 1000.0
):
    return Contract(
        contract_id=contract_id if contract_id else uuid4(),
        project_id=project_id if project_id else uuid4(),
        client_id=client_id if client_id else uuid4(),
        freelancer_id=freelancer_id if freelancer_id else uuid4(),
        terms="Standard contract terms for testing.",
        agreed_amount=agreed_amount,
        start_date=datetime.utcnow(),
        end_date=None,
        status=status,
        creation_date=datetime.utcnow() # Pydantic default usually handles this
    )

# --- Tests for GET /contracts/ ---

def test_list_my_contracts_client_success(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    
    client_user_id_obj = UUID(MOCK_CONTRACTS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID, role="client")
    mock_firestore_ops_contracts.get.return_value = mock_client_user # For fetching current user

    mock_contracts_list = [
        create_mock_contract_contracts(client_id=client_user_id_obj),
        create_mock_contract_contracts(client_id=client_user_id_obj)
    ]
    mock_firestore_ops_contracts.query.return_value = mock_contracts_list
    
    response = client.get("/contracts/", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["client_id"] == MOCK_CONTRACTS_TOKEN_USER_ID
    
    mock_firestore_ops_contracts.query.assert_called_once_with(
        collection_name="contracts", field="client_id", operator="==", value=client_user_id_obj, pydantic_model=Contract
    )

def test_list_my_contracts_freelancer_success(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    
    freelancer_user_id_obj = UUID(MOCK_CONTRACTS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID, role="freelancer")
    mock_firestore_ops_contracts.get.return_value = mock_freelancer_user

    mock_contracts_list = [create_mock_contract_contracts(freelancer_id=freelancer_user_id_obj)]
    mock_firestore_ops_contracts.query.return_value = mock_contracts_list
    
    response = client.get("/contracts/", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["freelancer_id"] == MOCK_CONTRACTS_TOKEN_USER_ID
    
    mock_firestore_ops_contracts.query.assert_called_once_with(
        collection_name="contracts", field="freelancer_id", operator="==", value=freelancer_user_id_obj, pydantic_model=Contract
    )

def test_list_my_contracts_no_contracts(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    mock_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID, role="client")
    mock_firestore_ops_contracts.get.return_value = mock_user
    mock_firestore_ops_contracts.query.return_value = [] # No contracts
    
    response = client.get("/contracts/", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 200
    assert response.json() == []

def test_list_my_contracts_other_role(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    mock_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID, role="admin") # e.g., admin
    mock_firestore_ops_contracts.get.return_value = mock_user
    
    response = client.get("/contracts/", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 200
    assert response.json() == [] # Expect empty list as per current logic

def test_list_my_contracts_auth_error(monkeypatch):
    monkeypatch.setattr("app.routers.contracts.decode_access_token", MagicMock(return_value=None))
    response = client.get("/contracts/", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401

# --- Tests for GET /contracts/{contract_id} ---

def test_get_contract_details_client_involved_success(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    
    client_user_id_obj = UUID(MOCK_CONTRACTS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID, role="client")
    
    test_contract_id = uuid4()
    mock_contract = create_mock_contract_contracts(contract_id=test_contract_id, client_id=client_user_id_obj)
    
    mock_firestore_ops_contracts.get.side_effect = [mock_client_user, mock_contract]
    
    response = client.get(f"/contracts/{test_contract_id}", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["contract_id"] == str(test_contract_id)
    assert data["client_id"] == MOCK_CONTRACTS_TOKEN_USER_ID

def test_get_contract_details_freelancer_involved_success(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    
    freelancer_user_id_obj = UUID(MOCK_CONTRACTS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID, role="freelancer")
    
    test_contract_id = uuid4()
    mock_contract = create_mock_contract_contracts(contract_id=test_contract_id, freelancer_id=freelancer_user_id_obj)
    
    mock_firestore_ops_contracts.get.side_effect = [mock_freelancer_user, mock_contract]
    
    response = client.get(f"/contracts/{test_contract_id}", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["contract_id"] == str(test_contract_id)
    assert data["freelancer_id"] == MOCK_CONTRACTS_TOKEN_USER_ID

def test_get_contract_details_unauthorized(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    
    unauthorized_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID, role="client") # This user is not part of the contract
    
    test_contract_id = uuid4()
    # Contract between two different users
    mock_contract = create_mock_contract_contracts(contract_id=test_contract_id, client_id=uuid4(), freelancer_id=uuid4())
    
    mock_firestore_ops_contracts.get.side_effect = [unauthorized_user, mock_contract]
    
    response = client.get(f"/contracts/{test_contract_id}", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to view this contract"

def test_get_contract_details_not_found(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    mock_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID)
    mock_firestore_ops_contracts.get.side_effect = [mock_user, None] # Contract not found
    
    test_contract_id = uuid4()
    response = client.get(f"/contracts/{test_contract_id}", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Contract not found"

def test_get_contract_details_auth_error(monkeypatch):
    monkeypatch.setattr("app.routers.contracts.decode_access_token", MagicMock(return_value=None))
    response = client.get(f"/contracts/{uuid4()}", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401

# --- Tests for PUT /contracts/{contract_id}/status ---

def test_update_contract_status_client_success(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    
    client_user_id_obj = UUID(MOCK_CONTRACTS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID, role="client")
    
    test_contract_id = uuid4()
    original_contract = create_mock_contract_contracts(contract_id=test_contract_id, client_id=client_user_id_obj, status="active")
    
    updated_contract_data = original_contract.model_dump()
    updated_contract_data["status"] = "completed"
    updated_contract_data["last_updated_date"] = datetime.utcnow() # Simulate update
    
    mock_firestore_ops_contracts.get.side_effect = [mock_client_user, original_contract, Contract(**updated_contract_data)]
    mock_firestore_ops_contracts.update.return_value = True

    payload = {"status": "completed"}
    response = client.put(f"/contracts/{test_contract_id}/status", json=payload, headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["contract_id"] == str(test_contract_id)
    
    mock_firestore_ops_contracts.update.assert_called_once()
    args, kwargs = mock_firestore_ops_contracts.update.call_args
    assert kwargs['collection_name'] == 'contracts'
    assert kwargs['document_id'] == str(test_contract_id)
    assert kwargs['updates']['status'] == "completed"
    assert "last_updated_date" in kwargs['updates']

def test_update_contract_status_freelancer_success(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    
    freelancer_user_id_obj = UUID(MOCK_CONTRACTS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID, role="freelancer")
    
    test_contract_id = uuid4()
    original_contract = create_mock_contract_contracts(contract_id=test_contract_id, freelancer_id=freelancer_user_id_obj, status="active")
    
    updated_contract_data = original_contract.model_dump()
    updated_contract_data["status"] = "disputed" # Freelancer might dispute
    
    mock_firestore_ops_contracts.get.side_effect = [mock_freelancer_user, original_contract, Contract(**updated_contract_data)]

    payload = {"status": "disputed"}
    response = client.put(f"/contracts/{test_contract_id}/status", json=payload, headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "disputed"

def test_update_contract_status_unauthorized(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    unauthorized_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID, role="admin") # Some other role
    test_contract_id = uuid4()
    mock_contract = create_mock_contract_contracts(contract_id=test_contract_id, client_id=uuid4(), freelancer_id=uuid4()) # Different users
    mock_firestore_ops_contracts.get.side_effect = [unauthorized_user, mock_contract]
    
    response = client.put(f"/contracts/{test_contract_id}/status", json={"status": "completed"}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to update this contract's status"

def test_update_contract_status_invalid_status_value(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    mock_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID)
    test_contract_id = uuid4()
    mock_contract = create_mock_contract_contracts(contract_id=test_contract_id, client_id=UUID(MOCK_CONTRACTS_TOKEN_USER_ID))
    mock_firestore_ops_contracts.get.side_effect = [mock_user, mock_contract]
    
    response = client.put(f"/contracts/{test_contract_id}/status", json={"status": "pending_payment"}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert "Invalid or missing status" in response.json()["detail"]

def test_update_contract_status_missing_status_payload(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    mock_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID)
    test_contract_id = uuid4()
    mock_contract = create_mock_contract_contracts(contract_id=test_contract_id, client_id=UUID(MOCK_CONTRACTS_TOKEN_USER_ID))
    mock_firestore_ops_contracts.get.side_effect = [mock_user, mock_contract]

    response = client.put(f"/contracts/{test_contract_id}/status", json={}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert "Invalid or missing status" in response.json()["detail"]
    
    response = client.put(f"/contracts/{test_contract_id}/status", json={"other_key": "active"}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert "Invalid or missing status" in response.json()["detail"]


def test_update_contract_status_contract_not_found(mock_firestore_ops_contracts, mock_decode_token_contracts, monkeypatch):
    monkeypatch.setattr("app.routers.contracts.get_firestore_ops_instance", lambda: mock_firestore_ops_contracts)
    mock_user = create_mock_user_contracts(MOCK_CONTRACTS_TOKEN_USER_ID)
    mock_firestore_ops_contracts.get.side_effect = [mock_user, None] # Contract not found
    
    test_contract_id = uuid4()
    response = client.put(f"/contracts/{test_contract_id}/status", json={"status": "completed"}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Contract not found"

def test_update_contract_status_auth_error(monkeypatch):
    monkeypatch.setattr("app.routers.contracts.decode_access_token", MagicMock(return_value=None))
    response = client.put(f"/contracts/{uuid4()}/status", json={"status": "completed"}, headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
