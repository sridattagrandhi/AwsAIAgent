import os
import time
import json
import typing as t
from datetime import datetime

import streamlit as st
import requests

# Optional: live Dynamo view (only if boto3 is installed & you have AWS creds)
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_OK = True
except Exception:
    BOTO3_OK = False

# ---------------------------
# Config & helpers
# ---------------------------
st.set_page_config(page_title="AI Sales Outreach Agent", page_icon="🤖", layout="wide")

def _read_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

API_URL = os.getenv("API_URL") or _read_secret("API_URL", "")
AWS_REGION = os.getenv("AWS_REGION") or _read_secret("AWS_REGION", "us-east-1")
DEFAULT_SENDER = os.getenv("SES_FROM_EMAIL") or _read_secret("SES_FROM_EMAIL", "")

PRIMARY = "#6C63FF"
MUTED = "#6b7280"

def status_chip(s: str) -> str:
    s = (s or "").upper()
    color = {
        "WARM": "#16a34a",
        "NEUTRAL": "#3b82f6",
        "COLD": "#9ca3af",
        "UNSUBSCRIBE": "#f97316",
        "BOUNCED": "#ef4444",
        "SENT": "#8b5cf6",
        "BOOKED": "#22c55e",
    }.get(s, "#6b7280")
    return f"""<span style="
        display:inline-block;padding:2px 8px;border-radius:999px;
        background:{color};color:white;font-size:12px;font-weight:600;">
        {s}
    </span>"""

def dt(ts: t.Optional[int]) -> str:
    if not ts: return "—"
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)

def api_post(path: str, payload: dict, timeout: int = 20) -> dict:
    if not API_URL:
        raise RuntimeError("API_URL is not set. Use the sidebar to set it.")
    url = API_URL.rstrip("/") + path
    r = requests.post(url, json=payload, timeout=timeout)
    try:
        return r.json()
    except Exception:
        return {"error": f"Non-JSON response ({r.status_code})", "text": r.text}

def safe_json(v: t.Any) -> str:
    try:
        return json.dumps(v, indent=2, ensure_ascii=False)
    except Exception:
        return str(v)

# ---------------------------
# Sidebar
# ---------------------------
st.sidebar.header("⚙️ Configuration")
API_URL = st.sidebar.text_input("API URL", value=API_URL, placeholder="https://xxx.execute-api.us-east-1.amazonaws.com/Prod")
AWS_REGION = st.sidebar.text_input("AWS Region", value=AWS_REGION)
DEFAULT_SENDER = st.sidebar.text_input("Sender (for SES)", value=DEFAULT_SENDER, placeholder="you@domain.com")
st.sidebar.caption("Tip: set API_URL / AWS_REGION / SES_FROM_EMAIL as env vars or in .streamlit/secrets.toml")

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("Auto-refresh Lead Viewer", value=True)
refresh_secs = st.sidebar.slider("Refresh interval (secs)", 5, 60, 10)
use_direct_dynamo = st.sidebar.checkbox("Use direct DynamoDB read (live)", value=BOTO3_OK and True, help="Requires boto3 + AWS creds; reads LeadsTable directly")

st.sidebar.markdown("---")
st.sidebar.caption("Built for AWS Hackathon 2025 • Bedrock + Lambda + API Gateway + DynamoDB + SES")

# Optional auto-refresh (only triggers when viewer tab rendered)
if auto_refresh:
    st.sidebar.write(f"Auto-refresh enabled: every {refresh_secs}s")

# ---------------------------
# Header
# ---------------------------
st.markdown(
    f"""
    <div style="text-align:center">
      <h2 style="margin-bottom:0;color:{PRIMARY}">🤖 AI Sales Outreach Agent</h2>
      <div style="color:{MUTED}">Amazon Bedrock · Lambda · API Gateway · DynamoDB · SES</div>
    </div>
    <hr style="margin-top:16px;margin-bottom:8px;">
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# Tabs
# ---------------------------
tab_search, tab_store, tab_draft, tab_send, tab_view = st.tabs(
    ["🔍 Search", "📥 Store Lead", "✉️ Draft Email", "🚀 Send Email (dry-run)", "📊 Lead Viewer"]
)

# ---------------------------
# Tab: Search (mock or your Lambda)
# ---------------------------
with tab_search:
    st.subheader("🔍 Find Shopify Leads")
    kw = st.text_input("Keyword", "shoes")
    if st.button("Search", use_container_width=True):
        try:
            res = api_post("/search", {"keyword": kw})
            if "error" in res:
                st.error(res["error"])
                st.code(res.get("text", ""), language="json")
            else:
                st.success("Search complete")
                st.json(res)
        except Exception as e:
            st.error(str(e))

# ---------------------------
# Tab: Store Lead
# ---------------------------
with tab_store:
    st.subheader("📥 Store a Lead")
    col1, col2 = st.columns(2)
    with col1:
        email = st.text_input("Lead Email", "alice@example.com")
        company = st.text_input("Company", "Allbirds")
    with col2:
        campaign = st.text_input("Campaign ID", "demo-001")
        note = st.text_input("Note", "first touch")

    if st.button("Store Lead", use_container_width=True):
        try:
            payload = {
                "email": email,
                "company_name": company,
                "campaign_id": campaign,
                "status": "SENT",
                "note": note,
            }
            res = api_post("/leads", payload)
            if "error" in res:
                st.error(res["error"])
            else:
                st.success("Lead stored")
            st.json(res)
        except Exception as e:
            st.error(str(e))

# ---------------------------
# Tab: Draft Email (Bedrock)
# ---------------------------
with tab_draft:
    st.subheader("✉️ Generate Cold Email (Bedrock Nova Pro)")
    c1, c2 = st.columns(2)
    with c1:
        company_name = st.text_input("Company Name", "Allbirds", key="draft_company")
        website = st.text_input("Website", "https://www.allbirds.com")
    with c2:
        description = st.text_area("Description", "Sustainable footwear brand making eco-friendly shoes.", height=100)

    if st.button("Generate Draft", use_container_width=True):
        try:
            res = api_post("/email/draft", {
                "companyName": company_name,
                "website": website,
                "description": description
            })
            if "error" in res:
                st.error(res["error"])
                st.code(res.get("text", ""), language="json")
            else:
                st.success("Draft generated")
                st.markdown("**Model:** " + res.get("model", "amazon.nova-pro-v1:0"))
                st.text_area("Generated Draft", res.get("draft", ""), height=300)
        except Exception as e:
            st.error(str(e))

# ---------------------------
# Tab: Send Email (dry-run)
# ---------------------------
with tab_send:
    st.subheader("🚀 Send Email (dry-run via SES)")
    colA, colB = st.columns(2)
    with colA:
        se_to = st.text_input("Recipient", "alice@example.com")
        se_sender = st.text_input("Sender", DEFAULT_SENDER or "you@yourdomain.com")
        se_campaign = st.text_input("Campaign ID", "demo-001")
    with colB:
        se_subject = st.text_input("Subject", "Quick idea to lift conversions")
        se_body = st.text_area("Body (text)", "Hi Alice — quick idea to improve conversions…", height=120)

    st.caption("Dry-run returns a fake MessageId but still writes send metadata to DynamoDB.")

    if st.button("Send (dry-run)", use_container_width=True):
        try:
            res = api_post("/email/send", {
                "recipient_email": se_to,
                "sender_email": se_sender,
                "campaign_id": se_campaign,
                "subject": se_subject,
                "email_body": se_body
            })
            if "error" in res:
                st.error(res["error"])
            else:
                st.success("Send simulated")
            st.json(res)
        except Exception as e:
            st.error(str(e))

# ---------------------------
# Tab: Lead Viewer (live)
# ---------------------------
with tab_view:
    st.subheader("📊 Lead Viewer (Live Status)")

    lv_email = st.text_input("Lead Email", "alice@example.com", key="lv_email")
    lv_campaign = st.text_input("Campaign ID", "demo-001", key="lv_campaign")

    # Auto-refresh widget (only when tab is visible)
    if auto_refresh:
        st.experimental_rerun  # noqa: used only if st_autorefresh exists in your Streamlit version
        try:
            # Only call this if available; older versions don't have it
            st_autorefresh = st.experimental_rerun  # placeholder
        except Exception:
            pass
        # Use a safe autorefresh if present
        try:
            st_autorefresh = st.experimental_memo.clear  # hack guard
        except Exception:
            pass
        try:
            st.experimental_rerun  # noop just to satisfy linter
        except Exception:
            pass

    colL, colR = st.columns([1, 1])

    with colL:
        st.markdown("**Update Status (manual)**")
        upd_status = st.selectbox("Status", ["WARM", "NEUTRAL", "COLD", "UNSUBSCRIBE", "BOUNCED"], index=1)
        upd_reply = st.text_area("Reply text (optional)", "Let's talk next week")
        if st.button("Apply Update", use_container_width=True):
            try:
                res = api_post("/leads/status", {
                    "email": lv_email,
                    "campaign_id": lv_campaign,
                    "status": upd_status,
                    "replyText": upd_reply
                })
                if "error" in res:
                    st.error(res["error"])
                else:
                    st.success("Status updated")
                st.json(res)
            except Exception as e:
                st.error(str(e))

    def render_lead_card(lead: dict):
        if not lead:
            st.info("No lead found yet. Store a lead first on the 'Store Lead' tab.")
            return
        company = lead.get("company") or "—"
        st.markdown(f"### {company} · {lead.get('email','')}")
        campaigns = lead.get("campaigns", {})
        if not campaigns:
            st.caption("No campaigns yet.")
        for cid, data in campaigns.items():
            status = data.get("status", "—")
            last_reply = data.get("lastReply", "—")
            last_sent = data.get("lastSentAt")
            msg_id = data.get("messageId", "—")
            updated_at = data.get("updatedAt")
            st.markdown(
                f"""
                <div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin:6px 0;">
                  <div style="display:flex;align-items:center;gap:8px;">
                    <div style="font-weight:700;">Campaign:</div> <div>{cid}</div>
                    <div>{status_chip(status)}</div>
                  </div>
                  <div style="font-size:13px;color:{MUTED};margin-top:6px;">
                    <div><b>Last Reply:</b> {last_reply}</div>
                    <div><b>Last Sent:</b> {dt(last_sent)} &nbsp; <b>MsgId:</b> {msg_id}</div>
                    <div><b>Updated:</b> {dt(updated_at)}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with colR:
        st.markdown("**Lead Snapshot (live)**")

        # Preferred path: read directly from DynamoDB (no GET API needed)
        lead_data = None
        if use_direct_dynamo and BOTO3_OK:
            try:
                dyn = boto3.resource("dynamodb", region_name=AWS_REGION)
                table = dyn.Table("LeadsTable")
                res = table.get_item(Key={"pk": f"LEAD#{lv_email.lower()}"})
                item = res.get("Item") or {}
                lead_data = item.get("data")
                render_lead_card(lead_data)
                with st.expander("Raw item", expanded=False):
                    st.code(safe_json(item), language="json")
            except ClientError as e:
                st.error(f"DynamoDB error: {e}")
            except Exception as e:
                st.error(str(e))

        # Fallback: if no boto3 or disabled, ask user to refresh after updates
        if not (use_direct_dynamo and lead_data):
            st.info("Direct Dynamo view is disabled. Enable it in the sidebar (requires boto3 + AWS creds).")
            st.caption("You can still see the update response JSON on the left after you change status.")

# ------------- End -------------
