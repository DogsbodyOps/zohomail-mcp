# zohomail-mcp

A Python-based MCP (Model Context Protocol) server that connects Claude to your Zoho Mail account, allowing Claude to read, search, and triage your emails directly from a conversation.

---

## Project Structure

```
zohomail-mcp/
├── .env                    # Your secrets — never commit this file
├── .zoho_tokens.json       # Auto-generated OAuth2 tokens — never commit this file
├── .gitignore
├── requirements.txt
├── README.md
├── server.py               # MCP server entrypoint
├── test_mail.py            # Quick sanity-check script
├── auth/
│   └── zoho_auth.py        # OAuth2 token management & refresh logic
└── zoho/
    └── mail_client.py      # Zoho Mail API wrapper functions
```

---

## Prerequisites

- Python 3.11 or newer
- A Zoho Mail account
- Access to the [Zoho API Console](https://api-console.zoho.eu) (EU) or [api-console.zoho.com](https://api-console.zoho.com)

---

## Step 1 — Get Zoho API Credentials

Before writing any code, you need OAuth2 credentials from Zoho.

1. Go to [https://api-console.zoho.eu](https://api-console.zoho.eu) (use `.com` if your account is on the global data centre)
2. Click **Add Client** → choose **Self Client** (simplest option for personal/script use)
3. Copy your **Client ID** and **Client Secret** — you'll need these shortly
4. Click the **Generate Code** tab
5. In the **Scope** field, enter:
   ```
   ZohoMail.messages.READ,ZohoMail.accounts.READ
   ```
6. Set **Time Duration** to the maximum available
7. Click **Create** — Zoho gives you a one-time authorisation code. **Copy it immediately**, it expires in a few minutes

---

## Step 2 — Clone the Project & Set Up a Virtual Environment

A virtual environment (`venv`) isolates this project's Python dependencies from the rest of your system.

```bash
git clone https://github.com/DogsbodyOps/zohomail-mcp.git
cd zohomail-mcp

# Create a virtual environment in a folder called .venv
python3 -m venv .venv
```

### Activate the virtual environment

You must activate the venv **every time** you open a new terminal session to work on this project.

**Linux / macOS:**
```bash
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

Once activated, your terminal prompt changes to show `(.venv)` at the start:

```
(.venv) aaron@machine:~/zohomail-mcp$
```

> **Tip:** To deactivate and return to your system Python, simply run `deactivate`.

---

## Step 3 — Install Dependencies

With your venv active, install the required packages from `requirements.txt`:

```bash
pip install -r requirements.txt
```

This installs:

| Package | Purpose |
|---|---|
| `mcp>=1.0.0` | Anthropic's MCP Python SDK — the server framework |
| `httpx>=0.27.0` | Async HTTP client for calling the Zoho REST API |
| `python-dotenv>=1.0.0` | Loads secrets from your `.env` file |

---

## Step 4 — Configure Your Secrets

Create a `.env` file in the project root. This file holds your credentials and is **never committed to version control**.

```bash
cp .env.example .env
```

Open it in your editor and replace the placeholder values with the Client ID and Client Secret you copied from the Zoho API Console in Step 1:

```
ZOHO_CLIENT_ID=your_client_id_here
ZOHO_CLIENT_SECRET=your_client_secret_here
```

---

## Step 5 — Run the Initial OAuth2 Authorisation

This is a **one-time step**. It exchanges the authorisation code from Step 1 for a long-lived refresh token, which is saved locally so the server can authenticate automatically from now on.

```bash
python auth/zoho_auth.py
```

When prompted, paste the authorisation code you generated in the Zoho API Console:

```
Paste the authorisation code from Zoho API Console: <paste here>
✅ Tokens saved to .zoho_tokens.json
   Access token expires in ~60 minutes
   Refresh token: present
```

> **What just happened?** The script exchanged your short-lived authorisation code for two tokens:
> - **Access token** — used to make API calls, valid for ~1 hour
> - **Refresh token** — used to get new access tokens automatically, long-lived
>
> Both are saved to `.zoho_tokens.json`. The server handles all token refreshing transparently from here on.

---

## Step 6 — Test the Mail Client

Before connecting to Claude, verify the API connection works:

```bash
python test_mail.py
```

You should see your 5 most recent unread emails printed to the terminal:

```
Fetching up to 5 unread emails...

  [1777226417286] Welcome to the latest council news
  From: news@example.com

  [1777223224579] Your weekly summary
  From: hello@example.com
```

If you see an error, check the troubleshooting section below.

---

## Step 7 — Connect to Claude Desktop

Add the server to Claude Desktop's MCP configuration file.

**Config file location:**

| OS | Path |
|---|---|
| Linux / WSL | `~/.config/claude/claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

Add the following, replacing the path with the absolute path to your project directory:

```json
{
  "mcpServers": {
    "zoho-mail": {
      "type": "stdio",
      "command": "/absolute/path/to/zohomail-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/zohomail-mcp/server.py"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/zohomail-mcp"
      }
    }
  }
}
```

To find your absolute path:
```bash
pwd
# Example: /home/aaron/zohomail-mcp
```

> **Important:** Point `command` at the Python binary **inside your venv**, not the system Python. This ensures the MCP server uses the correct installed packages.

**Restart Claude Desktop** after saving the config. The zoho-mail tools will now appear in Claude's tool list.

---

## Available Tools

Once connected, Claude can use these tools:

| Tool | Description |
|---|---|
| `list_unread_emails` | Fetch unread messages (default: 20) |
| `read_email` | Read the full content of an email by its ID |
| `search_emails` | Search by sender, subject fragment, or keyword |

**Example prompts to try:**
- *"Check my unread emails and flag anything urgent"*
- *"Do I have any emails from AWS about billing?"*
- *"Read email ID `abc123` in full"*

---

## Troubleshooting

### `No valid tokens found`
Your `.zoho_tokens.json` is missing or corrupt. Re-run Step 5:
```bash
python auth/zoho_auth.py
```

### `401 Unauthorized` from Zoho API
Your refresh token may have been revoked (Zoho does this if unused for 30+ days, or if you revoke it in the API Console). Re-run Step 5.

### `ModuleNotFoundError: No module named 'mcp'`
Your virtual environment isn't active, or you installed packages outside it:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Wrong Zoho region
If you see `Invalid client` errors, check `auth/zoho_auth.py` and `zoho/mail_client.py` — the base URLs use `.eu`. Change to `.com` (or `.in` for India) to match your account's data centre.

### Claude Desktop doesn't show the tools
- Confirm the paths in the config file are **absolute**, not relative
- Confirm `command` points to `.venv/bin/python`, not system Python
- Restart Claude Desktop fully after any config change
- Check Claude Desktop logs for MCP server startup errors

---

## Security Notes

- `.env` and `.zoho_tokens.json` contain credentials — they are listed in `.gitignore` and must **never** be committed to version control
- The OAuth2 scopes (`ZohoMail.messages.READ`, `ZohoMail.accounts.READ`) are read-only — this server cannot send, delete, or modify emails
- Tokens are stored locally on disk; treat `.zoho_tokens.json` with the same care as a password

---

## Keeping Dependencies Up to Date

```bash
source .venv/bin/activate
pip install --upgrade -r requirements.txt
```
