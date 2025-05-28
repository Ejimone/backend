"""
Example script demonstrating how to use the Firebase Models
"""

from Models import ClientModel, FreelancerModel, SellerModel, BuyerModel

def main():
    print("=== Firebase Models Example ===\n")
    
    # Create a Client
    print("1. Creating a Client...")
    client = ClientModel(
        user_id="c001",
        username="student123",
        email="student123@example.com",
        full_name="John Smith",
        phone_number="123-456-7890",
        task_name="Math Assignment",
        bio="College student needing help with calculus"
    )
    print(f"Client created: {client.to_dict()}")
    
    # Create a Freelancer
    print("\n2. Creating a Freelancer...")
    freelancer = FreelancerModel(
        user_id="f001",
        username="math_tutor",
        email="tutor@example.com",
        full_name="Dr. Sarah Wilson",
        skills=["Mathematics", "Calculus", "Statistics"],
        hourly_rate=30.0,
        bio="PhD in Mathematics with 5 years tutoring experience"
    )
    print(f"Freelancer created: {freelancer.to_dict()}")
    
    # Create a Seller
    print("\n3. Creating a Seller...")
    seller = SellerModel(
        user_id="s001",
        username="campus_bookstore",
        email="books@campus.edu",
        full_name="Campus Bookstore",
        business_name="University Bookstore",
        business_type="books",
        bio="Official campus bookstore selling textbooks and supplies"
    )
    print(f"Seller created: {seller.to_dict()}")
    
    # Create a Buyer
    print("\n4. Creating a Buyer...")
    buyer = BuyerModel(
        user_id="b001",
        username="student_buyer",
        email="buyer@student.edu",
        full_name="Alice Johnson",
        preferred_categories=["books", "electronics", "stationery"],
        bio="College student looking for textbooks and supplies"
    )
    print(f"Buyer created: {buyer.to_dict()}")
    
    print("\n=== Attempting to save to Firebase ===")
    print("Note: This will only work if you have Firebase credentials set up")
    
    # Try to save to Firebase (will show warning if credentials not set up)
    try:
        client_id = client.save_to_db()
        if client_id:
            print(f"✓ Client saved with ID: {client_id}")
        else:
            print("✗ Failed to save client")
            
        freelancer_id = freelancer.save_to_db()
        if freelancer_id:
            print(f"✓ Freelancer saved with ID: {freelancer_id}")
        else:
            print("✗ Failed to save freelancer")
            
        seller_id = seller.save_to_db()
        if seller_id:
            print(f"✓ Seller saved with ID: {seller_id}")
        else:
            print("✗ Failed to save seller")
            
        buyer_id = buyer.save_to_db()
        if buyer_id:
            print(f"✓ Buyer saved with ID: {buyer_id}")
        else:
            print("✗ Failed to save buyer")
            
    except Exception as e:
        print(f"Error during Firebase operations: {e}")
    
    print("\n=== Setup Instructions ===")
    print("To enable Firebase functionality:")
    print("1. Go to Firebase Console (https://console.firebase.google.com)")
    print("2. Select your project: collegemaster-f522d")
    print("3. Go to Project Settings > Service Accounts")
    print("4. Click 'Generate new private key'")
    print("5. Save the downloaded JSON file as 'service-account-key.json' in this directory")
    print("6. Run this script again to test Firebase operations")

if __name__ == "__main__":
    main()
