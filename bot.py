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

# 🚀 Global State for Dual Strategy Dashboard & Logic
bot_state = {
    "name": "WinGo 1M Dual Strategy",
    "last_processed_issue": "Waiting...",
    
    # Strategy 1 (20th Record)
    "s1_pred": "WAIT",
    "s1_level": 1,
    
    # Strategy 2 (3 Consecutive Opposite)
    "s2_pred": "WAIT",
    "s2_level": 1,
    "s2_active": False,
    "s2_rounds_left": 0,
    
    "full_history": [], 
    "history": [],
    
    # Stats
    "s1_win": 0,
    "s1_fail": 0,
    "s2_win": 0,
    "s2_fail": 0,
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
                            send_telegram_message_direct(chat_id, f"✅ *[1M Dual Strategy] Activated! Live Prediction is ON.*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    # 🔴 STOP COMMAND
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == SECRET_PASSWORD:
                            bot_state["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *[1M Dual Strategy] Stopped Successfully!*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    # 🔄 RESET COMMAND
                    elif text.startswith("/reset"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == SECRET_PASSWORD:
                            bot_state["s1_level"] = 1
                            bot_state["s2_level"] = 1
                            bot_state["s1_pred"] = "WAIT"
                            bot_state["s2_pred"] = "WAIT"
                            bot_state["s2_active"] = False
                            bot_state["s2_rounds_left"] = 0
                            bot_state["s1_win"] = 0
                            bot_state["s1_fail"] = 0
                            bot_state["s2_win"] = 0
                            bot_state["s2_fail"] = 0
                            bot_state["last_result_text"] = "Stats Reset Successfully!"
                            send_telegram_message_direct(chat_id, "🔄 *Levels & Stats Reset Successfully!*\nLevels are back to L1.")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, prev_res_text=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    text = f"🚀 *VSR WINGO 1M Dual Strategy* 🚀\n\n"
    
    if prev_res_text:
        text += f"🔄 *Last Trade Result:*\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Next Issue:* `{issue}`\n\n"
    
    # Strategy 1 Text
    if state["s1_pred"] == "WAIT":
        text += f"📏 *Strategy 1 (20th):* ⏳ Syncing...\n"
    else:
        s1_icon = "🟠 Big" if state["s1_pred"] == "Big" else "🔵 Small"
        text += f"📏 *Strategy 1 (20th):* *{s1_icon}* | 🎯 L{state['s1_level']}\n"

    # Strategy 2 Text
    if state["s2_pred"] == "WAIT":
        text += f"📐 *Strategy 2 (3-Opp):* ⏳ Waiting for 3 B/S...\n\n"
    else:
        s2_icon = "🟠 Big" if state["s2_pred"] == "Big" else "🔵 Small"
        text += f"📐 *Strategy 2 (3-Opp):* *{s2_icon}* | 🎯 L{state['s2_level']}\n\n"
        
    text += f"💡 _Bet according to your level._"
        
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
    # --- Strategy 1 Logic (20th Record) ---
    target_issue_str = str(next_issue_int - 20) 
    target_record = next((x for x in state["full_history"] if x["issue"] == target_issue_str), None)
    
    if target_record:
        state["s1_pred"] = target_record["bs"]
    elif len(state["full_history"]) >= 20:
        state["s1_pred"] = state["full_history"][19]["bs"]
    else:
        state["s1_pred"] = "WAIT"

    # --- Strategy 2 Logic (Wait for 3 Consecutive) ---
    if not state["s2_active"] and len(state["full_history"]) >= 3:
        last_3_bs = [x["bs"] for x in state["full_history"][:3]]
        
        if last_3_bs == ["Big", "Big", "Big"]:
            state["s2_active"] = True
            state["s2_rounds_left"] = 3
            state["s2_pred"] = "Small"
            state["s2_level"] = 1
        elif last_3_bs == ["Small", "Small", "Small"]:
            state["s2_active"] = True
            state["s2_rounds_left"] = 3
            state["s2_pred"] = "Big"
            state["s2_level"] = 1
        else:
            state["s2_pred"] = "WAIT"

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
        s1_res_status = "-"
        s2_res_status = "-"
        
        # --- Evaluate Strategy 1 ---
        if state["s1_pred"] != "WAIT":
            if state["s1_pred"] == latest_bs:
                state["s1_win"] += 1
                state["s1_level"] = 1 
                s1_res_status = "WIN"
                prev_res_text += f"📏 S1 (20th): ✅ WIN\n"
            else:
                state["s1_fail"] += 1
                state["s1_level"] += 1
                s1_res_status = "FAIL"
                prev_res_text += f"📏 S1 (20th): ❌ FAIL\n"
        
        # --- Evaluate Strategy 2 ---
        if state["s2_active"] and state["s2_pred"] != "WAIT":
            if state["s2_pred"] == latest_bs:
                state["s2_win"] += 1
                state["s2_active"] = False
                state["s2_level"] = 1
                state["s2_pred"] = "WAIT"
                s2_res_status = "WIN"
                prev_res_text += f"📐 S2 (3-Opp): ✅ WIN\n"
            else:
                state["s2_fail"] += 1
                state["s2_level"] += 1
                state["s2_rounds_left"] -= 1
                s2_res_status = "FAIL"
                prev_res_text += f"📐 S2 (3-Opp): ❌ FAIL\n"
                
                if state["s2_rounds_left"] <= 0:
                    state["s2_active"] = False
                    state["s2_level"] = 1
                    state["s2_pred"] = "WAIT"

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
    <title>VSR 1M Dual Strategy Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, sans-serif; text-align: center; padding: 20px; }
        .card { background: #1e293b; border-radius: 16px; padding: 25px; max-width: 480px; margin: auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 20px; margin-bottom: 5px; }
        .subtitle { color: #94a3b8; font-size: 13px; margin-bottom: 15px; }
        .stats-box { background: #1e293b; padding: 12px; border-radius: 10px; border: 1px solid #475569; margin-bottom: 12px; }
        .metric { background: #334155; margin: 8px 0; padding: 10px 12px; border-radius: 8px; font-size: 14px; text-align: left; display: flex; justify-content: space-between; align-items: center; }
        .highlight { color: #38bdf8; font-weight: bold; font-size: 15px; }
        .result-box { background: #0f172a; margin-top: 15px; padding: 12px; border-radius: 8px; font-size: 13px; color: #cbd5e1; text-align: left; border-left: 4px solid #facc15; }
        .status-badge { background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .status-active { background: #22c55e; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🚀 VSR 1M Dual Strategy</h1>
        <div class="subtitle">
            Bot Status: <span id="timer_status" class="status-badge">INACTIVE</span>
        </div>
        
        <div class="stats-box">
            <div style="font-size: 14px; color: #a7f3d0; margin-bottom: 4px;">📊 Performance Stats</div>
            <div style="font-size: 13px; color: #6ee7b7;">S1 (20th) - Won: <b id="s1_w">0</b> | Failed: <b id="s1_f">0</b></div>
            <div style="font-size: 13px; color: #93c5fd;">S2 (3-Opp) - Won: <b id="s2_w">0</b> | Failed: <b id="s2_f">0</b></div>
        </div>
        
        <div class="metric"><span>🎟️ Next Ticket:</span> <span class="highlight" id="last_issue">Loading...</span></div>
        <div class="metric"><span>📏 S1 Pred (20th):</span> <span class="highlight" id="s1_info">-</span></div>
        <div class="metric"><span>📐 S2 Pred (3-Opp):</span> <span class="highlight" id="s2_info">-</span></div>
        
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
                    
                    // S1 Info
                    let s1Text = data.s1_pred;
                    if(data.s1_pred !== "WAIT") s1Text += " (L" + data.s1_level + ")";
                    document.getElementById('s1_info').innerText = s1Text;
                    
                    // S2 Info
                    let s2Text = data.s2_pred;
                    if(data.s2_pred !== "WAIT") s2Text += " (L" + data.s2_level + ")";
                    document.getElementById('s2_info').innerText = s2Text;
                    
                    // Stats
                    document.getElementById('s1_w').innerText = data.s1_win;
                    document.getElementById('s1_f').innerText = data.s1_fail;
                    document.getElementById('s2_w').innerText = data.s2_win;
                    document.getElementById('s2_f').innerText = data.s2_fail;
                    
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
