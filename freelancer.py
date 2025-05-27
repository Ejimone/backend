
class Freelancer:
    def __init__(self, user_id, username, email, full_name="", phone_number="", skills=None, portfolio_url=None, bio=None, hourly_rate=None, average_rating=0.0):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.phone_number = phone_number
        self.role = "freelancer"  # As per the image context "Freelancer = Commerce sender"
        self.is_active = True

        # Freelancer-specific profile attributes
        self.skills = skills if skills is not None else []
        self.portfolio_url = portfolio_url
        self.bio = bio
        self.hourly_rate = hourly_rate
        self.average_rating = average_rating
        self.payout_details = {} # Placeholder for payment information

    def update_profile(self, full_name=None, phone_number=None, skills=None, portfolio_url=None, bio=None, hourly_rate=None):
        if full_name is not None:
            self.full_name = full_name
        if phone_number is not None:
            self.phone_number = phone_number
        if skills is not None:
            self.skills = skills
        if portfolio_url is not None:
            self.portfolio_url = portfolio_url
        if bio is not None:
            self.bio = bio
        if hourly_rate is not None:
            self.hourly_rate = hourly_rate

    def add_skill(self, skill):
        if skill not in self.skills:
            self.skills.append(skill)

    def remove_skill(self, skill):
        if skill in self.skills:
            self.skills.remove(skill)

    def set_payout_details(self, details):
        # In a real application, this would be handled securely
        self.payout_details = details

    def __str__(self):
        return f"Freelancer: {self.username} (ID: {self.user_id}, Skills: {", ".join(self.skills)})"

# # Example of how this class might be used (not part of the file content itself normally):
# if __name__ == "__main__":
#     freelancer1 = Freelancer(
#         user_id="f001", 
#         username="creative_coder", 
#         email="cc@example.com",
#         full_name="Alex Doe",
#         skills=["Python", "Web Design", "Graphic Art"]
#     )
#     print(freelancer1)
#     freelancer1.update_profile(bio="Experienced developer and designer.", hourly_rate=50)
#     freelancer1.add_skill("Django")
#     print(freelancer1)

