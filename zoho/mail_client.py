# zoho/mail_client.py

import httpx
from auth.zoho_auth import get_access_token

# ---------------------------------------------------------------------------
# Zoho Mail API base URL — adjust region if needed (.com, .eu, .in etc.)
# ---------------------------------------------------------------------------
BASE_URL = "https://mail.zoho.eu/api"


async def _get(path: str, params: dict = None) -> dict:
    """
    Internal helper: make an authenticated GET request to the Zoho Mail API.
    Every public function in this module goes through here.
    """
    token = await get_access_token()          # always fresh thanks to our auth module
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}{path}",
            headers=headers,
            params=params or {},
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()


async def get_account_id() -> str:
    """
    Fetch your primary Zoho Mail account ID.
    Zoho's API is account-scoped, so almost every endpoint needs this.
    We call it lazily — only when needed — rather than at startup.
    """
    data = await _get("/accounts")
    # The first account in the list is your primary one
    accounts = data.get("data", [])
    if not accounts:
        raise RuntimeError("No Zoho Mail accounts found for this token.")
    return accounts[0]["accountId"]


async def list_unread_emails(max_results: int = 20) -> list[dict]:
    """
    Return the most recent unread messages from your inbox.
    
    Zoho's message list endpoint returns summaries (no body).
    We include: subject, sender, date, and the messageId for follow-up reads.
    """
    account_id = await get_account_id()
    data = await _get(
        f"/accounts/{account_id}/messages/view",
        params={
            "status":  "unread",
            "limit":   max_results,
        }
    )
    messages = data.get("data", [])

    # Shape the response into something clean and readable
    return [
        {
            "id":      msg.get("messageId"),
            "subject": msg.get("subject", "(no subject)"),
            "from":    msg.get("fromAddress", ""),
            "date":    msg.get("receivedTime", ""),
            "summary": msg.get("summary", ""),   # Zoho provides a short snippet
            "hasAttachment": msg.get("hasAttachment", False),
        }
        for msg in messages
    ]


async def read_email(message_id: str) -> dict:
    """
    Fetch the full content of a single email by its messageId.
    Returns subject, sender, body (plain text preferred over HTML).
    """
    account_id = await get_account_id()
    data = await _get(f"/accounts/{account_id}/messages/{message_id}/content")
    content = data.get("data", {})

    return {
        "id":      message_id,
        "subject": content.get("subject", ""),
        "from":    content.get("fromAddress", ""),
        "to":      content.get("toAddress", ""),
        "date":    content.get("receivedTime", ""),
        "body":    content.get("content", ""),         # HTML
        "hasAttachment": content.get("hasAttachment", False),
    }


async def search_emails(query: str, max_results: int = 10) -> list[dict]:
    """
    Search across your mailbox using Zoho's server-side search.
    `query` can be a sender address, subject fragment, or keyword.
    """
    account_id = await get_account_id()
    data = await _get(
        f"/accounts/{account_id}/messages/search",
        params={
            "searchKey": query,
            "limit":     max_results,
        }
    )
    messages = data.get("data", [])

    return [
        {
            "id":      msg.get("messageId"),
            "subject": msg.get("subject", "(no subject)"),
            "from":    msg.get("fromAddress", ""),
            "date":    msg.get("receivedTime", ""),
            "snippet": msg.get("summary", ""),
        }
        for msg in messages
    ]