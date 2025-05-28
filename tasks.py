# This module handles task assignments between clients and freelancers
from Models import ClientModel as client, FreelancerModel as freelancer, SellerModel as seller, BuyerModel as buyer
from firebase_admin import initialize_app, credentials, firestore #for storing data in Firebase

# Initialize Firebase app
cred = credentials.Certificate("./service-account-key.json")
initialize_app(cred)
db = firestore.client()


# this is where the client will enter that they want to do, an available freelancer will pick it up, if there are multiple freelancers, the client can choose one, the freelancer and the client will be in touch when the freelanncer is working on the task, once the task is done, the client will give pay in cash or online, and the freelancer will give feedback, the client will also give feedback(optional), and the task will be marked as completed. everything will be stored in the database, so that the client can see their tasks, and the freelancer can see their tasks, and the seller can see their products, and the buyer can see their products, and the admin can see everything.