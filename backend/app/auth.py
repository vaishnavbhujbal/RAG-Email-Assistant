import os
from google.oauth2 import id_token
from google.auth.transport import requests

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def verify_google_token(token, users_collection):
    try:
        # Verify token with Google's API
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        email = idinfo["email"]
        name = idinfo.get("name", "")
        picture = idinfo.get("picture", "")
        # Check if user exists in DB
        user = users_collection.find_one({"email": email})
        if not user:
            # Register new user
            user = {
                "email": email,
                "name": name,
                "picture": picture,
                "auth_provider": "google"
            }
            users_collection.insert_one(user)
        else:
            # Optionally update name/picture if changed
            update = {}
            if user.get("name") != name:
                update["name"] = name
            if user.get("picture") != picture:
                update["picture"] = picture
            if update:
                users_collection.update_one({"email": email}, {"$set": update})
                user.update(update)
        return {
            "email": email,
            "name": name,
            "picture": picture
        }
    except Exception as e:
        raise Exception(f"Token validation failed: {e}")