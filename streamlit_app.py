# streamlit_app.py
import streamlit as st
import requests
import json
import os

# --- CONFIG ---
API_URL = os.getenv("API_URL") or st.secrets.get("API_URL", "")
st.set_page_config(
    page_title="AI Sales Outreach Agent",
    layout="wide",
    page_icon="🤖"
)

# --- HEADER ---
st.markdown(
    """
    <h2 style='text-align:center;color:#6C63FF;'>🤖 AI Sales Outreach Agent</h2>
    <p style='text-align:center;color:gray;'>
    Powered by AWS Bedrock · DynamoDB · Lambda · API Gateway
    </p>
    <hr style='margin-top:-5px;'>
    """,
    unsafe_allow_html=True,
)

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configuration")
st.sidebar.write("Update environment or endpoint as needed.")
api_input = st.sidebar.text_input("API Endpoint", API_URL, help="Your API Gateway Prod URL")
if api_input:
    API_URL = api_input.strip()

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(
    ["🔍 Search Shopify Brands", "📥 Store Lead", "✉️ Draft Email", "📈 Update Lead Status"]
)

# --- Search Tab ---
with tab1:
    st.subheader("🔍 Search Shopify Retailers (mocked data)")
    keyword = st.text_input("Enter keyword (e.g., 'shoes', 'fashion')", "shoes")
    if st.button("Search", use_container_width=True):
        try:
            with st.spinner("Searching Shopify retailers..."):
                res = requests.post(f"{API_URL}/search", json={"keyword": keyword})
                st.success("✅ Search complete!")
                st.json(res.json())
        except Exception as e:
            st.error(f"Error: {e}")

# --- Store Lead Tab ---
with tab2:
    st.subheader("📥 Store New Lead")
    email = st.text_input("Lead Email", "alice@example.com")
    company = st.text_input("Company Name", "Allbirds")
    campaign_id = st.text_input("Campaign ID", "demo-001")
    note = st.text_area("Note", "first touch")
    if st.button("Store Lead", use_container_width=True):
        payload = {
            "email": email,
            "company_name": company,
            "campaign_id": campaign_id,
            "status": "SENT",
            "note": note,
        }
        try:
            with st.spinner("Storing lead..."):
                res = requests.post(f"{API_URL}/leads", json=payload)
                data = res.json()
                st.success("✅ Lead stored successfully!")
                st.json(data)
        except Exception as e:
            st.error(f"Error: {e}")

# --- Draft Email Tab ---
with tab3:
    st.subheader("✉️ Generate Cold Email (via Bedrock Nova Pro)")
    company_name = st.text_input("Company Name", "Allbirds", key="draft_company")
    website = st.text_input("Website", "https://www.allbirds.com")
    description = st.text_area("Description", "Sustainable footwear brand making eco-friendly shoes.")
    if st.button("Generate Email Draft", use_container_width=True):
        payload = {
            "companyName": company_name,
            "website": website,
            "description": description
        }
        try:
            with st.spinner("Generating draft with Bedrock Nova Pro..."):
                res = requests.post(f"{API_URL}/email/draft", json=payload)
                data = res.json()
                st.success("✅ Draft generated!")
                st.markdown("### 📧 Suggested Cold Email")
                st.text_area("Generated Draft", data.get("draft", ""), height=350)
                st.caption(f"Model used: {data.get('model', 'amazon.nova-pro-v1:0')}")
        except Exception as e:
            st.error(f"Error: {e}")

# --- Update Status Tab ---
with tab4:
    st.subheader("📈 Update Lead Status")
    email_upd = st.text_input("Email", "alice@example.com", key="upd_email")
    campaign_upd = st.text_input("Campaign ID", "demo-001", key="upd_campaign")
    status = st.selectbox("Status", ["WARM", "COLD", "BOUNCED", "UNSUBSCRIBE"], index=0)
    reply_text = st.text_area("Reply Text", "Let's talk next week")
    if st.button("Update Lead Status", use_container_width=True):
        payload = {
            "email": email_upd,
            "campaign_id": campaign_upd,
            "status": status,
            "replyText": reply_text,
        }
        try:
            with st.spinner("Updating lead status..."):
                res = requests.post(f"{API_URL}/leads/status", json=payload)
                data = res.json()
                st.success("✅ Lead updated successfully!")
                st.json(data)
        except Exception as e:
            st.error(f"Error: {e}")
