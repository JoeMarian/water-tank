from fastapi import APIRouter, HTTPException, Query
from app.database import db
import datetime

router = APIRouter(tags=["data"])

@router.get("/{channel_name}/latest", summary="Get latest data for a channel")
async def get_latest_data(channel_name: str, api_key: str = Query(..., description="API key for authentication")):
    """
    Retrieves the most recent data entry for a specific channel.
    This fetches the single latest record from the historical data.
    """
    channel = await db.channels.find_one({"channel_name": channel_name})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if api_key != channel["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Fetch the latest data entry based on timestamp
    # We sort by timestamp in descending order and take the first one
    data = await db.data.find({"tank_id": channel_name}).sort("timestamp", -1).to_list(length=1)

    if not data:
        raise HTTPException(status_code=404, detail="No data found for this channel.")

    latest_entry = data[0]
    # Convert ObjectId to str for JSON serialization (if it exists)
    if "_id" in latest_entry:
        latest_entry["_id"] = str(latest_entry["_id"])
    # Convert datetime object to ISO format string for consistency
    if isinstance(latest_entry.get("timestamp"), datetime.datetime):
        latest_entry["timestamp"] = latest_entry["timestamp"].isoformat()

    return latest_entry

@router.get("/{channel_name}/latest/{field_name}", summary="Get specific field value from latest data")
async def get_field_value(
    channel_name: str,
    field_name: str,
    api_key: str = Query(..., description="API key for authentication")
):
    """
    Retrieves the value of a specific field from the most recent data entry for a channel.
    """
    channel = await db.channels.find_one({"channel_name": channel_name})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if api_key != channel["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if field_name not in channel["fields"]:
        raise HTTPException(status_code=400, detail=f"Field '{field_name}' is not defined for channel '{channel_name}'")

    # Fetch the latest data entry
    data = await db.data.find({"tank_id": channel_name}).sort("timestamp", -1).to_list(length=1)

    if not data or field_name not in data[0]:
        raise HTTPException(status_code=404, detail=f"Field '{field_name}' data not found for this channel.")

    return {
        "channel_name": channel_name,
        "field": field_name,
        "value": data[0][field_name],
        "timestamp": data[0]["timestamp"].isoformat() if isinstance(data[0].get("timestamp"), datetime.datetime) else data[0].get("timestamp")
    }

# Removed:
# @router.post("/{tank_id}", status_code=201) - Replaced by POST /channels/{channel_name}/data in channels.py
# @router.patch("/{tank_id}", summary="Update fields in latest data") - Modifying historical data directly is not desired for a time-series system.
# DataEntry BaseModel - No longer needed as data fields are dynamic based on channel definition.
