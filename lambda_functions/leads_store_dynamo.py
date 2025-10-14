import os
import time
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

_TABLE = None

def _table():
    global _TABLE
    if _TABLE is not None:
        return _TABLE
    name = os.environ.get("LEADS_TABLE_NAME")
    if not name:
        raise RuntimeError("LEADS_TABLE_NAME env var not set")
    _TABLE = boto3.resource("dynamodb").Table(name)
    return _TABLE

def _pk(email: str) -> str:
    return f"LEAD#{email.lower()}"

def upsert_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    now = int(time.time())
    email = (lead.get("email") or "").lower()
    if not email:
        raise ValueError("lead.email required")
    item = {
        "pk": _pk(email),
        "email": email,
        "data": lead,
        "updatedAt": now,
    }
    _table().put_item(Item=item)
    return {"ok": True, "email": email, "updatedAt": now}

def get_lead(email: str) -> Optional[Dict[str, Any]]:
    try:
        res = _table().get_item(Key={"pk": _pk(email)})
    except ClientError:
        return None
    item = res.get("Item")
    return item.get("data") if item else None

def update_status(email: str, campaign_id: str, status: Optional[str], reply_text: Optional[str]) -> Dict[str, Any]:
    email = (email or "").lower()
    if not email:
        raise ValueError("email required")
    lead = get_lead(email) or {"email": email}
    lead.setdefault("campaigns", {})
    c = lead["campaigns"].setdefault(campaign_id, {})
    if status:
        c["status"] = status
    if reply_text:
        c["lastReply"] = reply_text
    c["updatedAt"] = int(time.time())
    upsert_lead(lead)
    return {"ok": True, "lead": lead}
