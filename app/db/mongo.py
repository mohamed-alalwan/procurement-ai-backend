"""MongoDB connection and utilities."""

from motor.motor_asyncio import AsyncIOMotorClient


class MongoDB:
    """MongoDB connection manager."""
    
    def __init__(self, uri: str, database: str):
        """Initialize MongoDB connection."""
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[database]
    
    async def close(self):
        """Close the database connection."""
        self.client.close()
