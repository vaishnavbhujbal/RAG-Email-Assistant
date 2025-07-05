import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv


from auth import verify_google_token


from semantic_rag_openai import ask_openai, search_emails, build_context

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
mongo_client = MongoClient(MONGO_URL)
db = mongo_client['email_assistant']
chats_collection = db['chats']
users_collection = db['users']

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    question: str

class GoogleAuthRequest(BaseModel):
    token: str

@app.post("/api/auth/google")
def google_auth(payload: GoogleAuthRequest):
    user = verify_google_token(payload.token, users_collection)
    return {"status": "success", "user": user}

@app.post("/api/ask")
async def ask_endpoint(req: AskRequest):
    found = search_emails(req.question, top_k=3)
    context = build_context(found, max_body_chars=500)
    answer = ask_openai(context, req.question)
    entry = {
        "question": req.question,
        "answer": answer,
        "timestamp": datetime.utcnow()
    }
    chats_collection.insert_one(entry)
    entry["timestamp"] = entry["timestamp"].isoformat()
    entry.pop("_id", None)
    return entry

@app.get("/api/history")
def get_history():
    history = list(chats_collection.find({}, {"_id": 0}))
    for chat in history:
        if isinstance(chat["timestamp"], datetime):
            chat["timestamp"] = chat["timestamp"].isoformat()
    return history


