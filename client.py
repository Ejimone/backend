
# since this is a college student which wants assignment done, he will be called a client, and he will have the characteristics of a client
class Client:
    def __init__(self, username, user_id, email, full_name="", phone_number="", task_name="", bio=None):
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
    
    def update_profile(self, full_name=None, phone_number=None, task_name=None, bio=None):
        if full_name:
            self.full_name = full_name
        if phone_number:
            self.phone_number = phone_number
        if task_name:
            self.task_name = task_name
        if bio:
            self.bio = bio

    def set_task_details(self, details):
        self.task_details = details
        self.budget = details.get("budget", None)
        self.status = "open"

    def add_proposal(self, proposal):
        self.proposals.append(proposal)
        self.status = "under_review"

    def select_freelancer(self, freelancer):
        if freelancer in self.proposals:
            self.selected_freelancer = freelancer
            self.status = "in_progress"
        else:
            raise ValueError("Freelancer not found in proposals")
        
    def provide_feedback(self, feedback):
        self.feedback = feedback
        self.status = "completed"
    def set_payment_details(self, details):
        # In a real application, this would be handled securely
        self.payment_details = details

    def __str__(self):
        return f"Client: {self.username} (ID: {self.user_id}, Task: {self.task_name})"
# Example of how this class might be used (not part of the file content itself normally):
if __name__ == "__main__":
    client1 = Client(
        user_id="c001",
        username="student123",
        email="student123@example.com",
        full_name="John Smith",
        phone_number="123-456-7890",
        task_name="Math Assignment"
    )
    print(client1)
    client1.update_profile(bio="Looking for a freelancer to help with assignments.")
    client1.set_task_details({
        "description": "Need help with calculus problems.",
        "budget": 100
    })
    print(client1)