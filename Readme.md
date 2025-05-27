1.1. User _ user_id (Primary Key, UUID) _ username (String, Unique) _ email (String, Unique) _ password_hash (String) _ phone_number (String, Optional) _ role (Enum: 'client', 'freelancer', 'admin') _ full_name (String) _ profile_picture_url (String, Optional) _ registration_date (Timestamp) _ last_login_date (Timestamp) \* is_active (Boolean, default: true)

1.2. ClientProfile (Extends User or 1:1 with User where role='client') _ user_id (Foreign Key to User, Primary Key) _ company_name (String, Optional) \* payment_method_details (JSON, encrypted)

1.3. FreelancerProfile (Extends User or 1:1 with User where role='freelancer') _ user_id (Foreign Key to User, Primary Key) _ skills (Array of Strings or JSON) _ portfolio_url (String, Optional) _ bio (Text) _ hourly_rate (Decimal, Optional) _ payout_details (JSON, encrypted) \* average_rating (Float, calculated)

1.4. Project (or Assignment) _ project_id (Primary Key, UUID) _ client_id (Foreign Key to User - client role) _ title (String) _ description (Text) _ budget_min (Decimal, Optional) _ budget_max (Decimal, Optional) _ deadline (Timestamp, Optional) _ status (Enum: 'open', 'in_progress', 'awaiting_review', 'completed', 'cancelled', 'disputed') _ creation_date (Timestamp) _ assigned_freelancer_id (Foreign Key to User - freelancer role, Nullable) _ category (String, Optional) _ required_skills (Array of Strings or JSON)

1.5. Bid (or Proposal) _ bid_id (Primary Key, UUID) _ project_id (Foreign Key to Project) _ freelancer_id (Foreign Key to User - freelancer role) _ proposal_text (Text) _ bid_amount (Decimal) _ estimated_delivery_time (String, e.g., "7 days") _ submission_date (Timestamp) _ status (Enum: 'submitted', 'accepted', 'rejected', 'withdrawn')

1.6. Contract (or WorkAgreement) _ contract_id (Primary Key, UUID) _ project_id (Foreign Key to Project) _ client_id (Foreign Key to User - client role) _ freelancer_id (Foreign Key to User - freelancer role) _ terms (Text, could include scope, payment terms, IP rights) _ agreed_amount (Decimal) _ start_date (Timestamp) _ end_date (Timestamp, expected) _ status (Enum: 'active', 'completed', 'terminated', 'disputed') _ creation_date (Timestamp)

1.7. WorkSubmission _ submission_id (Primary Key, UUID) _ project_id (Foreign Key to Project) _ freelancer_id (Foreign Key to User - freelancer role) _ submission_date (Timestamp) _ files (Array of JSON: {filename, url, size}) _ notes (Text) \* version (Integer, for revisions)

1.8. PaymentTransaction _ transaction_id (Primary Key, UUID) _ project_id (Foreign Key to Project, Nullable if other type of payment) _ payer_id (Foreign Key to User - client) _ payee_id (Foreign Key to User - freelancer) _ amount (Decimal) _ currency (String, e.g., "USD") _ payment_gateway_txn_id (String, from payment provider) _ status (Enum: 'pending', 'successful', 'failed', 'refunded') _ transaction_date (Timestamp) _ type (Enum: 'project_payment', 'platform_fee', 'refund', 'withdrawal') \* description (String, e.g., "Payment for Project X", "Platform fee for Project X")

1.9. Message _ message_id (Primary Key, UUID) _ chat_id (Foreign Key to Chat/Conversation) _ sender_id (Foreign Key to User) _ receiver_id (Foreign Key to User) _ content (Text) _ timestamp (Timestamp) _ is_read (Boolean, default: false) _ ai_suggestions (JSON, Optional, for LLM-generated replies)

1.10. Chat (or Conversation) _ chat_id (Primary Key, UUID) _ participant1_id (Foreign Key to User) _ participant2_id (Foreign Key to User) _ last_message_timestamp (Timestamp) \* project_context_id (Foreign Key to Project, Optional)

1.11. Review _ review_id (Primary Key, UUID) _ project_id (Foreign Key to Project) _ reviewer_id (Foreign Key to User) _ reviewee_id (Foreign Key to User) _ rating (Integer, 1-5) _ comment (Text) \* review_date (Timestamp)

1.12. Notification _ notification_id (Primary Key, UUID) _ user_id (Foreign Key to User - recipient) _ type (Enum: 'new_message', 'project_update', 'bid_received', 'payment_processed', etc.) _ content (Text) _ link (String, URL to relevant page) _ is_read (Boolean, default: false) \* creation_date (Timestamp)

1.13. Hostel (Potential Feature) _ hostel_id (Primary Key, UUID) _ name (String) _ address (String) _ description (Text) \* amenities (Array of Strings)

1.14. HostelRoom (Potential Feature) _ room_id (Primary Key, UUID) _ hostel_id (Foreign Key to Hostel) _ room_number (String) _ type (String, e.g., "single", "double") _ price_per_night (Decimal) _ is_available (Boolean)

1.15. HostelBooking (Potential Feature) _ booking_id (Primary Key, UUID) _ room_id (Foreign Key to HostelRoom) _ user_id (Foreign Key to User) _ check_in_date (Date) _ check_out_date (Date) _ total_price (Decimal) \* status (Enum: 'confirmed', 'pending', 'cancelled')

1.16. LLMInteractionLog (For tracking and improving AI features) _ log_id (Primary Key, UUID) _ user_id (Foreign Key to User, Optional) _ feature_area (String, e.g., "messaging_suggestion", "project_matching") _ prompt (Text) _ response (Text) _ timestamp (Timestamp) \* user_feedback (Integer, Optional, e.g., rating of suggestion)

2. Key API Endpoints (RESTful, Conceptual)
   Authentication (/auth)

POST /auth/register (client or freelancer)
POST /auth/login
POST /auth/logout
GET /auth/me (get current user details)
Users (users)

GET /users/{userId} (get public profile)
PUT /users/me/profile (update own profile - client or freelancer specific fields)
Projects (/projects)

POST /projects (Client: create new project)
GET /projects (List all open projects, with filters for skills, budget, etc.)
GET /projects/{projectId} (Get project details)
PUT /projects/{projectId} (Client: update own project)
DELETE /projects/{projectId} (Client: cancel own project)
GET /users/me/projects (Client: list their projects; Freelancer: list their assigned/bid-on projects)
Bids (/projects/{projectId}/bids)

POST /projects/{projectId}/bids (Freelancer: submit a bid)
GET /projects/{projectId}/bids (Client: view bids for their project)
GET /bids/{bidId} (Freelancer: view their bid; Client: view specific bid)
PUT /bids/{bidId} (Freelancer: update/withdraw their bid)
POST /projects/{projectId}/bids/{bidId}/accept (Client: accept a bid, triggers contract creation)
Contracts (/contracts)

GET /contracts (List contracts for the current user)
GET /contracts/{contractId} (Get contract details)
PUT /contracts/{contractId}/status (e.g., mark as complete, dispute)
Work Submissions (/projects/{projectId}/submissions)

POST /projects/{projectId}/submissions (Freelancer: submit work)
GET /projects/{projectId}/submissions (Client/Freelancer: view submissions)
POST /projects/{projectId}/submissions/{submissionId}/approve (Client: approve work)
Payments (/payments)

POST /payments/checkout (Client: initiate payment for a project/milestone)
GET /payments/history (User: view their transaction history)
POST /payments/withdraw (Freelancer: request withdrawal of funds)
Messaging (/chats)

POST /chats (Start a new chat, e.g., client with freelancer about a project)
GET /chats (List user's chats)
GET /chats/{chatId}/messages (Get messages for a chat)
POST /chats/{chatId}/messages (Send a message, potentially with LLM assist)
GET /chats/{chatId}/messages/ai-suggestions (LLM: get message suggestions)
Reviews (/reviews)

POST /reviews (Submit a review for a completed project)
GET /users/{userId}/reviews (Get reviews for a user)
GET /projects/{projectId}/reviews (Get reviews for a project)
Hostel (Potential Feature - /hostels)

GET /hostels (List available hostels)
GET /hostels/{hostelId}/rooms (List rooms in a hostel)
POST /hostels/rooms/{roomId}/book (Book a room)
GET /users/me/bookings (View my hostel bookings)
LLM Services (Internal or specific endpoints, e.g., /llm)

POST /llm/generate-text (Generic text generation)
POST /llm/analyze-text (Sentiment, keywords, etc.)
(More specific endpoints for features like smart reply, matching, etc.) 3. Backend Process Flowcharts (Descriptive)
3.1. User Registration & Profile Setup

Client/Freelancer Initiates Registration: User selects role (Client/Freelancer), provides email, username, password, phone.
Backend Validation: Checks for unique email/username, password strength.
User Creation: Creates User record.
Profile Creation: Creates corresponding ClientProfile or FreelancerProfile.
Confirmation: Sends verification email (optional).
Login: User logs in.
Profile Completion: User is prompted to complete their profile (e.g., skills for freelancer, company for client).
3.2. Client Posts a New Project

Client Authenticated: Client logs in.
Navigate to "Post Project": Client fills out project form (title, description, budget, skills, deadline).
Backend Receives Request: Validates input data.
Project Creation: Creates a new Project record, status 'open', linked to client_id.
Notification (Optional): Notifies freelancers with matching skills (if implemented).
Confirmation: Project is listed as open.
3.3. Freelancer Bids on a Project

Freelancer Authenticated: Freelancer logs in.
Browse/Search Projects: Freelancer finds a suitable project.
Submit Bid: Freelancer fills out bid form (proposal text, bid amount, estimated time).
Backend Receives Request: Validates input.
Bid Creation: Creates a Bid record, linked to project_id and freelancer_id.
Notification: Notifies the Client about the new bid.
Confirmation: Bid is listed under the project for the Client and in the Freelancer's bid history.
3.4. Client Hires a Freelancer

Client Authenticated: Client reviews bids on their project.
Selects Bid: Client chooses a bid and clicks "Accept" or "Hire".
Backend Processes Hiring: a. Updates Bid status to 'accepted' for the chosen bid, 'rejected' for others. b. Updates Project status to 'in_progress' and sets assigned_freelancer_id. c. Creates a Contract record with terms (can be templated or custom).
Notifications: a. Notifies the hired Freelancer. b. Notifies other bidders about the decision.
Confirmation: Project moves to "in progress" state.
3.5. Work Submission, Review, and Payment

Freelancer Submits Work: Freelancer uploads files and notes for the project via WorkSubmission.
Notification: Client is notified of the submission.
Client Reviews Work: Client examines the submitted work.
If Revision Needed: Client requests revision, provides feedback. Freelancer submits a new version. (Loop back to step 1 for new submission).
If Approved: Client approves the work.
Payment Initiation (Client): a. Client is prompted to make payment (if not pre-funded/escrowed). b. Backend interacts with payment gateway to process PaymentTransaction from Client.
Funds Allocation (Backend): a. Upon successful payment from Client, backend records the transaction. b. Calculates platform fee. c. Credits Freelancer's account balance (minus fee). d. Creates PaymentTransaction records for freelancer payout and platform fee.
Project Completion: a. Updates Project status to 'completed'. b. Updates Contract status to 'completed'.
Notifications: Both parties notified of project completion and payment.
Review Prompt: Users prompted to leave reviews.
3.6. Messaging with AI Assistance (LLM)

User A Initiates/Sends Message: User A types a message to User B in a chat.
Frontend (Optional): As User A types, frontend might query an LLM endpoint for predictive text or smart reply suggestions.
Backend Receives Message: a. Stores the Message in the database, linked to the Chat. b. (Optional Server-Side LLM) If AI features are server-driven (e.g., translation, summarization of past messages for context): i. Message content and/or chat history sent to LLM service. ii. LLM service returns processed data (e.g., translation, suggested replies for User B).
Real-time Delivery: Message (and any AI enhancements) pushed to User B via WebSockets or similar.
Notification: User B receives a notification for the new message.
3.7. LLM for Project-Freelancer Matching (Conceptual)

New Project Posted: When a client posts a project with specific requirements (description, skills).
LLM Analysis (Project): Backend sends project details to an LLM service. LLM extracts key skills, project type, complexity.
LLM Analysis (Freelancers): LLM service has access to (or is periodically fed) freelancer profiles (skills, past projects, ratings).
Matching Algorithm: LLM (or a system using LLM embeddings) compares project requirements with freelancer profiles to find best matches.
Suggestion/Notification:
System can suggest top matching freelancers to the client.
System can notify relevant freelancers about the new project.
3.8. "Assignment Legal" & "Work Legal" Flow Integration

Assignment Legal (Pre-Work):
During "Client Hires a Freelancer" (Flow 3.4), the creation of the Contract entity embodies the "Assignment Legal" aspect.
Terms within the Contract (scope, deliverables, IP, payment schedule) are agreed upon.
This might involve digital signatures or acceptance tracking.
Work Legal (Post-Work/Payment):
During "Work Submission, Review, and Payment" (Flow 3.5), the PaymentTransaction records serve as proof of payment ("Amount Paid" by Client, "Amount Earned" by Freelancer).
The WorkSubmission records serve as proof of work delivered.
The project_id (or a specific work_id if granular) links these records.
Dispute resolution mechanisms (if any) would also fall under this, potentially involving admin intervention and review of contract/submissions/communication.
