# local_test_status_flow.py
import os, json
from lambda_functions.store_lead_data import lambda_handler as store
from lambda_functions.update_lead_status import lambda_handler as upd
from lambda_functions.leads_store import list_leads

# Persist locally here (so you can inspect the file)
os.environ["LEADS_STORE_PATH"] = "./_leads_store.json"

def invoke(func, payload):
    event = {"httpMethod": "POST", "body": json.dumps(payload)}
    resp = func(event, None)
    print(resp["statusCode"], resp["body"])
    return resp

print("\n-- 1) Create/Upsert lead (SENT) --")
invoke(store, {
    "email": "owner@acmeshoes.example",
    "company_name": "Acme Shoes",
    "campaign_id": "demo-001",
    "status": "SENT",
    "note": "Initial outreach"
})

print("\n-- 2) Update from replyText (classify -> WARM) --")
invoke(upd, {
    "email": "owner@acmeshoes.example",
    "campaign_id": "demo-001",
    "replyText": "Hi, I'm interested. Let's schedule a call."
})

print("\n-- 3) Explicit status change to COLD --")
invoke(upd, {
    "email": "owner@acmeshoes.example",
    "campaign_id": "demo-001",
    "status": "COLD",
    "replyText": "Not interested right now."
})

print("\n-- 4) Inspect all leads --")
print(json.dumps(list_leads(), indent=2))
