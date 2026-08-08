import time
import requests
import os

# ---------------- TELEGRAM BOT CONFIGURATION ----------------
TELEGRAM_BOT_TOKEN = "8886107397:AAHENOebGnrupxvGKqKh5cKC3SmujXJOV3w"
SECRET_PASSWORD = "12345"
TARGET_CHANNEL_ID = "-1004370895879"  # <--- तुझा चॅनेल आयडी
# ------------------------------------------------------------

state = {
    "last_processed_issue": None,
    "status": "WAITING",  
    "bs_pred": None, "bs_step": 0, "bs_level": 1,
    "color_pred": None, "color_step": 0, "color_level": 1,
    "history": [],
    "stats": {"bs_win": 0, "bs_fail": 0, "color_win": 0, "color_fail": 0, "total_trades": 0}
}

active_until = 0
notified_sleep = True

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
        print(f"API Response Code: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict) and ("data" in data or "list" in data):
                return data
    except Exception as e:
        print(f"API Fetch Error: {e}")
    return None

def extract_records(data):
    if not data: return []
    if "data" in data and isinstance(data["data"], list): return data["data"]
    elif "list" in data and isinstance(data["list"], list): return data["list"]
    elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: return data["data"]["list"]
    return []

def check_and_send_signal():
    global state
    data = get_wingo_data()
    records = extract_records(data)
    if not records:
        print("No records found from API!")
        return

    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or latest_item.get("period") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if not latest_number_str.isdigit(): return
        
    number = int(latest_number_str)
    latest_bs = "Big" if number >= 5 else "Small"
    latest_color = "Red" if number % 2 == 0 else "Green"

    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        state["bs_pred"] = latest_bs
        state["bs_step"] = 1
        state["color_pred"] = latest_color
        state["color_step"] = 1
        state["status"] = "PREDICTING"
        print(f"Base issue set: {latest_issue}")
        return

    if state["last_processed_issue"] != latest_issue:
        bs_res_status, color_res_status = None, None
        bs_win, color_win = False, False

        if state["status"] == "PREDICTING":
            bs_win = (state["bs_pred"] == latest_bs)
            color_win = (state["color_pred"] == latest_color)

            bs_res_status = f"{state['bs_pred']} {'✅ WIN' if bs_win else '❌ FAIL'}"
            color_res_status = f"{state['color_pred']} {'✅ WIN' if color_win else '❌ FAIL'}"

            state["stats"]["total_trades"] += 1
            if bs_win: state["stats"]["bs_win"] += 1
            else: state["stats"]["bs_fail"] += 1
            if color_win: state["stats"]["color_win"] += 1
            else: state["stats"]["color_fail"] += 1

            state["history"].append({
                "trade": state["stats"]["total_trades"], "issue": latest_issue,
                "bs_level": f"L{state['bs_level']}", "bs_pred": state["bs_pred"], "bs_res": "WIN" if bs_win else "FAIL",
                "color_level": f"L{state['color_level']}", "color_pred": state["color_pred"], "color_res": "WIN" if color_win else "FAIL"
            })

            if bs_win: state["bs_level"] = 1
            else: state["bs_level"] += 1
            if color_win: state["color_level"] = 1
            else: state["color_level"] += 1

        if state["status"] == "WAITING":
            state["bs_pred"] = latest_bs; state["bs_step"] = 1
            state["color_pred"] = latest_color; state["color_step"] = 1
            state["status"] = "PREDICTING"
        elif state["status"] == "PREDICTING":
            if state["bs_step"] < 3: state["bs_step"] += 1
            else:
                state["bs_pred"] = "Small" if state["bs_pred"] == "Big" else "Big"
                state["bs_step"] = 1
            if state["color_step"] < 3: state["color_step"] += 1
            else:
                state["color_pred"] = "Green" if state["color_pred"] == "Red" else "Red"
                state["color_step"] = 1

        next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
        state["last_processed_issue"] = latest_issue

        text = f"🚀 *VSR WINGO Signals 1 Minute* 🚀\n\n"
        if bs_res_status and color_res_status:
            text += f"🔄 *Last Trade Result:*\n"
            text += f"📏 B/S: {bs_res_status}\n"
            text += f"🎨 Color: {color_res_status}\n\n"
            if bs_win and color_win: 
                text += f"🔥🎉 *JACKPOT! BOTH WON!* 🎉🔥\n"
            text += f"➖➖➖➖➖➖➖➖\n\n"
            
        text += (
            f"🎟️ *New Issue:* {next_issue}\n\n"
            f"📏 *Prediction:* {state['bs_pred']}\n"
            f"🎯 *Level:* L{state['bs_level']}\n\n"
            f"🎨 *Prediction Color:* {state['color_pred']}\n"
            f"🎯 *Level:* L{state['color_level']}"
        )

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={"chat_id": TARGET_CHANNEL_ID, "text": text, "parse_mode": "Markdown"}, timeout=5)
        print(f"Signal sent! Status: {resp.status_code}")

def main():
    global active_until, notified_sleep
    print("🤖 Clean Cloud Bot is running...")
    offset = 0
    
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
                            active_until = time.time() + 3600
                            notified_sleep = False
                            print("Bot activated via Telegram!")
                            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "✅ *Bot Activated for 1 Hour on Cloud!*"}, timeout=5)
                        else:
                            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "❌ Access Denied!", "parse_mode": "Markdown"}, timeout=5)
            
            if active_until > 0 and time.time() < active_until:
                check_and_send_signal()
            elif active_until > 0 and time.time() >= active_until:
                if not notified_sleep:
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TARGET_CHANNEL_ID, "text": "💤 *1 Hour Session Completed!*", "parse_mode": "Markdown"}, timeout=5)
                    notified_sleep = True
                    active_until = 0
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(3)

if __name__ == "__main__":
    main()
