# /Users/joemarian/water-tank/main.py
# /Users/joemarian/water-tank/main.py
import os
import json
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any
from coap_server import coap_main
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# --- MODIFIED load_dotenv CALL ---
# Get the absolute path to the directory where main.py resides
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the .env file in the project root
dotenv_path = os.path.join(BASE_DIR, '.env')
# Explicitly load the .env file from the determined path
load_dotenv(dotenv_path=dotenv_path)
# --- END MODIFIED load_dotenv CALL ---

print(f"DEBUG: MONGO_URI from .env is: {os.getenv('MONGO_URI')}") # Keep this debug line

from app.routes import channels, data
from app.database import db

import paho.mqtt.client as mqtt

app = FastAPI(
    title="Water Tank Management",
    version="1.0.0"
)

# ... rest of your main.py ...

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(channels.router, prefix="/api/channels")
app.include_router(data.router, prefix="/api/data", tags=["Data"])

# --- MQTT Integration (using paho-mqtt) ---
mqtt_client: mqtt.Client = None
main_event_loop = None # New: Global variable to hold the main event loop

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")



def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print(f"Connected to MQTT Broker with result code {rc}")
        client.subscribe("tanks/+/data")
        print("Subscribed to MQTT topic: tanks/+/data successfully.")
    else:
        print(f"Failed to connect to MQTT Broker, return code {rc}")

def on_message(client, userdata, msg):
    print(f"Received MQTT message on topic '{msg.topic}': {msg.payload.decode()}")
    try:
        data_payload = json.loads(msg.payload.decode())
        topic_parts = msg.topic.split('/')
        if len(topic_parts) >= 2:
            channel_name = topic_parts[1]
            # IMPORTANT CHANGE: Use run_coroutine_threadsafe to submit to the main loop
            if main_event_loop and main_event_loop.is_running():
                asyncio.run_coroutine_threadsafe(save_mqtt_data(channel_name, data_payload), main_event_loop)
            else:
                print("Error: Main event loop not running or not available. Cannot process MQTT message.")
        else:
            print(f"Invalid MQTT topic format received: {msg.topic}")

    except json.JSONDecodeError:
        print(f"Error: Invalid JSON payload from topic '{msg.topic}': {msg.payload.decode()}")
    except Exception as e:
        print(f"Error processing MQTT message for topic '{msg.topic}': {e}")

async def save_mqtt_data(channel_name: str, data: Dict[str, Any]):
    if db.channels is None or db.data is None:
        print("Database connection not yet initialized. Skipping MQTT data save.")
        return

    channel = await db.channels.find_one({"channel_name": channel_name})
    if not channel:
        print(f"Channel '{channel_name}' not found. Please create the channel via API first. Skipping MQTT data save.")
        return

    allowed_fields = set(channel.get("fields", []))
    cleaned_data = {}
    for key, value in data.items():
        if key in allowed_fields:
            cleaned_data[key] = value
        else:
            print(f"Warning: Field '{key}' from MQTT not defined for channel '{channel_name}'. Skipping.")

    data_entry = {
        "_id": str(uuid.uuid4()),
        "tank_id": channel_name,
        "timestamp": datetime.utcnow(),
        **cleaned_data
    }
    await db.data.insert_one(data_entry)
    print(f"MQTT data saved successfully for channel '{channel_name}': {cleaned_data}")

@app.on_event("startup")
async def startup_event():
    print("Application startup event triggered.")
    await db.connect_to_mongodb()

    # New: Capture the main asyncio event loop here
    global main_event_loop
    main_event_loop = asyncio.get_event_loop()

    asyncio.create_task(coap_main())

    global mqtt_client
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    if MQTT_USERNAME and MQTT_PASSWORD:
        mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    try:
        print(f"Attempting to connect to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}...")
        mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        mqtt_client.loop_start()
        print("MQTT client started in background thread.")
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    print("Application shutdown event triggered.")
    await db.close_mongodb_connection()

    if mqtt_client:
        print("Stopping MQTT client loop and disconnecting...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("MQTT client disconnected.")

@app.get("/")
def read_root():
    file_path = os.path.join("app", "static", "dashboard.html")
    print(f"Looking for dashboard file at: {os.path.abspath(file_path)}")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Dashboard file not found.")
    

'''
# /Users/joemarian/water-tank/main.py
import os
import json
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv # Keep this import

load_dotenv() # Load environment variables from .env if running directly (or if passed via docker-compose)

# Remove the specific BASE_DIR and dotenv_path logic you added for debugging:
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# dotenv_path = os.path.join(BASE_DIR, '.env')
# load_dotenv(dotenv_path=dotenv_path)

print(f"DEBUG: MONGO_URI from .env/env var is: {os.getenv('MONGO_URI')}") # Keep this debug line for now

from app.routes import channels, data
from app.database import db

import paho.mqtt.client as mqtt

app = FastAPI(
    title="Water Tank Management",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(channels.router, prefix="/api/channels")
app.include_router(data.router, prefix="/api/data", tags=["Data"])

# --- MQTT Integration (using paho-mqtt) ---
mqtt_client: mqtt.Client = None
main_event_loop = None # Global variable to hold the main event loop

# IMPORTANT: These now use the service names as default if not explicitly set in .env or docker-compose
# However, for Docker Compose, they will be explicitly set in the docker-compose.yml
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mosquitto_broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

# ... rest of your main.py (on_connect, on_message, save_mqtt_data, startup_event, shutdown_event, read_root) ...

# The startup_event should use the MONGO_URI from os.getenv as before:
# @app.on_event("startup")
# async def startup_event():
#     print("Application startup event triggered.")
#     await db.connect_to_mongodb(mongo_uri=os.getenv("MONGO_URI")) # Ensure this still passes the URI
'''