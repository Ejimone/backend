import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, call
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.main import app # FastAPI application
from app.models.schemas import Chat, Message, User # ChatInitiateRequest, MessageContent are defined in router
from app.routers.messaging import ChatInitiateRequest, MessageContent # Import request models

client = TestClient(app)

MOCK_MESSAGING_TOKEN_USER_ID = "mock-messaging-user-id"

@pytest.fixture
def mock_firestore_ops_messaging():
    mock_ops = MagicMock()
    # Default behavior for direct methods
    mock_ops.get.return_value = None
    mock_ops.query.return_value = [] # For simple queries
    mock_ops.save.side_effect = lambda collection_name, data_model, document_id: document_id
    mock_ops.update.return_value = True
    
    # Mocking for chained calls: firestore_ops.db.collection("...").where("...").where("...").stream()
    # This setup allows for mocking the full chain.
    mock_db_instance = MagicMock()
    mock_collection_ref = MagicMock()
    mock_query_ref = MagicMock() # This will be returned by .where() and can be returned by itself for chaining .where()

    mock_ops.db = mock_db_instance
    mock_db_instance.collection.return_value = mock_collection_ref
    mock_collection_ref.where.return_value = mock_query_ref
    mock_query_ref.where.return_value = mock_query_ref # For multiple .where() calls
    mock_query_ref.stream.return_value = [] # Default to no results for streams
    
    return mock_ops

@pytest.fixture
def mock_decode_token_messaging(monkeypatch):
    """Mocks decode_access_token for messaging routes to return a fixed user ID."""
    mock_decoder = MagicMock(return_value=MOCK_MESSAGING_TOKEN_USER_ID)
    monkeypatch.setattr("app.routers.messaging.decode_access_token", mock_decoder)
    return mock_decoder

# Helper functions
def create_mock_user_messaging(user_id_str: str, role="client", username_prefix="msguser"):
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
        registration_date=datetime.now(timezone.utc),
        phone_number=None,
        profile_picture_url=None,
        last_login_date=None
    )

def create_mock_chat_messaging(
    chat_id: Optional[UUID] = None,
    participant1_id: Optional[UUID] = None,
    participant2_id: Optional[UUID] = None,
    project_context_id: Optional[UUID] = None,
    last_message_timestamp: Optional[datetime] = None
):
    return Chat(
        chat_id=chat_id if chat_id else uuid4(),
        participant1_id=participant1_id if participant1_id else uuid4(),
        participant2_id=participant2_id if participant2_id else uuid4(),
        project_context_id=project_context_id,
        last_message_timestamp=last_message_timestamp
    )

def create_mock_message_messaging(
    message_id: Optional[UUID] = None,
    chat_id: Optional[UUID] = None,
    sender_id: Optional[UUID] = None,
    receiver_id: Optional[UUID] = None,
    content: str = "Test message content",
    timestamp: Optional[datetime] = None
):
    return Message(
        message_id=message_id if message_id else uuid4(),
        chat_id=chat_id if chat_id else uuid4(),
        sender_id=sender_id if sender_id else uuid4(),
        receiver_id=receiver_id if receiver_id else uuid4(),
        content=content,
        timestamp=timestamp if timestamp else datetime.now(timezone.utc),
        is_read=False,
        ai_suggestions=None
    )

# Mock document structure for stream() results
class MockFirestoreDocument:
    def __init__(self, data_dict):
        self._data = data_dict
    def to_dict(self):
        return self._data

# --- Tests for POST /chats/ (Start New Chat) ---

def test_start_new_chat_success(mock_firestore_ops_messaging, mock_decode_token_messaging, monkeypatch):
    monkeypatch.setattr("app.routers.messaging.get_firestore_ops_instance", lambda: mock_firestore_ops_messaging)

    p1_id_obj = UUID(MOCK_MESSAGING_TOKEN_USER_ID)
    mock_p1_user = create_mock_user_messaging(MOCK_MESSAGING_TOKEN_USER_ID)
    
    p2_id_obj = uuid4()
    mock_p2_user = create_mock_user_messaging(str(p2_id_obj), username_prefix="p2user")

    mock_firestore_ops_messaging.get.side_effect = [mock_p1_user, mock_p2_user] # P1, then P2
    # Simulate no existing chat: both stream() calls return empty list
    mock_firestore_ops_messaging.db.collection("chats").where().stream.return_value = [] 

    chat_req_data = ChatInitiateRequest(participant2_id=p2_id_obj)
    response = client.post("/chats/", json=chat_req_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 201
    data = response.json()
    assert data["participant1_id"] == MOCK_MESSAGING_TOKEN_USER_ID
    assert data["participant2_id"] == str(p2_id_obj)
    assert "chat_id" in data
    
    mock_firestore_ops_messaging.save.assert_called_once()
    args, kwargs = mock_firestore_ops_messaging.save.call_args
    assert kwargs['collection_name'] == 'chats'
    assert kwargs['data_model']['participant1_id'] == p1_id_obj
    assert kwargs['data_model']['participant2_id'] == p2_id_obj

def test_start_new_chat_participant2_not_found(mock_firestore_ops_messaging, mock_decode_token_messaging, monkeypatch):
    monkeypatch.setattr("app.routers.messaging.get_firestore_ops_instance", lambda: mock_firestore_ops_messaging)
    mock_p1_user = create_mock_user_messaging(MOCK_MESSAGING_TOKEN_USER_ID)
    mock_firestore_ops_messaging.get.side_effect = [mock_p1_user, None] # P2 not found

    chat_req_data = ChatInitiateRequest(participant2_id=uuid4())
    response = client.post("/chats/", json=chat_req_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Participant 2 not found."

def test_start_new_chat_with_self(mock_firestore_ops_messaging, mock_decode_token_messaging, monkeypatch):
    monkeypatch.setattr("app.routers.messaging.get_firestore_ops_instance", lambda: mock_firestore_ops_messaging)
    p1_id_obj = UUID(MOCK_MESSAGING_TOKEN_USER_ID)
    mock_p1_user = create_mock_user_messaging(MOCK_MESSAGING_TOKEN_USER_ID)
    mock_firestore_ops_messaging.get.return_value = mock_p1_user # P1 lookup

    chat_req_data = ChatInitiateRequest(participant2_id=p1_id_obj) # P2 is same as P1
    response = client.post("/chats/", json=chat_req_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot start a chat with yourself."

def test_start_new_chat_already_exists(mock_firestore_ops_messaging, mock_decode_token_messaging, monkeypatch):
    monkeypatch.setattr("app.routers.messaging.get_firestore_ops_instance", lambda: mock_firestore_ops_messaging)
    
    p1_id_obj = UUID(MOCK_MESSAGING_TOKEN_USER_ID)
    mock_p1_user = create_mock_user_messaging(MOCK_MESSAGING_TOKEN_USER_ID)
    
    p2_id_obj = uuid4()
    mock_p2_user = create_mock_user_messaging(str(p2_id_obj), username_prefix="p2user")

    mock_firestore_ops_messaging.get.side_effect = [mock_p1_user, mock_p2_user]
    
    existing_chat_obj = create_mock_chat_messaging(participant1_id=p1_id_obj, participant2_id=p2_id_obj)
    mock_chat_doc = MockFirestoreDocument(existing_chat_obj.model_dump(mode='json'))
    
    # Simulate finding chat in the first query (P1 -> P2)
    mock_firestore_ops_messaging.db.collection("chats").where().stream.return_value = [mock_chat_doc]

    chat_req_data = ChatInitiateRequest(participant2_id=p2_id_obj)
    response = client.post("/chats/", json=chat_req_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200 # Changed from 201 based on previous subtask that returns existing chat with 200
    data = response.json()
    assert data["chat_id"] == str(existing_chat_obj.chat_id)
    mock_firestore_ops_messaging.save.assert_not_called() # Should not save a new one

def test_start_new_chat_auth_error(monkeypatch):
    monkeypatch.setattr("app.routers.messaging.decode_access_token", MagicMock(return_value=None))
    chat_req_data = ChatInitiateRequest(participant2_id=uuid4())
    response = client.post("/chats/", json=chat_req_data.model_dump(mode='json'), headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401

# --- Tests for GET /chats/ (List User's Chats) ---

def test_list_my_chats_success(mock_firestore_ops_messaging, mock_decode_token_messaging, monkeypatch):
    monkeypatch.setattr("app.routers.messaging.get_firestore_ops_instance", lambda: mock_firestore_ops_messaging)
    
    user_id_obj = UUID(MOCK_MESSAGING_TOKEN_USER_ID)
    mock_user = create_mock_user_messaging(MOCK_MESSAGING_TOKEN_USER_ID)
    mock_firestore_ops_messaging.get.return_value = mock_user

    # Timezones are important for correct sorting if not naive
    now = datetime.now(timezone.utc)
    chat1_p1 = create_mock_chat_messaging(participant1_id=user_id_obj, last_message_timestamp=now)
    chat2_p2 = create_mock_chat_messaging(participant2_id=user_id_obj, last_message_timestamp=now - timedelta(hours=1))
    
    mock_chat1_doc = MockFirestoreDocument(chat1_p1.model_dump(mode='json'))
    mock_chat2_doc = MockFirestoreDocument(chat2_p2.model_dump(mode='json'))

    # Mock the stream results for the two queries
    mock_query_p1_ref = MagicMock()
    mock_query_p1_ref.stream.return_value = [mock_chat1_doc]
    
    mock_query_p2_ref = MagicMock()
    mock_query_p2_ref.stream.return_value = [mock_chat2_doc]

    # Configure the .where().where()... chain to return these specific query mocks
    # This assumes the `where` calls are distinct enough or we can use side_effect
    def collection_side_effect(collection_name):
        if collection_name == "chats":
            mock_coll_ref = MagicMock()
            # This is tricky because .where("participant1_id").stream and .where("participant2_id").stream
            # need different return values.
            # We'll use a simpler approach: have query() return a list of Chat objects directly for this test.
            # This means the endpoint logic using firestore_ops.db.collection... will not be hit by this test method directly.
            # For robust testing of the exact implementation, the mocking of .db.collection()... needs to be more sophisticated
            # or the endpoint needs to be refactored to use a more abstract method from FirestoreBaseModel.
            #
            # For this test, we'll assume the endpoint's query logic correctly fetches and we mock the combined result.
            # This simplifies the test but doesn't test the direct Firestore query chain as deeply.
            # A more accurate way is to mock the `stream` method of the final query object.
            
            # Let's try to mock the chain as intended by the note.
            # We need to differentiate the call to .where()
            # This requires knowing which .where() is called first or making them distinguishable.
            # The endpoint does:
            # p1_chats_query = firestore_ops.db.collection("chats").where("participant1_id", "==", current_user_data.user_id)
            # p2_chats_query = firestore_ops.db.collection("chats").where("participant2_id", "==", current_user_data.user_id)
            
            # We can use side_effect on .where()
            def where_side_effect(field, op, value):
                q_ref = MagicMock()
                if field == "participant1_id":
                    q_ref.stream.return_value = [mock_chat1_doc]
                elif field == "participant2_id":
                    q_ref.stream.return_value = [mock_chat2_doc]
                else:
                    q_ref.stream.return_value = []
                return q_ref
            
            mock_coll_ref.where.side_effect = where_side_effect
            return mock_coll_ref
        return MagicMock() # Default for other collections

    mock_firestore_ops_messaging.db.collection.side_effect = collection_side_effect
    
    response = client.get("/chats/", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["chat_id"] == str(chat1_p1.chat_id) # Sorted by last_message_timestamp desc
    assert data[1]["chat_id"] == str(chat2_p2.chat_id)

def test_list_my_chats_empty(mock_firestore_ops_messaging, mock_decode_token_messaging, monkeypatch):
    monkeypatch.setattr("app.routers.messaging.get_firestore_ops_instance", lambda: mock_firestore_ops_messaging)
    mock_user = create_mock_user_messaging(MOCK_MESSAGING_TOKEN_USER_ID)
    mock_firestore_ops_messaging.get.return_value = mock_user
    
    # Simulate no chats found for either participant role
    mock_firestore_ops_messaging.db.collection("chats").where().stream.return_value = []
    
    response = client.get("/chats/", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 200
    assert response.json() == []

def test_list_my_chats_auth_error(monkeypatch):
    monkeypatch.setattr("app.routers.messaging.decode_access_token", MagicMock(return_value=None))
    response = client.get("/chats/", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401

# --- Tests for GET /chats/{chat_id}/messages ---

def test_get_messages_for_chat_success(mock_firestore_ops_messaging, mock_decode_token_messaging, monkeypatch):
    monkeypatch.setattr("app.routers.messaging.get_firestore_ops_instance", lambda: mock_firestore_ops_messaging)
    
    user_id_obj = UUID(MOCK_MESSAGING_TOKEN_USER_ID)
    mock_user = create_mock_user_messaging(MOCK_MESSAGING_TOKEN_USER_ID)
    test_chat_id = uuid4()
    mock_chat = create_mock_chat_messaging(chat_id=test_chat_id, participant1_id=user_id_obj) # User is P1
    
    mock_firestore_ops_messaging.get.side_effect = [mock_user, mock_chat]
    
    msg1_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    msg2_time = datetime.now(timezone.utc)
    mock_messages_list = [
        create_mock_message_messaging(chat_id=test_chat_id, timestamp=msg1_time),
        create_mock_message_messaging(chat_id=test_chat_id, timestamp=msg2_time)
    ]
    mock_firestore_ops_messaging.query.return_value = mock_messages_list
    
    response = client.get(f"/chats/{test_chat_id}/messages", headers={"Authorization": "Bearer fake-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["timestamp"] == msg1_time.isoformat().replace("+00:00", "Z") # Check sorting
    assert data[1]["timestamp"] == msg2_time.isoformat().replace("+00:00", "Z")
    
    mock_firestore_ops_messaging.query.assert_called_once_with(
        collection_name="messages", field="chat_id", operator="==", value=test_chat_id, pydantic_model=Message
    )

def test_get_messages_for_chat_unauthorized(mock_firestore_ops_messaging, mock_decode_token_messaging, monkeypatch):
    monkeypatch.setattr("app.routers.messaging.get_firestore_ops_instance", lambda: mock_firestore_ops_messaging)
    mock_user = create_mock_user_messaging(MOCK_MESSAGING_TOKEN_USER_ID) # User is not in chat
    test_chat_id = uuid4()
    mock_chat = create_mock_chat_messaging(chat_id=test_chat_id, participant1_id=uuid4(), participant2_id=uuid4())
    mock_firestore_ops_messaging.get.side_effect = [mock_user, mock_chat]
    
    response = client.get(f"/chats/{test_chat_id}/messages", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to view messages for this chat"

def test_get_messages_for_chat_chat_not_found(mock_firestore_ops_messaging, mock_decode_token_messaging, monkeypatch):
    monkeypatch.setattr("app.routers.messaging.get_firestore_ops_instance", lambda: mock_firestore_ops_messaging)
    mock_user = create_mock_user_messaging(MOCK_MESSAGING_TOKEN_USER_ID)
    mock_firestore_ops_messaging.get.side_effect = [mock_user, None] # Chat not found
    
    response = client.get(f"/chats/{uuid4()}/messages", headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Chat not found"

# --- Tests for POST /chats/{chat_id}/messages (Send Message) ---

def test_send_message_success(mock_firestore_ops_messaging, mock_decode_token_messaging, monkeypatch):
    monkeypatch.setattr("app.routers.messaging.get_firestore_ops_instance", lambda: mock_firestore_ops_messaging)

    sender_id_obj = UUID(MOCK_MESSAGING_TOKEN_USER_ID)
    mock_sender_user = create_mock_user_messaging(MOCK_MESSAGING_TOKEN_USER_ID)
    
    receiver_id_obj = uuid4()
    test_chat_id = uuid4()
    mock_chat = create_mock_chat_messaging(chat_id=test_chat_id, participant1_id=sender_id_obj, participant2_id=receiver_id_obj)

    mock_firestore_ops_messaging.get.side_effect = [mock_sender_user, mock_chat]
    mock_firestore_ops_messaging.save.return_value = str(uuid4()) # Message save
    mock_firestore_ops_messaging.update.return_value = True # Chat timestamp update

    message_data = MessageContent(content="Hello there!")
    response = client.post(f"/chats/{test_chat_id}/messages", json=message_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 201
    data = response.json()
    assert data["content"] == message_data.content
    assert data["sender_id"] == MOCK_MESSAGING_TOKEN_USER_ID
    assert data["receiver_id"] == str(receiver_id_obj)
    assert data["chat_id"] == str(test_chat_id)
    
    mock_firestore_ops_messaging.save.assert_called_once()
    args_save, kwargs_save = mock_firestore_ops_messaging.save.call_args
    assert kwargs_save['collection_name'] == 'messages'
    assert kwargs_save['data_model']['content'] == message_data.content
    
    mock_firestore_ops_messaging.update.assert_called_once()
    args_update, kwargs_update = mock_firestore_ops_messaging.update.call_args
    assert kwargs_update['collection_name'] == 'chats'
    assert kwargs_update['document_id'] == str(test_chat_id)
    assert "last_message_timestamp" in kwargs_update['updates']

def test_send_message_unauthorized_not_participant(mock_firestore_ops_messaging, mock_decode_token_messaging, monkeypatch):
    monkeypatch.setattr("app.routers.messaging.get_firestore_ops_instance", lambda: mock_firestore_ops_messaging)
    mock_sender_user = create_mock_user_messaging(MOCK_MESSAGING_TOKEN_USER_ID) # Not in chat
    test_chat_id = uuid4()
    mock_chat = create_mock_chat_messaging(chat_id=test_chat_id, participant1_id=uuid4(), participant2_id=uuid4())
    mock_firestore_ops_messaging.get.side_effect = [mock_sender_user, mock_chat]

    message_data = MessageContent(content="Intruder message")
    response = client.post(f"/chats/{test_chat_id}/messages", json=message_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to send messages in this chat"

def test_send_message_chat_not_found(mock_firestore_ops_messaging, mock_decode_token_messaging, monkeypatch):
    monkeypatch.setattr("app.routers.messaging.get_firestore_ops_instance", lambda: mock_firestore_ops_messaging)
    mock_sender_user = create_mock_user_messaging(MOCK_MESSAGING_TOKEN_USER_ID)
    mock_firestore_ops_messaging.get.side_effect = [mock_sender_user, None] # Chat not found

    message_data = MessageContent(content="Message to nowhere")
    response = client.post(f"/chats/{uuid4()}/messages", json=message_data.model_dump(mode='json'), headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Chat not found"

def test_send_message_auth_error(monkeypatch):
    monkeypatch.setattr("app.routers.messaging.decode_access_token", MagicMock(return_value=None))
    message_data = MessageContent(content="Auth error message")
    response = client.post(f"/chats/{uuid4()}/messages", json=message_data.model_dump(mode='json'), headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401

from datetime import timedelta # Add timedelta for time manipulation in tests
