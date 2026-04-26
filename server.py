# server.py

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from zoho.mail_client import list_unread_emails, read_email, search_emails

# ---------------------------------------------------------------------------
# Initialise the MCP server with a name Claude will use to identify it
# ---------------------------------------------------------------------------
app = Server("zoho-mail")


# ---------------------------------------------------------------------------
# Tool definitions — these are what Claude sees and can choose to call
# ---------------------------------------------------------------------------
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    Advertise our tools to the MCP client (Claude).
    The descriptions matter — Claude reads them to decide which tool to use.
    """
    return [
        types.Tool(
            name="list_unread_emails",
            description=(
                "Fetch unread emails from the Zoho Mail inbox. "
                "Returns subject, sender, date, and a short snippet for each message. "
                "Use this first to get an overview of what needs attention."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type":        "integer",
                        "description": "Maximum number of emails to return (default 20)",
                        "default":     20,
                    }
                },
            },
        ),
        types.Tool(
            name="read_email",
            description=(
                "Read the full content of a specific email by its ID. "
                "Use list_unread_emails first to get message IDs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type":        "string",
                        "description": "The messageId returned by list_unread_emails",
                    }
                },
                "required": ["message_id"],
            },
        ),
        types.Tool(
            name="search_emails",
            description=(
                "Search emails by keyword, sender address, or subject fragment. "
                "Useful for finding specific threads or checking if something was received."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type":        "string",
                        "description": "Search term — sender email, subject words, or any keyword",
                    },
                    "max_results": {
                        "type":    "integer",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool execution — Claude calls a tool, we run the corresponding function
# ---------------------------------------------------------------------------
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Router: maps tool names to actual Python functions.
    Whatever we return here is what Claude reads as the tool result.
    """
    try:
        if name == "list_unread_emails":
            results = await list_unread_emails(
                max_results=arguments.get("max_results", 20)
            )
            # Format as readable text — Claude handles plain text well
            if not results:
                text = "No unread emails found."
            else:
                lines = [f"Found {len(results)} unread email(s):\n"]
                for i, msg in enumerate(results, 1):
                    attachment_flag = " 📎" if msg["hasAttachment"] else ""
                    lines.append(
                        f"{i}. [{msg['date']}] {msg['subject']}{attachment_flag}\n"
                        f"   From: {msg['from']}\n"
                        f"   ID: {msg['id']}\n"
                        f"   Preview: {msg['summary']}\n"
                    )
                text = "\n".join(lines)

        elif name == "read_email":
            msg = await read_email(arguments["message_id"])
            text = (
                f"Subject: {msg['subject']}\n"
                f"From:    {msg['from']}\n"
                f"To:      {msg['to']}\n"
                f"Date:    {msg['date']}\n"
                f"{'─' * 60}\n"
                f"{msg['body']}"
            )

        elif name == "search_emails":
            results = await search_emails(
                query=arguments["query"],
                max_results=arguments.get("max_results", 10),
            )
            if not results:
                text = f"No emails found matching '{arguments['query']}'"
            else:
                lines = [f"Search results for '{arguments['query']}':\n"]
                for i, msg in enumerate(results, 1):
                    lines.append(
                        f"{i}. {msg['subject']}\n"
                        f"   From: {msg['from']} | Date: {msg['date']}\n"
                        f"   ID: {msg['id']}\n"
                    )
                text = "\n".join(lines)

        else:
            text = f"Unknown tool: {name}"

    except Exception as e:
        # Surface errors back to Claude rather than silently failing
        text = f"Error calling {name}: {type(e).__name__}: {e}"

    # MCP requires a list of content blocks — TextContent is the simplest
    return [types.TextContent(type="text", text=text)]


# ---------------------------------------------------------------------------
# Entry point — stdio transport means Claude talks to us via stdin/stdout
# ---------------------------------------------------------------------------
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())