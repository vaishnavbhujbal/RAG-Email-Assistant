from gmail_client import fetch_emails

if __name__ == "__main__":
    emails = fetch_emails(query="", max_results=3)
    for email in emails:
        print(email["snippet"])