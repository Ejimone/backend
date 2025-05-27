#!/usr/bin/env python3
"""
Firebase Connection Test Script

This script tests the Firebase Firestore connection and performs basic CRUD operations.
Run this after setting up your service account credentials.
"""

from Models import *
import traceback

def test_firebase_connection():
    """Test Firebase connection and basic operations"""
    print("=" * 60)
    print("FIREBASE CONNECTION TEST")
    print("=" * 60)
    
    try:
        # Initialize Firebase Manager
        firebase_manager = FirebaseManager()
        db = firebase_manager.get_db()
        
        if db is None:
            print("❌ Firebase connection failed!")
            print("Please set up your service account credentials:")
            print("1. Download service-account-key.json from Firebase Console")
            print("2. Place it in the backend directory")
            print("3. Run this test again")
            return False
            
        print("✅ Firebase connection successful!")
        
        # Test basic Firestore operations
        print("\n" + "=" * 40)
        print("TESTING BASIC FIRESTORE OPERATIONS")
        print("=" * 40)
        
        # Test collection access
        test_collection = db.collection('test')
        print("✅ Can access Firestore collections")
        
        # Test write operation
        test_doc = {
            'message': 'Hello from Python!',
            'timestamp': datetime.now(),
            'test': True
        }
        
        doc_ref = test_collection.add(test_doc)
        doc_id = doc_ref[1].id
        print(f"✅ Test document created with ID: {doc_id}")
        
        # Test read operation
        doc = test_collection.document(doc_id).get()
        if doc.exists:
            print("✅ Test document read successfully")
            print(f"   Data: {doc.to_dict()}")
        else:
            print("❌ Failed to read test document")
            
        # Test delete operation
        test_collection.document(doc_id).delete()
        print("✅ Test document deleted successfully")
        
        print("\n🎉 All Firebase tests passed!")
        return True
        
    except Exception as e:
        error_message = str(e)
        print(f"❌ Firebase test failed: {e}")
        
        if "SERVICE_DISABLED" in error_message or "firestore.googleapis.com" in error_message:
            print("\n🔧 FIRESTORE API NOT ENABLED")
            print("=" * 50)
            print("The Firestore API needs to be enabled for your project.")
            print("\nQuick fix:")
            print(f"1. Click this link: https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=collegemaster-f522d")
            print("2. Click 'Enable API'")
            print("3. Set up Firestore database in Firebase Console")
            print("4. Run this test again")
            print("\nDetailed instructions: See FIRESTORE_SETUP.md")
        elif "database (default) does not exist" in error_message or "404" in error_message:
            print("\n🔧 FIRESTORE DATABASE NOT CREATED")
            print("=" * 50)
            print("The Firestore database needs to be created for your project.")
            print("\nQuick fix:")
            print("1. Go to: https://console.firebase.google.com/")
            print("2. Select project 'collegemaster-f522d'")
            print("3. Click 'Firestore Database' in left sidebar")
            print("4. Click 'Create database'")
            print("5. Choose 'Start in test mode' for development")
            print("6. Select a location and click 'Done'")
            print("7. Run this test again")
            print("\n✅ Your Firebase credentials are working correctly!")
        else:
            print("\nError details:")
            traceback.print_exc()
        return False

def test_model_operations():
    """Test model CRUD operations"""
    print("\n" + "=" * 40)
    print("TESTING MODEL OPERATIONS")
    print("=" * 40)
    
    try:        # Test Client model
        client = ClientModel(
            user_id="test_client_123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            phone_number="1234567890",
            task_name="Test Task",
            bio="Test bio"
        )
          # Save client
        client_id = client.save_to_db()
        if client_id:
            print(f"✅ Client saved with ID: {client_id}")
        else:
            print("❌ Failed to save client")
            return False
              # Retrieve client
        retrieved_client_data = ClientModel.get_by_id("test_client_123")
        if retrieved_client_data:
            print("✅ Client retrieved successfully")
            print(f"   Name: {retrieved_client_data.get('full_name', 'N/A')}")
            print(f"   Email: {retrieved_client_data.get('email', 'N/A')}")
        else:
            print("❌ Failed to retrieve client")
            
        # Update client
        if client.update('clients', 'test_client_123', {'bio': 'Updated bio'}):
            print("✅ Client updated successfully")
        else:
            print("❌ Failed to update client")
              # Test Seller model
        seller = SellerModel(
            user_id="test_seller_456",
            username="testseller",
            email="seller@example.com",
            full_name="Test Seller",
            phone_number="9876543210",
            business_name="Test Business",
            business_type="E-commerce",
            bio="Seller bio",
            products=["Product 1", "Product 2"]
        )
        
        seller_id = seller.save_to_db()
        if seller_id:
            print(f"✅ Seller saved with ID: {seller_id}")
        else:
            print("❌ Failed to save seller")
            
        # Test Buyer model
        buyer = BuyerModel(
            user_id="test_buyer_789",
            username="testbuyer",
            email="buyer@example.com",
            full_name="Test Buyer",
            phone_number="5555555555",
            bio="Buyer bio",
            preferred_categories=["Electronics", "Books"]
        )
        
        buyer_id = buyer.save_to_db()
        if buyer_id:
            print(f"✅ Buyer saved with ID: {buyer_id}")
        else:
            print("❌ Failed to save buyer")
              # Clean up test data
        client.delete('clients', 'test_client_123')
        seller.delete('sellers', 'test_seller_456')
        buyer.delete('buyers', 'test_buyer_789')
        print("✅ Test data cleaned up")
        
        print("\n🎉 All model tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        print("\nError details:")
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("Firebase and Model Testing Suite")
    print("Project ID: collegemaster-f522d")
    print()
    
    # Test Firebase connection
    firebase_ok = test_firebase_connection()
    
    if firebase_ok:
        # Test model operations
        test_model_operations()
    else:
        print("\n⚠️  Skipping model tests due to Firebase connection issues")
        print("\n🔧 TO FIX FIRESTORE SETUP:")
        print("1. Go to Firebase Console: https://console.firebase.google.com/")
        print("2. Select project 'collegemaster-f522d'")
        print("3. Click 'Firestore Database' in left sidebar") 
        print("4. Click 'Create database'")
        print("5. Choose 'Start in test mode' for development")
        print("6. Select a location and click 'Done'")
        print("7. Run this test again")
        print("\n📋 See FIRESTORE_SETUP.md for detailed instructions")

if __name__ == "__main__":
    main()
