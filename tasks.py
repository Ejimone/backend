# This module handles task assignments between clients and freelancers
from Models import ClientModel as client, FreelancerModel as freelancer, SellerModel as seller, BuyerModel as buyer
from firebase_admin import initialize_app, credentials, firestore #for storing data in Firebase

# Initialize Firebase app
cred = credentials.Certificate("./service-account-key.json")
initialize_app(cred)
db = firestore.client()

def save_to_db(model_instance):
    """
    Save a model instance to Firebase Firestore.
    :param model_instance: An instance of ClientModel, FreelancerModel, SellerModel, or BuyerModel
    :return: The document ID of the saved instance
    """
    collection_name = model_instance.__class__.__name__.lower() + 's'  # e.g., 'clients', 'freelancers'
    doc_ref = db.collection(collection_name).add(model_instance.to_dict())
    print(f"Saved {model_instance.__class__.__name__} to Firestore with ID: {doc_ref.id}")
    return doc_ref.id

# this is where the client will enter that they want to do, an available freelancer will pick it up, if there are multiple freelancers, the client can choose one, the freelancer and the client will be in touch when the freelanncer is working on the task, once the task is done, the client will give pay in cash or online, and the freelancer will give feedback, the client will also give feedback(optional), and the task will be marked as completed.
