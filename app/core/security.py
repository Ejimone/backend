def get_password_hash(password: str) -> str:
    """
    Placeholder password hashing function.
    In a real application, use a strong hashing algorithm like bcrypt or Argon2.
    """
    return f"hashed_{password}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Placeholder password verification function.
    Compares plain_password with the placeholder hashed_password.
    """
    return f"hashed_{plain_password}" == hashed_password

def create_access_token(data: dict) -> str:
    """
    Placeholder for creating an access token.
    """
    return f"fake-jwt-token-for-{data.get('sub')}"

def decode_access_token(token: str) -> str | None:
    """
    Placeholder for decoding an access token.
    Returns the subject (e.g., username or user_id) if valid, else None.
    """
    if token.startswith("fake-jwt-token-for-"):
        return token.replace("fake-jwt-token-for-", "")
    return None

from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str
