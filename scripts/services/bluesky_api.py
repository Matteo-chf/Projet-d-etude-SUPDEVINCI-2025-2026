import requests
import json

API_URL = "https://bsky.social/xrpc/app.bsky.feed.getTimeline"

def load_token():
    with open("token.json", "r", encoding="utf-8") as f:
        return json.load(f)["accessJwt"]

def get_full_timeline(limit_per_call=100, max_pages=5):
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}

    all_items = []
    cursor = None

    for _ in range(max_pages):
        params = {"limit": limit_per_call}
        if cursor:
            params["cursor"] = cursor

        r = requests.get(API_URL, headers=headers, params=params, timeout=10)
        r.raise_for_status()

        data = r.json()
        feed = data.get("feed", [])
        all_items.extend(feed)

        cursor = data.get("cursor")
        if not cursor:
            break

    return all_items
