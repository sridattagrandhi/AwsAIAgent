# lambda_functions/update_lead_status.py
import json
from .leads_store import update_status

def classify_reply_simple(reply_text: str) -> str:
    t = (reply_text or "").lower()
    if any(x in t for x in ["unsubscribe", "remove me", "stop emailing"]):
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
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body if body is not None else {"ok": True})
    }

def lambda_handler(event, context):
    """
    Body JSON:
      - email (required)
      - campaign_id or campaignId (required)
      - status (optional)  OR
      - replyText (optional) -> will be classified to a status if 'status' missing
    """
    try:
        body_raw = event.get("body") or "{}"
        body = json.loads(body_raw) if isinstance(body_raw, str) else (body_raw or {})

        email = (body.get("email") or "").strip()
        campaign_id = (body.get("campaign_id") or body.get("campaignId") or "").strip()
        status = (body.get("status") or "").strip()
        reply_text = body.get("replyText")  # optional note & classification source

        if not (email and campaign_id):
            return _resp(400, {"error": "Missing required: email, campaign_id"})

        if not status and reply_text:
            status = classify_reply_simple(reply_text)

        if not status:
            return _resp(400, {"error": "Provide either status or replyText"})

        lead = update_status(email, campaign_id, status, note=(reply_text or ""))
        return _resp(200, {"ok": True, "lead": lead})
    except KeyError:
        return _resp(404, {"error": "Lead not found"})
    except Exception as e:
        return _resp(500, {"error": str(e)})
