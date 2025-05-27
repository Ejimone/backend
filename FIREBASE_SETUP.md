# Firebase Setup Instructions

## Setting up Firebase Admin SDK for Python

### Step 1: Download Service Account Key

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Select your project: `collegemaster-f522d`
3. Click on the gear icon (Settings) and select "Project settings"
4. Go to the "Service accounts" tab
5. Click "Generate new private key" button
6. Save the downloaded JSON file as `service-account-key.json` in this directory

### Step 2: File Structure

Your backend directory should look like this:

```
backend/
├── service-account-key.json  # <- Place your downloaded key here
├── Models.py
├── client.py
├── freelancer.py
├── Seller.py
├── Buyer.py
├── test_models.py
└── Firebase.json
```

### Step 3: Security Note

**Important**: Never commit `service-account-key.json` to version control!

Add this to your `.gitignore` file:

```
service-account-key.json
*.json
!Firebase.json
```

### Step 4: Alternative Setup (Environment Variable)

Instead of using a file, you can set an environment variable:

**Windows PowerShell:**

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\your\service-account-key.json"
```

**Windows Command Prompt:**

```cmd
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your\service-account-key.json
```

### Step 5: Test the Setup

Run the test script to verify everything works:

```bash
python test_models.py
```

## Available Collections in Firestore

The Models.py file creates the following collections:

- **clients** - College students who need assignments done
- **freelancers** - People who can help with assignments
- **sellers** - People/businesses selling products
- **buyers** - People buying products

## Example Usage

```python
from Models import ClientModel, SellerModel

# Create and save a client
client = ClientModel(
    user_id="c001",
    username="student123",
    email="student@college.edu",
    full_name="John Smith",
    task_name="Math Assignment"
)
client_id = client.save_to_db()

# Retrieve a client
client_data = ClientModel.get_by_id("c001")

# Query clients
all_clients = ClientModel.get_all_clients(limit=10)
```

## Firebase Rules (Optional)

For production, set up Firestore security rules in the Firebase Console.
