from flask import Flask, request, jsonify
import pandas as pd
import io

app = Flask(__name__)

# ---- M-1 Processing Functions ----
def process_m1_sheet(df, type_label, deduction_rule):
    df = df.copy()
    df['Account Number'] = ''
    df['Account Description'] = df['Description']
    df['Book Amount'] = pd.to_numeric(df['Trial Balance'], errors='coerce').fillna(0)
    df['Adjustment'] = df.apply(deduction_rule, axis=1)
    df['TR Amount'] = df['Book Amount'] - df['Adjustment']
    df['Source'] = type_label
    return df[['Account Number', 'Account Description', 'Book Amount', 'Adjustment', 'TR Amount', 'Source']]

# ---- Deduction Rules ----
def meals_rule(row):
    pct = float(row.get('% Disallowed', 0))
    return row['Book Amount'] * pct

def accrual_rule(row):
    return row['Book Amount'] if str(row.get('Paid within 2.5 months', '')).strip().upper() not in ['Y', 'YES'] else 0

def default_full_disallowance(row):
    return row['Book Amount']

def depreciation_rule(row):
    return row.get('Book/Tax Difference', 0)

# ---- Upload Workpaper ----
@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    xls = pd.ExcelFile(file)
    summaries = []

    try:
        # Meals
        df_meals = xls.parse('Meals & Entertainment', skiprows=5, usecols="D:G").dropna(subset=['Unnamed: 3'])
        df_meals.columns = ['Description', 'Trial Balance', '% Disallowed', 'Book/Tax Difference']
        summaries.append(process_m1_sheet(df_meals, 'Meals & Entertainment', meals_rule))

        # Accrued
        df_accr = xls.parse('Accrued Expenses', skiprows=5, usecols="D:G").dropna(subset=['Unnamed: 3'])
        df_accr.columns = ['Description', 'Trial Balance', 'Paid within 2.5 months', 'Book/Tax Difference']
        summaries.append(process_m1_sheet(df_accr, 'Accrued Expenses', accrual_rule))

        # Payroll
        df_payroll = xls.parse('Payroll Liabilities', skiprows=5, usecols="D:G").dropna(subset=['Unnamed: 3'])
        df_payroll.columns = ['Description', 'Trial Balance', 'Paid within 2.5 months', 'Book/Tax Difference']
        summaries.append(process_m1_sheet(df_payroll, 'Payroll Liabilities', accrual_rule))

        # Penalties
        df_pen = xls.parse('Penalties & Fines', skiprows=5, usecols="D:F").dropna(subset=['Unnamed: 3'])
        df_pen.columns = ['Description', 'Trial Balance', 'Book/Tax Difference']
        summaries.append(process_m1_sheet(df_pen, 'Penalties & Fines', default_full_disallowance))

        # Fed Taxes
        df_tax = xls.parse('Federal Taxes ', skiprows=5, usecols="D:F").dropna(subset=['Unnamed: 3'])
        df_tax.columns = ['Description', 'Trial Balance', 'Book/Tax Difference']
        summaries.append(process_m1_sheet(df_tax, 'Federal Taxes', default_full_disallowance))

        # Depreciation
        df_depr = xls.parse('Depreciation', skiprows=5, usecols="D:F").dropna(subset=['Unnamed: 3'])
        df_depr.columns = ['Description', 'Trial Balance', 'Book/Tax Difference']
        summaries.append(process_m1_sheet(df_depr, 'Depreciation', depreciation_rule))

        final_df = pd.concat(summaries, ignore_index=True)
        output = io.StringIO()
        final_df.to_csv(output, index=False)
        return output.getvalue(), 200, {'Content-Type': 'text/csv'}

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---- Review Prompts ----
@app.route('/review-prompts', methods=['GET'])
def get_review_prompts():
    prompts = [
        {"id": "tax_depr", "question": "What is your total tax depreciation?", "context": "MACRS or 179 methods"},
        {"id": "interest_limit_disallowed", "question": "Any disallowed interest under §163(j)?", "context": "Excess interest addback"},
        {"id": "sec481a", "question": "Is there a Section 481(a) adjustment?", "context": "Accounting method change"}
    ]
    return jsonify({"prompts": prompts})

# ---- Apply Adjustments ----
@app.route('/apply-adjustments', methods=['POST'])
def apply_adjustments():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    adjustments = []
    try:
        if 'tax_depr' in data and 'book_depr' in data:
            diff = float(data['book_depr']) - float(data['tax_depr'])
            adjustments.append({
                "Account Number": '',
                "Account Description": "Book vs Tax Depreciation",
                "Book Amount": float(data['book_depr']),
                "Adjustment": diff,
                "TR Amount": float(data['tax_depr']),
                "Source": "Depreciation Prompt"
            })

        if 'interest_limit_disallowed' in data:
            val = float(data['interest_limit_disallowed'])
            adjustments.append({
                "Account Number": '',
                "Account Description": "Disallowed Interest §163(j)",
                "Book Amount": val,
                "Adjustment": val,
                "TR Amount": 0,
                "Source": "Interest Prompt"
            })

        if 'sec481a' in data:
            val = float(data['sec481a'])
            adjustments.append({
                "Account Number": '',
                "Account Description": "Section 481(a) Adjustment",
                "Book Amount": 0,
                "Adjustment": val,
                "TR Amount": val,
                "Source": "Sec 481(a) Prompt"
            })

        return jsonify({"adjustments": adjustments})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---- Run App ----
if __name__ == '__main__':
    app.run(debug=True)
