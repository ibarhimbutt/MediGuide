"""Azure Cosmos DB — store session and reported-answer records."""

import uuid
from datetime import datetime, timezone
from typing import Any, List, Dict

from azure.cosmos import CosmosClient
from config import Config

_container = None


def get_cosmos_container():
    """Return the Cosmos DB container client, or None if not configured."""
    global _container
    if _container is not None:
        return _container
    if not Config.COSMOSDB_ACCOUNT_URI or not Config.COSMOSDB_ACCOUNT_KEY:
        return None
    try:
        client = CosmosClient(
            Config.COSMOSDB_ACCOUNT_URI,
            credential=Config.COSMOSDB_ACCOUNT_KEY,
        )
        db = client.get_database_client(Config.COSMOSDB_DATABASE_NAME)
        _container = db.get_container_client(Config.COSMOSDB_CONTAINER_NAME)
        return _container
    except Exception:
        return None


def store_session_record(
    user_id: str,
    feature: str,
    payload: dict[str, Any],
) -> None:
    """Persist a session or reported-answer record. Silently no-op if Cosmos is unavailable."""
    if not user_id:
        return
    container = get_cosmos_container()
    if not container:
        return
    try:
        item = {
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "feature": feature,
            "payload": payload,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        container.upsert_item(item)
    except Exception:
        pass


def get_recent_sessions(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Return a list of the most recent records for this user, newest first."""
    container = get_cosmos_container()
    if not container or not user_id:
        return []

    try:
        query = (
            "SELECT TOP @limit c.id, c.feature, c.payload, c.createdAt "
            "FROM c WHERE c.userId = @userId ORDER BY c.createdAt DESC"
        )
        params = [
            {"name": "@userId", "value": user_id},
            {"name": "@limit", "value": limit},
        ]
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=False))
        return items
    except Exception:
        return []
