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
        company = body.get("companyName", "the company")
        desc = body.get("description", "")
        website = body.get("website", "")
        recipient_email = body.get("recipientEmail", "")
        sender_name = body.get("senderName", "Raghav")
        sender_company = body.get("senderCompany", "AI Sales Solutions")
        sender_email = body.get("senderEmail", "raghav.dewangan2004@gmail.com")

        # Extract recipient name from email (first part before @)
        recipient_name = recipient_email.split("@")[0].replace(".", " ").title() if recipient_email else "there"

        bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", "us-east-1"))
        model_id = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")

        # Enhanced prompt with real names and details
        prompt = (
            f"Write a personalized B2B sales email from {sender_name} at {sender_company} to {recipient_name} at {company}. "
            f"Company website: {website}. Company info: {desc}. "
            f"Requirements: "
            f"1. Address {recipient_name} by name (not 'Hi there' or placeholders) "
            f"2. Reference something specific about {company} or their website "
            f"3. Sign with {sender_name}'s real details "
            f"4. Include a clear, specific call-to-action "
            f"5. Keep it under 150 words "
            f"6. Professional but friendly tone "
            f"7. No placeholder text like [Your Name] or [Recipient Name] "
            f"Sender details: {sender_name}, {sender_company}, {sender_email}"
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
