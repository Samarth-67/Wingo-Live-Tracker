import time
import threading
import os
import requests
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# ---------------- TELEGRAM BOT CONFIGURATION ----------------
TELEGRAM_BOT_TOKEN = "8886107397:AAHENOebGnrupxvGKqKh5cKC3SmujXJOV3w"
SECRET_PASSWORD = "12345"
TARGET_CHANNEL_ID = "-1004370895879"  # <--- तुझा चॅनेल आयडी
# ------------------------------------------------------------

# Global State for Dashboard and Logic
bot_state = {
    "last_issue": "Waiting for data...",
    "latest_number": "-",
    "status": "WAITING",
    "bs_pred": "-", "bs_level_num": 1, "bs_level": "L1",
    "last_result": "Bot is initializing...",
    "jackpot": False,
    "violet_gap": 0,
    
    # --- 3-Circle Strategy Variables ---
    "mode": "normal",
    "circle_current_target": None, 
    "circle_count": 0,
    
    # AI Violet Strategy States & 100 Rounds Data
    "full_history": [],
    "hot_gap": None,
    "hot_number": None,
    "v_count_100": 0,
    "max_lvl_100": 1,
    
    "violet_alert_active": False,   
    "violet_alert_type": "None",      
    "violet_level": 0,              
    "violet_mega_win": False,       
    
    "active_until": 0,
    "notified_sleep": True
}

def get_wingo_data():
    ts = int(time.time() * 1000)
    target_url = f"https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?ts={ts}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://ar-lottery01.com/"
    }
    try:
        res = requests.get(target_url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list): return data["data"]
                elif "list" in data and isinstance(data["list"], list): return data["list"]
                elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: return data["data"]["list"]
    except:
        pass
    return []

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except Exception as e:
        print("Telegram Send Error:", e)

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
                            bot_state["active_until"] = time.time() + 3600
                            bot_state["notified_sleep"] = False
                            print("✅ Bot activated via Telegram!")
                            send_telegram_message(chat_id, "✅ *Bot Activated! AI Violet + 3-Circle + 100-Round Stats Running!*")
                        else:
                            send_telegram_message(chat_id, "❌ Access Denied!")
        except Exception as e:
            pass
        time.sleep(3)

def analyze_violet_history(full_history):
    if not full_history or len(full_history) < 20:
        return None, None
        
    gaps = []
    preceding_numbers = {}
    last_violet_idx = -1
    
    for i in range(len(full_history)):
        num = full_history[i]['number']
        is_violet = (num == 0 or num == 5)
        
        if is_violet:
            if i + 1 < len(full_history):
                prev_num = full_history[i+1]['number']
                preceding_numbers[prev_num] = preceding_numbers.get(prev_num, 0) + 1
            
            if last_violet_idx != -1:
                gap = i - last_violet_idx - 1
                gaps.append(gap)
            
            last_violet_idx = i
            
    hot_gap = max(set(gaps), key=gaps.count) if gaps else None
    hot_number = max(preceding_numbers, key=preceding_numbers.get) if preceding_numbers else None
    return hot_gap, hot_number

def get_100_rounds_stats(full_history):
    if not full_history or len(full_history) < 2:
        return 0, 1
        
    violet_count = sum(1 for x in full_history if x['number'] in [0, 5])
    history_asc = sorted(full_history, key=lambda x: x['issue'])
    
    bs_pred = None
    bs_level = 1
    max_level = 1
    mode = "normal"
    circle_target = None
    circle_count = 0
    
    for item in history_asc:
        num = item['number']
        actual_bs = "Big" if num >= 5 else "Small"
        
        if bs_pred is None:
            bs_pred = actual_bs
            continue
            
        if bs_pred == actual_bs:
            bs_level = 1
            mode = "normal"
        else:
            bs_level += 1
            if bs_level > max_level:
                max_level = bs_level
                
        if mode == "normal":
            if bs_level >= 4:
                mode = "3-circle"
                circle_target = actual_bs
                circle_count = 1
                bs_pred = circle_target
            else:
                bs_pred = actual_bs
        elif mode == "3-circle":
            circle_count += 1
            if circle_count > 3:
                circle_target = "Small" if circle_target == "Big" else "Big"
                circle_count = 1
            bs_pred = circle_target
            
    return violet_count, max_level

def background_bot_loop():
    global bot_state
    last_processed = None

    while True:
        try:
            records = get_wingo_data()
            if records:
                # ---------------- Update Full History for AI & Stats ----------------
                for r in records:
                    iss = str(r.get("issueNumber") or r.get("issue") or "")
                    num_str = str(r.get("number") or r.get("drawNumber") or "")
                    if iss and num_str.isdigit():
                        if not any(x['issue'] == iss for x in bot_state["full_history"]):
                            bot_state["full_history"].append({'issue': iss, 'number': int(num_str)})
                
                bot_state["full_history"].sort(key=lambda x: x['issue'], reverse=True)
                bot_state["full_history"] = bot_state["full_history"][:100]
                
                h_gap, h_num = analyze_violet_history(bot_state["full_history"])
                bot_state["hot_gap"] = h_gap
                bot_state["hot_number"] = h_num
                
                v_count, max_lvl = get_100_rounds_stats(bot_state["full_history"])
                bot_state["v_count_100"] = v_count
                bot_state["max_lvl_100"] = max_lvl
                # --------------------------------------------------------------------

                latest = records[0]
                issue = str(latest.get("issueNumber") or latest.get("issue") or latest.get("period") or "-")
                num_str = str(latest.get("number") or latest.get("drawNumber") or "-")

                if num_str.isdigit():
                    number = int(num_str)
                    actual_bs = "Big" if number >= 5 else "Small"
                    is_violet = (number == 0 or number == 5)

                    if last_processed is None:
                        last_processed = issue
                        bot_state["bs_pred"] = actual_bs
                        bot_state["status"] = "PREDICTING"
                        bot_state["jackpot"] = False
                        
                        gap = 0
                        for r in records:
                            n_str = str(r.get("number", "-"))
                            if n_str.isdigit() and (int(n_str) == 0 or int(n_str) == 5): break
                            gap += 1
                        bot_state["violet_gap"] = gap
                        
                        print(f"✅ Initialized at Ticket: {issue} | AI Training Ready")

                    elif last_processed != issue:
                        print("\n" + "=" * 55)
                        print(f"✅ Result Declared for Ticket: {issue}")
                        print(f"🎲 Number Came: {number}")

                        bs_res_status = None
                        violet_res_status = ""  # इथे रिकामी स्ट्रिंग वापरली आहे (खोटा मेसेज टाळण्यासाठी)

                        if bot_state["status"] == "PREDICTING":
                            # --- 1. Big/Small Logic (Trend + 3-Circle) ---
                            bs_win = (bot_state["bs_pred"] == actual_bs)
                            bot_state["jackpot"] = bs_win 
                            bs_res_status = f"{bot_state['bs_pred']} {'✅ WIN' if bs_win else '❌ FAIL'}"

                            if bs_win: 
                                bot_state["bs_level_num"] = 1
                                bot_state["mode"] = "normal" 
                            else: 
                                bot_state["bs_level_num"] += 1
                                
                            if bot_state["mode"] == "normal":
                                if bot_state["bs_level_num"] >= 4:
                                    bot_state["mode"] = "3-circle"
                                    bot_state["circle_current_target"] = actual_bs
                                    bot_state["circle_count"] = 1
                                    bot_state["bs_pred"] = bot_state["circle_current_target"]
                                else:
                                    bot_state["bs_pred"] = actual_bs
                            elif bot_state["mode"] == "3-circle":
                                bot_state["circle_count"] += 1
                                if bot_state["circle_count"] > 3:
                                    bot_state["circle_current_target"] = "Small" if bot_state["circle_current_target"] == "Big" else "Big"
                                    bot_state["circle_count"] = 1
                                bot_state["bs_pred"] = bot_state["circle_current_target"]

                            # --- 2. AI Violet Evaluation ---
                            bot_state["violet_mega_win"] = False
                            
                            if is_violet:
                                if bot_state["violet_alert_active"]:
                                    print(f"   👉 🟣🔥 VIOLET AI MEGA WIN! ({bot_state['violet_alert_type']} Success at L{bot_state['violet_level']}) 🔥🟣")
                                    violet_res_status = f"🟣 ✅ AI WIN (L{bot_state['violet_level']})"
                                    bot_state["violet_mega_win"] = True
                                else:
                                    print("   👉 🟣 Violet Appeared! (Resetting gap, no message to Telegram)")
                                    violet_res_status = ""  # जर अलर्ट नसेल, तर मेसेजमध्ये काहीही जाणार नाही
                                    
                                bot_state["violet_gap"] = 0 
                                bot_state["violet_alert_active"] = False
                                bot_state["violet_alert_type"] = "None"
                                bot_state["violet_level"] = 0
                            else:
                                bot_state["violet_gap"] += 1
                                
                                if bot_state["violet_alert_active"]:
                                    print(f"   👉 ❌ AI {bot_state['violet_alert_type']} Level {bot_state['violet_level']} Fail")
                                    violet_res_status = f"🟣 ❌ FAIL ({bot_state['violet_alert_type']} L{bot_state['violet_level']})"
                                    
                                    if bot_state["violet_level"] >= 2:
                                        print("   ⚠️ 🛑 AI STOP LOSS HIT! Waiting for next exact AI pattern.")
                                        violet_res_status += " [🛑 STOP]"
                                        bot_state["violet_alert_active"] = False
                                        bot_state["violet_alert_type"] = "None"
                                        bot_state["violet_level"] = 0
                                    else:
                                        bot_state["violet_level"] += 1
                                else:
                                    print(f"   👉 No Violet. Current Gap: {bot_state['violet_gap']}")
                                    violet_res_status = ""

                            # --- 3. AI Trigger Checker for Next Round ---
                            if not bot_state["violet_alert_active"] and len(bot_state["full_history"]) >= 20:
                                if bot_state["hot_gap"] is not None and bot_state["violet_gap"] == bot_state["hot_gap"]:
                                    bot_state["violet_alert_active"] = True
                                    bot_state["violet_alert_type"] = f"AI Hot Gap ({bot_state['hot_gap']})"
                                    bot_state["violet_level"] = 1
                                    print(f"   🚨 AI TRIGGER: Current Gap matches Hot Gap ({bot_state['hot_gap']})! Alert L1 Started.")
                                elif bot_state["hot_number"] is not None and number == bot_state["hot_number"]:
                                    bot_state["violet_alert_active"] = True
                                    bot_state["violet_alert_type"] = f"AI Hot Num ({bot_state['hot_number']})"
                                    bot_state["violet_level"] = 1
                                    print(f"   🚨 AI TRIGGER: Result '{number}' matches Hot Number! Alert L1 Started.")

                            bot_state["last_result"] = f"B/S: {bs_res_status}"
                            if violet_res_status != "":
                                bot_state["last_result"] += f" | Violet: {violet_res_status}"

                        next_issue = str(int(issue) + 1) if issue.isdigit() else "Next"
                        
                        bot_state["last_issue"] = next_issue
                        bot_state["latest_number"] = number
                        bot_state["bs_level"] = f"L{bot_state['bs_level_num']}"
                        
                        last_processed = issue

                        # ---------------- 4. PREDICTION CONSOLE OUTPUT ----------------
                        print("-" * 55)
                        print(f"🎟️ PREDICTION FOR NEXT TICKET: {next_issue}")
                        print(f"📊 AI Status: Hot Gap = {bot_state['hot_gap']} | Hot Num = {bot_state['hot_number']}")
                        print(f"📈 100 Rounds Stats -> Violets: {bot_state['v_count_100']} | Max B/S Level: L{bot_state['max_lvl_100']}")
                        
                        if bot_state["violet_alert_active"]:
                            print(f"🔮 Violet Prediction: 🟣 {bot_state['violet_alert_type']} - Level {bot_state['violet_level']}")
                        else:
                            print(f"🔮 Violet Prediction: Waiting for AI match (Current Gap {bot_state['violet_gap']})")
                        print("=" * 55)

                        # Send Telegram Signal if active
                        if bot_state["active_until"] > 0 and time.time() < bot_state["active_until"]:
                            text = f"🚀 *VSR WINGO Signals 1 Minute* 🚀\n\n"
                            
                            text += f"🧠 *AI DATA:* Hot Gap [{bot_state['hot_gap']}] | Hot Num [{bot_state['hot_number']}]\n"
                            text += f"📊 *LAST 100:* 🟣 Violets: {bot_state['v_count_100']} | 📈 Max B/S: L{bot_state['max_lvl_100']}\n\n"
                            
                            if bs_res_status:
                                text += f"🔄 *Result for {issue}:*\n"
                                text += f"📏 B/S: {bs_res_status}\n"
                                
                                # जर अलर्ट असेल तरच वॉयलेटचा मेसेज ऍड होईल
                                if violet_res_status != "":
                                    text += f"🟣 Violet: {violet_res_status}\n"
                                    
                                if bot_state["violet_mega_win"]:
                                    text += f"\n🟣🔥 *VIOLET AI WIN!* 🔥🟣\n"
                                elif bot_state["jackpot"]:
                                    text += f"\n🔥🎉 *JACKPOT! WIN!* 🎉🔥\n"
                                    
                                text += f"\n➖➖➖➖➖➖➖➖\n\n"
                            
                            text += f"🎟️ *Prediction For Ticket:* {next_issue}\n\n"
                            
                            mode_text = " *(🔄 3-Circle)*" if bot_state.get("mode") == "3-circle" else ""
                            text += f"📏 *B/S Pred:* {bot_state['bs_pred']} (L{bot_state['bs_level_num']}){mode_text}\n\n"
                            
                            if bot_state["violet_alert_active"]:
                                text += f"⚠️ 🟣 *{bot_state['violet_alert_type'].upper()}*\n"
                                text += f"🎯 *Violet Level:* L{bot_state['violet_level']}\n"
                            else:
                                text += f"⏸️ *Violet Status:* Analyzing Pattern (Gap: {bot_state['violet_gap']})\n"

                            send_telegram_message(TARGET_CHANNEL_ID, text)
                        elif bot_state["active_until"] > 0 and time.time() >= bot_state["active_until"]:
                            if not bot_state["notified_sleep"]:
                                send_telegram_message(TARGET_CHANNEL_ID, "💤 *1 Hour Session Completed!*")
                                bot_state["notified_sleep"] = True
                                bot_state["active_until"] = 0
                                
        except Exception as e:
            pass
        time.sleep(5)

# Dashboard Design
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>VSR Wingo Live AI Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; padding: 20px; }
        .card { background: #1e293b; border-radius: 16px; padding: 25px; max-width: 450px; margin: auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 20px; margin-bottom: 5px; }
        .subtitle { color: #94a3b8; font-size: 12px; margin-bottom: 10px; }
        .ai-stats { background: #020617; padding: 10px; border-radius: 8px; font-size: 13px; color: #fbbf24; margin-bottom: 15px; border: 1px solid #fbbf24; line-height: 1.6;}
        .metric { background: #334155; margin: 12px 0; padding: 15px; border-radius: 10px; font-size: 16px; text-align: left; display: flex; justify-content: space-between; align-items: center; }
        .highlight { color: #4ade80; font-weight: bold; font-size: 18px; }
        .violet-active { color: #c084fc; font-weight: bold; font-size: 15px; animation: pulse 1.5s infinite; }
        .violet-waiting { color: #94a3b8; font-size: 15px; }
        .result-box { background: #0f172a; margin-top: 15px; padding: 12px; border-radius: 8px; font-size: 13px; color: #cbd5e1; text-align: left; border-left: 4px solid #38bdf8; }
        .jackpot { background: #eab308; color: #000; font-weight: bold; padding: 12px; border-radius: 8px; margin-top: 15px; font-size: 15px; display: none; animation: pulse 1.5s infinite; }
        .mega-win { background: #9333ea; color: #fff; font-weight: bold; padding: 12px; border-radius: 8px; margin-top: 15px; font-size: 15px; display: none; animation: pulse 1s infinite; }
        .status-badge { background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .status-active { background: #22c55e; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="card">
        <h1>🚀 VSR WINGO AI Dashboard</h1>
        <div class="subtitle">
            Signals Status: <span id="timer_status" class="status-badge">INACTIVE</span>
        </div>
        
        <div class="ai-stats">
            🧠 <b>Live AI Analytics:</b> <br>
            Hot Gap: <span id="hot_gap">-</span> | Hot Number: <span id="hot_num">-</span><br>
            📊 <b>Last 100:</b> Violets: <span id="v_100">0</span> | Max B/S: L<span id="max_l_100">1</span>
        </div>
        
        <div class="metric"><span>🎟️ Next Ticket:</span> <span class="highlight" id="last_issue">Loading...</span></div>
        <div class="metric"><span>📏 B/S Pred:</span> <span class="highlight" id="bs_info">-</span></div>
        <div class="metric"><span>🟣 Violet Pred:</span> <span id="violet_info">Analyzing...</span></div>
        
        <div class="result-box" id="last_result">
            <b>📊 Last Trade Status:</b><br>Initializing...
        </div>

        <div class="mega-win" id="mega_win_box">🟣🔥 VIOLET AI WIN! 🔥🟣</div>
        <div class="jackpot" id="jackpot_box">🔥🎉 JACKPOT! WIN! 🎉🔥</div>
    </div>

    <script>
        function updateDashboard() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('last_issue').innerText = data.last_issue;
                    
                    let bsText = data.bs_pred + " (" + data.bs_level + ")";
                    if(data.mode === "3-circle") { bsText += " 🔄 3-Circle"; }
                    document.getElementById('bs_info').innerText = bsText;
                    
                    document.getElementById('hot_gap').innerText = data.hot_gap !== null ? data.hot_gap : "Calc...";
                    document.getElementById('hot_num').innerText = data.hot_number !== null ? data.hot_number : "Calc...";
                    document.getElementById('v_100').innerText = data.v_count_100;
                    document.getElementById('max_l_100').innerText = data.max_lvl_100;
                    
                    const vInfo = document.getElementById('violet_info');
                    if (data.violet_alert_active) {
                        vInfo.innerText = "⚠️ " + data.violet_alert_type + " (L" + data.violet_level + ")";
                        vInfo.className = "violet-active";
                    } else {
                        vInfo.innerText = "⏸️ WAITING (Gap: " + data.violet_gap + ")";
                        vInfo.className = "violet-waiting";
                    }
                    
                    document.getElementById('last_result').innerHTML = "<b>📊 Last Trade Status:</b><br>" + data.last_result;
                    
                    const mw = document.getElementById('mega_win_box');
                    if (data.violet_mega_win) { mw.style.display = 'block'; } else { mw.style.display = 'none'; }
                    
                    const jp = document.getElementById('jackpot_box');
                    if (data.jackpot && !data.violet_mega_win) { jp.style.display = 'block'; } else { jp.style.display = 'none'; }

                    const statusBadge = document.getElementById('timer_status');
                    if (data.active_until > (Date.now() / 1000)) {
                        statusBadge.innerText = "ACTIVE (Running)";
                        statusBadge.className = "status-badge status-active";
                    } else {
                        statusBadge.innerText = "INACTIVE (Sleeping)";
                        statusBadge.className = "status-badge";
                    }
                }).catch(err => console.log(err));
        }
        setInterval(updateDashboard, 3000);
        updateDashboard();
    </script>
</body>
</html>
