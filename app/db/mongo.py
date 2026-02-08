from pymongo import MongoClient
from typing import Any, Dict, List, Optional

from app.core.config import settings


_mongoClient: Optional[MongoClient] = None


def getMongoClient() -> MongoClient:
    global _mongoClient

    # Important: create one client and reuse it (connection pooling).
    
    if not _mongoClient:
        _mongoClient = MongoClient(settings.mongodbUri)

    return _mongoClient


def getCollection():
    client = getMongoClient()

    db = client[settings.mongodbDb]

    collection = db[settings.mongodbCollection]

    return collection


def runAggregation(pipeline: List[Dict[str, Any]], limit: int = 30) -> List[Dict[str, Any]]:
    collection = getCollection()

    # Important: allowDiskUse helps when aggregations are heavy.
    
    results = list(collection.aggregate(pipeline, allowDiskUse=True))

    # Note: BSON types may appear depending on dataset (ObjectId, datetime).
    # We'll handle JSON serialization later in utils if needed.

    return results
