import os
import time
import threading
import requests
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# ---------------- TELEGRAM BOT CONFIGURATION ----------------
TELEGRAM_BOT_TOKEN = "8886107397:AAHENOebGnrupxvGKqKh5cKC3SmujXJOV3w" 
TARGET_GROUP_ID = "-1004370895879"  
SECRET_PASSWORD = "12345"   
# ------------------------------------------------------------

# ⚡ फास्ट इंटरनेट कनेक्शनसाठी Session
api_session = requests.Session()

# 💰 Betting Table (Level: Amount)
BET_TABLE = {
    1: 100,
    2: 200,
    3: 500,
    4: 1100
}

# 🚀 Global State for Single Strategy & Virtual Wallet
bot_state = {
    "name": "WinGo 1M (2-Opp) Strategy",
    "last_processed_issue": "Waiting...",
    
    # Strategy Logic (2 Consecutive Opposite)
    "pred": "WAIT",
    "level": 1,
    "active": False,
    "rounds_left": 0,
    
    # Virtual Wallet
    "virtual_balance": 20000,
    
    "full_history": [], 
    "history": [],
    
    # Stats
    "win": 0,
    "fail": 0,
    "total_trades": 0,
    
    "is_running": False,        
    "last_result_text": "Initializing..."
}

def send_telegram_message_direct(chat_id, text):
    if not chat_id: return
    def _send():
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            api_session.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=3)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()

def telegram_listener():
    offset = 0
    print("🤖 Telegram Listener Started...")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=2"
            response = api_session.get(url, timeout=5)
            if response.status_code == 200:
                for result in response.json().get("result", []):
                    offset = result["update_id"] + 1
                    message = result.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "").strip()

                    # 🟢 START COMMAND
                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == SECRET_PASSWORD:
                            bot_state["is_running"] = True
                            send_telegram_message_direct(chat_id, f"✅ *[1M 2-Opp Strategy] Activated! Live Prediction is ON.*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    # 🔴 STOP COMMAND
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == SECRET_PASSWORD:
                            bot_state["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *[1M 2-Opp Strategy] Stopped Successfully!*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    # 🔄 RESET COMMAND
                    elif text.startswith("/reset"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == SECRET_PASSWORD:
                            bot_state["level"] = 1
                            bot_state["pred"] = "WAIT"
                            bot_state["active"] = False
                            bot_state["rounds_left"] = 0
                            bot_state["win"] = 0
                            bot_state["fail"] = 0
                            bot_state["virtual_balance"] = 20000
                            bot_state["last_result_text"] = "Stats & Wallet Reset Successfully!"
                            send_telegram_message_direct(chat_id, "🔄 *Bot Reset Successfully!*\nLevels are back to L1 and Wallet is ₹20,000.")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, prev_res_text=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    text = f"🚀 *VSR WINGO 1M (2-Opp) Strategy* 🚀\n\n"
    
    if prev_res_text:
        text += f"🔄 *Last Trade Result:*\n"
        text += f"{prev_res_text}\n"
        text += f"💰 *Virtual Balance:* ₹{state['virtual_balance']}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Next Issue:* `{issue}`\n\n"
    
    # Strategy Text
    if state["pred"] == "WAIT":
        text += f"📐 *Prediction:* ⏳ Waiting for 2 B/S...\n\n"
    else:
        icon = "🟠 Big" if state["pred"] == "Big" else "🔵 Small"
        bet_amt = BET_TABLE.get(state["level"], 0)
        text += f"📐 *Prediction:* *{icon}*\n"
        text += f"🎯 *Level:* L{state['level']}\n"
        text += f"💵 *Virtual Bet:* ₹{bet_amt}\n\n"
        
    text += f"💡 _Auto Virtual Betting is ON._"
        
    send_telegram_message_direct(target_chat_id, text)

# 🚀 फास्ट मल्टी-पेज हिस्ट्री
def fetch_history_records(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://draw.ar-lottery01.com/",
    }
    all_records = []
    
    try:
        params = {"pageSize": 30, "pageNo": 1, "ts": int(time.time() * 1000)}
        response = api_session.get(url, headers=headers, params=params, timeout=3)
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
                response = api_session.get(url, headers=headers, params=params, timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and isinstance(data["data"], list): all_records.extend(data["data"])
                    elif "list" in data and isinstance(data["list"], list): all_records.extend(data["list"])
                    elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: all_records.extend(data["data"]["list"])
            except Exception:
                pass
            
    return all_records

def update_predictions(state, next_issue_int):
    # --- Strategy Logic (Wait for 2 Consecutive) ---
    if not state["active"] and len(state["full_history"]) >= 2:
        last_2_bs = [x["bs"] for x in state["full_history"][:2]]
        
        if last_2_bs == ["Big", "Big"]:
            state["active"] = True
            state["rounds_left"] = 4 # Allow 4 Levels (100, 200, 500, 1100)
            state["pred"] = "Small"
            state["level"] = 1
        elif last_2_bs == ["Small", "Small"]:
            state["active"] = True
            state["rounds_left"] = 4
            state["pred"] = "Big"
            state["level"] = 1
        else:
            state["pred"] = "WAIT"

def process_strategy(state, records):
    if not records: return False
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if not (latest_number_str.isdigit() and latest_issue.isdigit()): return False
    latest_bs = "Big" if int(latest_number_str) >= 5 else "Small"

    existing_issues = {x["issue"] for x in state["full_history"]}
    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss.isdigit() and num_str.isdigit() and iss not in existing_issues:
            bs_val = "Big" if int(num_str) >= 5 else "Small"
            state["full_history"].append({
                "issue": iss, 
                "bs": bs_val
            })
            existing_issues.add(iss)
                
    state["full_history"].sort(key=lambda x: int(x["issue"]), reverse=True)
    state["full_history"] = state["full_history"][:60]

    # --- Initial State ---
    if state["last_processed_issue"] == "Waiting...":
        state["last_processed_issue"] = latest_issue
        next_issue_int = int(latest_issue) + 1
        
        update_predictions(state, next_issue_int)
        
        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int))
        return True

    # --- Next Trades ---
    if state["last_processed_issue"] != latest_issue and state["last_processed_issue"] != "Waiting...":
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        state["total_trades"] += 1
        prev_res_text = f"🎯 Result: *{latest_number_str}* ({latest_bs})\n"
        
        # --- Evaluate Strategy ---
        if state["active"] and state["pred"] != "WAIT":
            bet_amt = BET_TABLE.get(state["level"], 0)
            
            if state["pred"] == latest_bs:
                state["win"] += 1
                state["virtual_balance"] += bet_amt  # Profit added to balance
                
                prev_res_text += f"✅ *WIN* (+₹{bet_amt})\n"
                
                # Reset for next pattern
                state["active"] = False
                state["level"] = 1
                state["pred"] = "WAIT"
            else:
                state["fail"] += 1
                state["virtual_balance"] -= bet_amt  # Loss deducted from balance
                
                prev_res_text += f"❌ *FAIL* (-₹{bet_amt})\n"
                
                state["level"] += 1
                state["rounds_left"] -= 1
                
                # Check if Level 4 failed (Max limit reached)
                if state["level"] > 4 or state["rounds_left"] <= 0:
                    prev_res_text += f"⚠️ *Level 4 Failed. Waiting for new pattern.*\n"
                    state["active"] = False
                    state["level"] = 1
                    state["pred"] = "WAIT"

        state["last_result_text"] = prev_res_text

        next_issue_int = int(latest_issue) + 1
        update_predictions(state, next_issue_int)

        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int), prev_res_text)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def background_bot_loop():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
    while True:
        records = fetch_history_records(url)
        if records:
            process_strategy(bot_state, records)
        time.sleep(3) 

# ----------------- WEB DASHBOARD TEMPLATE -----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>VSR 1M (2-Opp) Bot</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, sans-serif; text-align: center; padding: 20px; }
        .card { background: #1e293b; border-radius: 16px; padding: 25px; max-width: 480px; margin: auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 22px; margin-bottom: 5px; }
        .subtitle { color: #94a3b8; font-size: 13px; margin-bottom: 15px; }
        .wallet-box { background: linear-gradient(135deg, #10b981, #059669); padding: 15px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #047857; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .wallet-title { font-size: 14px; opacity: 0.9; margin-bottom: 5px; }
        .wallet-amount { font-size: 28px; font-weight: bold; letter-spacing: 1px; }
        .stats-box { background: #1e293b; padding: 12px; border-radius: 10px; border: 1px solid #475569; margin-bottom: 12px; display: flex; justify-content: space-around;}
        .stat-item { font-size: 14px; }
        .metric { background: #334155; margin: 8px 0; padding: 10px 12px; border-radius: 8px; font-size: 14px; text-align: left; display: flex; justify-content: space-between; align-items: center; }
        .highlight { color: #38bdf8; font-weight: bold; font-size: 15px; }
        .result-box { background: #0f172a; margin-top: 15px; padding: 12px; border-radius: 8px; font-size: 13px; color: #cbd5e1; text-align: left; border-left: 4px solid #facc15; line-height: 1.5; }
        .status-badge { background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .status-active { background: #22c55e; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🚀 VSR 1M Auto Trading Bot</h1>
        <div class="subtitle">
            Bot Status: <span id="timer_status" class="status-badge">INACTIVE</span>
        </div>
        
        <div class="wallet-box">
            <div class="wallet-title">Virtual Balance</div>
            <div class="wallet-amount" id="v_balance">₹20,000</div>
        </div>
        
        <div class="stats-box">
            <div class="stat-item" style="color: #6ee7b7;">Won: <b id="stat_w">0</b></div>
            <div class="stat-item" style="color: #fca5a5;">Failed: <b id="stat_f">0</b></div>
        </div>
        
        <div class="metric"><span>🎟️ Next Ticket:</span> <span class="highlight" id="last_issue">Loading...</span></div>
        <div class="metric"><span>📐 Prediction:</span> <span class="highlight" id="pred_info">-</span></div>
        <div class="metric"><span>💵 Bet Amount:</span> <span class="highlight" id="bet_info">-</span></div>
        
        <div class="result-box" id="last_result">
            <b>📊 Last Trade Status:</b><br>Initializing...
        </div>
    </div>

    <script>
        const betTable = {1: 100, 2: 200, 3: 500, 4: 1100};
        
        function updateDashboard() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    let nextIss = data.last_processed_issue;
                    if(nextIss !== "Waiting..." && !isNaN(nextIss)) {
                        nextIss = (parseInt(nextIss) + 1).toString();
                    }
                    
                    document.getElementById('last_issue').innerText = nextIss;
                    document.getElementById('v_balance').innerText = "₹" + data.virtual_balance.toLocaleString();
                    
                    // Pred Info
                    let predText = data.pred;
                    if(data.pred !== "WAIT") predText += " (L" + data.level + ")";
                    document.getElementById('pred_info').innerText = predText;
                    
                    // Bet Info
                    if(data.pred !== "WAIT" && data.level <= 4) {
                        document.getElementById('bet_info').innerText = "₹" + betTable[data.level];
                    } else {
                        document.getElementById('bet_info').innerText = "₹0 (Waiting)";
                    }
                    
                    // Stats
                    document.getElementById('stat_w').innerText = data.win;
                    document.getElementById('stat_f').innerText = data.fail;
                    
                    // Result Box Formatting
                    let formatted_result = data.last_result_text.replace(/\\n/g, "<br>");
                    document.getElementById('last_result').innerHTML = "<b>📊 Last Trade Status:</b><br>" + formatted_result;
                    
                    // Status Badge
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
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/data')
def get_data():
    return jsonify(bot_state)

if __name__ == '__main__':
    t1 = threading.Thread(target=background_bot_loop, daemon=True)
    t1.start()
    
    t2 = threading.Thread(target=telegram_listener, daemon=True)
    t2.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
