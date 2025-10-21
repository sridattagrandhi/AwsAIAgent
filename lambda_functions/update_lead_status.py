# lambda_functions/update_lead_status.py
import json, time
from decimal import Decimal
from leads_store_dynamo import update_status, get_lead, upsert_lead
from replies import classify_reply_simple
from log import jlog
from scoring import compute_campaign_score

def _json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def _resp(code=200, body=None):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body if body is not None else {"ok": True}, default=_json_default)
    }

def lambda_handler(event, context):
    try:
        raw = event.get("body") or "{}"
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        body = json.loads(raw) if isinstance(raw, str) else (raw or {})

        email = (body.get("email") or "").strip().lower()
        campaign_id = (body.get("campaign_id") or body.get("campaignId") or "").strip()
        status = (body.get("status") or "").strip()
        reply_text = body.get("replyText")

        if not (email and campaign_id):
            jlog(op="update_lead_status", ok=False, err="missing_fields", email=email, campaignId=campaign_id)
            return _resp(400, {"error": "Missing required: email, campaign_id"})

        # If status not provided but reply is, classify
        if not status and reply_text:
            status = classify_reply_simple(reply_text)

        if not status:
            jlog(op="update_lead_status", ok=False, err="no_status_or_reply", email=email, campaignId=campaign_id)
            return _resp(400, {"error": "Provide either status or replyText"})

        # Update base status
        res = update_status(email, campaign_id, status.upper(), reply_text or "")
        lead = res.get("lead") or get_lead(email) or {"email": email}

        # Adjust per-campaign score with penalties/boosts
        lead.setdefault("campaigns", {})
        c = lead["campaigns"].setdefault(campaign_id, {})
        fit = lead.get("fitScore", 0)
        intent = lead.get("intentScore", 0)

        penalties = 0
        if c.get("status") == "UNSUBSCRIBE": penalties += 50
        if c.get("status") == "COLD": penalties += 20
        if c.get("status") == "WARM": intent += 10  # slight boost for positive interest

        c["score"] = compute_campaign_score(fit, intent, penalties)
        c["updatedAt"] = int(time.time())
        upsert_lead(lead)

        jlog(op="update_lead_status", ok=True, email=email, campaignId=campaign_id, status=status)
        return _resp(200, {"ok": True, "lead": lead})
    except KeyError:
        return _resp(404, {"error": "Lead not found"})
    except Exception as e:
        jlog(op="update_lead_status", ok=False, err=str(e))
        return _resp(500, {"error": str(e)})
