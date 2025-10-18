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

def get_lead(email: str) -> Optional[Dict[str, Any]]:
    try:
        res = _table().get_item(Key={"pk": _pk(email)})
    except ClientError:
        return None
    item = res.get("Item")
    return item.get("data") if item else None

def upsert_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Stores the lead dict under attribute 'data' to keep a simple item shape."""
    now = int(time.time())
    email = (lead.get("email") or "").lower()
    if not email:
        raise ValueError("lead.email required")

    # merge minimal non-destructive fields with existing
    existing = get_lead(email)
    if existing:
        # preserve/merge company aliases if changed
        old_company = existing.get("company")
        new_company = lead.get("company") or old_company
        if old_company and new_company and new_company != old_company:
            aliases = set(existing.get("aliases", []))
            aliases.add(old_company)
            lead["aliases"] = sorted(list(aliases))

        # preserve existing campaigns if caller didn't provide them
        if "campaigns" not in lead and "campaigns" in existing:
            lead["campaigns"] = existing["campaigns"]

        # preserve profile/signals unless caller provided richer info
        if "profile" not in lead and "profile" in existing:
            lead["profile"] = existing["profile"]
        if "signals" not in lead and "signals" in existing:
            lead["signals"] = existing["signals"]

        # preserve prior scores if not provided
        if "fitScore" not in lead and "fitScore" in existing:
            lead["fitScore"] = existing["fitScore"]
        if "intentScore" not in lead and "intentScore" in existing:
            lead["intentScore"] = existing["intentScore"]

        # final company set
        lead["company"] = new_company

    item = {
        "pk": _pk(email),
        "email": email,
        "data": lead,          # canonical payload lives under 'data'
        "updatedAt": now,
    }
    _table().put_item(Item=item)
    return {"ok": True, "email": email, "updatedAt": now}

def update_status(email: str, campaign_id: str, status: Optional[str], reply_text: Optional[str]) -> Dict[str, Any]:
    """Read-modify-write against the 'data' payload for consistency."""
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

def update_send_metadata(email: str, campaign_id: str, message_id: str, sent_at: int):
    """
    Save SES MessageId + lastSentAt on the lead's campaign node within 'data'.
    """
    email = (email or "").lower()
    if not email:
        raise ValueError("email required")
    lead = get_lead(email) or {"email": email}
    lead.setdefault("campaigns", {})
    c = lead["campaigns"].setdefault(campaign_id, {})
    c["messageId"] = message_id
    c["lastSentAt"] = int(sent_at or time.time())
    c["updatedAt"] = int(time.time())
    upsert_lead(lead)
    return {"ok": True, "email": email, "campaignId": campaign_id, "messageId": message_id, "lastSentAt": c["lastSentAt"]}
