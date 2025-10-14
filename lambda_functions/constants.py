# lambda_functions/constants.py
STATUSES = {"NEW", "SENT", "NEUTRAL", "WARM", "COLD", "UNSUBSCRIBE", "BOUNCED"}
FOLLOWUP_DELAY_DAYS = 4  # for SENT/NEUTRAL

def normalize_status(s: str | None, default: str = "SENT") -> str:
    if not s:
        return default
    s = s.strip().upper()
    return s if s in STATUSES else default
