import streamlit as st
import pandas as pd
import io
import os
import json
import difflib
from pandas import ExcelWriter

st.set_page_config(page_title="AI Tax Adjustment Assistant", layout="wide")
st.title("📊 AI-Powered Tax Adjustment from Trial Balance")

# Step 1: Select or Create Client File
st.header("1. Select or Create Client File")
client_list = [f.replace(".json", "") for f in os.listdir() if f.endswith(".json")]
selected_client = st.selectbox("Select Existing Client or Enter New:", ["New Client"] + client_list)

if selected_client == "New Client":
    client_name = st.text_input("Enter New Client Name")
    tax_year = st.text_input("Enter Tax Year")
    if st.button("Create Client"):
        filename = f"{client_name}_{tax_year}.json"
        with open(filename, 'w') as f:
            json.dump({}, f)
        st.success(f"New client file created: {filename}")
else:
    client_name = selected_client.rsplit('_', 1)[0]
    tax_year = selected_client.rsplit('_', 1)[1]
    filename = f"{selected_client}.json"
    st.info(f"Editing file: {filename}")

# Step 2: Upload Master Mapping File
st.header("2. Upload Master Mapping File")
mapping_file = st.file_uploader("Upload Lacerte Mapping File (.xlsx)", type=["xlsx"], key="mapping")
mapping_df = None
tax_line_col = None
if mapping_file:
    try:
        mapping_df = pd.read_excel(mapping_file)
        tax_line_col = next((col for col in mapping_df.columns if "tax line" in col.lower()), None)
        st.success("Mapping file loaded.")
    except:
        st.warning("Failed to read the mapping file.")

# Step 3: Upload Trial Balance
st.header("3. Upload Trial Balance")
tb_file = st.file_uploader("Upload Trial Balance (.xlsx)", type=["xlsx"])

if tb_file:
    try:
        tb_df = pd.read_excel(tb_file, sheet_name='TB')
        st.success("Trial Balance loaded successfully.")
        st.dataframe(tb_df)

        tb_total = tb_df['Amount'].sum()
        is_balanced = abs(tb_total) < 1e-2
        st.markdown(f"📘 Trial Balance Footing: {'✅ Balanced' if is_balanced else f'❌ Not Balanced (${tb_total:,.2f})'}")

        if 'Type' in tb_df.columns:
            income = tb_df[tb_df['Type'].str.lower() == 'income']['Amount'].sum()
            expenses = tb_df[tb_df['Type'].str.lower() == 'expense']['Amount'].sum()
            book_income = income + expenses
            st.markdown(f"🧾 Book Income (Income + Expense): ${book_income:,.2f}")
        else:
            book_income = 0.0
            st.warning("⚠️ 'Type' column not found. Add column with 'Income', 'Expense', etc.")

        # Step 4: AI M-1 Prompt Generation
        st.header("4. AI-Prompted M-1 Adjustments")
        prompts = []
        for _, row in tb_df.iterrows():
            desc = str(row['Account Description']).lower()
            amt = row['Amount']
            acc_type = str(row['Type']).lower() if 'Type' in row else ''
            if 'insurance' in desc:
                prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'deductibility', 'category': 'Prepaid Insurance'})
            elif 'meals' in desc:
                prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'meals', 'category': 'Meals and Entertainment'})
            elif 'entertainment' in desc:
                prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'nondeductible', 'category': 'Entertainment'})
            elif 'depreciation' in desc and acc_type == 'expense':
                prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'custom', 'category': 'Depreciation'})
            elif 'amortization' in desc and acc_type == 'expense':
                prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'custom', 'category': 'Amortization'})
            elif 'rent' in desc or 'accrued' in desc:
                prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'deductibility', 'category': 'Accrued Expenses'})
            elif 'penalty' in desc or 'fine' in desc:
                prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'nondeductible', 'category': 'Penalties'})
            elif 'federal tax' in desc:
                prompts.append({'account': row['Account Description'], 'book_amt': amt, 'type': 'nondeductible', 'category': 'Federal Tax'})

        st.subheader("AI-Generated Adjustment Prompts")
        adj_rows = []
        for p in prompts:
            st.markdown(f"**Prompt:** Is **{p['account']}** of **${p['book_amt']:,.2f}** deductible or not?")
            tax_amt = None
            if p['type'] == 'deductibility':
                choice = st.radio("Choose:", ["✅ Fully deductible", "❌ Prepaid (Not deductible)", "✏️ Partially deductible"], key=p['account'])
                if "Fully" in choice:
                    tax_amt = p['book_amt']
                elif "Prepaid" in choice:
                    tax_amt = 0.0
                elif "Partial" in choice:
                    tax_amt = st.number_input(f"Enter deductible portion for {p['account']}", value=0.0, key=f"custom_{p['account']}")
            elif p['type'] == 'meals':
                choice = st.radio("Meals Treatment", ["✅ 50% deductible", "✏️ Enter custom"], key=p['account'])
                tax_amt = p['book_amt'] * 0.5 if "50%" in choice else st.number_input(f"Enter deductible amount", value=0.0, key=f"custom_{p['account']}")
            elif p['type'] == 'nondeductible':
                tax_amt = 0.0
            elif p['type'] == 'custom':
                tax_amt = st.number_input(f"Enter allowed amount for {p['account']}", value=0.0, key=f"custom_{p['account']}")

            adj_type = 'Permanent' if p['type'] in ['nondeductible'] else 'Temporary'
            adj_rows.append({
                'Account': p['account'],
                'Book Amount': p['book_amt'],
                'Tax Amount': tax_amt,
                'Adjustment': p['book_amt'] - tax_amt,
                'Adjustment Type': adj_type,
                'M-1 Category': p['category']
            })

        # Step 5: Custom M-1 Entry
        st.header("5. ➕ Add Custom M-1")
        with st.expander("Add Manual M-1 Adjustment"):
            custom_account = st.text_input("Account Description")
            custom_book = st.number_input("Book Amount", value=0.0)
            custom_tax = st.number_input("Tax Amount", value=0.0)
            custom_category = st.text_input("M-1 Category")
            custom_type = st.selectbox("Adjustment Type", ["Temporary", "Permanent"])
            if st.button("Add Custom"):
                adj_rows.append({
                    'Account': custom_account,
                    'Book Amount': custom_book,
                    'Tax Amount': custom_tax,
                    'Adjustment': custom_book - custom_tax,
                    'Adjustment Type': custom_type,
                    'M-1 Category': custom_category
                })

        if adj_rows:
            adj_df = pd.DataFrame(adj_rows)
            st.subheader("📄 M-1 Adjustments")
            st.dataframe(adj_df)

            # Final Adjusted TB + Mapping
            atb_df = tb_df.copy()
            atb_df['Tax Adjustment'] = 0.0
            atb_df['Tax Balance'] = atb_df['Amount']
            atb_df['Lacerte Line'] = ""

            for i, row in atb_df.iterrows():
                acct_num = str(row.get("Account Number", "")).strip()
                acct_desc = str(row.get("Account Description", "")).strip().lower()
                matched_line = ""
                if mapping_df is not None and tax_line_col:
                    match = mapping_df[mapping_df["Account Number"].astype(str).str.strip() == acct_num]
                    if not match.empty:
                        matched_line = match.iloc[0][tax_line_col]
                    elif acct_desc:
                        close = difflib.get_close_matches(acct_desc, mapping_df["Account Name"].astype(str).str.lower(), n=1, cutoff=0.6)
                        if close:
                            row_match = mapping_df[mapping_df["Account Name"].str.lower() == close[0]]
                            if not row_match.empty:
                                matched_line = row_match.iloc[0][tax_line_col]
                atb_df.at[i, 'Lacerte Line'] = matched_line

            # Apply Adjustments + Offsets
            journal_entries = []
            for _, adj in adj_df.iterrows():
                idx = atb_df['Account Description'].str.lower() == adj['Account'].lower()
                atb_df.loc[idx, 'Tax Adjustment'] = adj['Adjustment']
                atb_df.loc[idx, 'Tax Balance'] = atb_df.loc[idx, 'Amount'] + adj['Adjustment']
                journal_entries.append({
                    'Account Description': f"Offset - {adj['Account']}",
                    'Account Number': '',
                    'Amount': 0,
                    'Type': 'Equity',
                    'Tax Adjustment': -adj['Adjustment'],
                    'Tax Balance': -adj['Adjustment'],
                    'DR/CR': 'CR' if adj['Adjustment'] > 0 else 'DR',
                    'Lacerte Line': ""
                })

            if journal_entries:
                atb_df = pd.concat([atb_df, pd.DataFrame(journal_entries)], ignore_index=True)

# Step 6: Review/Edit Lacerte Line Mappings
st.header("6. Review/Edit Lacerte Line Mappings")
if mapping_df is not None:
    st.markdown("Edit or confirm Lacerte Tax Line mappings below:")

    for i in range(len(atb_df)):
        acct_desc = atb_df.at[i, 'Account Description']
        current_line = atb_df.at[i, 'Lacerte Line']
        new_val = st.text_input(f"Lacerte Line for: {acct_desc}", value=current_line, key=f"lac_edit_{i}")
        atb_df.at[i, 'Lacerte Line'] = new_val

# Collect mapping summary
mapping_summary_df = atb_df[['Account Number', 'Account Description', 'Tax Adjustment', 'Lacerte Line']]

# Save mapping to JSON (optional)
if st.checkbox("✅ Save Lacerte mapping to JSON file?"):
    client_map_file = f"{client_name}_{tax_year}_mapping.json"
    map_dict = mapping_summary_df.set_index('Account Number')['Lacerte Line'].dropna().to_dict()
    with open(client_map_file, 'w') as f:
        json.dump(map_dict, f, indent=2)
    st.success(f"Saved mapping to {client_map_file}")

            # Step 6: Export
            st.header("📤 Download Tax Workpaper")
            excel_buffer = io.BytesIO()
            with ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                pd.DataFrame({
                    "Client Name": [client_name],
                    "Tax Year": [tax_year],
                    "Book Income": [book_income],
                    "Is Balanced": ["Yes" if is_balanced else "No"]
                }).to_excel(writer, sheet_name="General Info", index=False)

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
                        "10. Income (line 6 less line 9)"
                    ],
                    "Amount": [
                        book_income, 0, 0, 0, adj_df['Adjustment'].sum(),
                        book_income + adj_df['Adjustment'].sum(), 0, 0, 0,
                        book_income + adj_df['Adjustment'].sum()
                    ]
                }).to_excel(writer, sheet_name="M-1 Summary", index=False)

                tb_df.to_excel(writer, sheet_name="Original TB", index=False)
                for cat, group in adj_df.groupby("M-1 Category"):
                    offset = pd.DataFrame([{
                        'Account': f"Offset - {cat}",
                        'Book Amount': '',
                        'Tax Amount': '',
                        'Adjustment': -group['Adjustment'].sum(),
                        'Adjustment Type': 'Offset',
                        'M-1 Category': cat,
                        'DR/CR': 'CR' if group['Adjustment'].sum() > 0 else 'DR'
                    }])
                    pd.concat([group, offset], ignore_index=True).to_excel(writer, sheet_name=cat[:31], index=False)

                atb_df.to_excel(writer, sheet_name="Adjusted TB", index=False)

            excel_buffer.seek(0)
            st.download_button("📥 Download Excel Workpaper", data=excel_buffer, file_name=f"{client_name}_{tax_year}_Tax_Workpaper.xlsx")

    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
