from app.database import db
import asyncio

async def fix_channel_names():
    result = await db.channels.update_many(
        {"channel_name": {"$exists": False}, "name": {"$exists": True}},
        {"$rename": {"name": "channel_name"}}
    )
    print(f"Renamed {result.modified_count} documents.")

asyncio.run(fix_channel_names())
