# lambda_functions/ses_events_handler.py
import json
from leads_store_dynamo import update_status
from log import jlog

def lambda_handler(event, context):
    """
    Triggered by SNS notifications from SES.
    Handles bounces, complaints, and deliveries.
    Updates the corresponding lead's status.
    """
    for rec in event.get("Records", []):
        try:
            msg = json.loads(rec["Sns"]["Message"])
            mail = msg.get("mail", {})
            event_type = msg.get("notificationType")
            message_id = mail.get("messageId")

            # Extract tags if you use them in SES sends
            tags = mail.get("tags", {})
            campaign_id = tags.get("campaign_id", ["default"])[0] if isinstance(tags, dict) else "default"
            lead_email = tags.get("lead_email", ["unknown@example.com"])[0] if isinstance(tags, dict) else "unknown@example.com"

            status_map = {"Bounce": "BOUNCED", "Complaint": "UNSUBSCRIBE", "Delivery": "SENT"}
            new_status = status_map.get(event_type, None)
            if not new_status:
                continue

            res = update_status(lead_email, campaign_id, new_status, f"SES:{event_type}")
            jlog(op="ses_event", ok=True, messageId=message_id, email=lead_email,
                 campaignId=campaign_id, status=new_status)
        except Exception as e:
            jlog(op="ses_event", ok=False, err=str(e))
    return {"statusCode": 200, "body": json.dumps({"ok": True})}
