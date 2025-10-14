import os, requests, streamlit as st

st.set_page_config(page_title="AI Sales Outreach Agent", layout="wide")
st.title("🤖 AI Sales Outreach Agent")

DEFAULT_API = os.environ.get("API_URL", "").rstrip("/")

with st.sidebar:
  api = st.text_input("API URL", DEFAULT_API)
  st.caption("Use the API URL from 'sam deploy' output.")
  sender = st.text_input("SES From Email", os.environ.get("SES_FROM_EMAIL",""))

tab1, tab2, tab3, tab4 = st.tabs(["🔎 Find Leads", "📥 Store Lead", "✉️ Draft & Send", "📈 Update Status"])

with tab1:
  q = st.text_input("Search query", "sustainable sneakers california")
  limit = st.slider("Limit", 1, 20, 5)
  if st.button("Search"):
    r = requests.post(f"{api}/search", json={"query": q, "limit": limit}, timeout=30)
    st.write(r.status_code, r.json())

with tab2:
  email = st.text_input("Lead email")
  company = st.text_input("Company name")
  website = st.text_input("Website")
  notes = st.text_area("Notes")
  if st.button("Store Lead"):
    r = requests.post(f"{api}/leads", json={"email": email, "company": company, "website": website, "notes": notes}, timeout=30)
    st.write(r.status_code, r.json())

with tab3:
  company = st.text_input("Company for draft")
  website = st.text_input("Company website (optional)")
  desc = st.text_area("Description/context", "")
  pain = st.text_input("Pain point", "improving Shopify conversions")
  pitch = st.text_area("Your product pitch", "AI agent that finds leads and personalizes outreach")
  if st.button("Draft Email"):
    r = requests.post(f"{api}/email/draft", json={
      "companyName": company,
      "website": website,
      "description": desc,
      "painPoint": pain,
      "productPitch": pitch
    }, timeout=60)
    if r.ok:
      st.session_state["draft"] = r.json().get("draft","")
      st.success("Draft generated")
    else:
      st.error(r.text)
  draft = st.text_area("Draft", st.session_state.get("draft",""), height=220)
  to = st.text_input("Send To")
  subject = st.text_input("Subject (override)", "")
  if st.button("Send (SES, dry-run by default)"):
    payload = {"recipient_email": to, "email_body": draft, "sender_email": sender}
    if subject:
      payload["subject"] = subject
    r = requests.post(f"{api}/email/send", json=payload, timeout=30)
    st.write(r.status_code, r.json())

with tab4:
  email = st.text_input("Lead email to update")
  campaign = st.text_input("Campaign ID", "demo-001")
  status = st.selectbox("Status", ["", "SENT", "NEUTRAL", "WARM", "COLD", "UNSUBSCRIBE", "BOUNCED"])
  reply = st.text_area("Paste reply (optional)")
  if st.button("Update Status"):
    r = requests.post(f"{api}/leads/status", json={
      "email": email, "campaign_id": campaign, "status": status or None, "replyText": reply or None
    }, timeout=30)
    st.write(r.status_code, r.json())
