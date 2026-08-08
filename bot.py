import time
import requests
from curl_cffi import requests as cureq
import urllib.parse
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

# ---------------- TELEGRAM BOT CONFIGURATION ----------------
TELEGRAM_BOT_TOKEN = "8886107397:AAHENOebGnrupxvGKqKh5cKC3SmujXJOV3w"
SECRET_PASSWORD = "12345"
# ------------------------------------------------------------

def get_wingo_data():
    ts = int(time.time() * 1000)
    target_url = f"https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?ts={ts}"
    encoded_url = urllib.parse.quote(target_url, safe='')

    # 🚀 STEP 1: Try Free Unblocker Proxies (This hides Render's IP)
    proxy_urls = [
        f"https://api.codetabs.com/v1/proxy?quest={target_url}",
        f"https://api.allorigins.win/raw?url={encoded_url}",
        f"https://corsproxy.io/?{encoded_url}"
    ]
    
    for p_url in proxy_urls:
        try:
            res = requests.get(p_url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, dict) and ("data" in data or "list" in data):
                    return data
        except:
            continue
            
    # 🚀 STEP 2: Fallback to Chrome Impersonation if proxies fail
    headers = {"Accept": "application/json", "Referer": "https://ar-lottery01.com/"}
    browsers = ["chrome120", "safari15_5"]
    for browser in browsers:
        try:
            res = cureq.get(target_url, headers=headers, impersonate=browser, timeout=10)
            if res.status_code == 200:
                return res.json()
        except:
            continue
            
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
                            send_message(chat_id, "⏳ Fetching secure live signal through Proxy...")
                            wingo_data = get_wingo_data()
                            if wingo_data:
                                records = wingo_data.get("data", []) or wingo_data.get("list", [])
                                if isinstance(wingo_data.get("data"), dict):
                                    records = wingo_data["data"].get("list", [])
                                signal_text = calculate_prediction(records)
                                send_message(chat_id, signal_text)
                            else:
                                send_message(chat_id, "⚠️ Error: Cloudflare blocked the request. Try again.")
                        else:
                            send_message(chat_id, "❌ Access Denied! Incorrect password.\nUse: `/signal 12345`")
        except Exception as e:
            pass
        time.sleep(2)

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Telegram Bot is Live!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server_address = ('', port)
    httpd = HTTPServer(server_address, DummyHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_dummy_server)
    server_thread.daemon = True
    server_thread.start()
    main()
