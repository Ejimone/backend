class Seller:
    def __init__(self, user_id, username, email, full_name="", phone_number="", business_name="", business_type="", bio=None, products=None):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.phone_number = phone_number
        self.role = "seller"
        self.business_name = business_name
        self.business_type = business_type  # e.g., "books", "electronics", "stationery"
        self.bio = bio
        self.is_active = True
        
        # Seller-specific attributes
        self.products = products if products is not None else []
        self.total_sales = 0.0
        self.average_rating = 0.0
        self.store_url = None
        self.payment_methods = []  # e.g., ["card", "paypal", "bank_transfer"]
        self.shipping_options = []  # e.g., ["standard", "express", "pickup"]
        
    def update_profile(self, full_name=None, phone_number=None, business_name=None, business_type=None, bio=None, store_url=None):
        if full_name is not None:
            self.full_name = full_name
        if phone_number is not None:
            self.phone_number = phone_number
        if business_name is not None:
            self.business_name = business_name
        if business_type is not None:
            self.business_type = business_type
        if bio is not None:
            self.bio = bio
        if store_url is not None:
            self.store_url = store_url
    
    def add_product(self, product):
        """Add a product to the seller's inventory"""
        if product not in self.products:
            self.products.append(product)
    
    def remove_product(self, product):
        """Remove a product from the seller's inventory"""
        if product in self.products:
            self.products.remove(product)
    
    def add_payment_method(self, payment_method):
        """Add a payment method"""
        if payment_method not in self.payment_methods:
            self.payment_methods.append(payment_method)
    
    def add_shipping_option(self, shipping_option):
        """Add a shipping option"""
        if shipping_option not in self.shipping_options:
            self.shipping_options.append(shipping_option)
    
    def update_rating(self, new_rating, total_reviews):
        """Update average rating based on new review"""
        self.average_rating = new_rating
    
    def record_sale(self, sale_amount):
        """Record a sale and update total sales"""
        self.total_sales += sale_amount
    
    def __str__(self):
        return f"Seller: {self.username} (ID: {self.user_id}, Business: {self.business_name})"

# Example usage
if __name__ == "__main__":
    seller1 = Seller(
        user_id="s001",
        username="bookstore_owner",
        email="bookstore@example.com",
        full_name="Jane Doe",
        business_name="Jane's Bookstore",
        business_type="books"
    )
    print(seller1)
    seller1.update_profile(bio="Selling quality textbooks and novels for college students.")
    seller1.add_product("Mathematics Textbook")
    seller1.add_product("Science Fiction Novel")
    seller1.add_payment_method("card")
    seller1.add_shipping_option("standard")
    print(f"Products: {seller1.products}")
    print(f"Payment Methods: {seller1.payment_methods}")
