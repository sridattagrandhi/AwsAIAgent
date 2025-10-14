import json, os
from typing import Dict, Any

try:
    import boto3
except Exception:
    boto3 = None

def _resp(code: int, obj: Dict[str, Any]):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(obj),
    }

def _bedrock():
    if boto3 is None:
        return None
    region = os.environ.get("BEDROCK_REGION", "us-east-1")
    return boto3.client("bedrock-runtime", region_name=region)

SYSTEM_PROMPT = (
    "You are an expert B2B SDR who writes short, specific cold emails. "
    "Tone: friendly, direct, credible. No fluff, no buzzwords. "
    "Use the company's context to craft 1 concise outreach email. "
    "Keep to 120-150 words. Include a subject line."
)

def _make_prompt(company_name: str, website: str, description: str, pain: str, product_pitch: str):
    return f"""
Company: {company_name}
Website: {website}
About: {description}
Observed pain: {pain}
Our product: {product_pitch}

Write one email (subject + body). Avoid placeholders like {{first_name}}.
"""

def lambda_handler(event, context):
    try:
        body_raw = event.get("body") or "{}"
        if isinstance(body_raw, bytes):
            body_raw = body_raw.decode("utf-8", errors="replace")
        body = json.loads(body_raw)
    except Exception:
        return _resp(400, {"error": "Invalid JSON body"})

    company_name = body.get("companyName") or body.get("company") or ""
    website = body.get("website") or ""
    description = body.get("description") or ""
    pain = body.get("painPoint") or "improving conversions and email capture on Shopify"
    product_pitch = body.get("productPitch") or "AI agent that finds leads and personalizes outreach to increase qualified demos"

    if not company_name:
        return _resp(400, {"error": "companyName required"})

    model_id = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")
    br = _bedrock()
    if br is None:
        draft = f"Subject: Idea for {company_name}\n\nHi team at {company_name}, ..."
        return _resp(200, {"model": "fallback", "draft": draft})

    prompt = _make_prompt(company_name, website, description, pain, product_pitch)

    try:
        payload = {
            "inputText": f"{SYSTEM_PROMPT}\n\n{prompt}",
        }
        res = br.invoke_model(
            modelId=model_id,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
        out = json.loads(res.get("body").read().decode("utf-8"))
        draft = out.get("outputText") or out.get("generation") or json.dumps(out)
        return _resp(200, {"model": model_id, "draft": draft})
    except Exception as e:
        return _resp(500, {"error": f"Bedrock call failed: {e}"})
