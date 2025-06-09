from app.database import db
import asyncio

async def check_channels():
    missing_name = await db.channels.find({"channel_name": {"$exists": False}}).to_list(10)
    missing_fields = await db.channels.find({"fields": {"$exists": False}}).to_list(10)

    print("Documents missing channel_name:", missing_name)
    print("Documents missing fields:", missing_fields)

asyncio.run(check_channels())
