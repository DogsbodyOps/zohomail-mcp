# auth/zoho_auth.py

import json
import time
import httpx
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# ---------------------------------------------------------------------------
# Zoho OAuth2 endpoints — use .eu if your account is on the EU data centre
# ---------------------------------------------------------------------------
TOKEN_URL = "https://accounts.zoho.eu/oauth/v2/token"

# Where we persist tokens between runs so we don't re-auth every time
TOKEN_FILE = Path(".zoho_tokens.json")


def save_tokens(data: dict):
    """Persist tokens to disk with an expiry timestamp we calculate ourselves."""
    data["expires_at"] = time.time() + data.get("expires_in", 3600) - 60
    # The -60 gives us a 60-second safety buffer before true expiry
    TOKEN_FILE.write_text(json.dumps(data, indent=2))


def load_tokens() -> dict | None:
    """Load tokens from disk if they exist."""
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


def is_expired(tokens: dict) -> bool:
    """Check if the access token has passed its expiry timestamp."""
    return time.time() >= tokens.get("expires_at", 0)


async def get_access_token() -> str:
    """
    Return a valid access token, refreshing automatically if needed.
    This is the main function the rest of the app will call.
    """
    tokens = load_tokens()

    if tokens and "access_token" in tokens and not is_expired(tokens):
        return tokens["access_token"]

    if tokens and "refresh_token" in tokens:
        # Token expired but we have a refresh token — exchange it for a new one
        return await refresh_access_token(tokens["refresh_token"])

    raise RuntimeError(
        "No valid tokens found. Run the initial auth flow first:\n"
        "  python auth/zoho_auth.py"
    )


async def refresh_access_token(refresh_token: str) -> str:
    """Exchange a refresh token for a new access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(TOKEN_URL, params={
            "refresh_token": refresh_token,
            "client_id":     os.getenv("ZOHO_CLIENT_ID"),
            "client_secret": os.getenv("ZOHO_CLIENT_SECRET"),
            "grant_type":    "refresh_token",
        })
        response.raise_for_status()
        data = response.json()

        # Refresh responses don't include a new refresh_token, so preserve the old one
        data["refresh_token"] = refresh_token
        save_tokens(data)
        return data["access_token"]


# ---------------------------------------------------------------------------
# Run this file directly once to complete the initial OAuth2 handshake
# ---------------------------------------------------------------------------
async def initial_auth_flow():
    """
    One-time setup: exchange the authorisation code Zoho gave you
    in the API console for a long-lived refresh token.
    """
    import asyncio

    client_id     = os.getenv("ZOHO_CLIENT_ID")
    client_secret = os.getenv("ZOHO_CLIENT_SECRET")
    auth_code     = input("Paste the authorisation code from Zoho API Console: ").strip()

    async with httpx.AsyncClient() as client:
        response = await client.post(TOKEN_URL, params={
            "code":          auth_code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "grant_type":    "authorization_code",
            # Self Client flows don't use a redirect URI
        })
        response.raise_for_status()
        data = response.json()

    save_tokens(data)
    print("✅ Tokens saved to .zoho_tokens.json")
    print(f"   Access token expires in ~{data.get('expires_in', 3600)//60} minutes")
    print(f"   Refresh token: {'present' if 'refresh_token' in data else 'MISSING — check scopes'}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(initial_auth_flow())