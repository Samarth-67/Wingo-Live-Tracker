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
    
    # --- B/S Strategy Variables ---
    "mode": "normal",
    
    # --- SUPER 8 DUAL Strategy States ---
    "se_wins_100": 0,
    "se_fails_100": 0,
    "se_active": False,   
    "se_level": 0,              
    "se_target": "4 & 6",       
    "se_mega_win": False,
    
    # --- SUPER 4 DUAL Strategy States ---
    "s4_wins_100": 0,
    "s4_fails_100": 0,
    "s4_active": False,   
    "s4_level": 0,              
    "s4_target": "8 & 6",       
    "s4_mega_win": False,
    
    # --- Stats ---
    "full_history": [],
    "max_lvl_100": 1,
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
                            send_telegram_message(chat_id, "✅ *Bot Activated! Master AI: S8 + S4 + Trend/ZigZag (Strict L8 Stop Loss) Running!*")
                        else:
                            send_telegram_message(chat_id, "❌ Access Denied!")
        except Exception as e:
            pass
        time.sleep(3)

def get_100_rounds_stats(full_history):
    if not full_history or len(full_history) < 2:
        return 0, 0, 0, 0, 1
        
    history_asc = sorted(full_history, key=lambda x: x['issue'])
    
    bs_pred = None
    bs_level = 1
    max_level = 1
    mode = "normal"
    
    se_wins, se_fails, se_active, se_level = 0, 0, False, 0
    s4_wins, s4_fails, s4_active, s4_level = 0, 0, False, 0
    
    for item in history_asc:
        num = item['number']
        actual_bs = "Big" if num >= 5 else "Small"
        
        # --- B/S Logic Simulation (With Zigzag & L8 Stop Loss) ---
        if bs_pred is None:
            bs_pred = actual_bs
        else:
            if bs_pred == actual_bs:
                bs_level = 1
                mode = "normal"
                bs_pred = actual_bs
            else:
                if bs_level == 8: # STOP LOSS HIT
                    bs_level = 1
                    mode = "normal"
                    bs_pred = actual_bs
                else:
                    bs_level += 1
                    if bs_level > max_level:
                        max_level = bs_level
                        
                    if bs_level <= 3:
                        mode = "normal"
                        bs_pred = actual_bs
                    elif bs_level == 4:
                        mode = "3-circle"
                        bs_pred = actual_bs
                    elif bs_level >= 5:
                        mode = "zigzag"
                        # खरा झिगझॅग: आधीच्या प्रेडिक्शनच्या विरुद्ध
                        bs_pred = "Small" if bs_pred == "Big" else "Big"

        # --- Super 8 & 4 Logic Simulation ---
        just_resolved = False
        
        if se_active:
            if num in [4, 6]:
                se_wins += 1
                se_active = False
                just_resolved = True 
            elif num == 8:
                se_level = 1
            else:
                if se_level == 1:
                    se_level = 2
                else:
                    se_fails += 1
                    se_active = False
                    
        if s4_active:
            if num in [8, 6]:
                s4_wins += 1
                s4_active = False
                just_resolved = True 
            elif num == 4:
                s4_level = 1
            elif num in [0, 5]:
                pass # Violet Skip
            else:
                if s4_level == 1:
                    s4_level = 2
                else:
                    s4_fails += 1
                    s4_active = False
                    
        if not just_resolved:
            if not se_active and num == 8:
                se_active = True
                se_level = 1
            if not s4_active and num == 4:
                s4_active = True
                s4_level = 1
                
    return se_wins, se_fails, s4_wins, s4_fails, max_level

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
                
                se_w, se_f, s4_w, s4_f, max_lvl = get_100_rounds_stats(bot_state["full_history"])
                bot_state["se_wins_100"] = se_w
                bot_state["se_fails_100"] = se_f
                bot_state["s4_wins_100"] = s4_w
                bot_state["s4_fails_100"] = s4_f
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
                        bot_state["mode"] = "normal"
                        bot_state["bs_level_num"] = 1
                        bot_state["status"] = "PREDICTING"
                        bot_state["jackpot"] = False
                        print(f"✅ Initialized at Ticket: {issue} | Multi-Tracker Ready")

                    elif last_processed != issue:
                        print("\n" + "=" * 55)
                        print(f"✅ Result Declared for Ticket: {issue}")
                        print(f"🎲 Number Came: {number}")

                        bs_res_status = None
                        se_res_status = ""  
                        s4_res_status = ""

                        if bot_state["status"] == "PREDICTING":
                            # --- 1. Big/Small Logic (Trend -> 3-Circle -> ZigZag + L8 Stop Loss) ---
                            bs_win = (bot_state["bs_pred"] == actual_bs)
                            bot_state["jackpot"] = bs_win 
                            
                            # Added Emoji to Result Log
                            past_emoji = "🟠" if bot_state['bs_pred'] == "Big" else "🔵"
                            bs_res_status = f"{past_emoji} {bot_state['bs_pred']} {'✅ WIN' if bs_win else '❌ FAIL'}"

                            if bs_win: 
                                bot_state["bs_level_num"] = 1
                                bot_state["mode"] = "normal"
                                bot_state["bs_pred"] = actual_bs # Normal Trend Follow
                            else: 
                                # STRICT L8 STOP LOSS
                                if bot_state["bs_level_num"] >= 8:
                                    print("   ⚠️ 🛑 B/S STRICT STOP LOSS HIT AT L8!")
                                    bs_res_status += " [🛑 L8 STOP LOSS]"
                                    bot_state["bs_level_num"] = 1
                                    bot_state["mode"] = "normal"
                                    bot_state["bs_pred"] = actual_bs # Reset to fresh trend
                                else:
                                    bot_state["bs_level_num"] += 1
                                    
                                    if bot_state["bs_level_num"] <= 3:
                                        bot_state["mode"] = "normal"
                                        bot_state["bs_pred"] = actual_bs
                                    elif bot_state["bs_level_num"] == 4:
                                        bot_state["mode"] = "3-circle"
                                        bot_state["bs_pred"] = actual_bs
                                    elif bot_state["bs_level_num"] >= 5:
                                        bot_state["mode"] = "zigzag"
                                        print("   ⚡ ZigZag Mode Activated!")
                                        # खरा झिगझॅग: जुन्या प्रेडिक्शनच्या विरुद्ध (Big -> Small -> Big)
                                        bot_state["bs_pred"] = "Small" if bot_state["bs_pred"] == "Big" else "Big"

                            # Flag to prevent S8 and S4 from chain-reacting
                            just_resolved = False

                            # --- 2. SUPER 8 Evaluation ---
                            bot_state["se_mega_win"] = False
                            if bot_state["se_active"]:
                                if number in [4, 6]:
                                    print(f"   👉 🎱🔥 SUPER 8 DUAL WIN! (Won at L{bot_state['se_level']} with {number}) 🔥🎱")
                                    se_res_status = f"🎱 ✅ WIN (L{bot_state['se_level']} - Num {number})"
                                    bot_state["se_mega_win"] = True
                                    bot_state["se_active"] = False
                                    bot_state["se_level"] = 0
                                    just_resolved = True # PREVENT S4 CHAIN
                                elif number == 8:
                                    print(f"   👉 🎱 Got '8' again! Restarting Super 8 Level 1.")
                                    se_res_status = f"🎱 ❌ FAIL (Got 8, Restarting L1)"
                                    bot_state["se_level"] = 1
                                else:
                                    if bot_state["se_level"] == 1:
                                        print(f"   👉 ❌ Super 8 L1 Fail. Moving to L2.")
                                        se_res_status = f"🎱 ❌ FAIL (L1 Targets 4 & 6)"
                                        bot_state["se_level"] = 2
                                    else:
                                        print(f"   👉 ⚠️ 🛑 SUPER 8 STOP LOSS HIT!")
                                        se_res_status = f"🎱 ❌ FAIL L2 [🛑 STOP]"
                                        bot_state["se_active"] = False
                                        bot_state["se_level"] = 0

                            # --- 3. SUPER 4 Evaluation (With Violet Skip) ---
                            bot_state["s4_mega_win"] = False
                            if bot_state["s4_active"]:
                                if number in [8, 6]:
                                    print(f"   👉 🍀🔥 SUPER 4 DUAL WIN! (Won at L{bot_state['s4_level']} with {number}) 🔥🍀")
                                    s4_res_status = f"🍀 ✅ WIN (L{bot_state['s4_level']} - Num {number})"
                                    bot_state["s4_mega_win"] = True
                                    bot_state["s4_active"] = False
                                    bot_state["s4_level"] = 0
                                    just_resolved = True # PREVENT S8 CHAIN
                                elif number == 4:
                                    print(f"   👉 🍀 Got '4' again! Restarting Super 4 Level 1.")
                                    s4_res_status = f"🍀 ❌ FAIL (Got 4, Restarting L1)"
                                    bot_state["s4_level"] = 1
                                elif number in [0, 5]:
                                    print(f"   👉 🍀 Violet ({number}) appeared! Skipping this level.")
                                    s4_res_status = f"🍀 ⏸️ SKIPPED (Violet Came, Holding L{bot_state['s4_level']})"
                                else:
                                    if bot_state["s4_level"] == 1:
                                        print(f"   👉 ❌ Super 4 L1 Fail. Moving to L2.")
                                        s4_res_status = f"🍀 ❌ FAIL (L1 Targets 8 & 6)"
                                        bot_state["s4_level"] = 2
                                    else:
                                        print(f"   👉 ⚠️ 🛑 SUPER 4 STOP LOSS HIT!")
                                        s4_res_status = f"🍀 ❌ FAIL L2 [🛑 STOP]"
                                        bot_state["s4_active"] = False
                                        bot_state["s4_level"] = 0

                            # --- 4. Trigger Checker for Next Round (Only if not just resolved) ---
                            if not just_resolved:
                                if not bot_state["se_active"]:
                                    if number == 8:
                                        bot_state["se_active"] = True
                                        bot_state["se_level"] = 1
                                if not bot_state["s4_active"]:
                                    if number == 4:
                                        bot_state["s4_active"] = True
                                        bot_state["s4_level"] = 1

                            # Format Status
                            bot_state["last_result"] = f"B/S: {bs_res_status}"
                            if se_res_status != "": bot_state["last_result"] += f" | S8: {se_res_status}"
                            if s4_res_status != "": bot_state["last_result"] += f" | S4: {s4_res_status}"

                        next_issue = str(int(issue) + 1) if issue.isdigit() else "Next"
                        bot_state["last_issue"] = next_issue
                        bot_state["latest_number"] = number
                        bot_state["bs_level"] = f"L{bot_state['bs_level_num']}"
                        last_processed = issue

                        # Send Telegram Signal if active
                        if bot_state["active_until"] > 0 and time.time() < bot_state["active_until"]:
                            text = f"🚀 *VSR WINGO Signals 1 Minute* 🚀\n\n"
                            
                            if bs_res_status:
                                text += f"🔄 *Result for {issue}:*\n"
                                text += f"📏 B/S: {bs_res_status}\n"
                                if se_res_status != "": text += f"🎱 Super 8: {se_res_status}\n"
                                if s4_res_status != "": text += f"🍀 Super 4: {s4_res_status}\n"
                                    
                                if bot_state["se_mega_win"] or bot_state["s4_mega_win"]:
                                    text += f"\n🎯🔥 *NUMBER PREDICTION WIN!* 🔥🎯\n"
                                elif bot_state["jackpot"]:
                                    text += f"\n🔥🎉 *JACKPOT! WIN!* 🎉🔥\n"
                                    
                                text += f"\n➖➖➖➖➖➖➖➖\n\n"
                            
                            text += f"🎟️ *Prediction For Ticket:* {next_issue}\n\n"
                            
                            mode_text = ""
                            if bot_state.get("mode") == "3-circle": mode_text = " *(🔄 3-Circle)*"
                            elif bot_state.get("mode") == "zigzag": mode_text = " *(⚡ ZigZag)*"
                            
                            # Added Big/Small Emojis based on Prediction
                            current_bs_emoji = "🟠 Big" if bot_state['bs_pred'] == "Big" else "🔵 Small"
                            text += f"📏 *B/S Pred:* {current_bs_emoji} (L{bot_state['bs_level_num']}){mode_text}\n\n"
                            
                            # Kept only active alerts, removed the 'Waiting' clutter
                            if bot_state["se_active"]:
                                text += f"⚠️ 🎱 *SUPER 8 ALERT!*\n"
                                text += f"🎯 *Targets:* {bot_state['se_target']} (L{bot_state['se_level']})\n\n"
                            if bot_state["s4_active"]:
                                text += f"⚠️ 🍀 *SUPER 4 ALERT!*\n"
                                text += f"🎯 *Targets:* {bot_state['s4_target']} (L{bot_state['s4_level']})\n\n"

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
    <title>VSR Wingo Multi-Tracker Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; padding: 20px; }
        .card { background: #1e293b; border-radius: 16px; padding: 25px; max-width: 450px; margin: auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 20px; margin-bottom: 5px; }
        .subtitle { color: #94a3b8; font-size: 12px; margin-bottom: 10px; }
        .ai-stats { background: #020617; padding: 10px; border-radius: 8px; font-size: 13px; color: #fbbf24; margin-bottom: 15px; border: 1px solid #fbbf24; line-height: 1.6;}
        .metric { background: #334155; margin: 10px 0; padding: 12px; border-radius: 10px; font-size: 15px; text-align: left; display: flex; justify-content: space-between; align-items: center; }
        .highlight { color: #4ade80; font-weight: bold; font-size: 16px; }
        .alert-active { color: #facc15; font-weight: bold; font-size: 14px; animation: pulse 1.5s infinite; }
        .alert-waiting { color: #94a3b8; font-size: 14px; }
        .result-box { background: #0f172a; margin-top: 15px; padding: 12px; border-radius: 8px; font-size: 13px; color: #cbd5e1; text-align: left; border-left: 4px solid #38bdf8; }
        .jackpot { background: #eab308; color: #000; font-weight: bold; padding: 12px; border-radius: 8px; margin-top: 15px; font-size: 15px; display: none; animation: pulse 1.5s infinite; }
        .status-badge { background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .status-active { background: #22c55e; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="card">
        <h1>🚀 VSR WINGO Multi-Tracker</h1>
        <div class="subtitle">
            Signals Status: <span id="timer_status" class="status-badge">INACTIVE</span>
        </div>
        
        <div class="ai-stats">
            🎯 <b>Analytics (Last 100):</b> <br>
            🎱 S8 Wins: <span id="se_wins">0</span> | 🍀 S4 Wins: <span id="s4_wins">0</span><br>
            📈 <b>Max B/S Trend:</b> L<span id="max_l_100">1</span>
        </div>
        
        <div class="metric"><span>🎟️ Next Ticket:</span> <span class="highlight" id="last_issue">Loading...</span></div>
        <div class="metric"><span>📏 B/S Pred:</span> <span class="highlight" id="bs_info">-</span></div>
        <div class="metric"><span>🎱 Super 8:</span> <span id="se_info">Analyzing...</span></div>
        <div class="metric"><span>🍀 Super 4:</span> <span id="s4_info">Analyzing...</span></div>
        
        <div class="result-box" id="last_result">
            <b>📊 Last Trade Status:</b><br>Initializing...
        </div>

        <div class="jackpot" id="jackpot_box">🔥🎉 JACKPOT! WIN! 🎉🔥</div>
    </div>

    <script>
        function updateDashboard() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('last_issue').innerText = data.last_issue;
                    
                    let bsText = data.bs_pred + " (L" + data.bs_level_num + ")";
                    if(data.mode === "3-circle") { bsText += " 🔄 3-Circle"; }
                    else if(data.mode === "zigzag") { bsText += " ⚡ ZigZag"; }
                    document.getElementById('bs_info').innerText = bsText;
                    
                    document.getElementById('se_wins').innerText = data.se_wins_100;
                    document.getElementById('s4_wins').innerText = data.s4_wins_100;
                    document.getElementById('max_l_100').innerText = data.max_lvl_100;
                    
                    const seInfo = document.getElementById('se_info');
                    if (data.se_active) {
                        seInfo.innerText = "⚠️ Nums " + data.se_target + " (L" + data.se_level + ")";
                        seInfo.className = "alert-active";
                    } else {
                        seInfo.innerText = "⏸️ WAITING (No 8)";
                        seInfo.className = "alert-waiting";
                    }

                    const s4Info = document.getElementById('s4_info');
                    if (data.s4_active) {
                        s4Info.innerText = "⚠️ Nums " + data.s4_target + " (L" + data.s4_level + ")";
                        s4Info.className = "alert-active";
                    } else {
                        s4Info.innerText = "⏸️ WAITING (No 4)";
                        s4Info.className = "alert-waiting";
                    }
                    
                    document.getElementById('last_result').innerHTML = "<b>📊 Last Trade Status:</b><br>" + data.last_result;
                    
                    const jp = document.getElementById('jackpot_box');
                    if (data.jackpot || data.se_mega_win || data.s4_mega_win) { 
                        jp.innerText = data.se_mega_win || data.s4_mega_win ? "🎯🔥 NUMBER PREDICTION WIN! 🔥🎯" : "🔥🎉 JACKPOT! WIN! 🎉🔥";
                        jp.style.display = 'block'; 
                    } else { 
                        jp.style.display = 'none'; 
                    }

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
