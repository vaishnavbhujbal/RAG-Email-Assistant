from dotenv import load_dotenv
load_dotenv()

import faiss
import json
import openai
import numpy as np
import re

FAISS_INDEX_PATH = "emails.index"
METADATA_PATH = "email_metadata.json"
EMAILS_PATH = "emails.json"
OPENAI_EMBED_MODEL = "text-embedding-3-small"  

def get_openai_embedding(text, model=OPENAI_EMBED_MODEL):
    client = openai.OpenAI()
    response = client.embeddings.create(
        input=[text],
        model=model
    )
    return np.array(response.data[0].embedding, dtype=np.float32)

def extract_possible_names_and_subjects(question):
    
    from_match = re.search(r'from\s+([A-Za-z0-9@.]+)', question, re.IGNORECASE)
    to_match = re.search(r'to\s+([A-Za-z0-9@.]+)', question, re.IGNORECASE)
    subject_match = re.search(r'subject\s+([A-Za-z0-9@. ]+)', question, re.IGNORECASE)
    return {
        "from": from_match.group(1) if from_match else None,
        "to": to_match.group(1) if to_match else None,
        "subject": subject_match.group(1).strip() if subject_match else None
    }

def search_emails(query, top_k=5):
    index = faiss.read_index(FAISS_INDEX_PATH)
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    with open(EMAILS_PATH, "r", encoding="utf-8") as f:
        emails = {e["id"]: e for e in json.load(f)}
    query_vector = get_openai_embedding(query)
    D, I = index.search(np.expand_dims(query_vector, axis=0), top_k * 3)  # get more for filtering

    clues = extract_possible_names_and_subjects(query)
    results = []
    for idx in I[0]:
        if idx < len(metadata):
            meta = metadata[idx]
            email = emails.get(meta["id"], {})
            # Additional filtering based on clues
            match = True
            if clues["from"] and clues["from"].lower() not in meta.get("from", "").lower():
                match = False
            if clues["to"] and clues["to"].lower() not in meta.get("to", "").lower():
                match = False
            if clues["subject"] and clues["subject"].lower() not in meta.get("subject", "").lower():
                match = False
            if match:
                results.append({
                    "subject": meta.get("subject"),
                    "from": meta.get("from"),
                    "date": meta.get("date"),
                    "to": meta.get("to", ""),
                    "body": email.get("body", ""),
                    "snippet": meta.get("snippet")
                })
        if len(results) >= top_k:
            break
    
    if not results:
        for idx in I[0][:top_k]:
            if idx < len(metadata):
                meta = metadata[idx]
                email = emails.get(meta["id"], {})
                results.append({
                    "subject": meta.get("subject"),
                    "from": meta.get("from"),
                    "date": meta.get("date"),
                    "to": meta.get("to", ""),
                    "body": email.get("body", ""),
                    "snippet": meta.get("snippet")
                })
    return results

def build_context(found_emails, max_body_chars=500):
    context = []
    for i, email in enumerate(found_emails, 1):
        body = email['body'][:max_body_chars]  
        context.append(
            f"Email {i}:\nSubject: {email['subject']}\nFrom: {email['from']}\nTo: {email.get('to','')}\nDate: {email['date']}\nBody: {body}\n"
        )
    return "\n".join(context)

def ask_openai(context, question, max_context_chars=12000):
    
    if len(context) > max_context_chars:
        context = context[:max_context_chars] + "\n[context truncated]\n"
    client = openai.OpenAI()
    prompt = f"""
You are an AI email assistant. Here are some emails:

{context}

Based on the above emails, answer the following question concisely and accurately.

If the question is about who sent or received an email, pay special attention to the 'From', 'To', and 'Subject' fields.

Also check the email body for while answering the question.

Question: {question}
Answer:
"""
    response = client.chat.completions.create(
        model="gpt-4",  # Or "gpt-3.5-turbo"
        messages=[
            {"role": "system", "content": "You are an AI assistant that helps users understand their emails."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    question = input("Ask your question about your emails: ")
    found = search_emails(question, top_k=3)
    context = build_context(found, max_body_chars=500)
    print("\n--- Top Emails Used as Context ---\n")
    print(context)
    print("\n--- OpenAI's Answer ---\n")
    answer = ask_openai(context, question)
    print(answer)
    print("\n")
    
    

