import asyncio
from zoho.mail_client import list_unread_emails

async def test():
    print("Fetching up to 5 unread emails...\n")
    emails = await list_unread_emails(max_results=5)

    if not emails:
        print("No unread emails found.")
        return

    for e in emails:
        print(f"  [{e['date']}] {e['subject']}")
        print(f"  From: {e['from']}")
        print()

asyncio.run(test())
