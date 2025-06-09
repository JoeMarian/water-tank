from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChannelCreate(BaseModel):
    """
    Pydantic model for creating a new channel.
    Includes fields and optional initial values.
    """
    channel_name: str
    fields: List[str]
    initial_values: Optional[Dict[str, Any]] = None

class ChannelOut(BaseModel):
    """
    Pydantic model for the output of a created or retrieved channel.
    """
    channel_name: str
    api_key: str
    fields: List[str]

# The DataEntry model with fixed fields is removed
# as the system now supports dynamic fields for data points.
# Data is ingested as Dict[str, Any] via the /channels/{channel_name}/data endpoint.
