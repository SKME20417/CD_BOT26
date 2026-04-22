import requests
import time
import logging

# ── Constants ──────────────────────────────────────────────────────────────────
GRAPH = "https://graph.microsoft.com/v1.0"
SENDER_UPN = "Sanjay265646@exlservice.com"
MAX_RETRIES = 3
DELAY_SECONDS = 2

logging.basicConfig(
    filename="teams_bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# ── User validation ────────────────────────────────────────────────────────────
def validate_user(upn: str, headers: dict) -> bool:
    """Return True if the UPN resolves to a real Entra user."""
    try:
        r = requests.get(f"{GRAPH}/users/{upn}", headers=headers, timeout=10)
        return r.status_code == 200
    except Exception as e:
        logging.error(f"validate_user({upn}) exception: {e}")
        return False


# ── Chat creation ──────────────────────────────────────────────────────────────
def _find_existing_chat(recipient_upn: str, headers: dict) -> str | None:
    """Search /me/chats for an existing oneOnOne chat with this recipient."""
    try:
        url = f"{GRAPH}/me/chats?$expand=members&$filter=chatType eq 'oneOnOne'"
        while url:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            for chat in data.get("value", []):
                members = chat.get("members", [])
                emails = [
                    (m.get("email") or m.get("upn") or "").lower()
                    for m in members
                ]
                if recipient_upn.lower() in emails:
                    return chat["id"]
            url = data.get("@odata.nextLink")
    except Exception as e:
        logging.error(f"_find_existing_chat({recipient_upn}) exception: {e}")
    return None


def create_chat(recipient_upn: str, sender_upn: str, headers: dict) -> str | None:
    """Get or create a oneOnOne chat and return its chat_id."""
    body = {
        "chatType": "oneOnOne",
        "members": [
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"{GRAPH}/users('{sender_upn}')",
            },
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"{GRAPH}/users('{recipient_upn}')",
            },
        ],
    }
    try:
        r = requests.post(f"{GRAPH}/chats", json=body, headers=headers, timeout=15)

        if r.status_code == 201:
            return r.json()["id"]

        if r.status_code == 409:
            # Chat already exists — find it
            return _find_existing_chat(recipient_upn, headers)

        logging.error(f"create_chat({recipient_upn}): {r.status_code} {r.text}")
        return None
    except Exception as e:
        logging.error(f"create_chat({recipient_upn}) exception: {e}")
        return None


# ── Message sending ────────────────────────────────────────────────────────────
def send_message(chat_id: str, message: str, headers: dict) -> bool:
    """Send an HTML message to a chat. Retries on 429 rate-limit."""
    url = f"{GRAPH}/chats/{chat_id}/messages"
    body = {"body": {"contentType": "html", "content": message}}

    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(url, json=body, headers=headers, timeout=15)

            if r.status_code == 201:
                return True

            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 5))
                logging.warning(f"Rate-limited. Waiting {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
                continue

            logging.error(f"send_message({chat_id}): {r.status_code} {r.text}")
            return False

        except Exception as e:
            logging.error(f"send_message({chat_id}) exception: {e}")
            return False

    return False
