import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel as PydanticBaseModel # Alias Pydantic's BaseModel

class FirebaseManager:
    """
    Firebase Firestore Manager for handling database operations
    """
    _instance = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._db is None:
            self.initialize_firebase()
    
    def initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            try:
                app = firebase_admin.get_app()
                self._db = firestore.client(app)
                print("Using existing Firebase app")
                return
            except ValueError:
                pass # App doesn't exist, so we need to initialize it
            
            # Paths relative to the project root (/app)
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            firebase_config_path = os.path.join(project_root, 'Firebase.json')
            service_account_path = os.path.join(project_root, 'service-account-key.json')
            
            project_id = None
            if os.path.exists(firebase_config_path):
                with open(firebase_config_path, 'r') as f:
                    config = json.load(f)
                    project_id = config.get('projectId')
                    print(f"Found Firebase project ID: {project_id} from {firebase_config_path}")
            
            if os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                if project_id:
                    firebase_admin.initialize_app(cred, {'projectId': project_id})
                else:
                    firebase_admin.initialize_app(cred)
                print(f"Firebase initialized with service account key from {service_account_path}")
            else:
                try:
                    cred = credentials.ApplicationDefault()
                    if project_id:
                        firebase_admin.initialize_app(cred, {'projectId': project_id})
                    else:
                        firebase_admin.initialize_app(cred)
                    print("Firebase initialized with application default credentials")
                except Exception as e:
                    print(f"Warning: Could not initialize Firebase with default credentials: {e}")
                    print("Firebase.json contains client-side config, but we need server-side credentials.")
                    print("Please ensure 'service-account-key.json' is in the project root or GOOGLE_APPLICATION_CREDENTIALS is set.")
                    print("See FIREBASE_SETUP.md for detailed instructions")
                    return
            
            self._db = firestore.client()
            print("Firebase Firestore client initialized successfully!")
            
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            print("Make sure you have the correct Firebase credentials set up in the project root.")
    
    def get_db(self):
        """Get Firestore database client"""
        if self._db is None:
            print("Warning: Firestore DB client accessed before initialization or initialization failed.")
        return self._db

class FirestoreBaseModel: # Renamed from BaseModel to avoid Pydantic conflict
    """
    Base model class for Firestore database operations, adapted for Pydantic.
    """
    
    def __init__(self):
        self.firebase_manager = FirebaseManager()
        self.db = self.firebase_manager.get_db()
    
    def _prepare_data_for_firestore(self, data_model: Any) -> Dict[str, Any]:
        """Converts Pydantic model or dict to Firestore-compatible dict."""
        if isinstance(data_model, PydanticBaseModel):
            data = data_model.model_dump(exclude_unset=True) # Use Pydantic's method
        elif isinstance(data_model, dict):
            data = data_model.copy()
        else:
            # Fallback for other types, or if it's an old BaseModel instance (should be rare)
            if hasattr(data_model, 'to_dict') and callable(data_model.to_dict):
                 data = data_model.to_dict()
            else:
                raise ValueError("Data must be a Pydantic model or a dictionary.")

        # Ensure datetime objects are correctly handled (Firestore client library usually handles this)
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value # Firestore handles datetime objects directly
        return data

    def save(self, collection_name: str, data_model: Any, document_id: Optional[str] = None) -> Optional[str]:
        """Save Pydantic model or dictionary to Firestore"""
        if not self.db:
            print("Database not initialized")
            return None
        
        data = self._prepare_data_for_firestore(data_model)
        
        now = datetime.utcnow() # Use UTC for consistency
        data['updated_at'] = now
        if not document_id or not self.get(collection_name, document_id): # Set created_at only if new or not present
            data.setdefault('created_at', now)
            
        try:
            if document_id:
                doc_ref = self.db.collection(collection_name).document(document_id)
                doc_ref.set(data, merge=True) # Use set with merge=True for creating or updating
                return document_id
            else:
                # Auto-generate document ID
                doc_ref = self.db.collection(collection_name).add(data)
                return doc_ref[1].id # add() returns a tuple (timestamp, DocumentReference)
        except Exception as e:
            print(f"Error saving to Firestore collection '{collection_name}': {e}")
            return None
    
    def get(self, collection_name: str, document_id: str, pydantic_model: Optional[type[PydanticBaseModel]] = None) -> Optional[Any]:
        """Get document from Firestore by ID, optionally parsing into a Pydantic model."""
        if not self.db:
            print("Database not initialized")
            return None
        
        try:
            doc_ref = self.db.collection(collection_name).document(document_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                if pydantic_model:
                    return pydantic_model(**data)
                return data
            else:
                # print(f"Document {document_id} not found in {collection_name}") # Less verbose
                return None
        except Exception as e:
            print(f"Error getting document '{document_id}' from Firestore collection '{collection_name}': {e}")
            return None
    
    def get_all(self, collection_name: str, limit: Optional[int] = None, pydantic_model: Optional[type[PydanticBaseModel]] = None) -> List[Any]:
        """Get all documents from a collection, optionally parsing into Pydantic models."""
        if not self.db:
            print("Database not initialized")
            return []
        
        try:
            collection_ref = self.db.collection(collection_name)
            if limit:
                docs_stream = collection_ref.limit(limit).stream()
            else:
                docs_stream = collection_ref.stream()
            
            results = []
            for doc in docs_stream:
                data = {'id': doc.id, **doc.to_dict()}
                if pydantic_model:
                    results.append(pydantic_model(**data))
                else:
                    results.append(data)
            return results
        except Exception as e:
            print(f"Error getting documents from Firestore collection '{collection_name}': {e}")
            return []
    
    def query(self, collection_name: str, field: str, operator: str, value: Any, pydantic_model: Optional[type[PydanticBaseModel]] = None) -> List[Any]:
        """Query documents by field, optionally parsing into Pydantic models."""
        if not self.db:
            print("Database not initialized")
            return []
        
        try:
            collection_ref = self.db.collection(collection_name)
            query_ref = collection_ref.where(field, operator, value)
            docs_stream = query_ref.stream()
            
            results = []
            for doc in docs_stream:
                data = {'id': doc.id, **doc.to_dict()}
                if pydantic_model:
                    results.append(pydantic_model(**data))
                else:
                    results.append(data)
            return results
        except Exception as e:
            print(f"Error querying Firestore collection '{collection_name}': {e}")
            return []
    
    def update(self, collection_name: str, document_id: str, updates: Dict[str, Any]) -> bool:
        """Update specific fields in a document."""
        if not self.db:
            print("Database not initialized")
            return False
        
        # Ensure updates is a dict
        if not isinstance(updates, dict):
            print("Error: 'updates' must be a dictionary.")
            return False

        try:
            # Automatically set 'updated_at' timestamp
            updates_copy = updates.copy() # Avoid modifying the input dict
            updates_copy['updated_at'] = datetime.utcnow() 
            
            doc_ref = self.db.collection(collection_name).document(document_id)
            doc_ref.update(updates_copy)
            return True
        except Exception as e:
            print(f"Error updating document '{document_id}' in Firestore collection '{collection_name}': {e}")
            return False
    
    def delete(self, collection_name: str, document_id: str) -> bool:
        """Delete a document from Firestore."""
        if not self.db:
            print("Database not initialized")
            return False
        
        try:
            doc_ref = self.db.collection(collection_name).document(document_id)
            doc_ref.delete()
            return True
        except Exception as e:
            print(f"Error deleting document '{document_id}' from Firestore collection '{collection_name}': {e}")
            return False

# Example of how to get a Firestore client instance (can be used in services/routers)
def get_firestore_client():
    return FirebaseManager().get_db()

def get_firestore_ops_instance():
    return FirestoreBaseModel()
