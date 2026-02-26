import requests
import json

API_URL = "https://bsky.social/xrpc/app.bsky.feed.getTimeline"

def load_token():
    with open("token.json", "r", encoding="utf-8") as f:
        return json.load(f)["accessJwt"]

def get_timeline(limit=10):
    token = load_token()

    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(f"{API_URL}?limit={limit}", headers=headers, timeout=10)

    print("HTTP status:", r.status_code)
    return r.json()

if __name__ == "__main__":
    data = get_timeline(5)
    print(data)
