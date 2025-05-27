"""
Comprehensive test for all models including Firebase integration
"""

from Models import ClientModel, FreelancerModel, SellerModel, BuyerModel
from client import Client
from freelancer import Freelancer
from Seller import Seller
from Buyer import Buyer

def test_basic_classes():
    """Test the basic classes without Firebase"""
    print("=== Testing Basic Classes (No Firebase) ===\n")
    
    # Test Client class
    print("1. Testing Client class:")
    client = Client(
        user_id="c001",
        username="student123",
        email="student123@example.com",
        full_name="John Smith",
        phone_number="123-456-7890",
        task_name="Math Assignment"
    )
    client.update_profile(bio="Looking for a freelancer to help with assignments.")
    print(f"   {client}")
    print(f"   Bio: {client.bio}")
    
    # Test Freelancer class
    print("\n2. Testing Freelancer class:")
    freelancer = Freelancer(
        user_id="f001",
        username="creative_coder",
        email="cc@example.com",
        full_name="Alex Doe",
        skills=["Python", "Web Design", "Graphic Art"]
    )
    freelancer.update_profile(bio="Experienced developer and designer.", hourly_rate=50)
    freelancer.add_skill("Django")
    print(f"   {freelancer}")
    print(f"   Bio: {freelancer.bio}")
    print(f"   Hourly Rate: ${freelancer.hourly_rate}")
    
    # Test Seller class
    print("\n3. Testing Seller class:")
    seller = Seller(
        user_id="s001",
        username="bookstore_owner",
        email="bookstore@example.com",
        full_name="Jane Doe",
        business_name="Jane's Bookstore",
        business_type="books"
    )
    seller.update_profile(bio="Selling quality textbooks and novels for college students.")
    seller.add_product("Mathematics Textbook")
    seller.add_product("Science Fiction Novel")
    seller.add_payment_method("card")
    seller.add_shipping_option("standard")
    print(f"   {seller}")
    print(f"   Products: {seller.products}")
    print(f"   Payment Methods: {seller.payment_methods}")
    
    # Test Buyer class
    print("\n4. Testing Buyer class:")
    buyer = Buyer(
        user_id="b001",
        username="student_buyer",
        email="student@example.com",
        full_name="John Smith",
        preferred_categories=["books", "electronics"]
    )
    buyer.update_profile(bio="College student looking for textbooks and tech gadgets.")
    buyer.add_to_wishlist("math_textbook_123")
    buyer.add_to_wishlist("laptop_456")
    buyer.set_shipping_address({
        "street": "123 College Ave",
        "city": "University Town",
        "state": "CA",
        "zip_code": "12345"
    })
    
    # Place an order
    order = {
        "order_id": "ord_001",
        "items": ["math_textbook_123"],
        "total_amount": 50.0,
        "seller_id": "s001"
    }
    buyer.place_order(order)
    
    print(f"   {buyer}")
    print(f"   Wishlist: {buyer.wishlist}")
    print(f"   Total spent: ${buyer.total_spent}")
    print(f"   Loyalty points: {buyer.loyalty_points}")

def test_firebase_models():
    """Test Firebase-enabled models"""
    print("\n\n=== Testing Firebase Models ===\n")
    
    # Test ClientModel
    print("1. Testing ClientModel:")
    client_model = ClientModel(
        user_id="c002",
        username="student456",
        email="student456@example.com",
        full_name="Jane Smith",
        task_name="Physics Assignment",
        bio="Need help with quantum mechanics"
    )
    print(f"   Created: {client_model.username}")
    print(f"   Data: {client_model.to_dict()}")
    
    # Test SellerModel
    print("\n2. Testing SellerModel:")
    seller_model = SellerModel(
        user_id="s002",
        username="tech_store",
        email="tech@store.com",
        full_name="Tech Store Inc.",
        business_name="Campus Tech Store",
        business_type="electronics"
    )
    print(f"   Created: {seller_model.business_name}")
    print(f"   Data: {seller_model.to_dict()}")
    
    # Test BuyerModel
    print("\n3. Testing BuyerModel:")
    buyer_model = BuyerModel(
        user_id="b002",
        username="tech_buyer",
        email="buyer2@student.edu",
        full_name="Bob Johnson",
        preferred_categories=["electronics", "software"]
    )
    print(f"   Created: {buyer_model.username}")
    print(f"   Data: {buyer_model.to_dict()}")
    
    # Try to save to Firebase
    print("\n4. Attempting to save to Firebase:")
    try:
        client_id = client_model.save_to_db()
        if client_id:
            print(f"   ✓ Client saved with ID: {client_id}")
            
            # Try to retrieve it
            retrieved_client = ClientModel.get_by_id(client_id)
            if retrieved_client:
                print(f"   ✓ Client retrieved: {retrieved_client['username']}")
            else:
                print("   ✗ Failed to retrieve client")
        else:
            print("   ✗ Failed to save client")
            
        seller_id = seller_model.save_to_db()
        if seller_id:
            print(f"   ✓ Seller saved with ID: {seller_id}")
        else:
            print("   ✗ Failed to save seller")
            
        buyer_id = buyer_model.save_to_db()
        if buyer_id:
            print(f"   ✓ Buyer saved with ID: {buyer_id}")
        else:
            print("   ✗ Failed to save buyer")
            
    except Exception as e:
        print(f"   Error: {e}")

def print_firebase_setup_instructions():
    """Print instructions for setting up Firebase"""
    print("\n\n=== Firebase Setup Instructions ===")
    print("Your Firebase.json shows project ID: collegemaster-f522d")
    print("To enable database operations, you need server-side credentials:")
    print()
    print("1. Go to Firebase Console: https://console.firebase.google.com")
    print("2. Select your project: collegemaster-f522d")
    print("3. Click the gear icon (Settings) → Project settings")
    print("4. Go to 'Service accounts' tab")
    print("5. Click 'Generate new private key'")
    print("6. Save the downloaded JSON file as 'service-account-key.json' in this directory")
    print("7. Run this test again to see Firebase operations in action!")
    print()
    print("Note: Never commit the service account key to version control!")
    print("Add 'service-account-key.json' to your .gitignore file.")

def main():
    """Run all tests"""
    print("🔥 College Manager Backend - Complete Model Testing 🔥")
    print("=" * 60)
    
    # Test basic classes
    test_basic_classes()
    
    # Test Firebase models
    test_firebase_models()
    
    # Print setup instructions
    print_firebase_setup_instructions()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("📖 Check FIREBASE_SETUP.md for detailed setup instructions")

if __name__ == "__main__":
    main()
