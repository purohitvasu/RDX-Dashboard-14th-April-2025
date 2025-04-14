# 📊 RDX Trading Dashboard – Streamlit Version
# Upload files, analyze, and send alerts from your local or deployed Streamlit app

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import base64

# Telegram Config
BOT_TOKEN = "8079995624:AAEHYRrmaoY6aYNfXKHxuzKu_rgTRjEI6i8"
CHAT_ID = "-4751937934"

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
        if not spikes.empty:
            date = datetime.today().strftime("%d-%b-%Y")
            message = f"📢 Delivery Spikes – {date}\n"
            for _, row in spikes.iterrows():
                message += f"🔹 {row['SYMBOL']}: {row['DELIV_PER']}%\n"
            sent = send_telegram(message)
            st.success("Alert sent to Telegram." if sent else "Failed to send alert.")
            st.dataframe(spikes)
        else:
            st.info("No spikes above 60% today.")
    else:
        st.error("❌ Uploaded file must contain 'SYMBOL' and 'DELIV_PER' columns.")

# 📈 Section 2: F&O Bhavcopy
st.subheader("📈 F&O OI Summary – NIFTY + Top 5 Movers")
fo_file = st.file_uploader("Upload F&O Bhavcopy (.csv)", type="csv", key="fo")

if fo_file and st.button("Analyze F&O Bhavcopy"):
    df = pd.read_csv(fo_file)
    df.columns = df.columns.str.strip()
    df.rename(columns={"TckrSymb": "SYMBOL", "FinInstrmTp": "INSTRUMENT", "XpryDt": "EXPIRY_DT",
                       "OptnTp": "OPTION_TYP", "StrkPric": "STRIKE_PR", "OpnIntrst": "OPEN_INT",
                       "ChngInOpnIntrst": "CHG_IN_OI"}, inplace=True)
    df["SYMBOL"] = df["SYMBOL"].astype(str).str.upper()
    df["OPTION_TYP"] = df["OPTION_TYP"].fillna("")
    df["OPEN_INT"] = pd.to_numeric(df["OPEN_INT"], errors="coerce")
    df["CHG_IN_OI"] = pd.to_numeric(df["CHG_IN_OI"], errors="coerce")

    # NIFTY Summary
    nifty_df = df[df["SYMBOL"] == "NIFTY"]
    fut_oi = nifty_df[nifty_df["INSTRUMENT"] == "IDF"]["OPEN_INT"].sum()
    chg_oi = nifty_df[nifty_df["INSTRUMENT"] == "IDF"]["CHG_IN_OI"].sum()
    ce_oi = nifty_df[(nifty_df["INSTRUMENT"] == "IDO") & (nifty_df["OPTION_TYP"] == "CE")]["OPEN_INT"].sum()
    pe_oi = nifty_df[(nifty_df["INSTRUMENT"] == "IDO") & (nifty_df["OPTION_TYP"] == "PE")]["OPEN_INT"].sum()
    pcr = round(pe_oi / ce_oi, 2) if ce_oi > 0 else 0

    # Top 5 Gainers & Losers from Futures
    stock_df = df[(df["INSTRUMENT"] == "STF") & (df["SYMBOL"].isin(nifty50))]
    gainers = stock_df.sort_values("CHG_IN_OI", ascending=False).head(5)
    losers = stock_df.sort_values("CHG_IN_OI", ascending=True).head(5)

    message = f"📉 NIFTY F&O Summary – {datetime.today().strftime('%d-%b-%Y')}\n"
    message += f"🔹 Fut OI: {fut_oi/1e6:.2f}M\n🔹 Chg in OI: {chg_oi/1e5:.2f}L\n"
    message += f"🔹 CE OI: {ce_oi/1e6:.2f}M\n🔹 PE OI: {pe_oi/1e6:.2f}M\n🔹 PCR: {pcr}\n\n"
    message += "📈 Top 5 OI Gainers:\n"
    for _, row in gainers.iterrows():
        message += f"🔹 {row['SYMBOL']}: +{row['CHG_IN_OI']/1e5:.2f}L\n"
    message += "\n📉 Top 5 OI Losers:\n"
    for _, row in losers.iterrows():
        message += f"🔻 {row['SYMBOL']}: {row['CHG_IN_OI']/1e5:.2f}L\n"

    sent = send_telegram(message)
    st.success("F&O Summary with Gainers/Losers sent to Telegram." if sent else "Failed to send.")
    st.text(message)
