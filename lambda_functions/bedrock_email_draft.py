import json, os
from typing import Dict, Any

try:
    import boto3
except Exception:
    boto3 = None

def _resp(code: int, obj: Dict[str, Any]):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(obj)}

def _bedrock():
    if boto3 is None:
        return None
    region = os.environ.get("BEDROCK_REGION", "us-east-1")
    return boto3.client("bedrock-runtime", region_name=region)

MODEL_PRIMARY = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
MODEL_FALLBACK = os.getenv("BEDROCK_MODEL_ID_FALLBACK", "")  # optional, e.g., Claude Sonnet

SYSTEM = (
    "You are an expert B2B SDR. Write ONE concise cold email with a Subject line.\n"
    "Tone: friendly, direct, credible. No placeholders. 120–150 words."
)

def _messages(user_prompt: str):
    # Nova in your account expects only 'user'/'assistant'. No 'system' role.
    return {
        "messages": [
            {
                "role": "user",
                "content": [
                    { "text": f"{SYSTEM}\n\n{user_prompt}" }
                ]
            }
        ]
    }

def _invoke(model_id: str, payload: Dict[str, Any]):
    br = _bedrock()
    res = br.invoke_model(
        modelId=model_id,
        body=json.dumps(payload),
        contentType="application/json",
        accept="application/json",
    )
    out = json.loads(res["body"].read().decode("utf-8"))
    # Nova returns: {"output": {"message": {"content": [{"text": "..."}]}}}
    txt = (
        out.get("output", {})
           .get("message", {})
           .get("content", [{}])[0]
           .get("text", "")
    )
    return txt.strip() or json.dumps(out)

def lambda_handler(event, context):
    # read body
    body_raw = event.get("body") or "{}"
    if isinstance(body_raw, bytes):
        body_raw = body_raw.decode("utf-8", errors="replace")
    try:
        body = json.loads(body_raw)
    except Exception:
        return _resp(400, {"error": "Invalid JSON body"})

    company = body.get("companyName") or body.get("company") or ""
    website = body.get("website") or ""
    desc = body.get("description") or ""
    pain = body.get("painPoint") or "improving Shopify conversions and email capture"
    pitch = body.get("productPitch") or "AI agent that finds leads and personalizes outreach to increase qualified demos"

    if not company:
        return _resp(400, {"error": "companyName required"})

    user_prompt = (
        f"Company: {company}\nWebsite: {website}\nAbout: {desc}\n"
        f"Observed pain: {pain}\nOur product: {pitch}\n\n"
        "Write one email (subject + body). No fluff, no placeholders."
    )
    payload = _messages(user_prompt)

    try:
        draft = _invoke(MODEL_PRIMARY, payload)
    except Exception as e:
        if MODEL_FALLBACK:
            try:
                draft = _invoke(MODEL_FALLBACK, payload)
            except Exception as e2:
                return _resp(500, {"error": f"Bedrock calls failed: {e} / {e2}"})
        else:
            return _resp(500, {"error": f"Bedrock call failed: {e}"})

    return _resp(200, {"model": MODEL_PRIMARY, "draft": draft})
