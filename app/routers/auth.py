from fastapi import APIRouter, HTTPException
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from uuid import uuid4
from datetime import datetime

from app.models.schemas import UserCreate, User
from app.db.firebase_ops import get_firestore_ops_instance, FirestoreBaseModel
from app.core.security import get_password_hash, verify_password, create_access_token, Token, decode_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@router.post("/register", response_model=User)
async def register_user(user_in: UserCreate):
    firestore_ops: FirestoreBaseModel = get_firestore_ops_instance()

    # Check if user with the same email exists
    existing_user_by_email = firestore_ops.query(collection_name="users", field="email", operator="==", value=user_in.email)
    if existing_user_by_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check if user with the same username exists
    existing_user_by_username = firestore_ops.query(collection_name="users", field="username", operator="==", value=user_in.username)
    if existing_user_by_username:
        raise HTTPException(status_code=400, detail="Username already taken")

    hashed_password = get_password_hash(user_in.password)
    
    user_id = uuid4()
    
    # Create a dictionary for the user data to be stored
    user_data_to_store = user_in.model_dump()
    user_data_to_store["hashed_password"] = hashed_password
    del user_data_to_store["password"] # Remove plain password

    # Create User object for Firestore (which includes default values for user_id, registration_date, is_active)
    # The User schema is also our response model.
    # We will use its structure but ensure the user_id is the one we generated for the document_id
    # And that other default fields are correctly set.
    
    user_for_response = User(
        user_id=user_id, 
        **user_in.model_dump(exclude={"password"}) # Exclude password from the input model
    )
    
    # The data to save should align with the User model, but with hashed_password
    # and other fields from UserCreate.
    # FirestoreBaseModel's save method will add created_at and updated_at
    user_record_to_save = user_for_response.model_dump()
    user_record_to_save["hashed_password"] = hashed_password # Add hashed_password to the record to be saved

    document_id = str(user_id)
    saved_user_id = firestore_ops.save(collection_name="users", data_model=user_record_to_save, document_id=document_id)

    if not saved_user_id:
        raise HTTPException(status_code=500, detail="Could not create user")

    # Return the User model object, which doesn't include 'hashed_password' field by default
    return user_for_response

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    firestore_ops: FirestoreBaseModel = get_firestore_ops_instance()

    # Query user by username
    # Note: Firestore query operators for "==" are exact matches.
    # We expect username to be unique, so query should return 0 or 1 result.
    users_found = firestore_ops.query(collection_name="users", field="username", operator="==", value=form_data.username)

    if not users_found:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Assuming username is unique, take the first result.
    user_data = users_found[0] 
    
    # The 'id' field in user_data is the document_id (which is user_id as a string)
    user_id_from_db = user_data.get("id") 
    # The `user_id` field within the document is the UUID type, if stored that way.
    # For consistency, we should rely on the 'username' or the document 'id' for fetching.

    if not user_data.get("hashed_password"):
        # This case should ideally not happen if registration is done correctly.
        raise HTTPException(
            status_code=500,
            detail="User account improperly configured.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user_data.get("hashed_password")):
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last_login_date
    if user_id_from_db: # Ensure we have the document ID to update
        firestore_ops.update(
            collection_name="users",
            document_id=user_id_from_db,
            updates={"last_login_date": datetime.utcnow()}
        )
    else:
        # Log this issue, as it implies data inconsistency or query problem
        print(f"Warning: Could not update last_login_date for user {form_data.username} due to missing document ID.")


    # Use user_id (document ID) for the token subject for better uniqueness
    access_token = create_access_token(data={"sub": user_id_from_db})
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def read_users_me(token: str = Depends(oauth2_scheme)):
    firestore_ops: FirestoreBaseModel = get_firestore_ops_instance()
    
    user_id_from_token = decode_access_token(token)
    if not user_id_from_token:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from Firestore by user_id (which is the document ID)
    # The 'get' method of FirestoreBaseModel can parse the result into a Pydantic model.
    # We need to ensure the User model can be initialized from the Firestore data,
    # especially if 'id' is expected as 'user_id'.
    
    # The User Pydantic model expects 'user_id' as a UUID.
    # The document ID from Firestore is a string.
    # The `get` method in `FirestoreBaseModel` returns a dict by default.
    # We can pass the `User` model to `pydantic_model` argument.
    
    user_data = firestore_ops.get(collection_name="users", document_id=user_id_from_token, pydantic_model=User)

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # user_data is already an instance of User if pydantic_model=User was used and successful
    return user_data

@router.post("/logout")
async def logout():
    # For a stateless JWT-based auth, logout is typically handled client-side by discarding the token.
    # This endpoint is a placeholder and doesn't perform server-side token invalidation.
    # If using a token blocklist or server-side sessions, this is where you'd add that logic.
    return {"message": "Logout successful. Please discard your token."}
