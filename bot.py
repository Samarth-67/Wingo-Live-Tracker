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
    "bs_pred": "-", "bs_step": 0, "bs_level_num": 1, "bs_level": "L1",
    "last_result": "Bot is initializing...",
    "jackpot": False,
    "violet_gap": 0,                
    "violet_alert_active": False,   
    "violet_normal_active": False,  # Gap 6 साठी नॉर्मल अलर्ट (लेव्हल नसलेला)
    "violet_mega_active": False,    # Gap 8 साठी मेगा अलर्ट (लेव्हल असलेला)
    "violet_level": 1,              
    "violet_alert_type": "None",      
    "violet_mega_win": False,       
    "active_until": 0,
    "notified_sleep": True
}

def get_wingo_data():
    ts = int(time.time() * 1000)
    target_url = f"https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?ts={ts}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
                            send_telegram_message(chat_id, "✅ *Bot Activated for 1 Hour with Gap 6 & Mega Alert Strategy!*")
                        else:
                            send_telegram_message(chat_id, "❌ Access Denied!")
        except Exception as e:
            pass
        time.sleep(3)

def background_bot_loop():
    global bot_state
    last_processed = None

    while True:
        try:
            records = get_wingo_data()
            if records:
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
                        bot_state["bs_step"] = 1
                        bot_state["status"] = "PREDICTING"
                        bot_state["jackpot"] = False
                        
                        # Calculate initial Violet Gap
                        gap = 0
                        for r in records:
                            n_str = str(r.get("number", "-"))
                            if n_str.isdigit() and (int(n_str) == 0 or int(n_str) == 5): break
                            gap += 1
                        bot_state["violet_gap"] = gap
                        
                        if gap >= 8:
                            bot_state["violet_mega_active"] = True
                            bot_state["violet_normal_active"] = False
                            bot_state["violet_alert_active"] = True
                            bot_state["violet_alert_type"] = "Mega Alert"
                            bot_state["violet_level"] = 1
                        elif gap >= 6:
                            bot_state["violet_normal_active"] = True
                            bot_state["violet_mega_active"] = False
                            bot_state["violet_alert_active"] = True
                            bot_state["violet_alert_type"] = "Normal Alert (Gap 6)"
                        
                        print(f"✅ Initialized at Ticket: {issue} | Current Violet Gap: {gap}")

                    elif last_processed != issue:
                        print("\n" + "=" * 55)
                        print(f"✅ Result Declared for Ticket: {issue}")
                        print(f"🎲 Number Came: {number}")

                        bs_res_status = None
                        violet_res_status = None

                        if bot_state["status"] == "PREDICTING":
                            # --- 1. Big/Small Logic ---
                            bs_win = (bot_state["bs_pred"] == actual_bs)
                            bot_state["jackpot"] = bs_win 
                            bs_res_status = f"{bot_state['bs_pred']} {'✅ WIN' if bs_win else '❌ FAIL'}"

                            if bs_win: bot_state["bs_level_num"] = 1
                            else: bot_state["bs_level_num"] += 1
                            
                            if bot_state["bs_step"] < 3:
                                bot_state["bs_step"] += 1
                            else:
                                bot_state["bs_pred"] = "Small" if bot_state["bs_pred"] == "Big" else "Big"
                                bot_state["bs_step"] = 1

                            # --- 2. Violet Strategy Logic (Gap 6 Normal & Gap 8+ Mega) ---
                            bot_state["violet_mega_win"] = False
                            
                            if is_violet:
                                if bot_state["violet_alert_active"]:
                                    if bot_state["violet_mega_active"]:
                                        print(f"   👉 🟣🔥 VIOLET MEGA WIN! (Mega Alert Success at L{bot_state['violet_level']}!) 🔥🟣")
                                        violet_res_status = f"🟣 ✅ MEGA WIN (L{bot_state['violet_level']})"
                                    else:
                                        print(f"   👉 🟣🔥 VIOLET WIN! (Normal Alert Gap 6 Success!) 🔥🟣")
                                        violet_res_status = f"🟣 ✅ NORMAL WIN"
                                    bot_state["violet_mega_win"] = True
                                else:
                                    print("   👉 🟣 Normal Violet Win!")
                                    violet_res_status = "🟣 ✅ WIN"
                                    
                                # Reset everything after win
                                bot_state["violet_gap"] = 0
                                bot_state["violet_level"] = 1
                                bot_state["violet_alert_active"] = False
                                bot_state["violet_normal_active"] = False
                                bot_state["violet_mega_active"] = False
                                bot_state["violet_alert_type"] = "None"
                                print("   🔄 Violet Tracker reset to 0")
                            else:
                                bot_state["violet_gap"] += 1
                                
                                if bot_state["violet_alert_active"]:
                                    if bot_state["violet_mega_active"]:
                                        print(f"   👉 ❌ Mega Alert Level {bot_state['violet_level']} Fail")
                                        violet_res_status = f"🟣 ❌ FAIL (Mega L{bot_state['violet_level']})"
                                        bot_state["violet_level"] += 1 # Mega alert gets levels
                                    else:
                                        print(f"   👉 ❌ Normal Alert (Gap {bot_state['violet_gap']}) Fail")
                                        violet_res_status = f"🟣 ❌ FAIL (Normal Gap {bot_state['violet_gap']})"
                                        # Normal alert has no levels, so level doesn't change
                                else:
                                    print(f"   👉 No Violet. Gap is now: {bot_state['violet_gap']}")

                                # Evaluate triggers based on current gap
                                if bot_state["violet_gap"] >= 8:
                                    bot_state["violet_mega_active"] = True
                                    bot_state["violet_normal_active"] = False
                                    bot_state["violet_alert_active"] = True
                                    bot_state["violet_alert_type"] = "Mega Alert"
                                    if bot_state["violet_level"] < 1:
                                        bot_state["violet_level"] = 1
                                    print("   🚨 Gap 8+ Reached! Activating Mega Alert L1")
                                elif bot_state["violet_gap"] >= 6:
                                    bot_state["violet_normal_active"] = True
                                    bot_state["violet_mega_active"] = False
                                    bot_state["violet_alert_active"] = True
                                    bot_state["violet_alert_type"] = "Normal Alert"
                                    print("   🚨 Gap 6 Reached! Activating Normal Alert (No Level)")
                                else:
                                    bot_state["violet_alert_active"] = False
                                    bot_state["violet_normal_active"] = False
                                    bot_state["violet_mega_active"] = False
                                    bot_state["violet_alert_type"] = "None"

                            bot_state["last_result"] = f"B/S: {bs_res_status}"
                            if violet_res_status:
                                bot_state["last_result"] += f" | Violet: {violet_res_status}"

                        next_issue = str(int(issue) + 1) if issue.isdigit() else "Next"
                        
                        bot_state["last_issue"] = next_issue
                        bot_state["latest_number"] = number
                        bot_state["bs_level"] = f"L{bot_state['bs_level_num']}"
                        
                        last_processed = issue

                        # ---------------- 3. PREDICTION FOR NEXT TICKET ----------------
                        print("-" * 55)
                        print(f"🎟️ PREDICTION FOR NEXT TICKET: {next_issue}")
                        if bot_state["violet_alert_active"]:
                            if bot_state["violet_mega_active"]:
                                print(f"🔮 Violet Prediction: 🟣 Mega Alert - Level {bot_state['violet_level']}")
                            else:
                                print(f"🔮 Violet Prediction: 🟣 Normal Alert (Gap {bot_state['violet_gap']}) - No Level")
                        else:
                            print(f"🔮 Violet Prediction: Waiting (Gap {bot_state['violet_gap']})")
                        print("=" * 55)

                        # Send Telegram Signal if active
                        if bot_state["active_until"] > 0 and time.time() < bot_state["active_until"]:
                            text = f"🚀 *VSR WINGO Signals 1 Minute* 🚀\n\n"
                            if bs_res_status:
                                text += f"🔄 *Result for {issue}:*\n"
                                text += f"📏 B/S: {bs_res_status}\n"
                                if violet_res_status:
                                    text += f"🟣 Violet: {violet_res_status}\n"
                                    
                                if bot_state["violet_mega_win"]:
                                    text += f"\n🟣🔥 *VIOLET WIN!* 🔥🟣\n"
                                elif bot_state["jackpot"]:
                                    text += f"\n🔥🎉 *JACKPOT! WIN!* 🎉🔥\n"
                                    
                                text += f"\n➖➖➖➖➖➖➖➖\n\n"
                            
                            text += f"🎟️ *Prediction For Ticket:* {next_issue}\n\n"
                            text += f"📏 *B/S Pred:* {bot_state['bs_pred']} (L{bot_state['bs_level_num']})\n\n"
                            
                            if bot_state["violet_alert_active"]:
                                if bot_state["violet_mega_active"]:
                                    text += f"⚠️ 🟣 *VIOLET MEGA ALERT*\n"
                                    text += f"🎯 *Violet Level:* L{bot_state['violet_level']}\n"
                                else:
                                    text += f"⚠️ 🟣 *VIOLET NORMAL ALERT (Gap {bot_state['violet_gap']})*\n"
                                    text += f"🎯 *Level:* None\n"
                            else:
                                text += f"⏸️ *Violet Status:* Waiting (Gap: {bot_state['violet_gap']})\n"

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
    <title>VSR Wingo Live Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; padding: 20px; }
        .card { background: #1e293b; border-radius: 16px; padding: 25px; max-width: 450px; margin: auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 20px; margin-bottom: 5px; }
        .subtitle { color: #94a3b8; font-size: 12px; margin-bottom: 20px; }
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
        <h1>🚀 VSR WINGO Dashboard</h1>
        <div class="subtitle">
            Signals Status: <span id="timer_status" class="status-badge">INACTIVE</span>
        </div>
        
        <div class="metric"><span>🎟️ Next Ticket:</span> <span class="highlight" id="last_issue">Loading...</span></div>
        <div class="metric"><span>📏 B/S Pred:</span> <span class="highlight" id="bs_info">-</span></div>
        <div class="metric"><span>🟣 Violet Pred:</span> <span id="violet_info">Calculating...</span></div>
        
        <div class="result-box" id="last_result">
            <b>📊 Last Trade Status:</b><br>Initializing...
        </div>

        <div class="mega-win" id="mega_win_box">🟣🔥 VIOLET WIN! 🔥🟣</div>
        <div class="jackpot" id="jackpot_box">🔥🎉 JACKPOT! WIN! 🎉🔥</div>
    </div>

    <script>
        function updateDashboard() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('last_issue').innerText = data.last_issue;
                    document.getElementById('bs_info').innerText = data.bs_pred + " (" + data.bs_level + ")";
                    
                    const vInfo = document.getElementById('violet_info');
                    if (data.violet_alert_active) {
                        if (data.violet_mega_active) {
                            vInfo.innerText = "⚠️ MEGA ALERT (L" + data.violet_level + ")";
                        } else {
                            vInfo.innerText = "⚠️ NORMAL ALERT (Gap " + data.violet_gap + ")";
                        }
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
