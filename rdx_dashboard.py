# 📊 RDX Trading Dashboard – Streamlit Version
# Upload files, analyze, and send alerts from your local or deployed Streamlit app

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import base64
import gspread
from gspread_dataframe import set_with_dataframe
from google.auth import default

# Telegram Config
BOT_TOKEN = "8079995624:AAEHYRrmaoY6aYNfXKHxuzKu_rgTRjEI6i8"
CHAT_ID = "-4751937934"

# Google Sheet Config
SHEET_URL = "https://docs.google.com/spreadsheets/d/1jTy1r04N-_WKNJmzpXoiY5KJkUzDJL-rRXpQ3O00T6E"
creds, _ = default()
gc = gspread.authorize(creds)
workbook = gc.open_by_url(SHEET_URL)

# Nifty50 symbols
nifty50 = ["ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK","BAJAJ-AUTO","BAJFINANCE",
           "BAJAJFINSV","BEL","BHARTIARTL","CIPLA","COALINDIA","DRREDDY","EICHERMOT","ETERNAL",
           "GRASIM","HCLTECH","HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDUNILVR","ICICIBANK",
           "ITC","INDUSINDBK","INFY","JSWSTEEL","JIOFIN","KOTAKBANK","LT","M&M","MARUTI","NTPC",
           "NESTLEIND","ONGC","POWERGRID","RELIANCE","SBILIFE","SHRIRAMFIN","SBIN","SUNPHARMA",
           "TCS","TATACONSUM","TATAMOTORS","TATASTEEL","TECHM","TITAN","TRENT","ULTRACEMCO","WIPRO"]

# Helper: Send Telegram message
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    r = requests.post(url, data=data)
    return r.status_code == 200

# --- Streamlit App Layout ---
st.title("📊 RDX Trading Dashboard")
st.markdown("Upload your daily files and run each section for analysis and alerts.")

# 📁 Section 1: Delivery Spike
st.subheader("🔍 Cash Delivery Spike Detection")
delivery_file = st.file_uploader("Upload Cash Bhavcopy (.csv)", type="csv", key="delivery")

if delivery_file and st.button("Analyze Delivery Spikes"):
    df = pd.read_csv(delivery_file)
    df.columns = df.columns.str.strip().str.upper()
    if "SYMBOL" in df.columns and "DELIV_PER" in df.columns:
        df = df[df["SYMBOL"].isin(nifty50)]
        df["DELIV_PER"] = pd.to_numeric(df["DELIV_PER"], errors="coerce")
        df = df.dropna(subset=["DELIV_PER"])
        spikes = df[df["DELIV_PER"] > 60][["SYMBOL", "DELIV_PER"]]
        df_spikes = spikes.copy()
        df_spikes["Date"] = datetime.today().strftime("%Y-%m-%d")

        try:
            worksheet = workbook.worksheet("Delivery Sheet")
            existing = pd.DataFrame(worksheet.get_all_records())
            updated = pd.concat([existing, df_spikes], ignore_index=True)
            worksheet.clear()
        except:
            worksheet = workbook.add_worksheet(title="Delivery Sheet", rows=1000, cols=10)
            updated = df_spikes

        set_with_dataframe(worksheet, updated)

        if not spikes.empty:
            date = datetime.today().strftime("%d-%b-%Y")
            message = f"📢 Delivery Spikes – {date}\n"
            for _, row in spikes.iterrows():
                message += f"🔹 {row['SYMBOL']}: {row['DELIV_PER']}%\n"
            sent = send_telegram(message)
            st.success("Alert sent to Telegram." if sent else "Failed to send alert.")
            st.dataframe(spikes)
        else:
            no_spike_msg = f"📢 No delivery spikes above 60% for {datetime.today().strftime('%d-%b-%Y')}"
            send_telegram(no_spike_msg)
            st.info("No spikes above 60% today.")
    else:
        st.error("❌ Uploaded file must contain 'SYMBOL' and 'DELIV_PER' columns.")
