import requests
import random
import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
import os # Import os module to get environment variables

# --- Configuration ---
# Ensure your FastAPI server is running. If it's on localhost, use this URL.
# If you deploy it elsewhere, update this base URL.
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000/api")

# Channel details for 'tank2'
CHANNEL_NAME = "tank2"
API_KEY = "MEV7H0D0NNKK"

# Standard values for each field
# These are your "baseline" values
STANDARD_VALUES = {
    "temp": 25.0, # degrees Celsius
    "humidity": 60.0,    # percentage
    "level": 100.0,      # units (e.g., liters, percentage full)
    "ph": 7.0,           # pH scale
    "pressure": 1010.0,  # hPa or kPa
}

# Range for random deviation from the standard value (+/- 10)
DEVIATION_RANGE = 10.0

# Interval for sending data (in minutes)
SEND_INTERVAL_MINUTES = 1

def generate_random_value(field_name):
    """
    Generates a random value for a given field within +/- DEVIATION_RANGE
    from its standard value. Applies specific constraints for 'ph' and 'level'.
    """
    standard_val = STANDARD_VALUES.get(field_name)
    if standard_val is None:
        print(f"Warning: No standard value defined for field '{field_name}'. Skipping.")
        return None
    
    min_val = standard_val - DEVIATION_RANGE
    max_val = standard_val + DEVIATION_RANGE
    
    # Apply specific constraints for certain fields
    if field_name == "ph":
        # pH typically ranges from 0 to 14
        return round(random.uniform(max(0.0, min_val), min(14.0, max_val)), 2)
    elif field_name == "level":
        # Level should generally not go below zero
        return round(random.uniform(max(0.0, min_val), max_val), 2)
    else:
        # For other fields, generate a float and round to 2 decimal places
        return round(random.uniform(min_val, max_val), 2)

def send_data_to_channel():
    """
    Generates data for all defined fields, constructs the URL with query parameters,
    and sends an HTTP GET request to the FastAPI server.
    """
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{current_time}] Generating and sending data for channel '{CHANNEL_NAME}'...")
    
    data_to_send = {}
    for field in STANDARD_VALUES.keys():
        value = generate_random_value(field)
        if value is not None:
            data_to_send[field] = value
    
    # Construct the query parameters for the GET request
    query_params = f"api_key={API_KEY}"
    for field, value in data_to_send.items():
        # URL-encode field names and values to handle spaces or special characters
        query_params += f"&{requests.utils.quote(field)}={requests.utils.quote(str(value))}"
            
    # Construct the full URL for the update endpoint
    url = f"{FASTAPI_BASE_URL}/channels/{requests.utils.quote(CHANNEL_NAME)}/update?{query_params}"
    
    try:
        # Send the GET request
        response = requests.get(url)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        print(f"Data sent successfully! Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending data: {e}")
        if hasattr(response, 'text'): # Check if response object exists and has text attribute
            print(f"Server response content: {response.text}")

# --- Scheduler Setup ---
scheduler = BlockingScheduler()

# Schedule the 'send_data_to_channel' function to run every 10 minutes
scheduler.add_job(send_data_to_channel, 'interval', minutes=SEND_INTERVAL_MINUTES)

print(f"IoT Data Simulator started for channel '{CHANNEL_NAME}'.")
print(f"Data will be sent every {SEND_INTERVAL_MINUTES} minutes to {FASTAPI_BASE_URL}.")
print("Press Ctrl+C to stop the simulator.")

try:
    # Start the scheduler. This will block the main thread.
    scheduler.start()
except (KeyboardInterrupt, SystemExit):
    # Handle graceful shutdown on Ctrl+C or system exit
    print("\nSimulator stopped.")
