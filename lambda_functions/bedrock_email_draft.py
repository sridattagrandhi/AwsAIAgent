# lambda_functions/bedrock_email_draft.py
import os, json
import boto3

def _resp(code=200, body=None):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body if body is not None else {"ok": True})
    }

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        company  = body.get("companyName", "the company")
        desc     = body.get("description", "")
        website  = body.get("website", "")

        bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", "us-east-1"))
        model_id = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")

        # Nova Pro: no 'system' role and do NOT include "modelId" key inside the JSON body.
        prompt = (
            f"You are a concise outreach assistant. "
            f"Write a brief, friendly, personalized cold email to {company}. "
            f"Website: {website}. Description: {desc}. "
            f"One tailored hook, one clear yes/no CTA."
        )

        payload = {
            "messages": [
                {"role": "user", "content": [{"text": prompt}]}
            ],
            "inferenceConfig": {"maxTokens": 500, "temperature": 0.5, "topP": 0.9}
        }

        resp = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )
        data = json.loads(resp["body"].read())
        draft = data.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")

        return _resp(200, {"ok": True, "model": model_id, "draft": draft})
    except Exception as e:
        return _resp(500, {"error": str(e)})
