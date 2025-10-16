# lambda_functions/send_cold_email.py
import os, json, uuid, time, logging
from botocore.exceptions import ClientError

try:
    import boto3
except Exception:
    boto3 = None

from leads_store_dynamo import update_send_metadata  # NEW helper we’ll add below

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def _resp(code=200, body=None):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body if body is not None else {"ok": True}),
    }

_SES = None
def _get_ses():
    global _SES
    if _SES is not None:
        return _SES
    if boto3 is None:
        return None
    region = os.environ.get("AWS_REGION") or os.environ.get("REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    try:
        _SES = boto3.client("ses", region_name=region)
        return _SES
    except Exception:
        logger.exception("Failed to init SES client")
        return None

def _ensure_cid_in_subject(subject: str, campaign_id: str, lead_email: str) -> str:
    tag = f"[CID:{campaign_id}|{lead_email}]"
    return subject if tag in subject else f"{subject} {tag}"

def lambda_handler(event, context):
    """
    JSON body:
      - recipient_email (str, required)
      - subject (str, required)
      - email_body or bodyText (str, optional if bodyHtml provided)
      - bodyHtml (str, optional)
      - sender_email (str, optional; falls back to env)
      - campaign_id (str, recommended)  -> used for tagging & correlation
      - lead_email (str, optional)      -> defaults to recipient_email
    Env:
      - EMAIL_DRY_RUN (default "1") -> simulate sending
      - SES_FROM_EMAIL / FROM_EMAIL (default sender)
      - SES_REPLY_TO_EMAIL (optional)
      - SES_CONFIG_SET (optional) -> SES ConfigurationSet for events/metrics
    """
    try:
        raw = event.get("body") or "{}"
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        body = json.loads(raw) if isinstance(raw, str) else (raw or {})

        to_addr    = (body.get("recipient_email") or "").strip().lower()
        subject    = (body.get("subject") or "").strip()
        text_body  = (body.get("email_body") or body.get("bodyText") or "").strip()
        html_body  = body.get("bodyHtml")
        sender     = (body.get("sender_email") or
                      os.environ.get("SES_FROM_EMAIL") or
                      os.environ.get("FROM_EMAIL") or "").strip()
        campaign_id = (body.get("campaign_id") or "default").strip()
        lead_email  = (body.get("lead_email") or to_addr).strip().lower()

        if not to_addr or not subject or (not text_body and not html_body):
            return _resp(400, {"error": "Missing required: recipient_email, subject, and one of email_body/bodyText or bodyHtml"})
        if not sender:
            return _resp(400, {"error": "Missing sender_email and SES_FROM_EMAIL/FROM_EMAIL env"})

        # Add correlation token to subject for inbound parsing
        subject = _ensure_cid_in_subject(subject, campaign_id, lead_email)

        dry_run = str(os.environ.get("EMAIL_DRY_RUN", "1")).strip().lower() in ("1", "true", "yes", "y")
        if dry_run:
            fake_id = f"dryrun-{uuid.uuid4()}"
            # Persist send metadata so the pipeline looks real in demos
            try:
                update_send_metadata(lead_email, campaign_id, fake_id, int(time.time()))
            except Exception:
                logger.exception("update_send_metadata failed (dry-run)")
            return _resp(200, {"ok": True, "message_id": fake_id, "dry_run": True, "recipient": to_addr, "subject": subject})

        ses = _get_ses()
        if not ses:
            return _resp(500, {"error": "SES not available (boto3 missing or client init failed)"})

        body_payload = {}
        if text_body:
            body_payload["Text"] = {"Data": text_body, "Charset": "UTF-8"}
        if html_body:
            body_payload["Html"] = {"Data": html_body, "Charset": "UTF-8"}

        ses_args = {
            "Source": sender,
            "Destination": {"ToAddresses": [to_addr]},
            "Message": {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": body_payload
            },
            # Add Reply-To so replies thread correctly; still includes CID tag in Subject as backup
            "ReplyToAddresses": [os.environ.get("SES_REPLY_TO_EMAIL", sender)]
        }

        # Tag the message for SES event correlation (Bounce/Complaint/Delivery)
        # Note: boto3 SES v1 supports 'Tags' on SendEmail; if not, this is a no-op.
        tags = [
            {"Name": "campaign_id", "Value": campaign_id[:256]},
            {"Name": "lead_email", "Value": lead_email[:256]},
        ]
        ses_args["Tags"] = tags

        # Attach configuration set if provided (for event destinations/metrics)
        config_set = os.environ.get("SES_CONFIG_SET")
        if config_set:
            ses_args["ConfigurationSetName"] = config_set

        resp = ses.send_email(**ses_args)
        msg_id = resp.get("MessageId")

        # Persist SES message id + timestamps so inbound/events can correlate
        try:
            update_send_metadata(lead_email, campaign_id, msg_id, int(time.time()))
        except Exception:
            logger.exception("update_send_metadata failed")

        return _resp(200, {"ok": True, "message_id": msg_id, "dry_run": False, "recipient": to_addr, "subject": subject})

    except ClientError as e:
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        logger.exception("SES ClientError: %s", msg)
        return _resp(502, {"error": f"SES error: {msg}"})
    except Exception as e:
        logger.exception("send_cold_email failed")
        return _resp(500, {"error": str(e)})
