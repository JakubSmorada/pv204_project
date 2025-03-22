from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()


class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    db = None

    def connect_to_mongo(self):
        # Get connection details from environment variables
        mongodb_url = os.getenv("MONGODB_URL")
        db_name = os.getenv("DB_NAME")

        if not mongodb_url:
            raise ValueError("MONGODB_URL environment variable is not set")
        if not db_name:
            raise ValueError("DB_NAME environment variable is not set")

        # Validate environment variables
        if not mongodb_url:
            raise ValueError("MONGODB_URL environment variable is not set")
        if not db_name:
            raise ValueError("MONGODB_DB_NAME environment variable is not set")

        # Set up connection
        self.client = AsyncIOMotorClient(mongodb_url)
        self.db = self.client[db_name]
        print("Connected to MongoDB!")
        return self.db

    def close_mongo_connection(self):
        if self.client:
            self.client.close()
            print("MongoDB connection closed")


# Create a database instance
mongodb = MongoDB()