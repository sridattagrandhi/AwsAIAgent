# lambda_functions/replies.py
def classify_reply_simple(reply_text: str) -> str:
    t = (reply_text or "").lower()

    unsub = ["unsubscribe", "remove me", "take me off", "stop emailing", "opt out", "do not contact"]
    negative = ["not interested", "no thanks", "no thank you", "stop", "decline", "we're good", "already have", "not a fit"]
    positive = ["interested", "let's talk", "lets talk", "schedule", "book", "demo", "call", "meet", "next week", "follow up", "sounds good", "sure", "yes"]
    bounce = ["undeliverable", "mail delivery", "mail failure", "address not found", "bounced"]

    if any(x in t for x in bounce): return "BOUNCED"
    if any(x in t for x in unsub): return "UNSUBSCRIBE"
    if any(x in t for x in positive): return "WARM"
    if any(x in t for x in negative): return "COLD"
    return "NEUTRAL"
