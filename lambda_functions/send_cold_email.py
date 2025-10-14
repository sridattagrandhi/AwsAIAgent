# lambda_functions/send_cold_email.py
import os, json, uuid, logging
from botocore.exceptions import ClientError

try:
    import boto3
except Exception:
    boto3 = None  # allows dry-run even if boto3 isn't present locally

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def _resp(code=200, body=None):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body if body is not None else {"ok": True})
    }

# cache client per cold start
_SES = None
def _get_ses():
    global _SES
    if _SES is not None:
        return _SES
    region = os.environ.get("AWS_REGION") or os.environ.get("REGION") or "us-east-1"
    if not boto3:
        return None
    _SES = boto3.client("ses", region_name=region)
    return _SES

def lambda_handler(event, context):
    """
    Send an email via Amazon SES.
    Accepts JSON body:
      - recipient_email (str, required)
      - subject (str, required)
      - email_body or bodyText (str, optional if bodyHtml provided)
      - bodyHtml (str, optional)
      - sender_email (str, optional; falls back to SES_FROM_EMAIL/ FROM_EMAIL env)
    Env:
      - EMAIL_DRY_RUN=1|true (default on) to simulate sending
      - AWS_REGION or REGION for SES region
      - SES_FROM_EMAIL / FROM_EMAIL as default sender
      - SES_REPLY_TO_EMAIL optional
    """
    try:
        raw = event.get("body") or "{}"
        body = json.loads(raw) if isinstance(raw, str) else (raw or {})

        to_addr   = (body.get("recipient_email") or "").strip()
        subject   = (body.get("subject") or "").strip()
        text_body = (body.get("email_body") or body.get("bodyText") or "").strip()
        html_body = body.get("bodyHtml")
        sender    = (body.get("sender_email") or
                     os.environ.get("SES_FROM_EMAIL") or
                     os.environ.get("FROM_EMAIL") or "").strip()

        if not to_addr or not subject or (not text_body and not html_body):
            logger.warning("missing_fields: to=%s subject?%s text?%s html?%s",
                           bool(to_addr), bool(subject), bool(text_body), bool(html_body))
            return _resp(400, {"error": "Missing required: recipient_email, subject, and one of email_body/bodyText or bodyHtml"})

        if not sender:
            return _resp(400, {"error": "Missing sender_email and SES_FROM_EMAIL/FROM_EMAIL env"})

        dry_run = (os.environ.get("EMAIL_DRY_RUN", "1").lower() in ("1", "true", "yes"))
        if dry_run:
            fake_id = f"dryrun-{uuid.uuid4()}"
            logger.info(json.dumps({
                "op": "send_email", "dryRun": True, "to": to_addr, "subject": subject, "sender": sender
            }))
            return _resp(200, {"ok": True, "message_id": fake_id, "dry_run": True, "recipient": to_addr})

        ses = _get_ses()
        if not ses:
            return _resp(500, {"error": "SES not available (boto3 missing or client init failed)"})

        # Build SES body
        body_payload = {}
        if text_body:
            body_payload["Text"] = {"Data": text_body, "Charset": "UTF-8"}
        if html_body:
            body_payload["Html"] = {"Data": html_body, "Charset": "UTF-8"}

        resp = ses.send_email(
            Source=sender,
            Destination={"ToAddresses": [to_addr]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": body_payload
            },
            ReplyToAddresses=[os.environ.get("SES_REPLY_TO_EMAIL", sender)]
        )

        msg_id = resp.get("MessageId")
        logger.info(json.dumps({"op": "send_email", "dryRun": False, "to": to_addr, "subject": subject, "messageId": msg_id}))
        return _resp(200, {"ok": True, "message_id": msg_id, "dry_run": False, "recipient": to_addr})

    except ClientError as e:
        # Report the SES error back clearly
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        logger.exception("SES ClientError: %s", msg)
        return _resp(502, {"error": f"SES error: {msg}"})
    except Exception as e:
        logger.exception("send_cold_email failed")
        return _resp(500, {"error": str(e)})
