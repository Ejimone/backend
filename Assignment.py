import Buyer
import freelancer
import Models



"""
This module handles the assignment of tasks to freelancers by clients.
"""
class Assignment:
    def __init__(self, client, freelancer, task_details):
        self.client = client
        self.freelancer = freelancer
        self.task_details = task_details
        self.status = "pending"  # can be 'pending', 'in_progress', or 'completed'
    
    def start_assignment(self):
        """Start the assignment process"""
        if self.status == "pending":
            self.status = "in_progress"
            print(f"Assignment started for {self.freelancer.username} by {self.client.username}.")
        else:
            print("Assignment cannot be started. Current status:", self.status)
    
    def complete_assignment(self):
        """Complete the assignment"""
        if self.status == "in_progress":
            self.status = "completed"
            print(f"Assignment completed by {self.freelancer.username}.")
        else:
            print("Assignment cannot be completed. Current status:", self.status)