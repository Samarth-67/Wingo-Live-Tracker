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
    
    # --- 3-Circle Strategy Variables ---
    "mode": "normal",
    "circle_current_target": None, 
    "circle_count": 0,
    
    # --- SUPER 8 Strategy States & 100 Rounds Data ---
    "full_history": [],
    "se_wins_100": 0,     # मागच्या १०० मध्ये 'सुपर 8' ने जिंकलेले
    "se_fails_100": 0,    # मागच्या १०० मध्ये 'सुपर 8' फेल गेलेले
    "max_lvl_100": 1,     # मागच्या १०० मध्ये B/S ची जास्तीत जास्त लेव्हल
    
    "se_active": False,   
    "se_level": 0,              
    "se_target": None,       
    "se_mega_win": False,
    
    "active_until": 0,
    "notified_sleep": True
}

def get_wingo_data():
    ts = int(time.time() * 1000)
    target_url = f"https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?pageSize=100&pageNumber=1&size=100&page=1&ts={ts}"
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
                            send_telegram_message(chat_id, "✅ *Bot Activated! Super 8 Strategy + 3-Circle Running!*")
                        else:
                            send_telegram_message(chat_id, "❌ Access Denied!")
        except Exception as e:
            pass
        time.sleep(3)

def get_100_rounds_stats(full_history):
    # Calculate Super 8 Wins/Fails and Max B/S Level
    if not full_history or len(full_history) < 2:
        return 0, 0, 1
        
    history_asc = sorted(full_history, key=lambda x: x['issue'])
    
    bs_pred = None
    bs_level = 1
    max_level = 1
    mode = "normal"
    circle_target = None
    circle_count = 0
    
    se_wins = 0
    se_fails = 0
    se_active = False
    se_level = 0
    se_target = None
    
    for item in history_asc:
        num = item['number']
        actual_bs = "Big" if num >= 5 else "Small"
        
        # --- B/S Logic Simulation ---
        if bs_pred is None:
            bs_pred = actual_bs
        else:
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

        # --- Super 8 Logic Simulation ---
        if se_active:
            if num == se_target:
                se_wins += 1
                se_active = False
            elif num == 8:
                # 8 आल्यास L1 पुन्हा सुरू करा
                se_level = 1
                se_target = 6
            else:
                if se_level == 1:
                    se_level = 2
                    se_target = 4
                else:
                    se_fails += 1
                    se_active = False
                    
        if not se_active:
            if num == 8:
                se_active = True
                se_level = 1
                se_target = 6
                
    return se_wins, se_fails, max_level

def background_bot_loop():
    global bot_state
    last_processed = None

    while True:
        try:
            records = get_wingo_data()
            if records:
                # ---------------- Update Full History & Stats ----------------
                for r in records:
                    iss = str(r.get("issueNumber") or r.get("issue") or "")
                    num_str = str(r.get("number") or r.get("drawNumber") or "")
                    if iss and num_str.isdigit():
                        if not any(x['issue'] == iss for x in bot_state["full_history"]):
                            bot_state["full_history"].append({'issue': iss, 'number': int(num_str)})
                
                bot_state["full_history"].sort(key=lambda x: x['issue'], reverse=True)
                bot_state["full_history"] = bot_state["full_history"][:100]
                
                wins_100, fails_100, max_lvl = get_100_rounds_stats(bot_state["full_history"])
                bot_state["se_wins_100"] = wins_100
                bot_state["se_fails_100"] = fails_100
                bot_state["max_lvl_100"] = max_lvl
                # --------------------------------------------------------------------

                latest = records[0]
                issue = str(latest.get("issueNumber") or latest.get("issue") or latest.get("period") or "-")
                num_str = str(latest.get("number") or latest.get("drawNumber") or "-")

                if num_str.isdigit():
                    number = int(num_str)
                    actual_bs = "Big" if number >= 5 else "Small"

                    if last_processed is None:
                        last_processed = issue
                        bot_state["bs_pred"] = actual_bs
                        bot_state["status"] = "PREDICTING"
                        bot_state["jackpot"] = False
                        
                        print(f"✅ Initialized at Ticket: {issue} | Fetched 100 Rounds Data | Super 8 Ready")

                    elif last_processed != issue:
                        print("\n" + "=" * 55)
                        print(f"✅ Result Declared for Ticket: {issue}")
                        print(f"🎲 Number Came: {number}")

                        bs_res_status = None
                        se_res_status = ""  

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

                            # --- 2. SUPER 8 Evaluation ---
                            bot_state["se_mega_win"] = False
                            
                            if bot_state["se_active"]:
                                if number == bot_state["se_target"]:
                                    print(f"   👉 🎱🔥 SUPER 8 WIN! (Won at L{bot_state['se_level']} with {number}) 🔥🎱")
                                    se_res_status = f"🎱 ✅ WIN (L{bot_state['se_level']} - Num {number})"
                                    bot_state["se_mega_win"] = True
                                    bot_state["se_active"] = False
                                    bot_state["se_level"] = 0
                                    bot_state["se_target"] = None
                                elif number == 8:
                                    # 8 परत आल्यास L1 नव्याने चालू करा
                                    print(f"   👉 🎱 Got '8' again! Restarting Super 8 Level 1.")
                                    se_res_status = f"🎱 ❌ FAIL (Got 8, Restarting L1)"
                                    bot_state["se_level"] = 1
                                    bot_state["se_target"] = 6
                                else:
                                    if bot_state["se_level"] == 1:
                                        print(f"   👉 ❌ Super 8 L1 Fail. Moving to L2.")
                                        se_res_status = f"🎱 ❌ FAIL (L1 Target {bot_state['se_target']})"
                                        bot_state["se_level"] = 2
                                        bot_state["se_target"] = 4
                                    else:
                                        print(f"   👉 ⚠️ 🛑 SUPER 8 STOP LOSS HIT!")
                                        se_res_status = f"🎱 ❌ FAIL L2 [🛑 STOP]"
                                        bot_state["se_active"] = False
                                        bot_state["se_level"] = 0
                                        bot_state["se_target"] = None

                            # --- 3. Super 8 Trigger Checker for Next Round ---
                            if not bot_state["se_active"]:
                                if number == 8:
                                    bot_state["se_active"] = True
                                    bot_state["se_level"] = 1
                                    bot_state["se_target"] = 6
                                    print(f"   🚨 SUPER 8 TRIGGER: '8' Appeared! Alert L1 Started.")

                            bot_state["last_result"] = f"B/S: {bs_res_status}"
                            if se_res_status != "":
                                bot_state["last_result"] += f" | Super 8: {se_res_status}"

                        next_issue = str(int(issue) + 1) if issue.isdigit() else "Next"
                        
                        bot_state["last_issue"] = next_issue
                        bot_state["latest_number"] = number
                        bot_state["bs_level"] = f"L{bot_state['bs_level_num']}"
                        
                        last_processed = issue

                        # ---------------- 4. PREDICTION CONSOLE OUTPUT ----------------
                        print("-" * 55)
                        print(f"🎟️ PREDICTION FOR NEXT TICKET: {next_issue}")
                        print(f"📈 100 Rounds Stats -> Super 8: {bot_state['se_wins_100']} Wins, {bot_state['se_fails_100']} Fails | Max B/S Lvl: L{bot_state['max_lvl_100']}")
                        
                        if bot_state["se_active"]:
                            print(f"🔮 Super 8 Prediction: 🎱 Number {bot_state['se_target']} - Level {bot_state['se_level']}")
                        else:
                            print(f"🔮 Super 8 Prediction: Waiting for '8'")
                        print("=" * 55)

                        # Send Telegram Signal if active
                        if bot_state["active_until"] > 0 and time.time() < bot_state["active_until"]:
                            text = f"🚀 *VSR WINGO Signals 1 Minute* 🚀\n\n"
                            
                            text += f"📊 *LAST 100:* 🎱 Super 8 Wins: {bot_state['se_wins_100']} | 📈 Max B/S: L{bot_state['max_lvl_100']}\n\n"
                            
                            if bs_res_status:
                                text += f"🔄 *Result for {issue}:*\n"
                                text += f"📏 B/S: {bs_res_status}\n"
                                
                                if se_res_status != "":
                                    text += f"🎱 Super 8: {se_res_status}\n"
                                    
                                if bot_state["se_mega_win"]:
                                    text += f"\n🎱🔥 *SUPER 8 NUMBER WIN!* 🔥🎱\n"
                                elif bot_state["jackpot"]:
                                    text += f"\n🔥🎉 *JACKPOT! WIN!* 🎉🔥\n"
                                    
                                text += f"\n➖➖➖➖➖➖➖➖\n\n"
                            
                            text += f"🎟️ *Prediction For Ticket:* {next_issue}\n\n"
                            
                            mode_text = " *(🔄 3-Circle)*" if bot_state.get("mode") == "3-circle" else ""
                            text += f"📏 *B/S Pred:* {bot_state['bs_pred']} (L{bot_state['bs_level_num']}){mode_text}\n\n"
                            
                            if bot_state["se_active"]:
                                text += f"⚠️ 🎱 *SUPER 8 ALERT!*\n"
                                text += f"🎯 *Target Number:* {bot_state['se_target']} (L{bot_state['se_level']})\n"
                            else:
                                text += f"⏸️ *Super 8 Status:* Waiting for number 8\n"

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
    <title>VSR Wingo Live Super 8 Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; padding: 20px; }
        .card { background: #1e293b; border-radius: 16px; padding: 25px; max-width: 450px; margin: auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 20px; margin-bottom: 5px; }
        .subtitle { color: #94a3b8; font-size: 12px; margin-bottom: 10px; }
        .ai-stats { background: #020617; padding: 10px; border-radius: 8px; font-size: 13px; color: #fbbf24; margin-bottom: 15px; border: 1px solid #fbbf24; line-height: 1.6;}
        .metric { background: #334155; margin: 12px 0; padding: 15px; border-radius: 10px; font-size: 16px; text-align: left; display: flex; justify-content: space-between; align-items: center; }
        .highlight { color: #4ade80; font-weight: bold; font-size: 18px; }
        .violet-active { color: #facc15; font-weight: bold; font-size: 15px; animation: pulse 1.5s infinite; }
        .violet-waiting { color: #94a3b8; font-size: 15px; }
        .result-box { background: #0f172a; margin-top: 15px; padding: 12px; border-radius: 8px; font-size: 13px; color: #cbd5e1; text-align: left; border-left: 4px solid #38bdf8; }
        .jackpot { background: #eab308; color: #000; font-weight: bold; padding: 12px; border-radius: 8px; margin-top: 15px; font-size: 15px; display: none; animation: pulse 1.5s infinite; }
        .mega-win { background: #eab308; color: #000; font-weight: bold; padding: 12px; border-radius: 8px; margin-top: 15px; font-size: 15px; display: none; animation: pulse 1s infinite; }
        .status-badge { background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .status-active { background: #22c55e; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="card">
        <h1>🚀 VSR WINGO Super 8 Dashboard</h1>
        <div class="subtitle">
            Signals Status: <span id="timer_status" class="status-badge">INACTIVE</span>
        </div>
        
        <div class="ai-stats">
            🎯 <b>Super 8 Analytics (Last 100):</b> <br>
            Wins: <span id="se_wins">0</span> | Fails: <span id="se_fails">0</span><br>
            📈 <b>Max B/S Trend:</b> L<span id="max_l_100">1</span>
        </div>
        
        <div class="metric"><span>🎟️ Next Ticket:</span> <span class="highlight" id="last_issue">Loading...</span></div>
        <div class="metric"><span>📏 B/S Pred:</span> <span class="highlight" id="bs_info">-</span></div>
        <div class="metric"><span>🎱 Super 8 Pred:</span> <span id="se_info">Analyzing...</span></div>
        
        <div class="result-box" id="last_result">
            <b>📊 Last Trade Status:</b><br>Initializing...
        </div>

        <div class="mega-win" id="mega_win_box">🎱🔥 SUPER 8 NUMBER WIN! 🔥🎱</div>
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
                    
                    document.getElementById('se_wins').innerText = data.se_wins_100;
                    document.getElementById('se_fails').innerText = data.se_fails_100;
                    document.getElementById('max_l_100').innerText = data.max_lvl_100;
                    
                    const seInfo = document.getElementById('se_info');
                    if (data.se_active) {
                        seInfo.innerText = "⚠️ Num " + data.se_target + " (L" + data.se_level + ")";
                        seInfo.className = "violet-active";
                    } else {
                        seInfo.innerText = "⏸️ WAITING (No 8 yet)";
                        seInfo.className = "violet-waiting";
                    }
                    
                    document.getElementById('last_result').innerHTML = "<b>📊 Last Trade Status:</b><br>" + data.last_result;
                    
                    const mw = document.getElementById('mega_win_box');
                    if (data.se_mega_win) { mw.style.display = 'block'; } else { mw.style.display = 'none'; }
                    
                    const jp = document.getElementById('jackpot_box');
                    if (data.jackpot && !data.se_mega_win) { jp.style.display = 'block'; } else { jp.style.display = 'none'; }

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
