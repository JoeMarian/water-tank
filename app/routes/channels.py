from fastapi import APIRouter, HTTPException, Query, Body, status, Request # Added Request
from typing import List, Optional, Dict, Any
from app.database import db # Assuming your db connection is in database.py
import string
import random
import datetime # Ensure datetime is imported
from pydantic import BaseModel # Added: Import BaseModel from pydantic

router = APIRouter(tags=["channels"])

def generate_api_key(length=12):
    """Generates a random API key of specified length."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

class ChannelCreate(BaseModel):
    """Pydantic model for creating a new channel."""
    channel_name: str
    fields: List[str]
    initial_values: Optional[Dict[str, Any]] = None

class DataWrite(BaseModel):
    """Pydantic model for writing data to a channel.
    This model allows for dynamic fields based on the channel's configuration.
    """
    # The actual fields will be validated dynamically based on the channel's 'fields'
    # This model acts as a placeholder for the arbitrary data dictionary.
    data: Dict[str, Any]

@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create a new channel")
async def create_channel(channel: ChannelCreate):
    """
    Creates a new channel with a unique API key and defines its fields.
    If initial values are provided, they are inserted as the first data entry
    with a timestamp.
    """
    existing = await db.channels.find_one({"channel_name": channel.channel_name})
    if existing:
        raise HTTPException(status_code=400, detail="Channel already exists")

    api_key = generate_api_key()

    channel_doc = {
        "channel_name": channel.channel_name,
        "api_key": api_key,
        "fields": channel.fields
    }
    await db.channels.insert_one(channel_doc)

    # Insert initial values as the first data document with a timestamp
    data_to_insert = {
        "tank_id": channel.channel_name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
    }
    if channel.initial_values:
        # Filter initial_values to only include fields defined for the channel
        for field, value in channel.initial_values.items():
            if field in channel.fields:
                data_to_insert[field] = value
            else:
                print(f"Warning: Initial value for undefined field '{field}' ignored.")
    else:
        # If no initial_values, set all fields to "N/A"
        for field in channel.fields:
            data_to_insert[field] = "N/A"

    await db.data.insert_one(data_to_insert)

    return {
        "channel_name": channel.channel_name,
        "api_key": api_key,
        "fields": channel.fields
    }

@router.get("/", summary="List all channels")
async def list_channels():
    """Retrieves a list of all available channels."""
    channels = await db.channels.find().to_list(100)
    return [{"channel_name": c["channel_name"], "fields": c["fields"]} for c in channels]

@router.get("/{channel_name}", summary="Get channel details")
async def get_channel(channel_name: str, api_key: str = Query(..., description="API key for authentication")):
    """Retrieves details for a specific channel, including its API key and fields."""
    channel = await db.channels.find_one({"channel_name": channel_name})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if api_key != channel["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {
        "channel_name": channel["channel_name"],
        "api_key": channel["api_key"],
        "fields": channel["fields"]
    }

@router.post("/{channel_name}/data", status_code=status.HTTP_201_CREATED, summary="Write data to a channel (JSON Body)")
async def write_data(
    channel_name: str,
    api_key: str = Query(..., description="API key for authentication"),
    data: Dict[str, Any] = Body(..., description="Dictionary of field-value pairs to write")
):
    """
    Writes new data to a specific channel using a JSON request body.
    Each write creates a new historical record with a timestamp.
    Only fields defined for the channel will be stored.
    """
    channel = await db.channels.find_one({"channel_name": channel_name})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if api_key != channel["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Prepare the data document, including only valid fields
    data_doc = {
        "tank_id": channel_name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
    }
    channel_fields = set(channel.get("fields", []))

    valid_field_found = False
    for field, value in data.items():
        if field in channel_fields:
            # Attempt to convert to float if it looks like a number, otherwise store as is
            try:
                data_doc[field] = float(value)
            except (ValueError, TypeError): # Catch TypeError for non-string types as well
                data_doc[field] = value
            valid_field_found = True
        else:
            print(f"Warning: Field '{field}' not defined for channel '{channel_name}'. Ignoring.")

    if not valid_field_found:
        # If no valid fields were provided in the data, raise an error
        raise HTTPException(status_code=400, detail="No valid channel fields provided in data.")

    await db.data.insert_one(data_doc)
    return {"message": "Data written successfully (JSON Body)", "timestamp": data_doc["timestamp"]}


@router.get("/{channel_name}/update", status_code=status.HTTP_200_OK, summary="Write data to a channel (URL Query Params)")
async def update_channel_data_by_query_params(
    channel_name: str,
    request: Request # Inject the Request object to access query parameters dynamically
):
    """
    Writes new data to a specific channel using URL query parameters.
    Each write creates a new historical record with a timestamp.
    Only fields defined for the channel will be stored.
    Example: GET /api/channels/myChannel/update?api_key=XYZ123&temperature=25.5&humidity=60
    """
    api_key = request.query_params.get("api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required in query parameters.")

    channel = await db.channels.find_one({"channel_name": channel_name})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if api_key != channel["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid API key")

    data_to_insert = {
        "tank_id": channel_name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
    }
    channel_fields = set(channel.get("fields", []))
    found_valid_field = False

    # Iterate through all query parameters
    for field, value in request.query_params.items():
        if field == "api_key": # Skip the api_key itself
            continue
        if field in channel_fields:
            # Attempt to convert to float if it looks like a number
            try:
                data_to_insert[field] = float(value)
            except ValueError:
                data_to_insert[field] = value # Store as string if not a number
            found_valid_field = True
        else:
            print(f"Warning: Query parameter field '{field}' not defined for channel '{channel_name}'. Ignoring.")

    if not found_valid_field:
        raise HTTPException(status_code=400, detail="No valid channel fields provided in query parameters (excluding api_key).")

    await db.data.insert_one(data_to_insert)
    return {"message": "Data written successfully via query parameters", "timestamp": data_to_insert["timestamp"]}


@router.get("/{channel_name}/data", summary="Get historical data for a channel")
async def get_historical_data(
    channel_name: str,
    api_key: str = Query(..., description="API key for authentication"),
    field_name: Optional[str] = Query(None, description="Specific field to retrieve history for (e.g., 'temperature')"),
    start_time: Optional[datetime.datetime] = Query(None, description="Start timestamp for data history (ISO 8601 format)"),
    end_time: Optional[datetime.datetime] = Query(None, description="End timestamp for data history (ISO 8601 format)"),
    limit: int = Query(100, description="Maximum number of historical records to retrieve", ge=1, le=1000)
):
    """
    Retrieves historical data for a specified channel.
    Can filter by a specific field, time range, and limit the number of results.
    """
    channel = await db.channels.find_one({"channel_name": channel_name})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if api_key != channel["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid API key")

    query = {"tank_id": channel_name}
    if start_time or end_time:
        query["timestamp"] = {}
        if start_time:
            query["timestamp"]["$gte"] = start_time
        if end_time:
            query["timestamp"]["$lte"] = end_time

    projection = {"_id": 0, "timestamp": 1} # Always include timestamp
    if field_name:
        if field_name not in channel["fields"]:
            raise HTTPException(status_code=400, detail=f"Field '{field_name}' is not defined for channel '{channel_name}'")
        projection[field_name] = 1
    else:
        # If no specific field, include all defined fields
        for field in channel["fields"]:
            projection[field] = 1

    # Fetch data, sort by timestamp, and apply limit
    historical_data = await db.data.find(query, projection).sort("timestamp", 1).to_list(limit)

    # Convert datetime objects to ISO format strings for better JSON serialization
    for entry in historical_data:
        if isinstance(entry.get("timestamp"), datetime.datetime):
            entry["timestamp"] = entry["timestamp"].isoformat()

    return historical_data


@router.delete("/{channel_name}", summary="Delete channel and all its data")
async def delete_channel(channel_name: str, api_key: str = Query(..., description="API key for authentication")):
    """Deletes a channel and all associated historical data."""
    channel = await db.channels.find_one({"channel_name": channel_name})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if api_key != channel["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid API key")

    await db.channels.delete_one({"channel_name": channel_name})
    await db.data.delete_many({"tank_id": channel_name})

    return {"message": f"Channel '{channel_name}' and all related data deleted"}

@router.delete("/{channel_name}/fields/{field_name}", summary="Delete a field from channel and its data")
async def delete_field(channel_name: str, field_name: str, api_key: str = Query(..., description="API key for authentication")):
    """
    Deletes a field from a channel's definition and sets its value to 'N/A'
    in all existing historical data documents for that channel.
    """
    channel = await db.channels.find_one({"channel_name": channel_name})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if api_key != channel["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if field_name not in channel["fields"]:
        raise HTTPException(status_code=404, detail="Field not found in channel")

    # Remove field from channel fields array
    await db.channels.update_one(
        {"channel_name": channel_name},
        {"$pull": {"fields": field_name}}
    )

    # Set its value to "N/A" in all historical data docs
    await db.data.update_many(
        {"tank_id": channel_name},
        {"$set": {field_name: "N/A"}}
    )

    return {"message": f"Field '{field_name}' deleted from channel '{channel_name}' (set to 'N/A' in all data)"}

class ChannelUpdate(BaseModel):
    """Pydantic model for updating channel fields."""
    add_fields: Optional[List[str]] = []
    remove_fields: Optional[List[str]] = []

@router.patch("/{channel_name}", summary="Update channel fields")
async def update_channel_fields(
    channel_name: str,
    update: ChannelUpdate = Body(..., description="Fields to add or remove"),
    api_key: str = Query(..., description="API key for authentication")
):
    """
    Updates the fields associated with a channel.
    Can add new fields or remove existing ones. Removed fields will have their
    values set to 'N/A' in all historical data documents.
    """
    channel = await db.channels.find_one({"channel_name": channel_name})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if api_key != channel["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid API key")

    current_fields = set(channel.get("fields", []))

    # Add new fields if any (avoid duplicates)
    if update.add_fields:
        current_fields.update(update.add_fields)

    # Remove fields if any
    if update.remove_fields:
        current_fields.difference_update(update.remove_fields)
        # For removed fields, set value to "N/A" in all data docs
        for field in update.remove_fields:
            await db.data.update_many(
                {"tank_id": channel_name},
                {"$set": {field: "N/A"}}
            )

    # Update the channel document with new fields list
    await db.channels.update_one(
        {"channel_name": channel_name},
        {"$set": {"fields": list(current_fields)}}
    )

    return {"message": "Channel fields updated", "fields": list(current_fields)}