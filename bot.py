import time
import requests
from curl_cffi import requests as cureq

# ---------------- TELEGRAM BOT CONFIGURATION ----------------
TELEGRAM_BOT_TOKEN = "8886107397:AAHENOebGnrupxvGKqKh5cKC3SmujXJOV3w"
# ------------------------------------------------------------

SECRET_PASSWORD = "12345" # <--- तुमचा सिक्रेट पासवर्ड

def get_wingo_data():
    ts = int(time.time() * 1000)
    target_url = f"https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?ts={ts}"
    
    # 🚀 Chrome Impersonation to bypass Cloudflare on Cloud Servers
    try:
        res = cureq.get(target_url, impersonate="chrome110", timeout=15)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return None

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except:
        pass

def calculate_prediction(records):
    if not records: return "No records found."
    latest_item = records[0]
    issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    num_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if num_str.isdigit():
        val = int(num_str)
        bs = "Big" if val >= 5 else "Small"
        color = "Red" if val % 2 == 0 else "Green"
        next_issue = str(int(issue) + 1) if issue.isdigit() else "Next"
        
        return (f"🚀 *VS WINGO Secure Signal* 🚀\n\n"
                f"🎟️ *Target Issue:* {next_issue}\n"
                f"📏 *Prediction:* {bs}\n"
                f"🎨 *Color:* {color}\n"
                f"📊 *Last Drawn Number:* {val}")
    return "Error parsing draw number."

def main():
    print("🤖 Secure Wingo Telegram Bot is running 24/7...")
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            response = requests.get(url, timeout=35)
            if response.status_code == 200:
                data = response.json()
                for result in data.get("result", []):
                    offset = result["update_id"] + 1
                    message = result.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "").strip()
                    
                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == SECRET_PASSWORD:
                            send_message(chat_id, "⏳ Fetching secure live signal...")
                            wingo_data = get_wingo_data()
                            if wingo_data:
                                records = wingo_data.get("data", []) or wingo_data.get("list", [])
                                if isinstance(wingo_data.get("data"), dict):
                                    records = wingo_data["data"].get("list", [])
                                signal_text = calculate_prediction(records)
                                send_message(chat_id, signal_text)
                            else:
                                send_message(chat_id, "⚠️ Error: Cloudflare blocked the request. Retrying soon.")
                        else:
                            send_message(chat_id, "❌ Access Denied! Incorrect or missing password. Use format: `/signal [password]`")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(2)

if __name__ == "__main__":
    main()
