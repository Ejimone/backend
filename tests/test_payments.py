import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, call 
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.main import app # FastAPI application
from app.models.schemas import Transaction, User, Project, Bid, TransactionCreate 
# Bid is needed for testing fallback for amount in checkout
# TransactionCreate might be useful for type hinting if not directly used

client = TestClient(app)

MOCK_PAYMENTS_TOKEN_USER_ID = "mock-payments-user-id"

@pytest.fixture
def mock_firestore_ops_payments():
    mock_ops = MagicMock()
    mock_ops.get.return_value = None
    mock_ops.query.return_value = []
    mock_ops.save.side_effect = lambda collection_name, data_model, document_id: document_id
    mock_ops.update.return_value = True
    return mock_ops

@pytest.fixture
def mock_decode_token_payments(monkeypatch):
    """Mocks decode_access_token for payment routes to return a fixed user ID."""
    mock_decoder = MagicMock(return_value=MOCK_PAYMENTS_TOKEN_USER_ID)
    monkeypatch.setattr("app.routers.payments.decode_access_token", mock_decoder)
    return mock_decoder

# Helper functions
def create_mock_user_payments(user_id_str: str, role="client", username_prefix="payuser"):
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

def create_mock_project_payments(
    project_id: Optional[UUID] = None, 
    client_user_id: Optional[UUID] = None, 
    freelancer_user_id: Optional[UUID] = None, 
    status="open",
    budget: Optional[float] = 100.0,
    title="Test Project"
):
    return Project(
        project_id=project_id if project_id else uuid4(),
        client_user_id=client_user_id if client_user_id else uuid4(),
        freelancer_user_id=freelancer_user_id,
        title=title,
        description="A test project description.",
        budget=budget,
        status=status,
        creation_date=datetime.utcnow(),
        last_updated_date=datetime.utcnow(),
        tags=["test", "mock"]
    )

def create_mock_transaction_payments(
    transaction_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    payer_user_id: Optional[UUID] = None,
    payee_user_id: Optional[UUID] = None,
    amount: float = 100.0,
    transaction_type: str = "project_payment",
    status: str = "completed"
):
    return Transaction(
        transaction_id=transaction_id if transaction_id else uuid4(),
        project_id=project_id,
        payer_user_id=payer_user_id,
        payee_user_id=payee_user_id if payee_user_id else uuid4(),
        amount=amount,
        currency="USD",
        transaction_type=transaction_type,
        status=status,
        transaction_date=datetime.utcnow()
    )

def create_mock_bid_payments(
    bid_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    freelancer_user_id: Optional[UUID] = None,
    status: str = "accepted", # Default to accepted for amount fallback
    amount: float = 150.0
):
    return Bid(
        bid_id=bid_id if bid_id else uuid4(),
        project_id=project_id if project_id else uuid4(),
        freelancer_user_id=freelancer_user_id if freelancer_user_id else uuid4(),
        proposal="Accepted test bid",
        amount=amount,
        estimated_completion_time="2 weeks",
        bid_date=datetime.utcnow(),
        status=status
    )

# --- Tests for POST /payments/checkout/project/{project_id} ---

def test_checkout_project_payment_success_with_project_budget(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)

    client_user_id_obj = UUID(MOCK_PAYMENTS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID, role="client")
    
    test_project_id = uuid4()
    assigned_freelancer_id = uuid4()
    mock_project = create_mock_project_payments(
        project_id=test_project_id, 
        client_user_id=client_user_id_obj, 
        freelancer_user_id=assigned_freelancer_id,
        status="completed", 
        budget=120.0
    )

    mock_firestore_ops_payments.get.side_effect = [mock_client_user, mock_project]
    mock_firestore_ops_payments.query.return_value = [] # No existing transactions

    response = client.post(f"/payments/checkout/project/{test_project_id}", headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == str(test_project_id)
    assert data["payer_user_id"] == MOCK_PAYMENTS_TOKEN_USER_ID
    assert data["payee_user_id"] == str(assigned_freelancer_id)
    assert data["amount"] == 120.0
    assert data["transaction_type"] == "project_payment"
    assert data["status"] == "completed"
    
    mock_firestore_ops_payments.save.assert_called_once()
    args, kwargs = mock_firestore_ops_payments.save.call_args
    assert kwargs['collection_name'] == 'transactions'
    assert kwargs['data_model']['amount'] == 120.0

def test_checkout_project_payment_success_with_bid_amount(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)

    client_user_id_obj = UUID(MOCK_PAYMENTS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID, role="client")
    
    test_project_id = uuid4()
    assigned_freelancer_id = uuid4()
    mock_project = create_mock_project_payments(
        project_id=test_project_id, 
        client_user_id=client_user_id_obj, 
        freelancer_user_id=assigned_freelancer_id,
        status="completed", 
        budget=None # Invalid budget to force bid amount fallback
    )
    mock_accepted_bid = create_mock_bid_payments(project_id=test_project_id, freelancer_user_id=assigned_freelancer_id, status="accepted", amount=180.0)

    mock_firestore_ops_payments.get.side_effect = [mock_client_user, mock_project]
    mock_firestore_ops_payments.query.side_effect = [[], [mock_accepted_bid]] # No existing transactions, then the bid

    response = client.post(f"/payments/checkout/project/{test_project_id}", headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 180.0
    mock_firestore_ops_payments.save.assert_called_once()

def test_checkout_project_payment_not_client_owner(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)
    mock_not_owner_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID, role="freelancer") # Not the client
    test_project_id = uuid4()
    mock_project = create_mock_project_payments(project_id=test_project_id, client_user_id=uuid4()) # Different client
    mock_firestore_ops_payments.get.side_effect = [mock_not_owner_user, mock_project]

    response = client.post(f"/payments/checkout/project/{test_project_id}", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Only the project client can make this payment."

def test_checkout_project_payment_project_not_completed(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)
    client_user_id_obj = UUID(MOCK_PAYMENTS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID, role="client")
    test_project_id = uuid4()
    mock_project = create_mock_project_payments(project_id=test_project_id, client_user_id=client_user_id_obj, status="in_progress") # Not completed
    mock_firestore_ops_payments.get.side_effect = [mock_client_user, mock_project]

    response = client.post(f"/payments/checkout/project/{test_project_id}", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Project is not marked as completed."

def test_checkout_project_payment_no_freelancer(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)
    client_user_id_obj = UUID(MOCK_PAYMENTS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID, role="client")
    test_project_id = uuid4()
    mock_project = create_mock_project_payments(project_id=test_project_id, client_user_id=client_user_id_obj, freelancer_user_id=None, status="completed") # No freelancer
    mock_firestore_ops_payments.get.side_effect = [mock_client_user, mock_project]

    response = client.post(f"/payments/checkout/project/{test_project_id}", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Project has no assigned freelancer to pay."

def test_checkout_project_payment_already_paid(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)
    client_user_id_obj = UUID(MOCK_PAYMENTS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID, role="client")
    test_project_id = uuid4()
    mock_project = create_mock_project_payments(project_id=test_project_id, client_user_id=client_user_id_obj, status="completed", freelancer_user_id=uuid4())
    
    existing_payment = create_mock_transaction_payments(project_id=test_project_id, transaction_type="project_payment", status="completed")
    mock_firestore_ops_payments.get.side_effect = [mock_client_user, mock_project]
    mock_firestore_ops_payments.query.return_value = [existing_payment.model_dump()] # Simulate existing completed payment (as dict)

    response = client.post(f"/payments/checkout/project/{test_project_id}", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Payment for this project has already been processed."

def test_checkout_project_payment_amount_undeterminable(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)
    client_user_id_obj = UUID(MOCK_PAYMENTS_TOKEN_USER_ID)
    mock_client_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID, role="client")
    test_project_id = uuid4()
    mock_project = create_mock_project_payments(
        project_id=test_project_id, client_user_id=client_user_id_obj, 
        freelancer_user_id=uuid4(), status="completed", budget=0 # Invalid budget
    )
    mock_firestore_ops_payments.get.side_effect = [mock_client_user, mock_project]
    mock_firestore_ops_payments.query.side_effect = [[], []] # No existing transactions, no accepted bid with valid amount

    response = client.post(f"/payments/checkout/project/{test_project_id}", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert "Project budget is not set or invalid" in response.json()["detail"]

def test_checkout_project_payment_project_not_found(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)
    mock_client_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID, role="client")
    mock_firestore_ops_payments.get.side_effect = [mock_client_user, None] # Project not found

    response = client.post(f"/payments/checkout/project/{uuid4()}", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"

# --- Tests for GET /payments/history ---

def test_get_payment_history_success(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)
    
    user_id_obj = UUID(MOCK_PAYMENTS_TOKEN_USER_ID)
    mock_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID)
    mock_firestore_ops_payments.get.return_value = mock_user

    tx1_time = datetime.utcnow()
    tx2_time = datetime(tx1_time.year, tx1_time.month, tx1_time.day, tx1_time.hour, tx1_time.minute -1, tx1_time.second, tzinfo=tx1_time.tzinfo) # 1 min before
    
    payer_tx = create_mock_transaction_payments(payer_user_id=user_id_obj, transaction_date=tx1_time)
    payee_tx = create_mock_transaction_payments(payee_user_id=user_id_obj, transaction_date=tx2_time)
    
    # Simulate two query calls
    mock_firestore_ops_payments.query.side_effect = [
        [payer_tx], # First call for payer_user_id
        [payee_tx]  # Second call for payee_user_id
    ]
    
    response = client.get("/payments/history", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["transaction_id"] == str(payer_tx.transaction_id) # tx1 is more recent
    assert data[1]["transaction_id"] == str(payee_tx.transaction_id)

def test_get_payment_history_empty(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)
    mock_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID)
    mock_firestore_ops_payments.get.return_value = mock_user
    mock_firestore_ops_payments.query.return_value = [] # Both queries return empty
    
    response = client.get("/payments/history", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 200
    assert response.json() == []

def test_get_payment_history_auth_error(monkeypatch):
    monkeypatch.setattr("app.routers.payments.decode_access_token", MagicMock(return_value=None))
    response = client.get("/payments/history", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401

# --- Tests for POST /payments/withdraw ---

def test_withdraw_funds_success(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)
    
    freelancer_user_id_obj = UUID(MOCK_PAYMENTS_TOKEN_USER_ID)
    mock_freelancer_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID, role="freelancer")
    mock_firestore_ops_payments.get.return_value = mock_freelancer_user

    withdrawal_amount = 50.0
    response = client.post("/payments/withdraw", json={"amount": withdrawal_amount}, headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 201
    data = response.json()
    assert data["payee_user_id"] == MOCK_PAYMENTS_TOKEN_USER_ID
    assert data["payer_user_id"] is None # Platform is payer
    assert data["amount"] == withdrawal_amount
    assert data["transaction_type"] == "withdrawal"
    assert data["status"] == "pending"
    
    mock_firestore_ops_payments.save.assert_called_once()
    args, kwargs = mock_firestore_ops_payments.save.call_args
    assert kwargs['collection_name'] == 'transactions'
    assert kwargs['data_model']['amount'] == withdrawal_amount
    assert kwargs['data_model']['payee_user_id'] == freelancer_user_id_obj
    assert kwargs['data_model']['payer_user_id'] is None

def test_withdraw_funds_not_freelancer(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)
    mock_client_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID, role="client") # Not a freelancer
    mock_firestore_ops_payments.get.return_value = mock_client_user
    
    response = client.post("/payments/withdraw", json={"amount": 50.0}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Only freelancers can withdraw funds."

def test_withdraw_funds_invalid_amount(mock_firestore_ops_payments, mock_decode_token_payments, monkeypatch):
    monkeypatch.setattr("app.routers.payments.get_firestore_ops_instance", lambda: mock_firestore_ops_payments)
    mock_freelancer_user = create_mock_user_payments(MOCK_PAYMENTS_TOKEN_USER_ID, role="freelancer")
    mock_firestore_ops_payments.get.return_value = mock_freelancer_user
    
    response = client.post("/payments/withdraw", json={"amount": 0}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or missing withdrawal amount."
    
    response = client.post("/payments/withdraw", json={"amount": -10}, headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or missing withdrawal amount."

def test_withdraw_funds_auth_error(monkeypatch):
    monkeypatch.setattr("app.routers.payments.decode_access_token", MagicMock(return_value=None))
    response = client.post("/payments/withdraw", json={"amount": 50.0}, headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
