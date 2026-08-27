import os
import time
import threading
import requests
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# ---------------- TELEGRAM BOT CONFIGURATION ----------------
TELEGRAM_BOT_TOKEN = "8886107397:AAHENOebGnrupxvGKqKh5cKC3SmujXJOV3w" # तुझा 1M चा अचूक टोकन
TARGET_GROUP_ID = "-1004370895879"  # तुझा My Home Group चा आयडी
SECRET_PASSWORD = "12345"   # 1M चा पासवर्ड
# ------------------------------------------------------------

# 🚀 Global State for Logic & Dashboard
bot_state = {
    "name": "WinGo 1M",
    "last_processed_issue": "Waiting...",
    "bs_pred": "WAIT", 
    "bs_level": 1, 
    
    # 💰 फंड मॅनेजमेंट (Virtual Wallet & Safe Mode)
    "balance": 20000.0,  
    "bet_amounts": {1: 100, 2: 200, 3: 500, 4: 1000}, # लेव्हल ५ ला ० रुपये लागतील
    
    "full_history": [], # 🚀 बॉटची स्वतःची अचूक मेमरी
    "history": [],
    "bs_win": 0, 
    "bs_fail": 0, 
    "total_trades": 0,
    
    "is_running": False,       
    "last_result_text": "Initializing..."
}

def send_telegram_message_direct(chat_id, text):
    if not chat_id: return
    # 🚀 Async Background Sending (मेसेज फास्ट जाईल, बॉट थांबणार नाही)
    def _send():
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=3)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()

def telegram_listener():
    offset = 0
    print("🤖 Telegram Listener Started...")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=2"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                for result in response.json().get("result", []):
                    offset = result["update_id"] + 1
                    message = result.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "").strip()

                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == SECRET_PASSWORD:
                            bot_state["is_running"] = True
                            send_telegram_message_direct(chat_id, f"✅ *[1M Strategy] Activated! Live Prediction is ON.*\n💰 *Initial Fund:* ₹20,000")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == SECRET_PASSWORD:
                            bot_state["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *[1M Strategy] Stopped Successfully!*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, bs_pred, bs_level, prev_bs_res=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    text = f"🚀 *VSR WINGO Signals 1 Minute* 🚀\n\n"
    
    if state["total_trades"] > 0 and prev_bs_res and prev_bs_res != "-":
        text += f"🔄 *Last Trade Result:*\n"
        text += f"📏 B/S: *{prev_bs_res}*\n"
        if "WIN" in prev_bs_res: text += f"\n🔥🎉 *CONGRATS! WIN!* 🎉🔥\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Prediction For Ticket:* {issue}\n"
    text += f"💰 *Total Balance:* ₹{state['balance']:.2f}\n\n"
    
    if bs_pred == "WAIT":
        text += f"⏳ *Building History Data...*\n_Waiting for issue {int(issue)-20} to sync..._\n"
    else:
        bs_pred_text = "🟠 Big" if bs_pred == "Big" else "🔵 Small"
        current_bet = state["bet_amounts"].get(bs_level, 0)
        
        text += f"📏 *B/S Pred:* *{bs_pred_text}*\n"
        text += f"🎯 *Level:* L{bs_level}\n"
        
        if current_bet > 0:
            text += f"💵 *Bet Amount:* ₹{current_bet}\n\n"
        else:
            text += f"🛡️ *Bet Amount:* ₹0 (Virtual Mode / Safe)\n\n"
        
    send_telegram_message_direct(target_chat_id, text)

def fetch_history_records(url, state):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://draw.ar-lottery01.com/",
    }
    all_records = []
    
    try:
        params = {"pageSize": 30, "pageNo": 1, "ts": int(time.time() * 1000)}
        response = requests.get(url, headers=headers, params=params, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and isinstance(data["data"], list): all_records.extend(data["data"])
            elif "list" in data and isinstance(data["list"], list): all_records.extend(data["list"])
            elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: all_records.extend(data["data"]["list"])
    except Exception:
        pass
        
    if len(all_records) <= 10:
        for p in [2, 3]:
            try:
                params = {"pageSize": 10, "pageNo": p, "ts": int(time.time() * 1000)}
                response = requests.get(url, headers=headers, params=params, timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and isinstance(data["data"], list): all_records.extend(data["data"])
                    elif "list" in data and isinstance(data["list"], list): all_records.extend(data["list"])
                    elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: all_records.extend(data["data"]["list"])
            except Exception:
                pass
            
    return all_records

def process_strategy(state, records):
    if not records: return False
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if not (latest_number_str.isdigit() and latest_issue.isdigit()): return False
    latest_bs = "Big" if int(latest_number_str) >= 5 else "Small"

    # सर्व रेकॉर्ड्स मेमरीमध्ये सेव्ह करणे
    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss.isdigit() and num_str.isdigit():
            if not any(x["issue"] == iss for x in state["full_history"]):
                bs_val = "Big" if int(num_str) >= 5 else "Small"
                state["full_history"].append({"issue": iss, "bs": bs_val})
                
    state["full_history"].sort(key=lambda x: int(x["issue"]), reverse=True)
    state["full_history"] = state["full_history"][:60]

    # --- Initial State ---
    if state["last_processed_issue"] == "Waiting...":
        state["last_processed_issue"] = latest_issue
        next_issue_int = int(latest_issue) + 1
        target_issue_str = str(next_issue_int - 20) 
        
        target_record = next((x for x in state["full_history"] if x["issue"] == target_issue_str), None)
        
        if target_record:
            state["bs_pred"] = target_record["bs"]
        elif len(state["full_history"]) >= 20:
            state["bs_pred"] = state["full_history"][19]["bs"] 
        else:
            state["bs_pred"] = "WAIT"
        
        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int), state["bs_pred"], state["bs_level"])
        return True

    # --- Next Trades ---
    if state["last_processed_issue"] != latest_issue and state["last_processed_issue"] != "Waiting...":
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        bs_res_status = "-"
        
        if state["bs_pred"] != "WAIT":
            state["total_trades"] += 1
            bs_win = (state["bs_pred"] == latest_bs)
            bs_emoji = "🟠" if state["bs_pred"] == "Big" else "🔵"
            
            current_bet = state["bet_amounts"].get(state["bs_level"], 0)
            
            if bs_win:
                state["bs_win"] += 1
                if current_bet > 0:
                    net_profit = current_bet * 0.96
                    state["balance"] += net_profit
                    bs_res_status = f"{bs_emoji} {state['bs_pred']} ✅ WIN (+₹{net_profit:.0f})"
                else:
                    bs_res_status = f"{bs_emoji} {state['bs_pred']} ✅ WIN (Virtual Mode)"
                
                old_level = state["bs_level"]
                state["bs_level"] = 1 
            else:
                state["bs_fail"] += 1
                if current_bet > 0:
                    state["balance"] -= current_bet
                    bs_res_status = f"{bs_emoji} {state['bs_pred']} ❌ FAIL (-₹{current_bet})"
                else:
                    bs_res_status = f"{bs_emoji} {state['bs_pred']} ❌ FAIL (Virtual Mode)"
                
                old_level = state["bs_level"]
                state["bs_level"] += 1
                    
            state["history"].append({
                "trade": state["total_trades"], "issue": latest_issue[-4:],
                "bs_level": f"L{old_level}", 
                "bs_pred": state["bs_pred"],
                "bs_res": "WIN" if "WIN" in bs_res_status else "FAIL"
            })
            if len(state["history"]) > 5: state["history"].pop(0)
            state["last_result_text"] = bs_res_status

        next_issue_int = int(latest_issue) + 1
        target_issue_str = str(next_issue_int - 20)
        
        target_record = next((x for x in state["full_history"] if x["issue"] == target_issue_str), None)
        
        if target_record:
            state["bs_pred"] = target_record["bs"]
        elif len(state["full_history"]) >= 20:
            state["bs_pred"] = state["full_history"][19]["bs"]
        else:
            state["bs_pred"] = "WAIT"

        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int), state["bs_pred"], state["bs_level"], bs_res_status)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def background_bot_loop():
    # 🚀 अचूक 1 Minute API लिंक
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
    while True:
        records = fetch_history_records(url, bot_state)
        if records:
            process_strategy(bot_state, records)
        time.sleep(3) # 1M गेमसाठी 3 सेकंदाचा रिफ्रेश योग्य आहे

# ----------------- WEB DASHBOARD TEMPLATE -----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>VSR 1M Manager Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, sans-serif; text-align: center; padding: 20px; }
        .card { background: #1e293b; border-radius: 16px; padding: 25px; max-width: 450px; margin: auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 22px; margin-bottom: 5px; }
        .subtitle { color: #94a3b8; font-size: 13px; margin-bottom: 15px; }
        .wallet-box { background: #064e3b; padding: 15px; border-radius: 10px; border: 1px solid #10b981; margin-bottom: 15px; }
        .wallet-amt { font-size: 28px; color: #4ade80; font-weight: bold; margin: 5px 0;}
        .metric { background: #334155; margin: 10px 0; padding: 12px; border-radius: 10px; font-size: 15px; text-align: left; display: flex; justify-content: space-between; align-items: center; }
        .highlight { color: #38bdf8; font-weight: bold; font-size: 16px; }
        .result-box { background: #0f172a; margin-top: 15px; padding: 12px; border-radius: 8px; font-size: 14px; color: #cbd5e1; text-align: left; border-left: 4px solid #facc15; }
        .status-badge { background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .status-active { background: #22c55e; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🚀 VSR 1M Manager</h1>
        <div class="subtitle">
            Bot Status: <span id="timer_status" class="status-badge">INACTIVE</span>
        </div>
        
        <div class="wallet-box">
            <div style="font-size: 14px; color: #a7f3d0;">💰 Virtual Wallet Balance</div>
            <div class="wallet-amt" id="balance">₹ 20,000.00</div>
            <div style="font-size: 13px; color: #6ee7b7;">W: <span id="w_cnt">0</span> | F: <span id="f_cnt">0</span></div>
        </div>
        
        <div class="metric"><span>🎟️ Next Ticket:</span> <span class="highlight" id="last_issue">Loading...</span></div>
        <div class="metric"><span>📏 Prediction:</span> <span class="highlight" id="bs_info">-</span></div>
        <div class="metric"><span>💵 Bet Amount:</span> <span class="highlight" style="color:#facc15;" id="bet_info">₹ 0</span></div>
        
        <div class="result-box" id="last_result">
            <b>📊 Last Trade Status:</b><br>Initializing...
        </div>
    </div>

    <script>
        function updateDashboard() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    let nextIss = data.last_processed_issue;
                    if(nextIss !== "Waiting..." && !isNaN(nextIss)) {
                        nextIss = (parseInt(nextIss) + 1).toString();
                    }
                    
                    document.getElementById('last_issue').innerText = nextIss;
                    
                    let bsText = data.bs_pred;
                    if(data.bs_pred !== "WAIT") {
                        bsText += " (L" + data.bs_level + ")";
                    }
                    document.getElementById('bs_info').innerText = bsText;
                    
                    document.getElementById('balance').innerText = "₹ " + parseFloat(data.balance).toFixed(2);
                    document.getElementById('w_cnt').innerText = data.bs_win;
                    document.getElementById('f_cnt').innerText = data.bs_fail;
                    
                    let current_bet = 0;
                    if(data.bs_level <= 4) {
                        if(data.bs_level === 1) current_bet = 100;
                        if(data.bs_level === 2) current_bet = 200;
                        if(data.bs_level === 3) current_bet = 500;
                        if(data.bs_level === 4) current_bet = 1000;
                    }
                    
                    if(data.bs_pred === "WAIT") current_bet = 0;
                    
                    if(current_bet === 0 && data.bs_pred !== "WAIT") {
                        document.getElementById('bet_info').innerText = "₹ 0 (Safe Mode)";
                    } else {
                        document.getElementById('bet_info').innerText = "₹ " + current_bet;
                    }
                    
                    document.getElementById('last_result').innerHTML = "<b>📊 Last Trade Status:</b><br>" + data.last_result_text;
                    
                    const statusBadge = document.getElementById('timer_status');
                    if (data.is_running) {
                        statusBadge.innerText = "ACTIVE (Running)";
                        statusBadge.className = "status-badge status-active";
                    } else {
                        statusBadge.innerText = "INACTIVE (Stopped)";
                        statusBadge.className = "status-badge";
                    }
                }).catch(err => console.log(err));
        }
        setInterval(updateDashboard, 1500);
        updateDashboard();
    </script>
</body>
</html>
