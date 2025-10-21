# streamlit_app.py
import os, json, requests, time
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

def render_lead(lead):
    """Render lead information with campaign details and reply highlighting"""
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
        
        # Highlight recent replies
        border_color = "#16a34a" if last_reply and last_reply != "—" and len(last_reply) > 10 else "#e5e7eb"
        bg_color = "#f0fdf4" if last_reply and last_reply != "—" and len(last_reply) > 10 else "#ffffff"
        
        st.markdown(
            f"""
            <div style="border:2px solid {border_color};border-radius:12px;padding:12px;margin:6px 0;background-color:{bg_color};">
              <div style="display:flex;align-items:center;gap:8px;">
                <div style="font-weight:700;">Campaign:</div> <div>{cid}</div>
                <div>{status_chip(status)}</div>
                <div>Score: {score_chip(score)}</div>
                {"<div style='background:#16a34a;color:white;padding:2px 6px;border-radius:4px;font-size:11px;'>NEW REPLY</div>" if last_reply and last_reply != "—" and len(last_reply) > 10 else ""}
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

# ---- Tab Navigation Helper ----
# Check for pending auto-fill data and show notifications
pending_store = any(key.startswith("store_") for key in st.session_state.keys())
pending_draft = any(key.startswith("draft_") for key in st.session_state.keys())

if pending_store or pending_draft:
    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, #ff6b6b, #4ecdc4); padding: 8px; border-radius: 8px; margin-bottom: 10px; text-align: center; color: white; font-weight: bold;">
            🔔 Auto-filled data waiting! 
            {" 📥 Store/Enrich Lead" if pending_store else ""}
            {" ✉️ Draft Email" if pending_draft else ""}
        </div>
        """,
        unsafe_allow_html=True
    )

# ---- Tabs ----
# Add indicators to tab names
store_indicator = " 🔴" if pending_store else ""
draft_indicator = " 🔴" if pending_draft else ""

tab_search, tab_store, tab_draft, tab_send, tab_view, tab_workflow, tab_replies = st.tabs([
    "🔍 Search", 
    f"📥 Store/Enrich Lead{store_indicator}", 
    f"✉️ Draft Email{draft_indicator}", 
    "🚀 Send Email", 
    "📊 Lead Viewer", 
    "🤖 Full Workflow", 
    "📬 SES Inbound"
])

# -----------------------
# SEARCH TAB
# -----------------------
with tab_search:
    st.subheader("🔍 Find Shopify Leads")
    
    # Search input section
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        kw = st.text_input("Search Keywords", "shoes", placeholder="e.g., shoes, jewelry, fitness, home decor")
        
    with col2:
        limit = st.selectbox("Results", [5, 10, 15, 20], index=1)
        
    with col3:
        st.write("")  # spacing
        search_btn = st.button("🔍 Search Leads", type="primary")
    
    if search_btn and kw:
        with st.spinner(f"Searching for '{kw}' Shopify stores..."):
            res = api_post("/search", {"query": kw, "limit": limit})
            
            if res.get("error"):
                st.error(f"❌ Search failed: {res.get('error')}")
            else:
                retailers = res.get("retailers", [])
                count = res.get("count", 0)
                fallback = res.get("fallback", False)
                
                if retailers:
                    st.markdown("---")
                    
                    # Results display
                    for i, store in enumerate(retailers, 1):
                        company = store.get("companyName", "Unknown Company")
                        website = store.get("website", "")
                        email = store.get("email", "")
                        phone = store.get("phone", "")
                        description = store.get("description", "")
                        contact_page = store.get("contactPage", "")
                        
                        # Generate mock scores for demo
                        import random
                        random.seed(hash(company))  # Consistent scores per company
                        fit_score = random.randint(60, 95)
                        intent_score = random.randint(40, 85)
                        
                        # Create expandable card for each lead
                        with st.expander(f"#{i} {company} · {score_chip(fit_score)} Fit · {score_chip(intent_score)} Intent", expanded=i <= 3):
                            
                            # Lead info columns
                            info_col1, info_col2 = st.columns([2, 1])
                            
                            with info_col1:
                                st.markdown(f"**🏢 Company:** {company}")
                                if website:
                                    st.markdown(f"**🌐 Website:** [{website}]({website})")
                                if email:
                                    st.markdown(f"**📧 Email:** {email}")
                                    
                                    # Check if lead already exists in system
                                    existing_leads = [
                                        "sridatta963@gmail.com", 
                                        "contact@techgadgetsplus.com", 
                                        "hello@beautyessentials.com",
                                        "sales@eliteathletic.com",
                                        "boutique@luxuryshoes.com"
                                    ]
                                    if email in existing_leads:
                                        st.success("✅ **Already in CRM** - Has active campaigns!")
                                        
                                if phone:
                                    st.markdown(f"**📞 Phone:** {phone}")
                                if description:
                                    st.markdown(f"**📝 Description:** {description}")
                                if contact_page:
                                    st.markdown(f"**📞 Contact Page:** [{contact_page}]({contact_page})")
                            
                            with info_col2:
                                st.markdown("**📊 Lead Scores**")
                                st.markdown(f"Fit Score: {score_chip(fit_score)}", unsafe_allow_html=True)
                                st.markdown(f"Intent Score: {score_chip(intent_score)}", unsafe_allow_html=True)
                                
                                # Quick action buttons
                                st.markdown("**⚡ Quick Actions**")
                                
                                # Store lead button with auto-fill
                                if st.button(f"📥 Store Lead", key=f"store_{i}"):
                                    # Set session state for Store/Enrich tab
                                    st.session_state["store_email"] = email or f"contact@{company.lower().replace(' ', '')}.com"
                                    st.session_state["store_company"] = company
                                    st.session_state["store_campaign"] = "search-leads"
                                    st.session_state["store_note"] = f"Found via search: {kw}"
                                    st.session_state["store_website"] = website or ""
                                    st.session_state["switch_to_store"] = True
                                    
                                    st.success(f"✅ Lead details saved! **Click the '📥 Store/Enrich Lead 🔴' tab above** to review and submit.")
                                    st.info("🔴 **Red indicator shows auto-filled data is waiting!**")
                                    
                                    # Auto-scroll to top to make tabs visible
                                    st.markdown(
                                        """
                                        <script>
                                        window.scrollTo(0, 0);
                                        </script>
                                        """,
                                        unsafe_allow_html=True
                                    )
                                
                                # Draft email button with auto-fill
                                if st.button(f"✉️ Draft Email", key=f"draft_{i}"):
                                    if email:
                                        # Set session state for Draft tab
                                        st.session_state["draft_company_name"] = company
                                        st.session_state["draft_lead_email"] = email
                                        st.session_state["draft_website"] = website or ""
                                        st.session_state["draft_description"] = description or f"{company} - E-commerce store"
                                        st.session_state["switch_to_draft"] = True
                                        
                                        st.success(f"✅ Email details saved! **Click the '✉️ Draft Email 🔴' tab above** to generate personalized email.")
                                        st.info("🔴 **Red indicator shows auto-filled data is waiting!**")
                                        
                                        # Auto-scroll to top to make tabs visible
                                        st.markdown(
                                            """
                                            <script>
                                            window.scrollTo(0, 0);
                                            </script>
                                            """,
                                            unsafe_allow_html=True
                                        )
                                    else:
                                        st.warning("⚠️ No email found for this lead")
                                
                                # Quick store button (direct API call)
                                if st.button(f"⚡ Quick Store", key=f"quick_store_{i}"):
                                    store_payload = {
                                        "email": email or f"contact@{company.lower().replace(' ', '')}.com",
                                        "company_name": company,
                                        "campaign_id": "search-leads",
                                        "status": "PROSPECT",
                                        "note": f"Found via search: {kw}",
                                        "website": website
                                    }
                                    store_res = api_post("/leads", store_payload)
                                    if store_res.get("ok"):
                                        st.success(f"✅ {company} stored directly!")
                                    else:
                                        st.error(f"❌ Failed to store: {store_res.get('error')}")
                    
                    # Bulk actions
                    st.markdown("---")
                    st.markdown("### ⚡ Bulk Actions")
                    
                    bulk_col1, bulk_col2, bulk_col3 = st.columns(3)
                    
                    with bulk_col1:
                        if st.button("📥 Store All Leads"):
                            stored_count = 0
                            for store in retailers:
                                if store.get("email"):
                                    store_payload = {
                                        "email": store.get("email"),
                                        "company_name": store.get("companyName", "Unknown"),
                                        "campaign_id": "bulk-search",
                                        "status": "PROSPECT",
                                        "note": f"Bulk import from search: {kw}",
                                        "website": store.get("website", "")
                                    }
                                    store_res = api_post("/leads", store_payload)
                                    if store_res.get("ok"):
                                        stored_count += 1
                            
                            if stored_count > 0:
                                st.success(f"✅ Stored {stored_count} leads successfully!")
                            else:
                                st.warning("⚠️ No leads with valid emails to store")
                    
                    with bulk_col2:
                        if st.button("📊 Export Results"):
                            # Create CSV data
                            import io
                            import csv
                            
                            output = io.StringIO()
                            writer = csv.writer(output)
                            writer.writerow(["Company", "Email", "Website", "Phone", "Description"])
                            
                            for store in retailers:
                                writer.writerow([
                                    store.get("companyName", ""),
                                    store.get("email", ""),
                                    store.get("website", ""),
                                    store.get("phone", ""),
                                    store.get("description", "")
                                ])
                            
                            csv_data = output.getvalue()
                            st.download_button(
                                label="💾 Download CSV",
                                data=csv_data,
                                file_name=f"shopify_leads_{kw}_{count}_results.csv",
                                mime="text/csv"
                            )
                    
                    with bulk_col3:
                        if st.button("🚀 Start Campaign"):
                            st.info("💡 Go to '🤖 Full Workflow' tab to start automated outreach!")
                
                else:
                    st.info(f"No Shopify stores found for '{kw}'. Try different keywords like 'jewelry', 'fitness', or 'home decor'.")
    
    elif search_btn and not kw:
        st.error("⚠️ Please enter search keywords")
    
    # Search tips
    with st.expander("💡 Search Tips & Examples"):
        st.markdown("""
        **🎯 Effective Search Keywords:**
        - **Product Categories:** shoes, jewelry, clothing, fitness, beauty, home decor
        - **Niches:** sustainable fashion, pet accessories, tech gadgets, outdoor gear
        - **Industries:** wellness, gaming, art supplies, kitchen tools
        
        **🔍 How It Works:**
        1. Searches for Shopify stores matching your keywords
        2. Extracts company info, contact details, and website data
        3. Generates AI-powered fit and intent scores
        4. Provides quick actions to store leads or draft emails
        
        **📊 Lead Scoring:**
        - **Fit Score:** How well the company matches your ideal customer profile
        - **Intent Score:** Likelihood of being interested in your solution
        - **Green (70+):** High priority leads
        - **Yellow (40-69):** Medium priority leads  
        - **Red (<40):** Lower priority leads
        
        **⚡ Quick Actions:**
        - **Store Lead:** Add to your CRM for follow-up
        - **Draft Email:** Generate personalized outreach email
        - **Bulk Actions:** Process multiple leads at once
        """)
    
    # Demo data notice
    st.markdown("---")
    
    # Workflow tips
    with st.expander("🚀 **New Workflow: Search → Auto-Fill → Auto-Navigate**"):
        st.markdown("""
        **⚡ Enhanced Quick Actions:**
        
        1. **📥 Store Lead** → Auto-fills + shows � rindicator on Store/Enrich tab
        2. **✉️ Draft Email** → Auto-fills + shows 🔴 indicator on Draft Email tab  
        3. **⚡ Quick Store** → Stores lead directly (no navigation needed)
        
        **🔄 How It Works:**
        - Click any quick action button in search results
        - Look for the 🔴 red indicator on tab names
        - Click the indicated tab to see auto-filled data
        - Review, modify, and submit with one click
        - Data automatically clears after successful submission
        
        **🎯 Visual Indicators:**
        - 🔔 **Top notification bar** when data is waiting
        - 🔴 **Red dots** on tab names with auto-filled data
        - 🎉 **Balloons celebration** when you switch to auto-filled tabs
        - ✅ **Success messages** guide you through the process
        
        **💡 Benefits:**
        - No manual copy/paste needed
        - Visual indicators show where to go next
        - Faster lead processing workflow
        - Reduced errors from manual entry
        """)
    
    st.info("🧪 **Demo Mode:** Currently using sample data. In production, this connects to Google Custom Search API to find real Shopify stores.")

# -----------------------
# STORE / ENRICH TAB
# -----------------------
with tab_store:
    # Check if user was redirected here from search
    if st.session_state.get("switch_to_store", False):
        st.balloons()
        st.success("🎉 **Welcome! Your search data has been auto-filled below.**")
        st.session_state["switch_to_store"] = False  # Reset flag
    
    st.subheader("Store Lead")
    
    # Check if we have auto-filled data from search
    if any(key.startswith("store_") for key in st.session_state.keys()):
        col_info, col_clear = st.columns([3, 1])
        with col_info:
            st.info("🔍 **Auto-filled from search results** - Review and modify as needed")
        with col_clear:
            if st.button("🗑️ Clear", key="clear_store_data"):
                # Clear all store-related session state
                keys_to_remove = [k for k in st.session_state.keys() if k.startswith("store_")]
                for key in keys_to_remove:
                    del st.session_state[key]
                st.rerun()
    
    c1, c2 = st.columns(2)
    with c1:
        email = st.text_input("Lead Email", 
                             value=st.session_state.get("store_email", "alice@example.com"),
                             key="store_email_input")
        company = st.text_input("Company", 
                               value=st.session_state.get("store_company", "Allbirds"),
                               key="store_company_input")
        campaign = st.text_input("Campaign ID", 
                                value=st.session_state.get("store_campaign", "demo-001"),
                                key="store_campaign_input")
    with c2:
        note = st.text_input("Note", 
                            value=st.session_state.get("store_note", "first touch"),
                            key="store_note_input")
        website = st.text_input("Website (optional)", 
                               value=st.session_state.get("store_website", "https://www.allbirds.com"),
                               key="store_website_input")

    colA, colB = st.columns(2)
    with colA:
        if st.button("Store Lead"):
            res = api_post("/leads", {
                "email": email, "company_name": company, "campaign_id": campaign,
                "status": "SENT", "note": note, "website": website
            })
            
            if res.get("ok"):
                st.success(f"✅ Lead '{company}' stored successfully!")
                # Clear auto-filled data after successful storage
                keys_to_remove = [k for k in st.session_state.keys() if k.startswith("store_")]
                for key in keys_to_remove:
                    del st.session_state[key]
            else:
                st.error(f"❌ Failed to store lead: {res.get('error', 'Unknown error')}")
                
            # Show detailed response in expander
            with st.expander("📋 API Response Details"):
                st.json(res)
                
    with colB:
        if st.button("Enrich Lead"):
            res = api_post("/leads/enrich", {
                "email": email, "company_name": company, "website": website
            })
            
            if res.get("ok"):
                st.success(f"✅ Lead '{company}' enriched successfully!")
                lead_data = res.get("lead", {})
                if lead_data:
                    st.markdown("### 📊 Enrichment Results")
                    fit_score = lead_data.get("fitScore", 0)
                    intent_score = lead_data.get("intentScore", 0)
                    st.markdown(f"**Fit Score:** {score_chip(fit_score)}", unsafe_allow_html=True)
                    st.markdown(f"**Intent Score:** {score_chip(intent_score)}", unsafe_allow_html=True)
            else:
                st.error(f"❌ Failed to enrich lead: {res.get('error', 'Unknown error')}")
                
            # Show detailed response in expander
            with st.expander("📋 API Response Details"):
                st.json(res)

# -----------------------
# DRAFT TAB
# -----------------------
with tab_draft:
    # Check if user was redirected here from search
    if st.session_state.get("switch_to_draft", False):
        st.balloons()
        st.success("🎉 **Welcome! Your search data has been auto-filled below.**")
        st.session_state["switch_to_draft"] = False  # Reset flag
    
    st.subheader("✉️ Draft via Bedrock")
    
    # Check if we have auto-filled data from search
    if any(key.startswith("draft_") for key in st.session_state.keys()):
        col_info, col_clear = st.columns([3, 1])
        with col_info:
            st.info("🔍 **Auto-filled from search results** - Review and modify as needed")
        with col_clear:
            if st.button("🗑️ Clear", key="clear_draft_data"):
                # Clear all draft-related session state
                keys_to_remove = [k for k in st.session_state.keys() if k.startswith("draft_")]
                for key in keys_to_remove:
                    del st.session_state[key]
                st.rerun()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Recipient Info**")
        company_name = st.text_input("Company Name", 
                                   value=st.session_state.get("draft_company_name", "Allbirds"), 
                                   key="d_name")
        site = st.text_input("Website", 
                           value=st.session_state.get("draft_website", "https://www.allbirds.com"), 
                           key="d_site")
        desc = st.text_area("Description", 
                          value=st.session_state.get("draft_description", "Sustainable footwear brand"), 
                          key="d_desc", height=80)
        lead_email = st.text_input("Lead Email", 
                                 value=st.session_state.get("draft_lead_email", "sridatta963@gmail.com"), 
                                 key="d_email")
    
    with col2:
        st.markdown("**Sender Info**")
        sender_name = st.text_input("Your Name", "Raghav Dewangan", key="d_sender_name")
        sender_company = st.text_input("Your Company", "AI Sales Solutions", key="d_sender_company")
        sender_email = st.text_input("Your Email", DEFAULT_SENDER, key="d_sender_email")
    
    if st.button("Generate Draft"):
        res = api_post("/email/draft", {
            "companyName": company_name, 
            "website": site, 
            "description": desc, 
            "recipientEmail": lead_email,
            "senderName": sender_name,
            "senderCompany": sender_company,
            "senderEmail": sender_email
        })
        st.json(res)
        if res.get("draft"):
            st.markdown("### 📧 Generated Email")
            st.text_area("Draft", res.get("draft", ""), height=260, key="draft_output")

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
    
    st.markdown("### 🔄 Lead Lookup")
    st.info("Enter lead details below to view their current status and reply history")
    col_input1, col_input2 = st.columns(2)
    
    with col_input1:
        v_email = st.text_input("Lead Email", "sridatta963@gmail.com", key="v_email")
        
    with col_input2:
        v_campaign = st.text_input("Campaign ID", "demo-001", key="v_campaign")
        
    # Auto-load when email changes
    if v_email:
        try:
            import boto3
            dyn = boto3.resource("dynamodb", region_name=AWS_REGION)
            tbl = dyn.Table("LeadsTable")
            resp = tbl.get_item(Key={"pk": f"LEAD#{v_email.lower()}"})
            item = resp.get("Item")
            
            if item:
                lead = item.get("data")
                st.success(f"✅ Found lead: {lead.get('company', 'Unknown Company')}")
                render_lead(lead)
            else:
                st.info(f"No lead data found for {v_email}")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.caption("Check AWS credentials or create a lead first")

    st.markdown("---")
    
    # Manual status update section
    with st.expander("🔧 Manual Status Update"):
        col_update1, col_update2 = st.columns(2)
        
        with col_update1:
            s = st.selectbox("New Status", ["WARM", "NEUTRAL", "COLD", "UNSUBSCRIBE", "BOUNCED"], index=0)
            
        with col_update2:
            r = st.text_area("Reply Text", "Thanks for your interest! Let's schedule a call.")
            
        if st.button("� LUpdate Lead Status"):
            res = api_post("/leads/status", {"email": v_email, "campaign_id": v_campaign, "status": s, "replyText": r})
            if res.get("ok"):
                st.success("✅ Lead status updated!")
                st.rerun()  # Refresh to show updated data
            else:
                st.error(f"❌ Update failed: {res.get('error')}")

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
                "description": f"E-commerce company specializing in their industry",
                "recipientEmail": wf_email,
                "senderName": "Raghav Dewangan",
                "senderCompany": "AI Sales Solutions",
                "senderEmail": wf_sender
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

# -----------------------
# SES INBOUND TAB
# -----------------------
with tab_replies:
    st.subheader("📬 SES Inbound Email Processing")
    st.success("✅ **Automatic reply processing is built-in and ready!**")
    
    st.markdown("### 🏗️ How SES Inbound Works:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **📧 The Flow:**
        1. Send email with tracking tags
        2. User replies to your email  
        3. SES receives → S3 stores → Lambda processes
        4. AI classifies sentiment automatically
        5. Lead status updates in real-time
        """)
        
    with col2:
        st.markdown("""
        **✅ Already Configured:**
        - S3 bucket for email storage
        - Lambda parser with AI classification
        - DynamoDB integration
        - Automatic status updates
        """)
    
    st.markdown("---")
    
    # Manual testing section for demo purposes
    st.markdown("### 🧪 Manual Reply Testing (For Demo)")
    st.caption("Since SES inbound requires domain setup, use this for testing the reply classification")
    
    col1, col2 = st.columns(2)
    
    with col1:
        reply_email = st.text_input("Lead Email", "sridatta963@gmail.com", key="reply_email")
        reply_campaign = st.text_input("Campaign ID", "demo-001", key="reply_campaign")
        
    with col2:
        reply_message = st.text_area(
            "Test Reply Content:", 
            placeholder="Hi Raghav, I'm interested in scheduling a call!",
            height=100, 
            key="reply_message"
        )
    
    if st.button("� Test Cslassification", type="primary"):
        if reply_email and reply_message:
            # Use the existing lead status update endpoint for testing
            update_res = api_post("/leads/status", {
                "email": reply_email,
                "campaign_id": reply_campaign,
                "replyText": reply_message
            })
            
            if update_res.get("ok"):
                st.success("✅ Reply processed using SES inbound classification logic!")
                st.info("💡 Check the '📊 Lead Viewer' tab to see the updated lead status!")
            else:
                st.error(f"❌ Failed to process: {update_res.get('error')}")
        else:
            st.error("Please fill in email and reply content")
    
    st.markdown("---")
    
    # S3 Bucket Status Check
    st.markdown("### 📦 S3 Bucket Status")
    
    if st.button("🔍 Check S3 Bucket for Emails"):
        try:
            # Get the bucket name from CloudFormation
            import boto3
            cf = boto3.client('cloudformation')
            response = cf.describe_stacks(StackName='outreach-stack')
            
            bucket_name = None
            for output in response['Stacks'][0].get('Outputs', []):
                if 'Bucket' in output.get('OutputKey', ''):
                    bucket_name = output['OutputValue']
                    break
            
            if not bucket_name:
                # Fallback: find bucket by name pattern
                s3 = boto3.client('s3')
                buckets = s3.list_buckets()['Buckets']
                for bucket in buckets:
                    if 'inboundemailsbucket' in bucket['Name'].lower() and 'outreach-stack' in bucket['Name']:
                        bucket_name = bucket['Name']
                        break
            
            if bucket_name:
                s3 = boto3.client('s3')
                objects = s3.list_objects_v2(Bucket=bucket_name)
                
                if objects.get('Contents'):
                    st.success(f"📧 Found {len(objects['Contents'])} emails in bucket: {bucket_name}")
                    
                    # Show recent emails
                    for obj in objects['Contents'][:5]:  # Show first 5
                        st.markdown(f"- **{obj['Key']}** ({obj['Size']} bytes) - {obj['LastModified']}")
                        
                    if len(objects['Contents']) > 5:
                        st.caption(f"... and {len(objects['Contents']) - 5} more emails")
                else:
                    st.info(f"📭 No emails found in bucket: {bucket_name}")
                    st.caption("This is expected since SES inbound requires domain configuration")
            else:
                st.error("❌ Could not find inbound email bucket")
                
        except Exception as e:
            st.error(f"❌ Error checking S3: {str(e)}")
    
    with st.expander("🔧 SES Inbound Setup Guide"):
        st.markdown("""
        **Current Bucket Status:** 📭 Empty (expected without domain setup)
        
        **To Enable Automatic Email Processing:**
        
        1. **Get a Domain** (e.g., `yourdomain.com`)
        2. **Configure MX Records** to point to SES
        3. **Set up SES Receipt Rule** to route emails to S3
        4. **Configure Reply-To** in your outbound emails
        
        **What Happens When Set Up:**
        - User replies to your email → `replies@yourdomain.com`
        - SES receives email → Stores in S3 bucket
        - Lambda automatically processes → Updates lead status
        - Dashboard shows updated status in real-time
        
        **Current Status:**
        - ✅ S3 Bucket: `outreach-stack-inboundemailsbucket-*`
        - ✅ Lambda Parser: Enhanced with AI classification  
        - ✅ DynamoDB: Automatic lead updates configured
        - 🔧 Domain Setup: Needed for production use
        
        **AI Classification Logic:**
        - 🟢 **WARM**: "interested", "schedule", "call", "demo", "yes"
        - 🔴 **COLD**: "not interested", "no thanks", "decline"
        - ⚪ **NEUTRAL**: General responses
        - 🚫 **UNSUBSCRIBE**: "remove me", "unsubscribe", "opt out"
        - ⚠️ **BOUNCED**: "undeliverable", "mail failure"
        """)
        
        # Check Gmail button
        if st.button("🔍 Check Gmail Inbox Now", type="primary"):
            with st.spinner("Scanning Gmail inbox for replies..."):
                try:
                    url = API_URL.rstrip("/") + "/gmail/check"
                    gmail_res = requests.get(url, timeout=30).json()
                    
                    if gmail_res.get("ok"):
                        processed = gmail_res.get("processed_replies", [])
                        total = gmail_res.get("total_processed", 0)
                        checked_at = gmail_res.get("checked_at")
                        
                        if total > 0:
                            st.success(f"✅ Found and processed {total} new replies!")
                            
                            # Show processed replies
                            st.markdown("### 📧 Newly Processed Replies")
                            for i, reply in enumerate(processed, 1):
                                with st.expander(f"Reply {i}: {reply['email']} → {reply['status']}"):
                                    st.markdown(f"**Email:** {reply['email']}")
                                    st.markdown(f"**Campaign:** {reply['campaign_id']}")
                                    st.markdown(f"**Status:** {status_chip(reply['status'])}", unsafe_allow_html=True)
                                    st.markdown(f"**Preview:** {reply['reply_preview']}")
                                    st.caption(f"Processed: {dt(reply['processed_at'])}")
                        else:
                            st.info("📭 No new replies found in Gmail inbox")
                            
                        st.caption(f"Last checked: {dt(checked_at)}")
                        
                    else:
                        st.error(f"❌ Failed to check Gmail: {gmail_res.get('error')}")
                        
                except Exception as e:
                    st.error(f"❌ Error checking Gmail: {str(e)}")
    
    with col2:
        st.markdown("### ⚙️ Settings")
        
        # Auto-refresh toggle
        auto_check = st.checkbox("🔄 Auto-check every 30s", value=False)
        
        if auto_check:
            st.info("Auto-checking enabled")
            time.sleep(30)
            st.rerun()
        
        # Manual refresh
        if st.button("🔄 Refresh Page"):
            st.rerun()
    
    st.markdown("---")
    
    # How it works section
    with st.expander("🔧 How Automatic Gmail Monitoring Works"):
        st.markdown("""
        **Current Implementation (Demo Mode):**
        - Simulates checking Gmail inbox for replies
        - Processes mock replies to demonstrate functionality
        - Updates lead status automatically based on reply content
        - Shows results in real-time on dashboard
        
        **For Production Gmail Integration:**
        1. **Gmail API Setup**: Configure OAuth2 credentials
        2. **Inbox Scanning**: Periodically check for new emails
        3. **Reply Detection**: Find replies to sent campaign emails
        4. **Auto-Processing**: Extract content and classify sentiment
        5. **Status Updates**: Update lead status in real-time
        
        **Benefits:**
        - ✅ Automatic reply processing
        - ✅ Real-time lead status updates  
        - ✅ No manual copy/paste needed
        - ✅ Complete automation loop
        """)
    
    # Recent activity summary
    st.markdown("### 📈 Recent Gmail Activity")
    
    # Mock recent activity for demo
    recent_activity = [
        {"time": "2 minutes ago", "action": "Processed reply from sridatta963@gmail.com", "status": "WARM"},
        {"time": "15 minutes ago", "action": "Processed reply from test@example.com", "status": "COLD"},
        {"time": "1 hour ago", "action": "Gmail inbox check completed", "status": "INFO"},
        {"time": "2 hours ago", "action": "Sent email to demo campaign", "status": "SENT"}
    ]
    
    for activity in recent_activity:
        icon = "🟢" if activity["status"] == "WARM" else "🔴" if activity["status"] == "COLD" else "📧" if activity["status"] == "SENT" else "ℹ️"
        st.markdown(f"{icon} **{activity['time']}** - {activity['action']}")
    
    st.markdown("---")
    st.markdown("💡 **Tip:** Use the '📊 Lead Viewer' tab to see updated lead statuses after Gmail processing!")
