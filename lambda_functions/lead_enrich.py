# lambda_functions/lead_enrich.py
import re, json
from decimal import Decimal
from urllib.parse import urlparse

from leads_store_dynamo import get_lead, upsert_lead
from log import jlog
from scoring import compute_campaign_score

TAG_RE = re.compile(r"<[^>]+>")

def _normalize_website(url: str) -> str:
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    u = urlparse(url)
    return f"{u.scheme}://{u.netloc}"

def _fake_fetch(url: str) -> str:
    return """
    <html><head>
    <title>Allbirds® — Sustainable Shoes</title>
    <meta name="description" content="Comfortable, sustainable shoes made from natural materials">
    </head><body>Powered by Shopify. Follow us on Instagram and Twitter. Contact: support@brand.com</body></html>
    """

def _extract_meta(html: str) -> dict:
    title = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    desc  = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.I | re.S)
    body  = TAG_RE.sub(" ", html or "")
    body_l = body.lower()
    return {
        "title": title.group(1).strip() if title else "",
        "description": desc.group(1).strip() if desc else "",
        "shopify": "shopify" in body_l,
        "has_social": any(x in body_l for x in ["instagram","twitter","facebook","tiktok","linkedin"]),
        "has_contact_email": "@" in body,
    }

def _json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    try:
        raw = event.get("body") or "{}"
        body = json.loads(raw) if isinstance(raw, str) else (raw or {})
        email   = (body.get("email") or "").strip().lower()
        company = (body.get("company_name") or body.get("company") or "").strip()
        website = (body.get("website") or body.get("company_website") or "").strip()

        if not email:
            return {"statusCode": 400, "body": json.dumps({"error": "email required"})}

        lead = get_lead(email) or {"email": email}
        if company:
            lead["company"] = company

        site = _normalize_website(website or lead.get("profile", {}).get("website") or "")
        html = _fake_fetch(site) if site else ""
        meta = _extract_meta(html) if html else {}

        # profile/signals
        profile = lead.get("profile", {})
        profile.update({
            "website": site,
            "industry": profile.get("industry") or "E-commerce",
            "shopify": bool(meta.get("shopify")),
            "tech": sorted(list(set((profile.get("tech") or []) + (["Shopify"] if meta.get("shopify") else [])))),
        })
        lead["profile"] = profile

        signals = lead.get("signals", {})
        signals.update({
            "has_contact_email": bool(meta.get("has_contact_email")),
            "has_social": bool(meta.get("has_social")),
            "recent_blog": signals.get("recent_blog", False),
            "newsletter": signals.get("newsletter", False),
        })
        lead["signals"] = signals

        # scores: do math in float, store in Decimal for DynamoDB
        fit_f = float(lead.get("fitScore", 0)) \
                + (35 if profile["shopify"] else 0) \
                + (10 if "sustainable" in (meta.get("title","")+meta.get("description","")).lower() else 0)
        intent_f = float(lead.get("intentScore", 0)) \
                   + (25 if signals["has_contact_email"] else 0) \
                   + (15 if signals["has_social"] else 0)

        lead["fitScore"]    = Decimal(str(min(100, round(fit_f, 2))))
        lead["intentScore"] = Decimal(str(min(100, round(intent_f, 2))))

        # per-campaign blended score (store Decimal)
        campaigns = lead.get("campaigns", {})
        for cid, cdata in campaigns.items():
            penalties = 0
            if cdata.get("status") == "UNSUBSCRIBE": penalties += 50
            if cdata.get("status") == "COLD": penalties += 20
            blended = compute_campaign_score(float(lead["fitScore"]), float(lead["intentScore"]), penalties)
            campaigns[cid]["score"] = Decimal(str(blended))
        lead["campaigns"] = campaigns

        upsert_lead(lead)
        jlog(op="lead_enrich", ok=True, email=email, fit=float(lead["fitScore"]), intent=float(lead["intentScore"]))
        return {"statusCode": 200, "body": json.dumps({"ok": True, "lead": lead}, default=_json_default)}

    except Exception as e:
        jlog(op="lead_enrich", ok=False, err=str(e))
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
