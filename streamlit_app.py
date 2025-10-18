# streamlit_app.py
import os, json, requests
import streamlit as st
from datetime import datetime

try:
    import boto3
    BOTO3_OK = True
except Exception:
    BOTO3_OK = False

# ---- Config ----
st.set_page_config(page_title="AI Sales Outreach Agent", page_icon="🤖", layout="wide")

def _secret(k, d=""):
    try:
        return st.secrets.get(k, d)
    except Exception:
        return d

API_URL = os.getenv("API_URL") or _secret("API_URL", "https://jnepug6nv2.execute-api.us-east-1.amazonaws.com/Prod")
AWS_REGION = os.getenv("AWS_REGION") or _secret("AWS_REGION", "us-east-1")
DEFAULT_SENDER = os.getenv("SES_FROM_EMAIL") or _secret("SES_FROM_EMAIL", "raghav.dewangan2004@gmail.com")

PRIMARY = "#6C63FF"
MUTED = "#6b7280"

# ---- Helpers ----
def api_post(path, payload):
    """POST request to API Gateway endpoint"""
    url = API_URL.rstrip("/") + path
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def chip(text, bg):
    return f'<span style="padding:2px 8px;border-radius:999px;background:{bg};color:#fff;font-weight:700">{text}</span>'

def status_chip(s):
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
    return chip(s, color)

def score_chip(n):
    try:
        n = int(n or 0)
    except:
        n = 0
    color = "#16a34a" if n >= 70 else "#eab308" if n >= 40 else "#ef4444"
    return chip(str(n), color)

def dt(ts):
    if not ts:
        return "—"
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)

# ---- Sidebar ----
st.sidebar.header("⚙️ Config")
API_URL = st.sidebar.text_input(
    "API URL", API_URL, placeholder="https://<api>.execute-api.us-east-1.amazonaws.com/Prod"
)
AWS_REGION = st.sidebar.text_input("AWS Region", AWS_REGION)
DEFAULT_SENDER = st.sidebar.text_input("Default Sender", DEFAULT_SENDER or "you@domain.com")
use_direct_dynamo = st.sidebar.checkbox("Use direct DynamoDB read (live)", value=BOTO3_OK)

st.markdown(
    f"""
<div style="text-align:center">
  <h2 style="margin-bottom:0;color:{PRIMARY}">🤖 AI Sales Outreach Agent</h2>
  <div style="color:{MUTED}">Bedrock · Lambda · API Gateway · DynamoDB · SES</div>
</div>
<hr/>
""",
    unsafe_allow_html=True,
)

# ---- Tabs ----
tab_search, tab_store, tab_draft, tab_send, tab_view, tab_workflow = st.tabs(
    ["🔍 Search", "📥 Store/Enrich Lead", "✉️ Draft Email", "🚀 Send Email", "📊 Lead Viewer", "🤖 Full Workflow"]
)

# -----------------------
# SEARCH TAB
# -----------------------
with tab_search:
    st.subheader("🔍 Find Shopify Leads")
    kw = st.text_input("Keyword", "shoes")
    if st.button("Search"):
        res = api_post("/search", {"keyword": kw})
        st.json(res)

# -----------------------
# STORE / ENRICH TAB
# -----------------------
with tab_store:
    st.subheader("📥 Store a Lead")
    c1, c2 = st.columns(2)
    with c1:
        email = st.text_input("Lead Email", "alice@example.com")
        company = st.text_input("Company", "Allbirds")
        campaign = st.text_input("Campaign ID", "demo-001")
    with c2:
        note = st.text_input("Note", "first touch")
        website = st.text_input("Website (optional)", "https://www.allbirds.com")

    colA, colB = st.columns(2)
    with colA:
        if st.button("Store Lead"):
            res = api_post("/leads", {
                "email": email, "company_name": company, "campaign_id": campaign,
                "status": "SENT", "note": note, "website": website
            })
            st.json(res)
    with colB:
        if st.button("Enrich Lead"):
            res = api_post("/leads/enrich", {
                "email": email, "company_name": company, "website": website
            })
            st.json(res)

# -----------------------
# DRAFT TAB
# -----------------------
with tab_draft:
    st.subheader("✉️ Draft via Bedrock")
    company_name = st.text_input("Company Name", "Allbirds", key="d_name")
    site = st.text_input("Website", "https://www.allbirds.com", key="d_site")
    desc = st.text_area("Description", "Sustainable footwear brand", key="d_desc", height=100)
    lead_email = st.text_input("Lead Email", "alice@example.com", key="d_email")
    if st.button("Generate Draft"):
        res = api_post("/email/draft", {
            "companyName": company_name, "website": site, "description": desc, "email": lead_email
        })
        st.json(res)
        st.text_area("Draft", res.get("draft", ""), height=260)

# -----------------------
# SEND TAB
# -----------------------
with tab_send:
    st.subheader("🚀 Send Email")
    a, b = st.columns(2)
    with a:
        to = st.text_input("Recipient", "alice@example.com")
        sender = st.text_input("Sender", DEFAULT_SENDER or "you@domain.com")
        camp = st.text_input("Campaign", "demo-001")
    with b:
        subj = st.text_input("Subject", "Quick idea for {{company}}")
        body = st.text_area("Body", "Hi — quick idea to lift conversions…", height=120)
    st.success("✅ SES is configured! Emails will be sent for real.")
    if st.button("Send Email"):
        res = api_post("/email/send", {
            "recipient_email": to, "sender_email": sender,
            "campaign_id": camp, "subject": subj, "email_body": body
        })
        st.json(res)

# -----------------------
# VIEW TAB
# -----------------------
with tab_view:
    st.subheader("📊 Lead Viewer")
    v_email = st.text_input("Lead Email", "alice@example.com", key="v_email")
    v_campaign = st.text_input("Campaign ID", "demo-001", key="v_campaign")

    def render_lead(lead):
        if not lead:
            st.info("No lead found yet.")
            return
        company = lead.get("company", "—")
        st.markdown(f"### {company} · {lead.get('email', '')}")
        fit = lead.get("fitScore", 0)
        intent = lead.get("intentScore", 0)
        st.markdown(f"**Fit:** {score_chip(fit)} &nbsp;&nbsp; **Intent:** {score_chip(intent)}", unsafe_allow_html=True)

        prof = lead.get("profile", {})
        sig = lead.get("signals", {})
        st.caption(f"Website: {prof.get('website', '—')} | Shopify: {prof.get('shopify')} | Tech: {', '.join(prof.get('tech', [])) or '—'}")
        st.caption(f"Signals → contact: {sig.get('has_contact_email')} • social: {sig.get('has_social')}")

        camps = lead.get("campaigns", {})
        for cid, data in camps.items():
            status = data.get("status", "—")
            last_reply = data.get("lastReply", "—")
            last_sent = data.get("lastSentAt")
            msg_id = data.get("messageId", "—")
            score = data.get("score", 0)
            updated = data.get("updatedAt")
            st.markdown(
                f"""
                <div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin:6px 0;">
                  <div style="display:flex;align-items:center;gap:8px;">
                    <div style="font-weight:700;">Campaign:</div> <div>{cid}</div>
                    <div>{status_chip(status)}</div>
                    <div>Score: {score_chip(score)}</div>
                  </div>
                  <div style="font-size:13px;color:{MUTED};margin-top:6px;">
                    <div><b>Last Reply:</b> {last_reply}</div>
                    <div><b>Last Sent:</b> {dt(last_sent)} &nbsp; <b>MsgId:</b> {msg_id}</div>
                    <div><b>Updated:</b> {dt(updated)}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    colL, colR = st.columns(2)
    with colL:
        st.markdown("**Update Status (manual)**")
        s = st.selectbox("Status", ["WARM", "NEUTRAL", "COLD", "UNSUBSCRIBE", "BOUNCED"], index=1)
        r = st.text_area("Reply text (optional)", "Let's talk next week")
        if st.button("Apply Update"):
            res = api_post("/leads/status", {"email": v_email, "campaign_id": v_campaign, "status": s, "replyText": r})
            st.json(res)

    with colR:
        st.markdown("**Lead Snapshot (live)**")
        lead = None
        if use_direct_dynamo and BOTO3_OK:
            try:
                dyn = boto3.resource("dynamodb", region_name=AWS_REGION)
                tbl = dyn.Table("LeadsTable")
                resp = tbl.get_item(Key={"pk": f"LEAD#{v_email.lower()}"})
                item = resp.get("Item") or {}
                lead = item.get("data")
                render_lead(lead)
                with st.expander("Raw item", expanded=False):
                    st.code(json.dumps(item, indent=2, ensure_ascii=False), language="json")
            except Exception as e:
                st.error(str(e))
        else:
            st.info("Enable direct Dynamo read in sidebar (requires boto3 + AWS creds).")

# -----------------------
# FULL WORKFLOW TAB
# -----------------------
with tab_workflow:
    st.subheader("🤖 Complete AI Sales Workflow")
    st.info("This demonstrates the full end-to-end sales automation process")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Lead Information")
        wf_email = st.text_input("Target Email", "sridatta963@gmail.com", key="wf_email")
        wf_company = st.text_input("Company Name", "Example Corp", key="wf_company") 
        wf_website = st.text_input("Website", "https://example.com", key="wf_website")
        wf_campaign = st.text_input("Campaign ID", "hackathon-demo", key="wf_campaign")
        
    with col2:
        st.markdown("### ✉️ Email Configuration")
        wf_sender = st.text_input("From Email", DEFAULT_SENDER, key="wf_sender")
        wf_recipient = st.text_input("To Email", wf_email, key="wf_recipient")
        
    if st.button("🚀 Run Complete Workflow", type="primary"):
        # Validate email addresses
        verified_emails = ["raghav.dewangan2004@gmail.com", "sridatta963@gmail.com"]
        if wf_recipient not in verified_emails:
            st.error(f"⚠️ For demo purposes, emails can only be sent to verified addresses: {', '.join(verified_emails)}")
            st.stop()
            
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Store Lead
            status_text.text("Step 1/5: Storing lead...")
            progress_bar.progress(20)
            store_res = api_post("/leads", {
                "email": wf_email,
                "company_name": wf_company, 
                "campaign_id": wf_campaign,
                "status": "SENT",
                "website": wf_website
            })
            
            if store_res.get("ok"):
                st.success("✅ Lead stored successfully")
            else:
                st.error(f"❌ Failed to store lead: {store_res.get('error')}")
                st.stop()
            
            # Step 2: Enrich Lead
            status_text.text("Step 2/5: Enriching lead data...")
            progress_bar.progress(40)
            enrich_res = api_post("/leads/enrich", {
                "email": wf_email,
                "company_name": wf_company,
                "website": wf_website
            })
            
            if enrich_res.get("ok"):
                lead_data = enrich_res.get("lead", {})
                fit_score = lead_data.get("fitScore", 0)
                intent_score = lead_data.get("intentScore", 0)
                st.success(f"✅ Lead enriched - Fit: {fit_score}, Intent: {intent_score}")
            else:
                st.error(f"❌ Failed to enrich lead: {enrich_res.get('error')}")
                st.stop()
            
            # Step 3: Generate Email
            status_text.text("Step 3/5: Generating AI email...")
            progress_bar.progress(60)
            draft_res = api_post("/email/draft", {
                "companyName": wf_company,
                "website": wf_website,
                "description": f"Company: {wf_company}",
                "email": wf_email
            })
            
            if draft_res.get("ok"):
                email_draft = draft_res.get("draft", "")
                st.success("✅ AI email generated")
                with st.expander("📧 Generated Email"):
                    st.text_area("Email Content", email_draft, height=200, key="generated_email")
            else:
                st.error(f"❌ Failed to generate email: {draft_res.get('error')}")
                st.stop()
            
            # Step 4: Send Email
            status_text.text("Step 4/5: Sending email via SES...")
            progress_bar.progress(80)
            send_res = api_post("/email/send", {
                "recipient_email": wf_recipient,
                "sender_email": wf_sender,
                "campaign_id": wf_campaign,
                "subject": f"Partnership Opportunity - {wf_company}",
                "email_body": email_draft
            })
            
            if send_res.get("ok"):
                message_id = send_res.get("message_id")
                dry_run = send_res.get("dry_run", True)
                if dry_run:
                    st.warning(f"⚠️ Email sent in dry-run mode: {message_id}")
                else:
                    st.success(f"✅ Email sent successfully! Message ID: {message_id}")
            else:
                st.error(f"❌ Failed to send email: {send_res.get('error')}")
                st.stop()
            
            # Step 5: Complete
            status_text.text("Step 5/5: Workflow complete!")
            progress_bar.progress(100)
            
            st.balloons()
            st.success("🎉 Complete AI Sales Workflow Executed Successfully!")
            
            # Show summary
            st.markdown("### 📊 Workflow Summary")
            summary_data = {
                "Lead Email": wf_email,
                "Company": wf_company,
                "Campaign": wf_campaign,
                "Fit Score": fit_score,
                "Intent Score": intent_score,
                "Email Status": "Sent" if send_res.get("ok") else "Failed",
                "Message ID": send_res.get("message_id", "N/A")
            }
            
            for key, value in summary_data.items():
                st.write(f"**{key}:** {value}")
                
        except Exception as e:
            st.error(f"❌ Workflow failed: {str(e)}")
            progress_bar.progress(0)
            status_text.text("Workflow failed")
