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
    df.columns = df.columns.str.strip()
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

# 📈 Section 2: F&O Bhavcopy
st.subheader("📈 F&O OI Summary – NIFTY")
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

    nifty_df = df[df["SYMBOL"] == "NIFTY"]
    fut_oi = nifty_df[nifty_df["INSTRUMENT"] == "IDF"]["OPEN_INT"].sum()
    chg_oi = nifty_df[nifty_df["INSTRUMENT"] == "IDF"]["CHG_IN_OI"].sum()
    ce_oi = nifty_df[(nifty_df["INSTRUMENT"] == "IDO") & (nifty_df["OPTION_TYP"] == "CE")]["OPEN_INT"].sum()
    pe_oi = nifty_df[(nifty_df["INSTRUMENT"] == "IDO") & (nifty_df["OPTION_TYP"] == "PE")]["OPEN_INT"].sum()
    pcr = round(pe_oi / ce_oi, 2) if ce_oi > 0 else 0

    message = f"📉 NIFTY F&O Summary\n\nFut OI: {fut_oi/1e6:.2f}M\nChg in OI: {chg_oi/1e5:.2f}L\nCE OI: {ce_oi/1e6:.2f}M\nPE OI: {pe_oi/1e6:.2f}M\nPCR: {pcr}"
    sent = send_telegram(message)
    st.success("F&O Summary sent to Telegram." if sent else "Failed to send.")
    st.text(message)

# 👥 Section 3: FII/DII OI Tracker
st.subheader("👥 FII / Pro Position Tracker")
fii_file = st.file_uploader("Upload Participant OI File (.csv)", type="csv", key="fii")

if fii_file and st.button("Analyze FII / Pro"):
    df = pd.read_csv(fii_file, skiprows=2)
    cols = ["Client Type", "Index Futures Long", "Index Futures Short", "Stock Futures Long", "Stock Futures Short",
            "Index Call Option Long", "Index Call Option Short", "Index Put Option Long", "Index Put Option Short",
            "Stock Call Option Long", "Stock Call Option Short", "Stock Put Option Long", "Stock Put Option Short",
            "Total Long Contracts", "Total Short Contracts"]
    df.columns = cols
    df = df[df["Client Type"].isin(["FII", "Pro"])]
    df[cols[1:]] = df[cols[1:]].apply(pd.to_numeric, errors='coerce')

    df["Index Net"] = (df["Index Futures Long"] + df["Index Call Option Long"] + df["Index Put Option Short"]) - \
                      (df["Index Futures Short"] + df["Index Call Option Short"] + df["Index Put Option Long"])
    df["Stock Net"] = (df["Stock Futures Long"] + df["Stock Call Option Long"] + df["Stock Put Option Short"]) - \
                      (df["Stock Futures Short"] + df["Stock Call Option Short"] + df["Stock Put Option Long"])

    lines = ["📉 FII & Pro Position – " + datetime.today().strftime("%d-%b-%Y")]
    for _, row in df.iterrows():
        i = "Long" if row["Index Net"] > 0 else "Short"
        s = "Long" if row["Stock Net"] > 0 else "Short"
        lines.append(f"🔹 {row['Client Type']}: Index = {row['Index Net']/1e3:+.1f}K ({i}), Stock = {row['Stock Net']/1e3:+.1f}K ({s})")

    message = "\n".join(lines)
    sent = send_telegram(message)
    st.success("FII/Pro alert sent." if sent else "Failed to send.")
    st.text(message)

st.markdown("---")
st.caption("Built by your AI Trading Assistant 🧠📈")
