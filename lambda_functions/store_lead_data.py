# lambda_functions/store_lead_data.py
import json
from constants import normalize_status           # <-- absolute import
from log import jlog                             # <-- absolute import
from leads_store_dynamo import upsert_lead as ddb_upsert_lead  # <-- absolute import

def _resp(code=200, body=None):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body if body is not None else {"ok": True}),
    }

def lambda_handler(event, context):
    try:
        body_raw = event.get("body") or "{}"
        if isinstance(body_raw, bytes):
            body_raw = body_raw.decode("utf-8", errors="replace")
        body = json.loads(body_raw) if isinstance(body_raw, str) else (body_raw or {})

        email = (body.get("email") or "").strip().lower()
        company_name = (body.get("company_name") or body.get("companyName") or "").strip()
        campaign_id = (body.get("campaign_id") or body.get("campaignId") or "").strip()
        status = normalize_status(body.get("status"), "SENT")
        note = (body.get("note") or "").strip()

        if not (email and company_name and campaign_id):
            jlog(op="store_lead", ok=False, err="missing_fields",
                 email=email, campaignId=campaign_id)
            return _resp(400, {"error": "Missing required fields: email, company_name, campaign_id"})

        lead = {
            "email": email,
            "company": company_name,
            "campaigns": {campaign_id: {"status": status, "note": note}}
        }

        result = ddb_upsert_lead(lead)
        jlog(op="store_lead", ok=True, email=email, campaignId=campaign_id, status=status)
        return _resp(200, {"ok": True, "lead": lead, "meta": result})

    except Exception as e:
        jlog(op="store_lead", ok=False, err=str(e))
        return _resp(500, {"error": str(e)})
