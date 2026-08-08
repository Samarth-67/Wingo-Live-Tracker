import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# ---------------- TELEGRAM BOT CONFIGURATION ----------------
TELEGRAM_BOT_TOKEN = "8886107397:AAHENOebGnrupxvGKqKh5cKC3SmujXJOV3w"
TELEGRAM_CHAT_ID = "-1004370895879"
# ------------------------------------------------------------

# 🔒 SECURITY CONFIGURATION
ACCESS_CODE = "6777"

# ⚙️ Page Setup
st.set_page_config(page_title="WinGo Live Tracker V3", page_icon="🚀", layout="wide")

# 🔐 Password Authentication Logic
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center;'>🔒 Security Check (V3)</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        pwd = st.text_input("Access Code:", type="password")
        if st.button("Unlock Dashboard", use_container_width=True):
            if pwd == ACCESS_CODE:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Incorrect Code! Access Denied.")
    st.stop()

# 🧠 Initialize Session State
if "init" not in st.session_state:
    st.session_state.last_processed_issue = None
    st.session_state.status = "WAITING"
    st.session_state.bs_pred = None; st.session_state.bs_step = 0; st.session_state.bs_level = 1
    st.session_state.color_pred = None; st.session_state.color_step = 0; st.session_state.color_level = 1
    st.session_state.history = []
    st.session_state.stats = {"bs_win": 0, "bs_fail": 0, "color_win": 0, "color_fail": 0, "total_trades": 0}
    st.session_state.hour_start_time = time.time()
    st.session_state.max_bs_level_hourly = 1
    st.session_state.max_color_level_hourly = 1
    st.session_state.init = True

def send_telegram_signal(issue, bs_pred, bs_level, color_pred, color_level, prev_bs_res=None, prev_color_res=None):
    if not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    text = f"🚀 *VS WINGO Signals 1 Minute* 🚀\n\n"
    if prev_bs_res and prev_color_res:
        bs_won = "WIN" in prev_bs_res; color_won = "WIN" in prev_color_res
        text += f"🔄 *Last Trade Result:*\n📏 B/S: {prev_bs_res}\n🎨 Color: {prev_color_res}\n"
        if bs_won and color_won: text += f"\n🔥🎉 *JACKPOT! BOTH WON!* 🎉🔥\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
    text += f"🎟️ *New Issue:* {issue}\n\n📏 *Prediction:* {bs_pred}\n🎯 *Level:* L{bs_level}\n\n🎨 *Prediction Color:* {color_pred}\n🎯 *Level:* L{color_level}"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def send_hourly_telegram_report():
    if not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    text = (f"⏱️ *HOURLY SYSTEM UPDATE* ⏱️\n➖➖➖➖➖➖➖➖➖➖\n"
            f"📊 *Max Drawdown (Loss Level):*\n📏 B/S: L{st.session_state.max_bs_level_hourly}\n🎨 Color: L{st.session_state.max_color_level_hourly}\n\n"
            f"📈 *Total Trades:* {st.session_state.stats['total_trades']}\n➖➖➖➖➖➖➖➖➖➖")
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def fetch_data():
    ts = int(time.time() * 1000)
    target_url = f"https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?ts={ts}"
    
    # 🔥 Secret Weapon: खऱ्या मोबाईलचे Headers (Cloudflare ला फसवण्यासाठी)
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://ar-lottery01.com/",
        "Origin": "https://ar-lottery01.com"
    }
    
    # 1st Attempt: Direct with proper headers
    try:
        res = requests.get(target_url, headers=headers, timeout=5)
        if res.status_code == 200: return res.json()
    except: pass

    # 2nd Attempt: Codetabs Proxy
    try:
        res = requests.get(f"https://api.codetabs.com/v1/proxy?quest={target_url}", headers=headers, timeout=8)
        if res.status_code == 200: return res.json()
    except: pass
    
    # 3rd Attempt: AllOrigins Proxy
    try:
        res = requests.get(f"https://api.allorigins.win/raw?url={target_url}", headers=headers, timeout=8)
        if res.status_code == 200: return res.json()
    except: pass

    return {"error": "WinGo Blocked All Requests (Headers & Proxies Failed)."}

def update_strategy(records):
    if not records: return
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or latest_item.get("period") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if latest_number_str.isdigit():
        number = int(latest_number_str)
        latest_bs = "Big" if number >= 5 else "Small"; latest_color = "Red" if number % 2 == 0 else "Green"
    else: return

    if st.session_state.last_processed_issue is None:
        st.session_state.last_processed_issue = latest_issue
        return

    if st.session_state.last_processed_issue != latest_issue:
        if st.session_state.bs_level > st.session_state.max_bs_level_hourly: st.session_state.max_bs_level_hourly = st.session_state.bs_level
        if st.session_state.color_level > st.session_state.max_color_level_hourly: st.session_state.max_color_level_hourly = st.session_state.color_level
        
        bs_res_status, color_res_status = None, None
        if st.session_state.status == "PREDICTING":
            bs_win = (st.session_state.bs_pred == latest_bs)
            color_win = (st.session_state.color_pred == latest_color)
            bs_res_status = f"{st.session_state.bs_pred} ✅ WIN" if bs_win else f"{st.session_state.bs_pred} ❌ FAIL"
            color_res_status = f"{st.session_state.color_pred} ✅ WIN" if color_win else f"{st.session_state.color_pred} ❌ FAIL"
            
            st.session_state.stats["total_trades"] += 1
            if bs_win: st.session_state.stats["bs_win"] += 1
            else: st.session_state.stats["bs_fail"] += 1
            if color_win: st.session_state.stats["color_win"] += 1
            else: st.session_state.stats["color_fail"] += 1
            
            st.session_state.history.append({
                "Trade": st.session_state.stats["total_trades"], "Issue": latest_issue,
                "B/S Level": f"L{st.session_state.bs_level}", "B/S Pred": st.session_state.bs_pred, "B/S Result": "✅ WIN" if bs_win else "❌ FAIL",
                "Color Level": f"L{st.session_state.color_level}", "Color Pred": st.session_state.color_pred, "Color Result": "✅ WIN" if color_win else "❌ FAIL"
            })
            st.session_state.bs_level = 1 if bs_win else st.session_state.bs_level + 1
            st.session_state.color_level = 1 if color_win else st.session_state.color_level + 1
            
        if st.session_state.status == "WAITING":
            st.session_state.bs_pred = latest_bs; st.session_state.bs_step = 1
            st.session_state.color_pred = latest_color; st.session_state.color_step = 1
            st.session_state.status = "PREDICTING"
        elif st.session_state.status == "PREDICTING":
            if st.session_state.bs_step < 3: st.session_state.bs_step += 1
            else: st.session_state.bs_pred = "Small" if st.session_state.bs_pred == "Big" else "Big"; st.session_state.bs_step = 1
            if st.session_state.color_step < 3: st.session_state.color_step += 1
            else: st.session_state.color_pred = "Green" if st.session_state.color_pred == "Red" else "Red"; st.session_state.color_step = 1
        
        current_time = time.time()
        if current_time - st.session_state.hour_start_time >= 3600:
            send_hourly_telegram_report()
            st.session_state.hour_start_time = current_time; st.session_state.max_bs_level_hourly = 1; st.session_state.max_color_level_hourly = 1

        next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
        send_telegram_signal(next_issue, st.session_state.bs_pred, st.session_state.bs_level, st.session_state.color_pred, st.session_state.color_level, bs_res_status, color_res_status)
        st.session_state.last_processed_issue = latest_issue

# --- Main App Execution ---
st.title("🤖 Secure WinGo Tracker (V3)")
st.markdown("---")

data = fetch_data()
records = []

if isinstance(data, dict) and "error" in data:
    st.error(f"⚠️ {data['error']}")
else:
    records = data.get("data", []) if data else (data.get("list", []) if data else [])
    if isinstance(data, dict) and "data" in data and "list" in data["data"]:
        records = data["data"]["list"]
    if records: update_strategy(records)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Trades", st.session_state.stats["total_trades"])
col2.metric("B/S Wins", f"{st.session_state.stats['bs_win']} W / {st.session_state.stats['bs_fail']} F")
col3.metric("Color Wins", f"{st.session_state.stats['color_win']} W / {st.session_state.stats['color_fail']} F")
col4.metric("Hourly Max Level", f"L{st.session_state.max_bs_level_hourly} (B/S) | L{st.session_state.max_color_level_hourly} (Col)")

st.markdown("### 🎯 Live Predictions")
if st.session_state.status == "WAITING":
    st.info("👀 Waiting for the next Live Trade... Strategy will start shortly.")
else:
    next_issue = str(int(st.session_state.last_processed_issue) + 1) if st.session_state.last_processed_issue and st.session_state.last_processed_issue.isdigit() else "Next"
    st.info(f"**Issue:** {next_issue}")
    c1, c2 = st.columns(2)
    with c1: st.success(f"📏 **B/S:** {st.session_state.bs_pred} (Circle {st.session_state.bs_step}/3) ➡️ **L{st.session_state.bs_level}**")
    with c2: st.error(f"🎨 **Color:** {st.session_state.color_pred} (Circle {st.session_state.color_step}/3) ➡️ **L{st.session_state.color_level}**")

st.markdown("---")
st.markdown("### 📊 Trade History (Last 10)")
if st.session_state.history: st.dataframe(pd.DataFrame(st.session_state.history[-10:]), use_container_width=True)
else: st.write("No trades yet.")

st.markdown("### 🔥 Live Draw Results")
if records:
    display_records = []
    for r in records[:5]:
        num = str(r.get("number") or r.get("drawNumber") or "-")
        if num.isdigit():
            val = int(num); bs = "Big" if val >= 5 else "Small"; col = "🔴 Red" if val % 2 == 0 else "🟢 Green"
        else: bs, col = "-", "-"
        display_records.append({"Ticket Number": r.get("issueNumber") or r.get("issue") or r.get("period") or "-", "Number": num, "Color": col, "Big / Small": bs})
    st.table(pd.DataFrame(display_records))

time.sleep(2.5)
st.rerun()
