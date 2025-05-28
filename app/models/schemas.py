from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr
from uuid import UUID, uuid4

class UserBase(BaseModel):
    username: str
    email: EmailStr
    phone_number: Optional[str] = None
    full_name: str
    profile_picture_url: Optional[str] = None
    role: str  # Enum: 'client', 'freelancer', 'admin'

class UserCreate(UserBase):
    password: str

class User(UserBase):
    user_id: UUID = uuid4()
    registration_date: datetime = datetime.now()
    last_login_date: Optional[datetime] = None
    is_active: bool = True

class ClientProfileBase(BaseModel):
    company_name: Optional[str] = None
    payment_method_details: Optional[Dict[str, Any]] = None # Storing payment method details; encryption to be handled

class ClientProfileCreate(ClientProfileBase):
    pass

class ClientProfile(ClientProfileBase):
    user_id: UUID # Foreign Key to User

class FreelancerProfileBase(BaseModel):
    skills: Optional[List[str]] = None
    portfolio_url: Optional[str] = None
    bio: Optional[str] = None
    hourly_rate: Optional[float] = None
    payout_details: Optional[Dict[str, Any]] = None # Storing payout details; encryption to be handled

class FreelancerProfileCreate(FreelancerProfileBase):
    pass

class FreelancerProfile(FreelancerProfileBase):
    user_id: UUID # Foreign Key to User
    average_rating: Optional[float] = None

class ProjectBase(BaseModel):
    title: str
    description: str
    budget: Optional[float] = None
    deadline: Optional[datetime] = None
    tags: Optional[List[str]] = None
    status: str # Enum: 'open', 'in_progress', 'completed', 'cancelled'

class ProjectCreate(ProjectBase):
    client_user_id: UUID # Foreign Key to User (Client)

class Project(ProjectBase):
    project_id: UUID = uuid4()
    client_user_id: UUID # Foreign Key to User (Client)
    freelancer_user_id: Optional[UUID] = None # Foreign Key to User (Freelancer)
    creation_date: datetime = datetime.now()
    last_updated_date: datetime = datetime.now()

class BidBase(BaseModel):
    proposal: str
    amount: float
    estimated_completion_time: Optional[str] = None # e.g., "2 weeks", "1 month"

class BidCreate(BidBase):
    project_id: UUID # Foreign Key to Project
    freelancer_user_id: UUID # Foreign Key to User (Freelancer)

class Bid(BidBase):
    bid_id: UUID = uuid4()
    project_id: UUID # Foreign Key to Project
    freelancer_user_id: UUID # Foreign Key to User (Freelancer)
    bid_date: datetime = datetime.now()
    status: str = "pending" # Enum: 'pending', 'accepted', 'rejected'

class ReviewBase(BaseModel):
    rating: int # Typically 1-5
    comment: Optional[str] = None

class ReviewCreate(ReviewBase):
    project_id: UUID # Foreign Key to Project
    reviewer_user_id: UUID # Foreign Key to User (who is giving the review)
    reviewee_user_id: UUID # Foreign Key to User (who is being reviewed)

class Review(ReviewBase):
    review_id: UUID = uuid4()
    project_id: UUID # Foreign Key to Project
    reviewer_user_id: UUID # Foreign Key to User
    reviewee_user_id: UUID # Foreign Key to User
    review_date: datetime = datetime.now()

class NotificationBase(BaseModel):
    message: str
    read_status: bool = False

class NotificationCreate(NotificationBase):
    user_id: UUID # Foreign Key to User

class Notification(NotificationBase):
    notification_id: UUID = uuid4()
    user_id: UUID # Foreign Key to User
    creation_date: datetime = datetime.now()

class TransactionBase(BaseModel):
    amount: float
    currency: str = "USD" # Default currency
    transaction_type: str # Enum: 'payment', 'payout', 'refund'
    status: str # Enum: 'pending', 'completed', 'failed'

class TransactionCreate(TransactionBase):
    project_id: Optional[UUID] = None # Optional, if related to a project
    payer_user_id: Optional[UUID] = None # Made Optional: Foreign Key to User (or None for system/platform)
    payee_user_id: UUID # Foreign Key to User

class Transaction(TransactionBase):
    transaction_id: UUID = uuid4()
    project_id: Optional[UUID] = None
    payer_user_id: Optional[UUID] = None # Made Optional: Foreign Key to User (or None for system/platform)
    payee_user_id: UUID # Foreign Key to User
    transaction_date: datetime = datetime.now()

class ContractBase(BaseModel):
    project_id: UUID
    client_id: UUID
    freelancer_id: UUID
    terms: str
    agreed_amount: float
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str # Enum: 'active', 'completed', 'terminated', 'disputed'

class ContractCreate(ContractBase):
    pass

class Contract(ContractBase):
    contract_id: UUID = uuid4()
    creation_date: datetime = datetime.now()

class WorkSubmissionBase(BaseModel):
    project_id: UUID
    freelancer_id: UUID
    files: Optional[List[Dict[str, Any]]] = None # Example: {filename, url, size}
    notes: Optional[str] = None

class WorkSubmissionCreate(WorkSubmissionBase):
    pass

class WorkSubmission(WorkSubmissionBase):
    submission_id: UUID = uuid4()
    submission_date: datetime = datetime.now()
    version: Optional[int] = None # for revisions

class MessageBase(BaseModel):
    chat_id: UUID
    sender_id: UUID
    receiver_id: UUID
    content: str

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    message_id: UUID = uuid4()
    timestamp: datetime = datetime.now()
    is_read: bool = False
    ai_suggestions: Optional[Dict[str, Any]] = None

class ChatBase(BaseModel): # Corresponds to Chat or Conversation
    participant1_id: UUID
    participant2_id: UUID
    project_context_id: Optional[UUID] = None

class ChatCreate(ChatBase):
    pass

class Chat(ChatBase):
    chat_id: UUID = uuid4()
    last_message_timestamp: Optional[datetime] = None
