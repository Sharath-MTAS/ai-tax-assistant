import streamlit as st
import requests
import pandas as pd
import io

st.set_page_config(page_title="AI Tax Review Assistant", layout="wide")
st.title("🧾 AI Tax Review Assistant")

# --- File Upload Section ---
st.header("1. Upload Adjusted Trial Balance Workpaper")
file = st.file_uploader("Upload your .xlsm file", type=["xlsm"])
main_df = None

if file:
    with st.spinner("Uploading and analyzing workpaper..."):
        response = requests.post("http://localhost:5000/upload", files={"file": file})
        if response.status_code == 200:
            main_df = pd.read_csv(io.StringIO(response.text))
            st.success("M-1 Adjustments extracted from workbook.")
            st.dataframe(main_df)
        else:
            st.error("Upload failed: " + response.text)

# --- Review Prompts Section ---
st.header("2. Review Additional Tax Adjustment Prompts")
resp = requests.get("http://localhost:5000/review-prompts")
if resp.status_code == 200:
    prompts = resp.json()["prompts"]
    responses = {}
    for prompt in prompts:
        responses[prompt["id"]] = st.text_input(f"{prompt['question']}", help=prompt['context'])

    if st.button("Submit Responses for Adjustments"):
        payload = {k: v for k, v in responses.items() if v.strip() != ''}
        res = requests.post("http://localhost:5000/apply-adjustments", json=payload)
        if res.status_code == 200:
            adj_df = pd.DataFrame(res.json()["adjustments"])
            st.success("Generated Adjustments from Prompts")
            st.dataframe(adj_df)

            if main_df is not None:
                combined_df = pd.concat([main_df, adj_df], ignore_index=True)
                st.subheader("📊 Combined Adjusted Trial Balance")
                st.dataframe(combined_df)

                st.download_button("Download Combined CSV", combined_df.to_csv(index=False), "combined_atb.csv")

                to_excel = combined_df.to_excel(index=False, engine='openpyxl')
                st.download_button("Download Combined Excel", data=to_excel, file_name="combined_atb.xlsx")
            else:
                st.dataframe(adj_df)
                st.download_button("Download CSV", adj_df.to_csv(index=False), "prompt_adjustments.csv")
        else:
            st.error("Failed to process responses: " + res.text)
else:
    st.error("Could not fetch prompts.")
