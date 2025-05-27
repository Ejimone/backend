import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

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
                # Try to get the existing app
                app = firebase_admin.get_app()
                self._db = firestore.client(app)
                print("Using existing Firebase app")
                return
            except ValueError:
                # App doesn't exist, so we need to initialize it
                pass
            
            # Load project configuration from Firebase.json
            firebase_config_path = os.path.join(os.path.dirname(__file__), 'Firebase.json')
            project_id = None
            
            if os.path.exists(firebase_config_path):
                with open(firebase_config_path, 'r') as f:
                    config = json.load(f)
                    project_id = config.get('projectId')
                    print(f"Found Firebase project ID: {project_id}")
            
            # Try to initialize with service account key if it exists
            service_account_path = os.path.join(os.path.dirname(__file__), 'service-account-key.json')
            
            if os.path.exists(service_account_path):
                # Use service account key file
                cred = credentials.Certificate(service_account_path)
                if project_id:
                    firebase_admin.initialize_app(cred, {'projectId': project_id})
                else:
                    firebase_admin.initialize_app(cred)
                print("Firebase initialized with service account key")
            else:
                # Fallback: Try to use application default credentials
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
                    print("Please set up Firebase service account key or application default credentials")
                    print("See FIREBASE_SETUP.md for detailed instructions")
                    return
            
            self._db = firestore.client()
            print("Firebase Firestore client initialized successfully!")
            
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            print("Make sure you have the correct Firebase credentials set up")
    
    def get_db(self):
        """Get Firestore database client"""
        return self._db

class BaseModel:
    """
    Base model class for all database models
    """
    
    def __init__(self):
        self.firebase_manager = FirebaseManager()
        self.db = self.firebase_manager.get_db()
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary for Firestore"""
        data = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_') and key not in ['firebase_manager', 'db']:
                if isinstance(value, datetime):
                    data[key] = value
                else:
                    data[key] = value
        return data
    
    def save(self, collection_name: str, document_id: Optional[str] = None) -> str:
        """Save model to Firestore"""
        if not self.db:
            print("Database not initialized")
            return None
        
        try:
            self.updated_at = datetime.now()
            data = self.to_dict()
            
            if document_id:
                # Create or update document with specific ID
                doc_ref = self.db.collection(collection_name).document(document_id)
                doc_ref.set(data)
                return document_id
            else:
                # Auto-generate document ID
                doc_ref = self.db.collection(collection_name).add(data)
                return doc_ref[1].id
        except Exception as e:
            print(f"Error saving to Firestore: {e}")
            return None
    
    @classmethod
    def get(cls, collection_name: str, document_id: str):
        """Get document from Firestore by ID"""
        firebase_manager = FirebaseManager()
        db = firebase_manager.get_db()
        
        if not db:
            print("Database not initialized")
            return None
        
        try:
            doc_ref = db.collection(collection_name).document(document_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                print(f"Document {document_id} not found in {collection_name}")
                return None
        except Exception as e:
            print(f"Error getting document from Firestore: {e}")
            return None
    
    @classmethod
    def get_all(cls, collection_name: str, limit: Optional[int] = None):
        """Get all documents from a collection"""
        firebase_manager = FirebaseManager()
        db = firebase_manager.get_db()
        
        if not db:
            print("Database not initialized")
            return []
        
        try:
            collection_ref = db.collection(collection_name)
            if limit:
                docs = collection_ref.limit(limit).stream()
            else:
                docs = collection_ref.stream()
            
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            print(f"Error getting documents from Firestore: {e}")
            return []
    
    @classmethod
    def query(cls, collection_name: str, field: str, operator: str, value: Any):
        """Query documents by field"""
        firebase_manager = FirebaseManager()
        db = firebase_manager.get_db()
        
        if not db:
            print("Database not initialized")
            return []
        
        try:
            collection_ref = db.collection(collection_name)
            query = collection_ref.where(field, operator, value)
            docs = query.stream()
            
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            print(f"Error querying Firestore: {e}")
            return []
    
    def update(self, collection_name: str, document_id: str, updates: Dict[str, Any]):
        """Update specific fields in a document"""
        if not self.db:
            print("Database not initialized")
            return False
        
        try:
            updates['updated_at'] = datetime.now()
            doc_ref = self.db.collection(collection_name).document(document_id)
            doc_ref.update(updates)
            return True
        except Exception as e:
            print(f"Error updating document in Firestore: {e}")
            return False
    
    def delete(self, collection_name: str, document_id: str):
        """Delete a document from Firestore"""
        if not self.db:
            print("Database not initialized")
            return False
        
        try:
            doc_ref = self.db.collection(collection_name).document(document_id)
            doc_ref.delete()
            return True
        except Exception as e:
            print(f"Error deleting document from Firestore: {e}")
            return False

class ClientModel(BaseModel):
    """Client model for Firestore operations"""
    
    def __init__(self, user_id, username, email, full_name="", phone_number="", task_name="", bio=None):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.phone_number = phone_number
        self.role = "client"
        self.task_name = task_name
        self.bio = bio
        self.is_active = True
        self.task_details = {}
        self.budget = None
        self.status = "open"
        self.proposals = []
        self.selected_freelancer = None
        self.feedback = None
        self.payment_details = {}
    
    def save_to_db(self):
        """Save client to Firestore"""
        return self.save('clients', self.user_id)
    
    @classmethod
    def get_by_id(cls, user_id: str):
        """Get client by user ID"""
        return cls.get('clients', user_id)
    
    @classmethod
    def get_all_clients(cls, limit: Optional[int] = None):
        """Get all clients"""
        return cls.get_all('clients', limit)

class FreelancerModel(BaseModel):
    """Freelancer model for Firestore operations"""
    
    def __init__(self, user_id, username, email, full_name="", phone_number="", skills=None, portfolio_url=None, bio=None, hourly_rate=None, average_rating=0.0):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.phone_number = phone_number
        self.role = "freelancer"
        self.is_active = True
        self.skills = skills if skills is not None else []
        self.portfolio_url = portfolio_url
        self.bio = bio
        self.hourly_rate = hourly_rate
        self.average_rating = average_rating
        self.payout_details = {}
    
    def save_to_db(self):
        """Save freelancer to Firestore"""
        return self.save('freelancers', self.user_id)
    
    @classmethod
    def get_by_id(cls, user_id: str):
        """Get freelancer by user ID"""
        return cls.get('freelancers', user_id)
    
    @classmethod
    def get_by_skills(cls, skill: str):
        """Get freelancers by skill"""
        return cls.query('freelancers', 'skills', 'array_contains', skill)

class SellerModel(BaseModel):
    """Seller model for Firestore operations"""
    
    def __init__(self, user_id, username, email, full_name="", phone_number="", business_name="", business_type="", bio=None, products=None):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.phone_number = phone_number
        self.role = "seller"
        self.business_name = business_name
        self.business_type = business_type
        self.bio = bio
        self.is_active = True
        self.products = products if products is not None else []
        self.total_sales = 0.0
        self.average_rating = 0.0
        self.store_url = None
        self.payment_methods = []
        self.shipping_options = []
    
    def save_to_db(self):
        """Save seller to Firestore"""
        return self.save('sellers', self.user_id)
    
    @classmethod
    def get_by_id(cls, user_id: str):
        """Get seller by user ID"""
        return cls.get('sellers', user_id)
    
    @classmethod
    def get_by_business_type(cls, business_type: str):
        """Get sellers by business type"""
        return cls.query('sellers', 'business_type', '==', business_type)

class BuyerModel(BaseModel):
    """Buyer model for Firestore operations"""
    
    def __init__(self, user_id, username, email, full_name="", phone_number="", bio=None, preferred_categories=None):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.phone_number = phone_number
        self.role = "buyer"
        self.bio = bio
        self.is_active = True
        self.preferred_categories = preferred_categories if preferred_categories is not None else []
        self.order_history = []
        self.wishlist = []
        self.shipping_address = {}
        self.payment_details = {}
        self.total_spent = 0.0
        self.loyalty_points = 0
    
    def save_to_db(self):
        """Save buyer to Firestore"""
        return self.save('buyers', self.user_id)
    
    @classmethod
    def get_by_id(cls, user_id: str):
        """Get buyer by user ID"""
        return cls.get('buyers', user_id)
    
    @classmethod
    def get_by_category(cls, category: str):
        """Get buyers interested in a specific category"""
        return cls.query('buyers', 'preferred_categories', 'array_contains', category)

# Example usage and testing
if __name__ == "__main__":
    print("Testing Firebase Models...")
    
    # Test ClientModel
    client = ClientModel(
        user_id="c001",
        username="student123",
        email="student123@example.com",
        full_name="John Smith",
        task_name="Math Assignment",
        bio="Looking for freelancer help"
    )
    
    # Test SellerModel
    seller = SellerModel(
        user_id="s001",
        username="bookstore_owner",
        email="bookstore@example.com",
        full_name="Jane Doe",
        business_name="Jane's Bookstore",
        business_type="books"
    )
    
    # Test BuyerModel
    buyer = BuyerModel(
        user_id="b001",
        username="student_buyer",
        email="buyer@example.com",
        full_name="Alice Johnson",
        preferred_categories=["books", "electronics"]
    )
    
    print("Models created successfully!")
    print("Note: To save to Firestore, you need to set up Firebase credentials.")
    print("1. Download service account key from Firebase Console")
    print("2. Save it as 'service-account-key.json' in the same directory")
    print("3. Or set up GOOGLE_APPLICATION_CREDENTIALS environment variable")
