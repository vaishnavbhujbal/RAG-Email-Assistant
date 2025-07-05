import pickle
import os
import base64
import json
import re
from googleapiclient.discovery import build
from email.utils import parsedate_to_datetime
from dateutil import parser as date_parser
from datetime import timezone

TOKEN_PATH = 'token.pickle'
OUTPUT_PATH = 'emails.json'
LAST_SEEN_PATH = 'last_seen_id.txt'
MAX_RESULTS = 500
MAX_EMAILS = 500

def get_service():
    with open(TOKEN_PATH, 'rb') as token:
        creds = pickle.load(token)
    return build('gmail', 'v1', credentials=creds)

def get_email_body(message):
    payload = message.get("payload", {})
    parts = payload.get("parts", [])
    data = None
    if "body" in payload and payload["body"].get("data"):
        data = payload["body"]["data"]
    elif parts:
        for part in parts:
            if part.get("mimeType") == "text/plain" and part["body"].get("data"):
                data = part["body"]["data"]
                break
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return ""

def clean_email_text(text):
    text = re.sub(r"(?m)^--\s*\n.*", "", text, flags=re.DOTALL)
    text = re.sub(r"(?m)^Sent from my.*", "", text)
    text = re.sub(r"(?s)This email is confidential.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()

def get_header(headers, name):
    for h in headers:
        if h['name'].lower() == name.lower():
            return h['value']
    return ""

def get_last_seen_id():
    if os.path.exists(LAST_SEEN_PATH):
        with open(LAST_SEEN_PATH) as f:
            return f.read().strip()
    return None

def set_last_seen_id(email_id):
    with open(LAST_SEEN_PATH, "w") as f:
        f.write(email_id)

def parse_email_date(email):
    date_str = email.get('dt') or email.get('date') or ''
    try:
        dt = date_parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return date_parser.parse("1970-01-01T00:00:00+00:00")

def main():
    service = get_service()
    last_seen_id = get_last_seen_id()
    print(f"Last seen email id: {last_seen_id}")

    results = service.users().messages().list(userId='me', maxResults=MAX_RESULTS).execute()
    messages = results.get('messages', [])
    if not messages:
        print("No messages found.")
        return

    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
            all_emails = json.load(f)
    else:
        all_emails = []

    processed_ids = set(e['id'] for e in all_emails)
    new_emails = []
    for msg in messages:
        if msg['id'] in processed_ids:
            continue
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_detail['payload'].get('headers', [])
        subject = get_header(headers, 'Subject')
        sender = get_header(headers, 'From')
        date = get_header(headers, 'Date')
        dt = None
        try:
            dt = parsedate_to_datetime(date) if date else None
        except Exception:
            dt = None
        email_data = {
            'id': msg_detail['id'],
            'threadId': msg_detail['threadId'],
            'subject': subject,
            'from': sender,
            'date': date,
            'dt': dt.isoformat() if dt else "",
            'body': clean_email_text(get_email_body(msg_detail))
        }
        new_emails.append(email_data)
        print(f"Fetched new email: {subject}")

    if new_emails:
        all_emails.extend(new_emails)
        
        all_emails = sorted(all_emails, key=parse_email_date, reverse=True)[:MAX_EMAILS]
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(all_emails, f, ensure_ascii=False, indent=2)
        set_last_seen_id(new_emails[0]['id'])
        print(f"Added {len(new_emails)} new emails to {OUTPUT_PATH}, kept only latest {MAX_EMAILS}.")
    else:
        print("No new emails to add.")

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f)
    main()