# cosmos_client.py
from config import cosmos_db
from models import TaskLedger, AEG
from datetime import datetime


# ─── Container references ──────────────────────────────────────────────────────
# Each of these matches a container you created in Cosmos DB on Day 1

ledgers   = cosmos_db.get_container_client("task_ledgers")
aeg_store = cosmos_db.get_container_client("aeg_state")
convs     = cosmos_db.get_container_client("conversations")
costs     = cosmos_db.get_container_client("cost_records")


# ─── Task Ledger operations ────────────────────────────────────────────────────

def save_task_ledger(ledger: TaskLedger):
    """Create or update a Task Ledger. Uses upsert so it works for both."""
    data = ledger.model_dump()
    data["id"] = ledger.project_id   # Cosmos requires an "id" field
    data["updated_at"] = datetime.utcnow().isoformat()
    ledgers.upsert_item(body=data)


def get_task_ledger(project_id: str) -> dict:
    """Fetch a Task Ledger by project ID. Raises error if not found."""
    return ledgers.read_item(
        item=project_id,
        partition_key=project_id
    )


def update_task_ledger_status(project_id: str, new_status: str):
    """Shortcut to update just the status field without rewriting everything."""
    ledger = get_task_ledger(project_id)
    ledger["status"] = new_status
    ledger["updated_at"] = datetime.utcnow().isoformat()
    ledgers.upsert_item(body=ledger)


# ─── AEG operations ────────────────────────────────────────────────────────────

def save_aeg(aeg: AEG):
    """Save or update an AEG. model_dump() handles nested Pydantic models."""
    data = aeg.model_dump()
    data["id"] = aeg.project_id     # Cosmos requires an "id" field
    aeg_store.upsert_item(body=data)


def get_aeg(project_id: str) -> dict:
    """Fetch an AEG by project ID."""
    return aeg_store.read_item(
        item=project_id,
        partition_key=project_id
    )


def update_aeg_status(project_id: str, new_status: str):
    """Update just the AEG status field."""
    aeg = get_aeg(project_id)
    aeg["status"] = new_status
    aeg_store.upsert_item(body=aeg)


# ─── Conversation operations ───────────────────────────────────────────────────

def save_conversation(project_id: str, history: list):
    """
    Save the full Director conversation history.
    history is a list of {"role": "user"/"assistant", "content": "..."} dicts.
    """
    convs.upsert_item({
        "id": project_id,
        "project_id": project_id,
        "history": history,
        "updated_at": datetime.utcnow().isoformat()
    })


def get_conversation(project_id: str) -> list:
    """
    Get conversation history. Returns empty list if project is new —
    this is expected behaviour on the first message.
    """
    try:
        doc = convs.read_item(item=project_id, partition_key=project_id)
        return doc.get("history", [])
    except Exception:
        return []   # New project — no history yet, this is fine
