import time
import threading
import os
import requests
from flask import Flask, render_template_string

app = Flask(__name__)

# डॅशबोर्डसाठी ग्लोबल स्टेट (Global State)
bot_state = {
    "last_issue": "Waiting for data...",
    "latest_number": "-",
    "bs_pred": "-", "bs_level": "L1",
    "color_pred": "-", "color_level": "L1",
    "last_result": "Bot is initializing...",
    "jackpot": False
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

def background_bot_loop():
    global bot_state
    last_processed = None
    bs_pred = "Big"
    color_pred = "Green"
    bs_level = 1
    color_level = 1

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
                    actual_color = "Red" if number % 2 == 0 else "Green"

                    if last_processed is None:
                        last_processed = issue
                        bs_pred = actual_bs
                        color_pred = actual_color
                    elif last_processed != issue:
                        # रिझल्ट तपासणे
                        bs_win = (bs_pred == actual_bs)
                        color_win = (color_pred == actual_color)

                        bot_state["last_result"] = f"Issue {last_processed} -> Number: {number} | B/S: {actual_bs} ({'WIN' if bs_win else 'FAIL'}), Color: {actual_color} ({'WIN' if color_win else 'FAIL'})"
                        bot_state["jackpot"] = bs_win and color_win

                        if bs_win: bs_level = 1
                        else: bs_level += 1
                        if color_win: color_level = 1
                        else: color_level += 1

                        # पुढील प्रेडिक्शन लॉजिक
                        bs_pred = "Small" if bs_pred == "Big" else "Big"
                        color_pred = "Green" if color_pred == "Red" else "Red"

                        next_issue = str(int(issue) + 1) if issue.isdigit() else "Next"
                        bot_state["last_issue"] = next_issue
                        bot_state["latest_number"] = number
                        bot_state["bs_pred"] = bs_pred
                        bot_state["bs_level"] = f"L{bs_level}"
                        bot_state["color_pred"] = color_pred
                        bot_state["color_level"] = f"L{color_level}"
                        
                        last_processed = issue
        except Exception as e:
            print("Loop error:", e)
        time.sleep(5)

# सुंदर आणि मॉडर्न डॅशबोर्ड डिझाईन (HTML UI)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>VSR Wingo Live Dashboard</title>
    <meta http-equiv="refresh" content="5">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; padding: 20px; }
        .card { background: #1e293b; border-radius: 16px; padding: 25px; max-width: 450px; margin: auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 22px; margin-bottom: 5px; }
        .subtitle { color: #94a3b8; font-size: 12px; margin-bottom: 20px; }
        .metric { background: #334155; margin: 12px 0; padding: 15px; border-radius: 10px; font-size: 16px; text-align: left; display: flex; justify-content: space-between; align-items: center; }
        .highlight { color: #4ade80; font-weight: bold; font-size: 18px; }
        .result-box { background: #0f172a; margin-top: 15px; padding: 12px; border-radius: 8px; font-size: 13px; color: #cbd5e1; text-align: left; border-left: 4px solid #38bdf8; }
        .jackpot { background: #eab308; color: #000; font-weight: bold; padding: 12px; border-radius: 8px; margin-top: 15px; font-size: 15px; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="card">
        <h1>🚀 VSR WINGO Live Dashboard 🚀</h1>
        <div class="subtitle">Auto-refreshing every 5 seconds (No Telegram Needed)</div>
        
        <div class="metric"><span>🎟️ Next Issue:</span> <span class="highlight">{{ state.last_issue }}</span></div>
        <div class="metric"><span>📏 Prediction B/S:</span> <span class="highlight">{{ state.bs_pred }} ({{ state.bs_level }})</span></div>
        <div class="metric"><span>🎨 Prediction Color:</span> <span class="highlight">{{ state.color_pred }} ({{ state.color_level }})</span></div>
        
        <div class="result-box">
            <b>📊 Last Trade Status:</b><br>{{ state.last_result }}
        </div>

        {% if state.jackpot %}
        <div class="jackpot">🔥🎉 JACKPOT! BOTH WON! 🎉🔥</div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, state=bot_state)

if __name__ == '__main__':
    # बॅकग्राउंडला प्रेडिक्शन इंजिन सुरू करणे
    t = threading.Thread(target=background_bot_loop, daemon=True)
    t.start()
    
    # Render साठी पोर्ट सेटिंग
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
