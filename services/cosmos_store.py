"""Azure Cosmos DB — store session and reported-answer records."""

import uuid
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional

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


def get_medication_history(user_id: str, limit: int = 10) -> List[str]:
    """Return medication inputs from medication-safety records for this user."""
    items = get_recent_sessions(user_id, limit=limit * 3)  # fetch extra to filter
    meds = []
    seen = set()
    for item in items:
        if item.get("feature") != "medication-safety":
            continue
        payload = item.get("payload") or {}
        raw = (payload.get("medicationInput") or "").strip()
        if raw and raw.lower() not in seen:
            seen.add(raw.lower())
            meds.append(raw)
        if len(meds) >= limit:
            break
    return meds


def get_timeline_interactions(
    user_id: str,
    limit: int = 100,
    since_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Return interactions for timeline, optionally filtered by date. Newest first."""
    container = get_cosmos_container()
    if not container or not user_id:
        return []

    try:
        if since_days is not None:
            # Cosmos SQL: date filter (createdAt >= cutoff)
            from datetime import datetime, timezone, timedelta
            cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
            query = (
                "SELECT TOP @limit c.id, c.feature, c.payload, c.createdAt "
                "FROM c WHERE c.userId = @userId AND c.createdAt >= @cutoff "
                "ORDER BY c.createdAt DESC"
            )
            params = [
                {"name": "@userId", "value": user_id},
                {"name": "@limit", "value": limit},
                {"name": "@cutoff", "value": cutoff},
            ]
        else:
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


def get_user_preference(user_id: str, key: str) -> Optional[Any]:
    """Get a user preference value. Returns None if not found."""
    if not user_id or not key:
        return None
    container = get_cosmos_container()
    if not container:
        return None
    try:
        query = "SELECT TOP 1 c.id, c.payload FROM c WHERE c.userId = @userId AND c.feature = 'user-preference'"
        params = [{"name": "@userId", "value": user_id}]
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        if items and items[0].get("payload"):
            return items[0]["payload"].get(key)
    except Exception:
        pass
    return None


def set_user_preference(user_id: str, key: str, value: Any) -> None:
    """Set a user preference. Creates or updates the prefs document."""
    if not user_id or not key:
        return
    container = get_cosmos_container()
    if not container:
        return
    try:
        prefs = {}
        items = []
        try:
            query = "SELECT TOP 1 c.id, c.payload FROM c WHERE c.userId = @userId AND c.feature = 'user-preference'"
            params = [{"name": "@userId", "value": user_id}]
            items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
            if items:
                prefs = items[0].get("payload") or {}
        except Exception:
            pass
        prefs[key] = value
        item = {
            "id": items[0]["id"] if items and items[0].get("id") else str(uuid.uuid4()),
            "userId": user_id,
            "feature": "user-preference",
            "payload": prefs,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        container.upsert_item(item)
    except Exception:
        pass
