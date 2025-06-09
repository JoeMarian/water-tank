# /Users/joemarian/water-tank/coap_simulation_client.py
import asyncio
import aiocoap
import json
import logging
import time
from urllib.parse import urlencode

# Configure logging for the client
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CoAPClientSimulator")

# --- CoAP Server Target Configuration ---
# When running locally (outside Docker Compose), the CoAP server is at localhost:5684
COAP_SERVER_HOST = "localhost"
COAP_SERVER_PORT = 5684
# ----------------------------------------

async def send_coap_post(channel_name: str, api_key: str, data_payload: dict):
    """Sends a CoAP POST request to the server with data."""
    protocol = await aiocoap.Context.create_client_context()
    
    # Construct the URI for data POST, including API key as a query parameter
    uri = f"coap://{COAP_SERVER_HOST}:{COAP_SERVER_PORT}/data/{channel_name}?api_key={api_key}"
    payload_bytes = json.dumps(data_payload).encode('utf-8')

    request = aiocoap.Message(
        code=aiocoap.Code.POST,
        uri=uri,
        content_format=aiocoap.ContentFormat.JSON,
        payload=payload_bytes
    )

    logger.info(f"Sending CoAP POST request to: {uri}")
    logger.info(f"Payload: {data_payload}")

    try:
        response = await protocol.request(request).response
        logger.info(f"CoAP POST Response Code: {response.code}")
        logger.info(f"CoAP POST Response Payload: {response.payload.decode('utf-8')}")
    except Exception as e:
        logger.error(f"Failed to send CoAP POST request: {e}")
    finally:
        await protocol.shutdown()

async def send_coap_get(channel_name: str, api_key: str, query_params: dict = None):
    """
    Sends a CoAP GET request to the server, typically for status updates or requests.
    Query parameters are included in the URL.
    """
    protocol = await aiocoap.Context.create_client_context()
    
    # Combine API key with any other query parameters provided
    full_query_params = {"api_key": api_key}
    if query_params:
        full_query_params.update(query_params)
        
    encoded_params = urlencode(full_query_params)
    
    # Construct the URI for GET request, including API key and other params
    uri = f"coap://{COAP_SERVER_HOST}:{COAP_SERVER_PORT}/update/{channel_name}?{encoded_params}"

    request = aiocoap.Message(
        code=aiocoap.Code.GET,
        uri=uri
    )

    logger.info(f"Sending CoAP GET request to: {uri}")

    try:
        response = await protocol.request(request).response
        logger.info(f"CoAP GET Response Code: {response.code}")
        logger.info(f"CoAP GET Response Payload: {response.payload.decode('utf-8')}")
    except Exception as e:
        logger.error(f"Failed to send CoAP GET request: {e}")
    finally:
        await protocol.shutdown()

async def main():
    # --- IMPORTANT: Configure your channel details here for local testing ---
    # These MUST match a channel you have already created via http://localhost:8000/docs
    YOUR_CHANNEL_NAME = "tank3"  # <<-- REPLACE WITH YOUR ACTUAL CHANNEL NAME
    YOUR_API_KEY = "XWHX1ZJA6Q8F"  # <<-- REPLACE WITH YOUR ACTUAL API KEY
    # ----------------------------------------------------------------------

    if YOUR_CHANNEL_NAME == "my_water_tank" or YOUR_API_KEY == "YOUR_API_KEY_HERE":
        logger.warning("ATTENTION: Please update 'YOUR_CHANNEL_NAME' and 'YOUR_API_KEY' in coap_simulation_client.py with your actual channel details.")
        logger.warning("You must create a channel first via http://localhost:8000/docs to get these values.")
        # You can add an exit here if you want to force the user to update details
        # return

    logger.info(f"Starting CoAP client simulation for channel '{YOUR_CHANNEL_NAME}'...")
    logger.info("Ensure your FastAPI app and CoAP server are running locally.")

    # Give the server components a moment to fully start up if just launched
    # This sleep is more crucial for Docker Compose startup, but can help locally too.
    # For manual runs, you might reduce or remove it if you start servers manually first.
    logger.info("Waiting 5 seconds before sending requests...")
    await asyncio.sleep(5) 

    # --- Simulate sending POST data ---
    logger.info("\n--- Sending first POST request (level, temperature, humidity) ---")
    data_payload_1 = {"level": 75.2, "temperature": 22.5, "humidity": 58.0}
    await send_coap_post(YOUR_CHANNEL_NAME, YOUR_API_KEY, data_payload_1)
    await asyncio.sleep(3) # Short delay

    logger.info("\n--- Sending second POST request (just level, simulating update) ---")
    data_payload_2 = {"level": 76.8}
    await send_coap_post(YOUR_CHANNEL_NAME, YOUR_API_KEY, data_payload_2)
    await asyncio.sleep(3) # Short delay

    # --- Simulate sending GET request (for status/update) ---
    logger.info("\n--- Sending GET request (client status update) ---")
    get_params = {"status": "online", "battery_level": "80%"}
    await send_coap_get(YOUR_CHANNEL_NAME, YOUR_API_KEY, get_params)
    await asyncio.sleep(3)

    logger.info("\nCoAP client simulation completed for this run.")

if __name__ == "__main__":
    asyncio.run(main())