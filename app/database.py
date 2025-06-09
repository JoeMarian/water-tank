# /Users/joemarian/water-tank/app/database.py
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    client: AsyncIOMotorClient = None
    db = None
    channels = None
    data = None

    async def connect_to_mongodb(self):
        MONGO_URI = os.getenv("MONGO_URI")
        if not MONGO_URI:
            raise ValueError("MONGO_URI environment variable not set.")
        print(f"Connecting to MongoDB with URI: {MONGO_URI}") # Added for better logging
        self.client = AsyncIOMotorClient(MONGO_URI)
        
        # --- CRITICAL CHANGE HERE ---
        # Get the database object directly from the client. It will use the database name
        # specified in the MONGO_URI (e.g., 'water_tank_db')
        self.db = self.client.get_default_database() 
        # Alternatively, if you want to hardcode it but match the URI:
        # self.db = self.client.get_database("water_tank_db") 
        # --- END CRITICAL CHANGE ---

        self.channels = self.db.channels
        self.data = self.db.data
        await self.db.command("ping") # Add this to test the connection immediately
        print("MongoDB connected successfully!")

    async def close_mongodb_connection(self):
        if self.client:
            print("Closing MongoDB connection...")
            self.client.close()
            print("MongoDB connection closed.")

db = Database()