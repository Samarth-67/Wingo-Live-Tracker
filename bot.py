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

# 🎨 कलर ओळखण्यासाठी फंक्शन
def get_color(num_str):
    num = int(num_str)
    if num in [1, 3, 7, 9]: return "Green 🟢"
    elif num in [2, 4, 6, 8]: return "Red 🔴"
    elif num == 0: return "Red & Violet 🔴🟣"
    elif num == 5: return "Green & Violet 🟢🟣"
    return "Unknown"

# 🚀 Global State for Logic & Dashboard
bot_state = {
    "name": "WinGo 1M",
    "last_processed_issue": "Waiting...",
    "bs_pred": "WAIT", 
    "color_pred": "WAIT",
    "bs_level": 1, 
    "color_level": 1, 
    
    "full_history": [], 
    "history": [],
    "bs_win": 0, 
    "bs_fail": 0, 
    "color_win": 0,
    "color_fail": 0,
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
                            send_telegram_message_direct(chat_id, f"✅ *[1M Strategy] Activated! Live Prediction is ON.*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    # 🔴 STOP COMMAND
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == SECRET_PASSWORD:
                            bot_state["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *[1M Strategy] Stopped Successfully!*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                            
                    # 🔄 RESET COMMAND
                    elif text.startswith("/reset"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == SECRET_PASSWORD:
                            bot_state["bs_level"] = 1
                            bot_state["color_level"] = 1
                            bot_state["bs_pred"] = "WAIT"
                            bot_state["color_pred"] = "WAIT"
                            bot_state["bs_win"] = 0
                            bot_state["bs_fail"] = 0
                            bot_state["color_win"] = 0
                            bot_state["color_fail"] = 0
                            bot_state["last_result_text"] = "Stats Reset Successfully!"
                            send_telegram_message_direct(chat_id, "🔄 *Levels & Stats Reset Successfully!*\nLevels are back to L1.")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, bs_pred, color_pred, bs_level, color_level, prev_res_text=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    text = f"🚀 *VSR WINGO 1M 20th Round Follower* 🚀\n\n"
    
    if state["total_trades"] > 0 and prev_res_text:
        text += f"🔄 *Last Trade Result:*\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Prediction For Ticket:* {issue}\n\n"
    
    if bs_pred == "WAIT":
        text += f"⏳ *Building History Data...*\n_Waiting for issue {int(issue)-20} to sync..._\n"
    else:
        bs_pred_text = "🟠 Big" if bs_pred == "Big" else "🔵 Small"
        
        text += f"📏 *B/S Pred:* *{bs_pred_text}* | 🎯 L{bs_level}\n"
        text += f"🎨 *Color Pred:* *{color_pred}* | 🎯 L{color_level}\n\n"
        
    send_telegram_message_direct(target_chat_id, text)

# 🚀 फास्ट मल्टी-पेज हिस्ट्री
def fetch_history_records(url, state):
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

# 🎯 20th Round Accurate Logic
def process_strategy(state, records):
    if not records: return False
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if not (latest_number_str.isdigit() and latest_issue.isdigit()): return False
    
    latest_bs = "Big" if int(latest_number_str) >= 5 else "Small"
    latest_color = get_color(latest_number_str)

    existing_issues = {x["issue"] for x in state["full_history"]}
    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss.isdigit() and num_str.isdigit() and iss not in existing_issues:
            bs_val = "Big" if int(num_str) >= 5 else "Small"
            state["full_history"].append({
                "issue": iss, 
                "bs": bs_val, 
                "color": get_color(num_str)
            })
            existing_issues.add(iss)
                
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
            state["color_pred"] = target_record["color"]
        elif len(state["full_history"]) >= 20:
            state["bs_pred"] = state["full_history"][19]["bs"]
            state["color_pred"] = state["full_history"][19]["color"]
        else:
            state["bs_pred"] = "WAIT"
            state["color_pred"] = "WAIT"
        
        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int), state["bs_pred"], state["color_pred"], state["bs_level"], state["color_level"])
        return True

    # --- Next Trades (Analysis & Levels Logic Combine) ---
    if state["last_processed_issue"] != latest_issue and state["last_processed_issue"] != "Waiting...":
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        prev_res_text = ""
        
        if state["bs_pred"] != "WAIT":
            state["total_trades"] += 1
            
            # --- B/S Win/Fail Logic ---
            bs_win = (state["bs_pred"] == latest_bs)
            
            # --- Color Win/Fail Logic ---
            color_win = False
            if "Green" in state["color_pred"] and "Green" in latest_color:
                color_win = True
            elif "Red" in state["color_pred"] and "Red" in latest_color:
                color_win = True
                
            bs_mark = "✅" if bs_win else "❌"
            color_mark = "✅" if color_win else "❌"
            
            prev_res_text = (
                f"📏 B/S: *{latest_bs}* {bs_mark}\n"
                f"🎨 Color: *{latest_color}* {color_mark}"
            )
            
            # --- Levels Update Logic ---
            if bs_win:
                state["bs_win"] += 1
                state["bs_level"] = 1 
                prev_res_text += f"\n\n🔥🎉 *CONGRATS! B/S WIN!* 🎉🔥"
            else:
                state["bs_fail"] += 1
                state["bs_level"] += 1
                prev_res_text += f"\n\n❌ *B/S FAIL* ❌"
                
            if color_win:
                state["color_win"] += 1
                state["color_level"] = 1 
                prev_res_text += f"\n🎨🎉 *COLOR WIN!* 🎉🎨"
            else:
                state["color_fail"] += 1
                state["color_level"] += 1

            state["last_result_text"] = prev_res_text

        # Calculate next target (20th round)
        next_issue_int = int(latest_issue) + 1
        target_issue_str = str(next_issue_int - 20)
        
        target_record = next((x for x in state["full_history"] if x["issue"] == target_issue_str), None)
        
        if target_record:
            state["bs_pred"] = target_record["bs"]
            state["color_pred"] = target_record["color"]
        elif len(state["full_history"]) >= 20:
            state["bs_pred"] = state["full_history"][19]["bs"]
            state["color_pred"] = state["full_history"][19]["color"]
        else:
            state["bs_pred"] = "WAIT"
            state["color_pred"] = "WAIT"

        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int), state["bs_pred"], state["color_pred"], state["bs_level"], state["color_level"], prev_res_text)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def background_bot_loop():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
    while True:
        records = fetch_history_records(url, bot_state)
        if records:
            process_strategy(bot_state, records)
        time.sleep(3) 

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
        .stats-box { background: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #475569; margin-bottom: 15px; }
        .metric { background: #334155; margin: 10px 0; padding: 12px; border-radius: 10px; font-size: 15px; text-align: left; display: flex; justify-content: space-between; align-items: center; }
        .highlight { color: #38bdf8; font-weight: bold; font-size: 16px; }
        .result-box { background: #0f172a; margin-top: 15px; padding: 12px; border-radius: 8px; font-size: 14px; color: #cbd5e1; text-align: left; border-left: 4px solid #facc15; }
        .status-badge { background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .status-active { background: #22c55e; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🚀 VSR 1M 20th Round Strategy</h1>
        <div class="subtitle">
            Bot Status: <span id="timer_status" class="status-badge">INACTIVE</span>
        </div>
        
        <div class="stats-box">
            <div style="font-size: 15px; color: #a7f3d0; margin-bottom: 5px;">📊 Performance Stats</div>
            <div style="font-size: 14px; color: #6ee7b7;">B/S - Won: <b id="w_cnt">0</b> | Failed: <b id="f_cnt">0</b></div>
        </div>
        
        <div class="metric"><span>🎟️ Next Ticket:</span> <span class="highlight" id="last_issue">Loading...</span></div>
        <div class="metric"><span>📏 B/S Pred:</span> <span class="highlight" id="bs_info">-</span></div>
        <div class="metric"><span>🎨 Color Pred:</span> <span class="highlight" id="color_info">-</span></div>
        
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
                    
                    // Predictions Update
                    let bsText = data.bs_pred;
                    if(data.bs_pred !== "WAIT") bsText += " (L" + data.bs_level + ")";
                    document.getElementById('bs_info').innerText = bsText;
                    
                    let colText = data.color_pred;
                    if(data.color_pred !== "WAIT") colText += " (L" + data.color_level + ")";
                    document.getElementById('color_info').innerText = colText;
                    
                    // Stats Update
                    document.getElementById('w_cnt').innerText = data.bs_win;
                    document.getElementById('f_cnt').innerText = data.bs_fail;
                    
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
