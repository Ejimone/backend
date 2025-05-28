class Buyer:
    def __init__(self, user_id, username, email, full_name="", phone_number="", bio=None, preferred_categories=None):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.phone_number = phone_number
        self.role = "buyer"
        self.bio = bio
        self.is_active = True
        
        # Buyer-specific attributes
        self.preferred_categories = preferred_categories if preferred_categories is not None else []
        self.order_history = []
        self.wishlist = []
        self.shipping_address = {}
        self.payment_details = {}
        self.total_spent = 0.0
        self.loyalty_points = 0
        
    def update_profile(self, full_name=None, phone_number=None, bio=None, shipping_address=None):
        if full_name is not None:
            self.full_name = full_name
        if phone_number is not None:
            self.phone_number = phone_number
        if bio is not None:
            self.bio = bio
        if shipping_address is not None:
            self.shipping_address = shipping_address
    
    def add_preferred_category(self, category):
        """Add a preferred product category"""
        if category not in self.preferred_categories:
            self.preferred_categories.append(category)
    
    def remove_preferred_category(self, category):
        """Remove a preferred product category"""
        if category in self.preferred_categories:
            self.preferred_categories.remove(category)
    
    def add_to_wishlist(self, product_id):
        """Add a product to wishlist"""
        if product_id not in self.wishlist:
            self.wishlist.append(product_id)
    
    def remove_from_wishlist(self, product_id):
        """Remove a product from wishlist"""
        if product_id in self.wishlist:
            self.wishlist.remove(product_id)
    
    def place_order(self, order_details):
        """Place an order and add to order history"""
        order_details['order_date'] = None  # Would be set to current timestamp in real app
        order_details['status'] = 'placed'
        self.order_history.append(order_details)
        
        # Update total spent and loyalty points
        if 'total_amount' in order_details:
            self.total_spent += order_details['total_amount']
            self.loyalty_points += int(order_details['total_amount'] / 10)  # 1 point per $10 spent
    
    def set_payment_details(self, payment_details):
        """Set payment details (in real app, this would be handled securely)"""
        self.payment_details = payment_details
    
    def set_shipping_address(self, address):
        """Set shipping address"""
        self.shipping_address = address
    
    def get_order_by_id(self, order_id):
        """Get order details by order ID"""
        for order in self.order_history:
            if order.get('order_id') == order_id:
                return order
        return None
    
    def __str__(self):
        return f"Buyer: {self.username} (ID: {self.user_id}, Categories: {', '.join(self.preferred_categories)})"

# Example usage
# if __name__ == "__main__":
#     buyer1 = Buyer(
#         user_id="b001",
#         username="student_buyer",
#         email="student@example.com",
#         full_name="John Smith",
#         preferred_categories=["books", "electronics"]
#     )
#     print(buyer1)
#     buyer1.update_profile(bio="College student looking for textbooks and tech gadgets.")
#     buyer1.add_to_wishlist("math_textbook_123")
#     buyer1.add_to_wishlist("laptop_456")
#     buyer1.set_shipping_address({
#         "street": "123 College Ave",
#         "city": "University Town",
#         "state": "CA",
#         "zip_code": "12345"
#     })
    
#     # Place an order
#     order = {
#         "order_id": "ord_001",
#         "items": ["math_textbook_123"],
#         "total_amount": 50.0,
#         "seller_id": "s001"
#     }
#     buyer1.place_order(order)
    
#     print(f"Wishlist: {buyer1.wishlist}")
#     print(f"Total spent: ${buyer1.total_spent}")
#     print(f"Loyalty points: {buyer1.loyalty_points}")
