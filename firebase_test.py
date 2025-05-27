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
    
    try:
        # Test Client model
        client = ClientModel(
            name="Test User",
            email="test@example.com",
            phone="1234567890",
            bio="Test bio"
        )
        
        # Save client
        client_id = client.save()
        if client_id:
            print(f"✅ Client saved with ID: {client_id}")
        else:
            print("❌ Failed to save client")
            return False
            
        # Retrieve client
        retrieved_client = ClientModel.get(client_id)
        if retrieved_client:
            print("✅ Client retrieved successfully")
            print(f"   Name: {retrieved_client.name}")
            print(f"   Email: {retrieved_client.email}")
        else:
            print("❌ Failed to retrieve client")
            
        # Update client
        retrieved_client.bio = "Updated bio"
        if retrieved_client.update():
            print("✅ Client updated successfully")
        else:
            print("❌ Failed to update client")
            
        # Test Seller model
        seller = SellerModel(
            name="Test Seller",
            email="seller@example.com",
            phone="9876543210",
            business_name="Test Business",
            business_type="E-commerce",
            products=["Product 1", "Product 2"],
            payment_methods=["Credit Card", "PayPal"]
        )
        
        seller_id = seller.save()
        if seller_id:
            print(f"✅ Seller saved with ID: {seller_id}")
        else:
            print("❌ Failed to save seller")
            
        # Test Buyer model
        buyer = BuyerModel(
            name="Test Buyer",
            email="buyer@example.com",
            phone="5555555555",
            preferred_categories=["Electronics", "Books"],
            wishlist=["Item 1", "Item 2"],
            loyalty_points=100
        )
        
        buyer_id = buyer.save()
        if buyer_id:
            print(f"✅ Buyer saved with ID: {buyer_id}")
        else:
            print("❌ Failed to save buyer")
            
        # Clean up test data
        ClientModel.delete(client_id)
        SellerModel.delete(seller_id)
        BuyerModel.delete(buyer_id)
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
        print("1. Enable Firestore API: https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=collegemaster-f522d")
        print("2. Go to Firebase Console: https://console.firebase.google.com/")
        print("3. Select project 'collegemaster-f522d'")
        print("4. Click 'Firestore Database' in left sidebar") 
        print("5. Click 'Create database'")
        print("6. Choose 'Start in test mode' for development")
        print("7. Select a location and click 'Done'")
        print("8. Run this test again")
        print("\n📋 See FIRESTORE_SETUP.md for detailed instructions")

if __name__ == "__main__":
    main()
