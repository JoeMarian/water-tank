# coap_server.py
import asyncio
import json
import datetime
from aiocoap import Context, Message, PUT, GET, Code
from aiocoap.resource import Resource, Site # Corrected import for Resource and Site
from aiocoap.numbers import ContentFormat

# Assuming your db connection and models are accessible
# You might need to adjust the import path based on your project structure
# The 'db' object is an instance of your Database class, which will be connected
# by FastAPI's startup event in main.py
from app.database import db

class ChannelDataResource(Resource):
    """
    CoAP Resource for putting data to a specific channel (similar to POST /channels/{channel_name}/data).
    Path: /channels/{channel_name}/data
    Method: PUT
    Payload: JSON (e.g., {"temperature": 25.5, "humidity": 60})
    """
    def __init__(self, db_instance):
        super().__init__()
        self.db = db_instance

    async def render_put(self, request):
        # uri_path is a tuple like ('channels', 'channel_name', 'data')
        # We need the second element, which is the channel_name
        if len(request.opt.uri_path) < 2:
            return Message(code=Code.BAD_REQUEST, payload=b"Invalid URI path for data put.")
        channel_name = request.opt.uri_path[1]

        # 1. Extract API Key (e.g., from query parameter)
        query_params = {}
        for param in request.opt.uri_query:
            if '=' in param:
                k, v = param.split('=', 1)
                query_params[k] = v
            else:
                query_params[param] = "" # Handle params without values
        api_key = query_params.get("api_key")

        if not api_key:
            return Message(code=Code.BAD_REQUEST, payload=b"API key is required in query parameters (e.g., ?api_key=YOUR_KEY).")

        # 2. Authenticate and Validate Channel
        channel = await self.db.channels.find_one({"channel_name": channel_name})
        if not channel:
            return Message(code=Code.NOT_FOUND, payload=b"Channel not found.")
        if api_key != channel["api_key"]:
            return Message(code=Code.UNAUTHORIZED, payload=b"Invalid API key.")

        # 3. Parse Payload
        if not request.payload:
            return Message(code=Code.BAD_REQUEST, payload=b"Empty payload.")

        try:
            payload_str = request.payload.decode('utf-8')
            data_payload = json.loads(payload_str)
        except json.JSONDecodeError:
            return Message(code=Code.BAD_REQUEST, payload=b"Invalid JSON payload.")
        except UnicodeDecodeError:
            return Message(code=Code.BAD_REQUEST, payload=b"Invalid payload encoding.")

        # 4. Prepare and Insert Data (similar to FastAPI's write_data logic)
        data_doc = {
            "tank_id": channel_name,
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        }
        channel_fields = set(channel.get("fields", []))
        valid_field_found = False

        for field, value in data_payload.items():
            if field in channel_fields:
                try:
                    # Attempt to convert to float if possible, otherwise keep as is
                    data_doc[field] = float(value)
                except (ValueError, TypeError):
                    data_doc[field] = value
                valid_field_found = True
            else:
                print(f"Warning: Field '{field}' from CoAP not defined for channel '{channel_name}'. Ignoring.")

        if not valid_field_found:
            return Message(code=Code.BAD_REQUEST, payload=b"No valid channel fields provided in data that match channel configuration.")

        await self.db.data.insert_one(data_doc)

        response_payload = json.dumps({
            "message": "Data written successfully via CoAP",
            "timestamp": data_doc["timestamp"].isoformat()
        }).encode('utf-8')
        return Message(code=Code.CREATED, payload=response_payload, content_format=ContentFormat.JSON)


class ChannelLatestDataResource(Resource):
    """
    CoAP Resource for getting the latest data for a specific channel
    (similar to GET /data/{channel_name}/latest).
    Path: /channels/{channel_name}/latest
    Method: GET
    """
    def __init__(self, db_instance):
        super().__init__()
        self.db = db_instance

    async def render_get(self, request):
        if len(request.opt.uri_path) < 2:
            return Message(code=Code.BAD_REQUEST, payload=b"Invalid URI path for latest data get.")
        channel_name = request.opt.uri_path[1]

        query_params = {}
        for param in request.opt.uri_query:
            if '=' in param:
                k, v = param.split('=', 1)
                query_params[k] = v
            else:
                query_params[param] = ""
        api_key = query_params.get("api_key")

        if not api_key:
            return Message(code=Code.BAD_REQUEST, payload=b"API key is required.")

        channel = await self.db.channels.find_one({"channel_name": channel_name})
        if not channel:
            return Message(code=Code.NOT_FOUND, payload=b"Channel not found.")
        if api_key != channel["api_key"]:
            return Message(code=Code.UNAUTHORIZED, payload=b"Invalid API key.")

        data = await self.db.data.find({"tank_id": channel_name}).sort("timestamp", -1).to_list(length=1)

        if not data:
            return Message(code=Code.NOT_FOUND, payload=b"No data found for this channel.")

        latest_entry = data[0]
        # Clean up _id for JSON serialization and format timestamp
        if "_id" in latest_entry:
            del latest_entry["_id"]
        if isinstance(latest_entry.get("timestamp"), datetime.datetime):
            latest_entry["timestamp"] = latest_entry["timestamp"].isoformat()

        response_payload = json.dumps(latest_entry).encode('utf-8')
        return Message(code=Code.CONTENT, payload=response_payload, content_format=ContentFormat.JSON)

class ChannelLatestFieldResource(Resource):
    """
    CoAP Resource for getting a specific field's latest value for a channel
    (similar to GET /data/{channel_name}/latest/{field_name}).
    Path: /channels/{channel_name}/latest/{field_name}
    Method: GET
    """
    def __init__(self, db_instance):
        super().__init__()
        self.db = db_instance

    async def render_get(self, request):
        if len(request.opt.uri_path) < 3:
            return Message(code=Code.BAD_REQUEST, payload=b"Invalid URI path for field data get.")
        channel_name = request.opt.uri_path[1]
        field_name = request.opt.uri_path[2]

        query_params = {}
        for param in request.opt.uri_query:
            if '=' in param:
                k, v = param.split('=', 1)
                query_params[k] = v
            else:
                query_params[param] = ""
        api_key = query_params.get("api_key")

        if not api_key:
            return Message(code=Code.BAD_REQUEST, payload=b"API key is required.")

        channel = await self.db.channels.find_one({"channel_name": channel_name})
        if not channel:
            return Message(code=Code.NOT_FOUND, payload=b"Channel not found.")
        if api_key != channel["api_key"]:
            return Message(code=Code.UNAUTHORIZED, payload=b"Invalid API key.")

        if field_name not in channel["fields"]:
            return Message(code=Code.BAD_REQUEST, payload=f"Field '{field_name}' is not defined for channel '{channel_name}'.".encode('utf-8'))

        data = await self.db.data.find({"tank_id": channel_name}).sort("timestamp", -1).to_list(length=1)

        if not data or field_name not in data[0]:
            return Message(code=Code.NOT_FOUND, payload=f"Field '{field_name}' data not found for this channel.".encode('utf-8'))

        response_data = {
            "channel_name": channel_name,
            "field": field_name,
            "value": data[0][field_name],
            "timestamp": data[0]["timestamp"].isoformat() if isinstance(data[0].get("timestamp"), datetime.datetime) else data[0].get("timestamp")
        }
        response_payload = json.dumps(response_data).encode('utf-8')
        return Message(code=Code.CONTENT, payload=response_payload, content_format=ContentFormat.JSON)

async def coap_main():
    """
    Main function to run the CoAP server.
    """
    # 1. Create a Site object to hold your resources
    root_resource = Site()

    # 2. Add resources to the root_resource (Site instance)
    # The first argument to add_resource is the path pattern as a tuple of segments
    # The second argument is the resource instance
    root_resource.add_resource(
        ('channels', '{channel_name}', 'data'), # Path: /channels/{channel_name}/data
        ChannelDataResource(db)
    )
    root_resource.add_resource(
        ('channels', '{channel_name}', 'latest'), # Path: /channels/{channel_name}/latest
        ChannelLatestDataResource(db)
    )
    root_resource.add_resource(
        ('channels', '{channel_name}', 'latest', '{field_name}'), # Path: /channels/{channel_name}/latest/{field_name}
        ChannelLatestFieldResource(db)
    )

    # 3. Create the CoAP server context, passing the root_resource as the 'site' argument
    # And continue to explicitly bind to ('0.0.0.0', 5683) for listening on all interfaces
    context = await Context.create_server_context(root_resource, bind=('0.0.0.0', 5683))

    print("CoAP server started on UDP port 5683.")
    try:
        # The CoAP server runs indefinitely until cancelled
        await asyncio.get_event_loop().create_future()
    except asyncio.CancelledError:
        print("CoAP server shutting down.")
    finally:
        await context.shutdown()

if __name__ == "__main__":
    # This block is for testing coap_server.py independently.
    # In your main application, it will be called by asyncio.create_task.
    async def run_test_server():
        # You'll need to manually connect to the database if running standalone
        # This part assumes a local MongoDB instance. Adjust as per your setup.
        from app.database import db as global_db
        try:
            await global_db.connect_to_mongodb()
            await coap_main()
        except Exception as e:
            print(f"Error running standalone CoAP server: {e}")
        finally:
            await global_db.close_mongodb_connection()


    try:
        asyncio.run(run_test_server())
    except KeyboardInterrupt:
        print("CoAP server stopped by user.")
    except Exception as e:
        print(f"An error occurred during standalone CoAP server execution: {e}")