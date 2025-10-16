# lambda_functions/ses_inbound_parser.py
import boto3, json, email
from email import policy
from leads_store_dynamo import update_status
from log import jlog

s3 = boto3.client("s3")

def extract_body(msg):
    """Extract plain text body from MIME message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_content().strip()
    return msg.get_body(preferencelist=('plain', 'html')).get_content().strip()

def classify_reply_simple(t: str) -> str:
    t = (t or "").lower()
    unsub = ["unsubscribe", "remove me", "stop emailing", "opt out"]
    negative = ["not interested", "no thanks", "decline", "already have"]
    positive = ["interested", "let's talk", "schedule", "book", "demo", "call"]
    bounce = ["undeliverable", "mail failure", "bounced"]
    if any(x in t for x in bounce): return "BOUNCED"
    if any(x in t for x in unsub): return "UNSUBSCRIBE"
    if any(x in t for x in positive): return "WARM"
    if any(x in t for x in negative): return "COLD"
    return "NEUTRAL"

def lambda_handler(event, context):
    for rec in event.get("Records", []):
        try:
            bucket = rec["s3"]["bucket"]["name"]
            key = rec["s3"]["object"]["key"]
            obj = s3.get_object(Bucket=bucket, Key=key)
            raw = obj["Body"].read()
            msg = email.message_from_bytes(raw, policy=policy.default)

            from_addr = (msg["From"] or "").lower()
            subj = msg["Subject"] or ""
            body = extract_body(msg)

            # Basic mapping: subject tag [CID:demo-001|alice@example.com]
            campaign_id, lead_email = "default", from_addr
            if "[CID:" in subj:
                try:
                    tag = subj.split("[CID:", 1)[1].split("]", 1)[0]
                    campaign_id, lead_email = tag.split("|", 1)
                    campaign_id, lead_email = campaign_id.strip(), lead_email.strip().lower()
                except Exception:
                    pass

            status = classify_reply_simple(body)
            update_status(lead_email, campaign_id, status, body[:500])
            jlog(op="inbound_reply", ok=True, email=lead_email,
                 campaignId=campaign_id, status=status)
        except Exception as e:
            jlog(op="inbound_reply", ok=False, err=str(e))
    return {"statusCode": 200, "body": json.dumps({"ok": True})}
