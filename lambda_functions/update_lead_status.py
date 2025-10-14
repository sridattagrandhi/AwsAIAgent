# lambda_functions/update_lead_status.py
import json
from .leads_store import update_status
from .constants import normalize_status
from .log import jlog
# at top of file
from lambda_functions.leads_store_dynamo import upsert_lead, update_status, get_lead


def classify_reply_simple(reply_text: str) -> str:
    t = (reply_text or "").lower()
    if any(x in t for x in ["unsubscribe", "remove me", "stop emailing", "opt out"]):
        return "UNSUBSCRIBE"
    if any(x in t for x in ["not interested", "no thanks", "not now", "decline"]):
        return "COLD"
    if any(x in t for x in ["interested", "let's talk", "schedule", "call", "demo", "book a time"]):
        return "WARM"
    if any(x in t for x in ["bounce", "undeliverable", "mail failure"]):
        return "BOUNCED"
    return "NEUTRAL"

def _resp(code=200, body=None):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body if body is not None else {"ok": True})
    }

def lambda_handler(event, context):
    try:
        body_raw = event.get("body") or "{}"
        if isinstance(body_raw, bytes):
            body_raw = body_raw.decode("utf-8", errors="replace")
        body = json.loads(body_raw) if isinstance(body_raw, str) else (body_raw or {})

        email = (body.get("email") or "").strip()
        campaign_id = (body.get("campaign_id") or body.get("campaignId") or "").strip()
        status = (body.get("status") or "").strip()
        reply_text = body.get("replyText")

        if not (email and campaign_id):
            jlog(op="update_lead_status", ok=False, err="missing_fields", email=email, campaignId=campaign_id)
            return _resp(400, {"error": "Missing required: email, campaign_id"})

        if not status and reply_text:
            status = classify_reply_simple(reply_text)

        status = normalize_status(status, "NEUTRAL")
        if not status:
            jlog(op="update_lead_status", ok=False, err="no_status_or_reply", email=email, campaignId=campaign_id)
            return _resp(400, {"error": "Provide either status or replyText"})

        lead = update_status(email, campaign_id, status, note=(reply_text or ""))
        jlog(op="update_lead_status", ok=True, email=email, campaignId=campaign_id, status=status)
        return _resp(200, {"ok": True, "lead": lead})

    except KeyError:
        jlog(op="update_lead_status", ok=False, err="lead_not_found", email=body.get("email"), campaignId=body.get("campaign_id"))
        return _resp(404, {"error": "Lead not found"})
    except Exception as e:
        jlog(op="update_lead_status", ok=False, err=str(e))
        return _resp(500, {"error": str(e)})
