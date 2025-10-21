# local_test_store_lead.py
import os, json, sys
sys.path.append('lambda_functions')
from store_lead_data import lambda_handler

# Optional: pick a custom local file to persist leads
os.environ["LEADS_STORE_PATH"] = "./_leads_store.json"

def invoke(payload: dict):
    event = {"httpMethod": "POST", "body": json.dumps(payload)}
    resp = lambda_handler(event, None)
    print(resp["statusCode"], resp["body"])
    return resp

# 1) Upsert a lead (SENT)
invoke({
    "email": "owner@acmeshoes.example",
    "company_name": "Acme Shoes",
    "campaign_id": "demo-001",
    "status": "SENT",
    "note": "Initial outreach"
})

# 2) Upsert same lead with a different note/status (simulates a follow-up)
invoke({
    "email": "owner@acmeshoes.example",
    "company_name": "Acme Shoes",
    "campaign_id": "demo-001",
    "status": "SENT",
    "note": "Follow-up #1 scheduled"
})
