# lambda_functions/store_lead_data.py
import json
from .leads_store import upsert_lead  # relative import because we're in the same folder

def _resp(code=200, body=None):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"  # handy if you curl or front it with API GW later
        },
        "body": json.dumps(body if body is not None else {"ok": True})
    }

def lambda_handler(event, context):
    """
    HTTP-style Lambda to store/update a lead (LOCAL JSON STORAGE for now).
    Body JSON fields:
      - email (str, required)
      - company_name OR companyName (str, required)
      - campaign_id OR campaignId (str, required)
      - status (str, optional; default: 'SENT')
      - note (str, optional; appended to history)
    """
    try:
        body_raw = event.get("body") or "{}"
        body = json.loads(body_raw) if isinstance(body_raw, str) else (body_raw or {})

        email = (body.get("email") or "").strip()
        company_name = (body.get("company_name") or body.get("companyName") or "").strip()
        campaign_id = (body.get("campaign_id") or body.get("campaignId") or "").strip()
        status = (body.get("status") or "SENT").strip()
        note = (body.get("note") or "").strip()

        if not (email and company_name and campaign_id):
            return _resp(400, {"error": "Missing required fields: email, company_name, campaign_id"})

        lead = upsert_lead(
            email=email,
            company_name=company_name,
            campaign_id=campaign_id,
            status=status,
            note=note
        )
        return _resp(200, {"ok": True, "lead": lead})

    except Exception as e:
        # Keep responses structured so API Gateway/Agent can handle them
        return _resp(500, {"error": str(e)})
