# lambda_functions/leads_store.py
import os, json, time, threading
from typing import Optional
from .constants import FOLLOWUP_DELAY_DAYS
from .log import jlog

DEFAULT_PATH = os.environ.get("LEADS_STORE_PATH") or "./_leads_store.json"
_lock = threading.Lock()

def _now() -> int:
    return int(time.time())

def _read(path: str = DEFAULT_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    with _lock:
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}

def _write(data: dict, path: str = DEFAULT_PATH) -> None:
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def _key(email: str, campaign_id: str) -> str:
    return f"LEAD#{email}::CAMPAIGN#{campaign_id}"

def _next_follow_up_for(status: str, now: int) -> Optional[int]:
    if status in ("SENT", "NEUTRAL"):
        return now + FOLLOWUP_DELAY_DAYS * 24 * 3600
    return None

def upsert_lead(*, email: str, company_name: str, campaign_id: str, status: str = "SENT", note: str = "") -> dict:
    data = _read()
    k = _key(email, campaign_id)
    now = _now()

    lead = data.get(k) or {
        "email": email,
        "companyName": company_name,
        "campaignId": campaign_id,
        "status": "NEW",
        "history": [],
        "createdAt": now
    }

    lead["companyName"] = company_name or lead.get("companyName", "")
    lead["status"] = status or lead.get("status", "SENT")
    lead["updatedAt"] = now
    lead["nextFollowUpAt"] = _next_follow_up_for(lead["status"], now)
    lead.setdefault("history", []).append({
        "ts": now,
        "action": "UPSERT",
        "status": lead["status"],
        "note": note
    })

    data[k] = lead
    _write(data)
    jlog(op="upsert_lead", email=email, campaignId=campaign_id, status=lead["status"], ok=True)
    return lead

def update_status(email: str, campaign_id: str, new_status: str, note: str = "") -> dict:
    data = _read()
    k = _key(email, campaign_id)
    if k not in data:
        jlog(op="update_status", email=email, campaignId=campaign_id, err="Lead not found")
        raise KeyError("Lead not found")

    now = _now()
    data[k]["status"] = (new_status or data[k]["status"]).upper()
    data[k]["updatedAt"] = now
    data[k]["nextFollowUpAt"] = _next_follow_up_for(data[k]["status"], now)
    data[k].setdefault("history", []).append({
        "ts": now,
        "action": "STATUS_UPDATE",
        "status": data[k]["status"],
        "note": note
    })
    _write(data)
    jlog(op="update_status", email=email, campaignId=campaign_id, status=data[k]["status"], ok=True)
    return data[k]

def get_lead(email: str, campaign_id: str) -> dict | None:
    return _read().get(_key(email, campaign_id))

def list_leads() -> list[dict]:
    return list(_read().values())
