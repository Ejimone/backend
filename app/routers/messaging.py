from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import BaseModel # For ChatInitiateRequest

from app.models.schemas import Chat, ChatCreate, Message, MessageCreate, User
from app.db.firebase_ops import get_firestore_ops_instance, FirestoreBaseModel
from app.routers.auth import oauth2_scheme # For dependency
from app.core.security import decode_access_token # For decoding token

router = APIRouter(prefix="/chats", tags=["Messaging"])

class ChatInitiateRequest(BaseModel):
    participant2_id: UUID
    project_context_id: Optional[UUID] = None

class MessageContent(BaseModel):
    content: str

@router.post("/", response_model=Chat, status_code=status.HTTP_201_CREATED)
async def start_new_chat(
    chat_request: ChatInitiateRequest,
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

    participant1_data = firestore_ops.get(collection_name="users", document_id=user_id_from_token, pydantic_model=User)
    if not participant1_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user (Participant 1) not found")

    if participant1_data.user_id == chat_request.participant2_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot start a chat with yourself.")

    participant2_data = firestore_ops.get(collection_name="users", document_id=str(chat_request.participant2_id), pydantic_model=User)
    if not participant2_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant 2 not found.")

    # Prevent Duplicate Chats
    # Query 1: P1 = current user, P2 = requested user
    query_params_1 = [
        ("participant1_id", "==", participant1_data.user_id),
        ("participant2_id", "==", chat_request.participant2_id)
    ]
    if chat_request.project_context_id:
        query_params_1.append(("project_context_id", "==", chat_request.project_context_id))
    
    # Firestore doesn't directly support OR queries on different fields in a way that's easy for this.
    # We'll do two queries and check.
    # A more robust way would be to create a compound key for participants like sorted(p1_id, p2_id)
    # and query on that, but that's a larger schema change.

    existing_chats_q1 = firestore_ops.db.collection("chats")
    for field, op, value in query_params_1:
        existing_chats_q1 = existing_chats_q1.where(field, op, value)
    
    docs_q1 = list(existing_chats_q1.stream())
    if docs_q1:
        return Chat(**docs_q1[0].to_dict())

    # Query 2: P1 = requested user, P2 = current user
    query_params_2 = [
        ("participant1_id", "==", chat_request.participant2_id),
        ("participant2_id", "==", participant1_data.user_id)
    ]
    if chat_request.project_context_id:
        query_params_2.append(("project_context_id", "==", chat_request.project_context_id))

    existing_chats_q2 = firestore_ops.db.collection("chats")
    for field, op, value in query_params_2:
        existing_chats_q2 = existing_chats_q2.where(field, op, value)
        
    docs_q2 = list(existing_chats_q2.stream())
    if docs_q2:
        return Chat(**docs_q2[0].to_dict())


    chat_id = uuid4()
    chat_to_save = Chat(
        chat_id=chat_id,
        participant1_id=participant1_data.user_id,
        participant2_id=chat_request.participant2_id,
        project_context_id=chat_request.project_context_id,
        # last_message_timestamp is Optional and defaults to None
    )

    saved_chat_doc_id = firestore_ops.save(
        collection_name="chats",
        data_model=chat_to_save.model_dump(),
        document_id=str(chat_id)
    )

    if not saved_chat_doc_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create chat.")
        
    return chat_to_save

@router.get("/", response_model=List[Chat])
async def list_my_chats(token: str = Depends(oauth2_scheme)):
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user not found")

    # Query 1: Chats where the user is participant1_id
    p1_chats_query = firestore_ops.db.collection("chats").where("participant1_id", "==", current_user_data.user_id)
    p1_chats_docs = list(p1_chats_query.stream())
    
    # Query 2: Chats where the user is participant2_id
    p2_chats_query = firestore_ops.db.collection("chats").where("participant2_id", "==", current_user_data.user_id)
    p2_chats_docs = list(p2_chats_query.stream())

    # Combine and de-duplicate results
    combined_chats: Dict[UUID, Chat] = {}
    
    for doc in p1_chats_docs:
        chat_data = doc.to_dict()
        chat_obj = Chat(**chat_data)
        combined_chats[chat_obj.chat_id] = chat_obj
        
    for doc in p2_chats_docs:
        chat_data = doc.to_dict()
        chat_obj = Chat(**chat_data)
        combined_chats[chat_obj.chat_id] = chat_obj # Overwrites if duplicate, which is fine

    all_user_chats = list(combined_chats.values())

    # Sort by last_message_timestamp (descending, None values last)
    all_user_chats.sort(key=lambda chat: (chat.last_message_timestamp is None, chat.last_message_timestamp), reverse=True)

    return all_user_chats

@router.get("/{chat_id}/messages", response_model=List[Message])
async def get_messages_for_chat(
    chat_id: UUID,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user not found")

    target_chat = firestore_ops.get(collection_name="chats", document_id=str(chat_id), pydantic_model=Chat)
    if not target_chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    # Authorization
    if not (current_user_data.user_id == target_chat.participant1_id or \
            current_user_data.user_id == target_chat.participant2_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view messages for this chat")

    chat_messages = firestore_ops.query(
        collection_name="messages",
        field="chat_id",
        operator="==",
        value=chat_id,
        pydantic_model=Message
    )
    
    # Sort messages by timestamp (ascending)
    if chat_messages:
        chat_messages.sort(key=lambda msg: msg.timestamp)

    return chat_messages

@router.post("/{chat_id}/messages", response_model=Message, status_code=status.HTTP_201_CREATED)
async def send_message_in_chat(
    chat_id: UUID,
    message_content: MessageContent, # Using the new MessageContent model for request body
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

    sender_data = firestore_ops.get(collection_name="users", document_id=user_id_from_token, pydantic_model=User)
    if not sender_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user (Sender) not found")

    target_chat = firestore_ops.get(collection_name="chats", document_id=str(chat_id), pydantic_model=Chat)
    if not target_chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    # Authorization: Ensure sender is a participant of the chat
    if not (sender_data.user_id == target_chat.participant1_id or \
            sender_data.user_id == target_chat.participant2_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to send messages in this chat")

    # Determine receiver_id
    receiver_id = None
    if sender_data.user_id == target_chat.participant1_id:
        receiver_id = target_chat.participant2_id
    else:
        receiver_id = target_chat.participant1_id
    
    if not receiver_id: # Should not happen if chat participants are valid UUIDs
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not determine message receiver.")


    message_id = uuid4()
    now = datetime.utcnow()
    
    # Create Message Pydantic object
    message_to_save = Message(
        message_id=message_id,
        chat_id=chat_id,
        sender_id=sender_data.user_id,
        receiver_id=receiver_id,
        content=message_content.content,
        timestamp=now, # Explicitly set for consistency
        is_read=False, # Default
        ai_suggestions=None # Default
    )

    saved_message_doc_id = firestore_ops.save(
        collection_name="messages",
        data_model=message_to_save.model_dump(),
        document_id=str(message_id)
    )

    if not saved_message_doc_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not send message.")

    # Update Chat's last_message_timestamp
    chat_update_success = firestore_ops.update(
        collection_name="chats",
        document_id=str(chat_id),
        updates={"last_message_timestamp": now}
    )
    if not chat_update_success:
        # Log this error, but the message was already saved.
        print(f"Warning: Message {message_id} sent, but failed to update chat {chat_id} last_message_timestamp.")
        
    return message_to_save
