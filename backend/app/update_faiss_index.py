from dotenv import load_dotenv
load_dotenv()

import faiss
import numpy as np
import openai
import json


EMAILS_PATH = "emails.json"
META_PATH = "email_metadata.json"
INDEX_PATH = "emails.index"
EMBEDDING_MODEL = "text-embedding-3-small"
MAX_CHARS = 16000  

def embed_text(text, client):
    text = text[:MAX_CHARS]
    response = client.embeddings.create(
        input=[text],
        model=EMBEDDING_MODEL
    )
    return np.array(response.data[0].embedding, dtype=np.float32)

def main():
    client = openai.OpenAI()
    # Load emails — should already be sorted and trimmed to 500
    with open(EMAILS_PATH, 'r', encoding='utf-8') as f:
        emails = json.load(f)
    if not emails:
        print("No emails to index.")
        return

    vectors = []
    metadata = []
    for e in emails:
        body_text = e.get("body", "")
        if not isinstance(body_text, str) or not body_text.strip():
            print(f"Skipping email with empty body: {e.get('subject', '')}")
            continue
        try:
            embedding = embed_text(body_text, client)
        except Exception as ex:
            print(f"Failed to embed email '{e.get('subject', '')}': {ex}")
            continue
        vectors.append(embedding)
        metadata.append({
            "id": e["id"],
            "threadId": e.get("threadId", ""),
            "subject": e.get("subject", ""),
            "from": e.get("from", ""),
            "date": e.get("date", "")
        })
        print(f"Embedded email: {e.get('subject', '')}")

    if vectors:
        dim = len(vectors[0])
        index = faiss.IndexFlatL2(dim)
        index.add(np.vstack(vectors))
        faiss.write_index(index, INDEX_PATH)
        with open(META_PATH, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"Indexed {len(metadata)} emails and updated metadata, keeping only the latest.")
    else:
        print("No valid emails to index.")

if __name__ == "__main__":
    main()