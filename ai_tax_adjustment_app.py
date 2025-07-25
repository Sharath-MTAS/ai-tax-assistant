# ai_tax_adjustment_app.py - Streamlit AI Tax Adjustment Assistant with Admin Password Reset + Logs

import streamlit as st
import pandas as pd
import io
import os
import json
import hashlib
import difflib
from pandas import ExcelWriter
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from streamlit_option_menu import option_menu

# Load environment variables
load_dotenv()

# ------------------ CONFIG ------------------
ADMIN_USERS = ["sharath@mtasllp.com"]
USERS_FILE = "users.json"
LOG_FILE = "reset_log.json"

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def log_reset(admin, target_user):
    log_entry = {
        "admin": admin,
        "user": target_user,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)
    logs.append(log_entry)
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

def load_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    return []

# ------------------ STREAMLIT SETUP ------------------
st.set_page_config(page_title="AI Tax Adjustment Assistant", layout="wide")

# Session Init
if "username" not in st.session_state:
    st.session_state.username = None
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# ------------------ LOGIN / SIGNUP ------------------
users = load_users()

if st.session_state.username is None:
    login_tab, register_tab = st.tabs(["🔐 Login", "🆕 Register"])

    with login_tab:
        st.subheader("Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            hashed = hash_password(password)
            if email in users and users[email] == hashed:
                st.session_state.username = email
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials.")

    with register_tab:
        st.subheader("Register")
        new_email = st.text_input("New Email")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            if not new_email or not new_pass:
                st.warning("Fill all fields.")
            elif "@" not in new_email:
                st.warning("Use valid email.")
            elif new_email in users:
                st.warning("User already exists.")
            else:
                users[new_email] = hash_password(new_pass)
                save_users(users)
                st.success("Account created! Log in now.")
    st.stop()

# -------- MAIN APP --------
st.sidebar.markdown(f"👤 Logged in as: `{st.session_state.username}`")
if st.sidebar.button("🚪 Sign Out"):
    del st.session_state.username
    st.rerun()




# -------------- MAIN APP AFTER LOGIN ----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Poppins', sans-serif !important;
    }
    </style>
""", unsafe_allow_html=True)
st.markdown("""
    <h1 style='font-family: Poppins, sans-serif; font-size: 36px; margin-bottom: 0;'>📊 AI Tax Adjustment Assistant</h1>
    <p style='font-family: Poppins, sans-serif; font-size: 16px;'>
        Welcome to your AI-powered platform for trial balance review, tax adjustments, and M-1 reconciliation.
    </p>
""", unsafe_allow_html=True)

# Sidebar navigation
if st.session_state.username:
    st.sidebar.markdown(f"👤 **Logged in as:** `{st.session_state.username}`")
    if st.sidebar.button("🚪 Sign Out", key="sign_out_button"):
        del st.session_state["username"]
        st.rerun()


with st.sidebar:
    menu = option_menu(
        "Navigation",
        [
            "Select/Create Client",
            "Upload TB & Mapping",
            "Review/Edit Lacerte Mapping",
            "M-1 Adjustments",
            "Download Workpaper",
            "State Nexus & Apportionment",
            "Shared Notes",
            "Admin Panel" if st.session_state.username in ADMIN_USERS else "–––"
        ],
        icons=[
            "person-plus", "cloud-upload", "list-check",
            "sliders", "download", "globe", "chat-dots",
            "gear" if st.session_state.username in ADMIN_USERS else "dash"
        ],
        menu_icon="cast",
        default_index=0,
        orientation="vertical"  # ⬅️ Ensure the menu appears in the sidebar
    )

# ------------------ ADMIN PANEL ------------------
if menu == "Admin Panel" and st.session_state.username in ADMIN_USERS:
    st.header("🔐 Admin Password Reset Panel")

    all_users = [u for u in users if u not in ADMIN_USERS]
    selected_user = st.selectbox("Select user to reset password", all_users)
    new_pass = st.text_input("New password", type="password")
    if st.button("Reset Password"):
        if selected_user and new_pass:
            users[selected_user] = hash_password(new_pass)
            save_users(users)
            log_reset(admin=st.session_state.username, target_user=selected_user)
            st.success(f"Password reset for {selected_user}")

    st.markdown("---")
    st.subheader("📜 Reset Logs")
    logs = load_logs()
    for log in logs[::-1]:
        st.markdown(f"- **{log['timestamp']}** — `{log['admin']}` reset password for `{log['user']}`")

# ------------------ OTHER SECTIONS PLACEHOLDER ------------------
if menu != "Admin Panel":
    st.success(f"📌 Welcome, {st.session_state.username}! You selected '{menu}' module.")
    st.info("App logic for this section goes here.")

# ------------------ NOTES SHARING SECTION ------------------
if menu == "Shared Notes":
    st.header("📝 Team Notes")
    notes_file = "shared_notes.json"
    if not os.path.exists(notes_file):
        with open(notes_file, 'w') as f:
            json.dump([], f)

    with open(notes_file, 'r') as f:
        notes = json.load(f)

    for note in notes:
        st.markdown(f"**{note['user']}** ({note['timestamp']}): {note['content']}")

    with st.form("add_note"):
        content = st.text_area("Add Note")
        submitted = st.form_submit_button("Post")
        if submitted and content:
            import datetime
            new_note = {
                "user": st.session_state.username,
                "timestamp": str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
                "content": content
            }
            notes.append(new_note)
            with open(notes_file, 'w') as f:
                json.dump(notes, f, indent=2)
            st.success("Note posted!")
            st.rerun()


# Globals
client_data = {}
tb_df = adj_df = atb_df = mapping_df = None
mapping_options = []

# Helper: save to file
def auto_save_client_data():
    filename = st.session_state.client_info["filename"]
    with open(filename, 'w') as f:
        json.dump({
            "tb_df": st.session_state.tb_df.to_dict() if "tb_df" in st.session_state else {},
            "adj_df": st.session_state.adj_df.to_dict() if "adj_df" in st.session_state else {},
            "mapping_df": st.session_state.mapping_df.to_dict() if "mapping_df" in st.session_state else {}
        }, f)
# AI Mapping Function
@st.cache_data
def ai_lacerte_match(account_desc, mapping_df):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    descriptions = mapping_df['Account Name'].astype(str).tolist()
    tfidf = TfidfVectorizer().fit_transform([account_desc] + descriptions)
    similarity = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
    best_idx = similarity.argmax()
    return mapping_df.iloc[best_idx]['Tax Line assignments'] if similarity[best_idx] > 0.3 else ""

# GPT-based M-1 Adjustment Suggestion
@st.cache_data
def gpt_m1_suggestion(desc, amount):
    prompt = f"Analyze the following expense description and suggest if it's a deductible, nondeductible, or partial M-1 adjustment for tax purposes.\\n\\nDescription: {desc}\\nAmount: {amount}\\n\\nClassify and explain:"
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = f"Error: {e}"
    return reply

# AI Nexus Justification
@st.cache_data
def generate_nexus_explanation(state, revenue, payroll, rule):
    try:
        explanation = f"For state {state}, the revenue reported is ${revenue:,} and payroll is ${payroll:,}. "
        explanation += f"The thresholds for filing are Revenue: ${rule['revenue_threshold']:,} and Payroll: ${rule['payroll_threshold']:,}. "
        explanation += f"The apportionment method used is '{rule['formula']}'. "
        if revenue >= rule['revenue_threshold'] or payroll >= rule['payroll_threshold']:
            explanation += "Thus, the filing requirement is met."
        else:
            explanation += "Thus, the filing requirement is not met."
    except Exception as e:
        explanation = f"Error generating explanation: {e}"
    return explanation


# Load existing clients
client_list = [f.replace(".json", "") for f in os.listdir() if f.endswith(".json")]
if "client_info" not in st.session_state:
    st.session_state.client_info = {"client_name": "", "tax_year": "", "filename": ""}

# 1. Select or Create Client
if menu == "Select/Create Client":
    selected_client = st.selectbox("Select Existing Client or Enter New", ["New Client"] + client_list)
    if selected_client == "New Client":
        client_name = st.text_input("Enter New Client Name")
        tax_year = st.text_input("Enter Tax Year")
        if st.button("Create Client"):
            filename = f"{client_name}_{tax_year}.json"
            with open(filename, 'w') as f:
                json.dump({}, f)
            st.session_state.client_info = {"client_name": client_name, "tax_year": tax_year, "filename": filename}
            st.success(f"New client created: {filename}")
    else:
        filename = f"{selected_client}.json"
        with open(filename, 'r') as f:
            client_data = json.load(f)
        client_name = selected_client.rsplit("_", 1)[0]
        tax_year = selected_client.rsplit("_", 1)[1]
        st.session_state.client_info = {"client_name": client_name, "tax_year": tax_year, "filename": filename}

        if client_data:
            if "tb_df" in client_data:
                st.session_state.tb_df = pd.DataFrame(client_data["tb_df"])
            if "adj_df" in client_data:
                st.session_state.adj_df = pd.DataFrame(client_data["adj_df"])
            if "mapping_df" in client_data:
                st.session_state.mapping_df = pd.DataFrame(client_data["mapping_df"])
            st.success("Client data loaded successfully")

# Upload TB & Mapping section indentation fix
if menu == "Upload TB & Mapping":
    tb_tab, map_tab = st.tabs(["📘 Trial Balance Upload", "🗂️ Mapping File Upload"])

    with tb_tab:
        st.header("Upload Trial Balance")
        tb_file = st.file_uploader("Upload Trial Balance (.xlsx)", type=["xlsx"])
        if tb_file:
            with st.spinner("Processing Trial Balance..."):
                tb_df = pd.read_excel(tb_file, sheet_name="TB")
                st.session_state.tb_df = tb_df
                st.success("Trial Balance loaded successfully!")
                st.dataframe(tb_df)

        if "tb_df" in st.session_state:
            st.markdown("### ✏️ Edit Trial Balance")
            edited_tb = st.data_editor(st.session_state.tb_df, num_rows="dynamic")
            if st.button("Save Edited TB", key="save_tb_edit"):
                st.session_state.tb_df = edited_tb
                auto_save_client_data()
                st.success("✅ Trial Balance updated.")

    with map_tab:
        st.header("Upload Master Mapping File")
        mapping_file = st.file_uploader("Upload Master Mapping (.xlsx)", type=["xlsx"])
        if mapping_file:
            with st.spinner("Loading Mapping File..."):
                mapping_df = pd.read_excel(mapping_file)
                st.session_state.mapping_df = mapping_df
                mapping_options = sorted(mapping_df["Tax Line assignments"].dropna().unique().tolist())
                st.session_state.mapping_options = mapping_options
                st.success("Mapping file loaded!")
                st.dataframe(mapping_df)

# 3. M-1 Adjustments
if menu == "M-1 Adjustments" and "tb_df" in st.session_state:
    tb_df = st.session_state.tb_df.copy()
    prompts = []
    if "adj_df" in st.session_state:
        st.markdown("### ✏️ Edit Existing M-1 Adjustments")
        editable_adj_df = st.data_editor(st.session_state.adj_df, num_rows="dynamic")
        if st.button("Save Edited M-1 Adjustments"):
            st.session_state.adj_df = editable_adj_df
            auto_save_client_data()
            st.success("✅ M-1 Adjustments updated.")

    for i, row in tb_df.iterrows():
        desc = str(row['Account Description']).lower()
        amt = row['Amount']
        acc_type = str(row.get('Type', '')).lower()
        if 'insurance' in desc:
            prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'deductibility', 'category': 'Prepaid Insurance'})
        elif 'meals' in desc:
            prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'meals', 'category': 'Meals and Entertainment'})
        elif 'entertainment' in desc:
            prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'nondeductible', 'category': 'Entertainment'})
        elif 'depreciation' in desc and acc_type == 'expense':
            prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'custom', 'category': 'Depreciation'})
        elif 'penalty' in desc:
            prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'nondeductible', 'category': 'Penalties'})

    adj_rows = []
    st.header("AI-Prompted Adjustments")
    for p in prompts:
        st.markdown(f"**{p['account']}** — Book Amount: ${p['book_amt']:,.2f}")
        tax_amt = 0.0
        if p['type'] == 'deductibility':
            choice = st.radio(f"{p['account']}?", ["Fully deductible", "Prepaid", "Partially deductible"], key=p['account'])
            tax_amt = p['book_amt'] if choice == "Fully deductible" else (0.0 if choice == "Prepaid" else st.number_input("Enter deductible portion", key=f"num_{p['account']}", value=0.0))
        elif p['type'] == 'meals':
            choice = st.radio(f"{p['account']}?", ["50% deductible", "Custom"], key=p['account'])
            tax_amt = p['book_amt'] * 0.5 if choice == "50% deductible" else st.number_input("Enter deductible portion", key=f"num_{p['account']}", value=0.0)
        elif p['type'] == 'nondeductible':
            tax_amt = 0.0
        elif p['type'] == 'custom':
            tax_amt = st.number_input("Enter deductible portion", key=f"num_{p['account']}", value=0.0)

        adj_type = "Permanent" if p['type'] == 'nondeductible' else "Temporary"
        adj_rows.append({
            'Account': p['account'],
            'Book Amount': p['book_amt'],
            'Tax Amount': tax_amt,
            'Adjustment': p['book_amt'] - tax_amt,
            'Adjustment Type': adj_type,
            'M-1 Category': p['category']
        })

    # Custom M-1 entry
    st.markdown("### ➕ Add Custom M-1 Adjustment")
    with st.form("custom_m1_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            custom_account = st.text_input("Account")
        with col2:
            custom_book = st.number_input("Book Amount", value=0.0)
        with col3:
            custom_tax = st.number_input("Tax Amount", value=0.0)
        custom_type = st.selectbox("Adjustment Type", ["Temporary", "Permanent"])
        custom_category = st.text_input("M-1 Category", value="Other")
        submitted = st.form_submit_button("Add Custom Entry")
        if submitted:
            adj_rows.append({
                'Account': custom_account,
                'Book Amount': custom_book,
                'Tax Amount': custom_tax,
                'Adjustment': custom_book - custom_tax,
                'Adjustment Type': custom_type,
                'M-1 Category': custom_category
            })
            st.success("Custom M-1 added!")

    if adj_rows:
        adj_df = pd.DataFrame(adj_rows)
        st.session_state.adj_df = adj_df
        auto_save_client_data()
        st.dataframe(adj_df)

# 4. Review/Edit Lacerte Mapping
if menu == "Review/Edit Lacerte Mapping" and "tb_df" in st.session_state and "adj_df" in st.session_state:
    tb_df = st.session_state.tb_df.copy()
    adj_df = st.session_state.adj_df.copy()
    mapping_df = st.session_state.get("mapping_df")
    mapping_options = st.session_state.get("mapping_options", [])

    # Apply adjustments
    atb_df = tb_df.copy()
    atb_df['Tax Adjustment'] = 0.0
    atb_df['Tax Balance'] = atb_df['Amount']
    atb_df['Lacerte Line'] = ""

    for i, row in atb_df.iterrows():
        acct_desc = row['Account Description']
        default = ""
        if mapping_df is not None:
            matches = difflib.get_close_matches(acct_desc.lower(), mapping_df["Account Name"].astype(str).str.lower(), n=1)
            if matches:
                match_row = mapping_df[mapping_df["Account Name"].str.lower() == matches[0]]
                if not match_row.empty:
                    default = match_row.iloc[0]["Tax Line assignments"]

        lacerte_val = st.selectbox(f"{acct_desc} — Lacerte Line", options=mapping_options, index=mapping_options.index(default) if default in mapping_options else 0, key=f"lac_{i}")
        atb_df.at[i, "Lacerte Line"] = lacerte_val

    for _, adj in adj_df.iterrows():
        match_idx = atb_df['Account Description'].str.lower() == adj['Account'].lower()
        atb_df.loc[match_idx, 'Tax Adjustment'] = adj['Adjustment']
        atb_df.loc[match_idx, 'Tax Balance'] = atb_df.loc[match_idx, 'Amount'] + adj['Adjustment']

        offset = {
            'Account Description': f"Offset - {adj['Account']}",
            'Account Number': '',
            'Amount': 0,
            'Type': 'Equity',
            'Tax Adjustment': -adj['Adjustment'],
            'Tax Balance': -adj['Adjustment'],
            'Lacerte Line': '',
            'DR/CR': 'DR' if adj['Adjustment'] < 0 else 'CR'
        }
        atb_df = pd.concat([atb_df, pd.DataFrame([offset])], ignore_index=True)

    st.session_state.atb_df = atb_df

    st.markdown("### ✏️ Edit Adjusted Trial Balance")
    editable_atb_df = st.data_editor(atb_df, num_rows="dynamic")
    if st.button("Save Adjusted TB", key="save_adj_tb"):
        st.session_state.atb_df = editable_atb_df
        auto_save_client_data()
        st.success("✅ Adjusted Trial Balance updated.")

    st.markdown("### 📄 Final Adjusted Trial Balance")
    st.dataframe(st.session_state.atb_df)

# 5. Download Workpaper

# 6. State Nexus & Apportionment
if menu == "State Nexus & Apportionment":
    st.header("📍 State Nexus & Apportionment")
    st.markdown("Upload revenue and payroll details to determine state filing requirements and calculate apportionment.")

    nexus_file = st.file_uploader("Upload State Revenue/Payroll File", type=["xlsx", "csv"])
    if nexus_file:
        if nexus_file.name.endswith(".csv"):
            state_df = pd.read_csv(nexus_file)
        else:
            state_df = pd.read_excel(nexus_file)

        st.write("### Raw Input Data")
        st.dataframe(state_df)

        # Sample rules - replace or extend with real data
        state_rules = {
  "AL": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "three_factor"},
  "AK": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "three_factor"},
  "AZ": {"revenue_threshold": 200000, "payroll_threshold": 25000, "formula": "sales"},
  "AR": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "CA": {"revenue_threshold": 69000, "payroll_threshold": 69000, "formula": "sales"},
  "CO": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "CT": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "three_factor"},
  "DE": {"revenue_threshold": 100000, "payroll_threshold": 5000, "formula": "three_factor"},
  "FL": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "GA": {"revenue_threshold": 250000, "payroll_threshold": 25000, "formula": "sales"},
  "HI": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "three_factor"},
  "ID": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "three_factor"},
  "IL": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "sales"},
  "IN": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "sales"},
  "IA": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "three_factor"},
  "KS": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "KY": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "LA": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "three_factor"},
  "ME": {"revenue_threshold": 250000, "payroll_threshold": 25000, "formula": "sales"},
  "MD": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "sales"},
  "MA": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "three_factor"},
  "MI": {"revenue_threshold": 350000, "payroll_threshold": 10000, "formula": "sales"},
  "MN": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "MS": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "three_factor"},
  "MO": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "MT": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "three_factor"},
  "NE": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "NV": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "sales"},
  "NH": {"revenue_threshold": 200000, "payroll_threshold": 25000, "formula": "three_factor"},
  "NJ": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "sales"},
  "NM": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "NY": {"revenue_threshold": 1000000, "payroll_threshold": 10000, "formula": "sales"},
  "NC": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "ND": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "OH": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "OK": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "OR": {"revenue_threshold": 750000, "payroll_threshold": 50000, "formula": "three_factor"},
  "PA": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "RI": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "three_factor"},
  "SC": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "SD": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "sales"},
  "TN": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "TX": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "UT": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "VT": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "three_factor"},
  "VA": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "sales"},
  "WA": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "sales"},
  "WV": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "three_factor"},
  "WI": {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"},
  "WY": {"revenue_threshold": 100000, "payroll_threshold": 10000, "formula": "sales"}
}




        results = []
        total_revenue = state_df['Revenue'].sum()
        total_payroll = state_df['Payroll'].sum()

        for _, row in state_df.iterrows():
            state = row['State']
            revenue = row['Revenue']
            payroll = row['Payroll']
            rules = state_rules.get(state, {"revenue_threshold": 500000, "payroll_threshold": 50000, "formula": "sales"})
            filing_required = (revenue >= rules["revenue_threshold"] or payroll >= rules["payroll_threshold"])

            if rules["formula"] == "sales":
                apportionment = revenue / total_revenue if total_revenue else 0
            elif rules["formula"] == "payroll":
                apportionment = payroll / total_payroll if total_payroll else 0
            else:
                apportionment = (revenue + payroll) / (total_revenue + total_payroll) if (total_revenue + total_payroll) else 0

            results.append({
                "State": state,
                "Revenue (Nominator)": revenue,
                "Revenue (Denominator)": total_revenue,
                "Payroll (Nominator)": payroll,
                "Payroll (Denominator)": total_payroll,
                "Apportionment %": round(apportionment * 100, 2),
                "Filing Required": "Yes" if filing_required else "No"
            })

        result_df = pd.DataFrame(results)
        st.write("### State Nexus & Apportionment Results")
        st.dataframe(result_df)

        st.download_button("📥 Download Nexus Report", data=result_df.to_csv(index=False), file_name="State_Nexus_Apportionment.csv")
if menu == "Download Workpaper":
    if all(k in st.session_state for k in ["tb_df", "adj_df", "atb_df"]):
        client = st.session_state.client_info
        tb_df = st.session_state.tb_df
        adj_df = st.session_state.adj_df
        atb_df = st.session_state.atb_df

        total_adj = adj_df['Adjustment'].sum()
        income = tb_df[tb_df['Type'].str.lower() == 'income']['Amount'].sum()
        expenses = tb_df[tb_df['Type'].str.lower() == 'expense']['Amount'].sum()
        book_income = income + expenses
        taxable_income = book_income + total_adj

        excel_buffer = io.BytesIO()
        with ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:

            # General Info tab
            pd.DataFrame({
                "Client Name": [client['client_name']],
                "Tax Year": [client['tax_year']],
                "Book Income": [book_income],
                "Taxable Income": [taxable_income]
            }).to_excel(writer, sheet_name="General Information", index=False)

            # M-1 IRS Summary
            pd.DataFrame({
                "IRS Schedule M-1 Line": [
                    "1. Net income (loss) per books",
                    "2. Federal income tax per books",
                    "3. Excess of capital losses over capital gains",
                    "4. Income subject to tax not recorded on books this year",
                    "5. Expenses recorded on books this year not deducted on this return",
                    "6. Add lines 1 through 5",
                    "7. Income recorded on books this year not included on this return",
                    "8. Deductions on this return not charged against book income",
                    "9. Add lines 7 and 8",
                    "10. Subtract line 9 from line 6. This is taxable income"
                ],
                "Amount": [
                    book_income,
                    0.0,
                    0.0,
                    0.0,
                    total_adj,
                    book_income + total_adj,
                    0.0,
                    0.0,
                    0.0,
                    book_income + total_adj
                ]
            }).to_excel(writer, sheet_name="M-1 Summary", index=False)

            

            # IRS Schedule M-1 Replica Summary
            pd.DataFrame({
                "IRS Schedule M-1 Line": [
                    "1. Net income (loss) per books",
                    "2. Federal income tax per books",
                    "3. Excess of capital losses over capital gains",
                    "4. Income subject to tax not recorded on books this year",
                    "5. Expenses recorded on books this year not deducted on this return",
                    "6. Add lines 1 through 5",
                    "7. Income recorded on books this year not included on this return",
                    "8. Deductions on this return not charged against book income",
                    "9. Add lines 7 and 8",
                    "10. Subtract line 9 from line 6. This is taxable income"
                ],
                "Amount": [
                    book_income,
                    0.0,
                    0.0,
                    0.0,
                    total_adj,
                    book_income + total_adj,
                    0.0,
                    0.0,
                    0.0,
                    book_income + total_adj
                ]
            }).to_excel(writer, sheet_name="M-1 Summary", index=False),
            pd.DataFrame({
                "Client Name": [client['client_name']],
                "Tax Year": [client['tax_year']],
                "Book Income": [book_income],
                "Taxable Income": [taxable_income]
            }).to_excel(writer, sheet_name="General Information", index=False)

            adj_df.to_excel(writer, sheet_name="M-1 Adjustments", index=False)
            tb_df.to_excel(writer, sheet_name="Original TB", index=False)
            atb_df.to_excel(writer, sheet_name="Adjusted TB", index=False)

            # Add journal entries per M-1 Adjustment (individual account)
            for idx, row in adj_df.iterrows():
                m1_name = row['Account'][:25]  # tab names must be ≤31 chars
                journal = pd.DataFrame([{
                    "Account": row['Account'],
                    "Book Amount": row['Book Amount'],
                    "Tax Amount": row['Tax Amount'],
                    "Adjustment": row['Adjustment'],
                    "Adjustment Type": row['Adjustment Type'],
                    "M-1 Category": row['M-1 Category'],
                    "DR/CR": 'DR' if row['Adjustment'] < 0 else 'CR'
                }, {
                    "Account": f"Offset - {row['Account']}",
                    "Book Amount": '',
                    "Tax Amount": '',
                    "Adjustment": -row['Adjustment'],
                    "Adjustment Type": 'Offset',
                    "M-1 Category": row['M-1 Category'],
                    "DR/CR": 'CR' if row['Adjustment'] < 0 else 'DR'
                }])
                journal.to_excel(writer, sheet_name=m1_name, index=False)

        excel_buffer.seek(0)
        st.download_button("📥 Download Tax Workpaper", data=excel_buffer, file_name=f"{client['client_name']}_{client['tax_year']}_Tax_Workpaper.xlsx")
