import os
import time
import threading
import requests
from rich.table import Table
from rich.console import Console, Group
from rich.panel import Panel
from rich.align import Align
from rich.live import Live

console = Console()

# --- 🚀 TELEGRAM BOT CONFIGURATION 🚀 ---
TELEGRAM_TOKEN = "7706219157:AAF-z7DfUlBtteflQNn5OsgPhbEc9XMthd4"
# आता इथे TARGET_GROUP_ID ची गरज नाही, बॉट आपोआप ग्रुप आयडी घेईल!

# 🔐 सिक्रेट पासवर्ड (30S साठी)
PASS_30S = "33333"
# -----------------------------------------------------------

api_session = requests.Session()

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "current_issue": None,
        "is_running": False,
        "active_chat_id": None, # डायनॅमिक आयडी सेव्ह करण्यासाठी
        "history": [],
        "last_signal_time": 0
    }

state_30s = create_state("WinGo 30S", 30)

def send_telegram_message_direct(chat_id, text):
    if not chat_id: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        api_session.post(url, json=payload, timeout=5)
    except Exception as e:
        console.print(f"[red]Telegram Error:[/red] {e}")

def send_telegram_signal(state, issue, prev_res_text=None):
    # आता बॉट ज्या ग्रुपमधून कमांड आली होती, तिथेच सिग्नल पाठवेल
    target_chat_id = state.get("active_chat_id")
    if not target_chat_id: 
        return

    result_text = ""
    if prev_res_text:
        result_text = f"\n\n🎯 *PREVIOUS RESULT:* {prev_res_text}"

    text = f"""🔥 *{state['name']} - NEW SIGNAL* 🔥

🎫 *ISSUE:* `{issue}`
📈 *PREDICTION:* 🟢 BIG (Example)

⚡ _Invest at your own risk_ {result_text}"""
    
    send_telegram_message_direct(target_chat_id, text)

# --- 🎯 TELEGRAM LISTENER (कमांड ऐकण्यासाठी) ---
def telegram_listener():
    offset = None
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    
    while True:
        try:
            params = {"timeout": 100, "offset": offset}
            resp = api_session.get(url, params=params, timeout=110)
            data = resp.json()
            
            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"].strip()
                        chat_id = update["message"]["chat"]["id"]
                        
                        if text.startswith("/signal"):
                            parts = text.split()
                            if len(parts) == 2 and parts[1] == PASS_30S:
                                state_30s["is_running"] = True
                                state_30s["active_chat_id"] = chat_id # इथे बॉट आपोआप तुमचा ग्रुप आयडी सेव्ह करेल!
                                send_telegram_message_direct(chat_id, "✅ *[30S Bot]* Activated successfully for this group!")
                            elif len(parts) == 2 and parts[1] == "stop":
                                state_30s["is_running"] = False
                                send_telegram_message_direct(chat_id, "🛑 *[30S Bot]* Stopped successfully.")
        except Exception:
            time.sleep(5)

# --- 🚀 FETCH API & PROCESS TIMERS ---
def fetch_api(typeid):
    try:
        url = "https://api.inlt.in/api/webapi/GetNoaverageEmerdList"
        payload = {"pageSize": 10, "pageNo": 1, "typeid": typeid, "language": 0}
        headers = {'Content-Type': 'application/json;charset=UTF-8'}
        r = api_session.post(url, json=payload, headers=headers, timeout=5)
        return r.json().get('data', {}).get('list', [])
    except:
        return []

def run_loop(state, typeid):
    while True:
        try:
            current_time = time.time()
            data = fetch_api(typeid)
            if data:
                latest = data[0]
                issue = latest.get("issueNumber")
                
                if issue != state["current_issue"]:
                    prev_res = ""
                    if len(data) > 1:
                        prev_issue = data[1].get("issueNumber")
                        prev_num = data[1].get("number")
                        sz = "BIG" if int(prev_num) > 4 else "SMALL"
                        prev_res = f"Issue {prev_issue[-4:]} ➡️ {prev_num} ({sz})"
                        
                        state["history"].insert(0, f"✅ {prev_issue[-4:]} ➡️ {prev_num} ({sz})")
                        if len(state["history"]) > 5:
                            state["history"].pop()

                    state["current_issue"] = issue
                    
                    if state["is_running"]:
                        send_telegram_signal(state, issue, prev_res)

        except Exception:
            pass
        
        time.sleep(1)

def build_ui():
    table = Table(title="💎 VIP SERVER MONITOR 💎", style="cyan")
    table.add_column("SERVER", style="magenta")
    table.add_column("ISSUE", style="yellow")
    table.add_column("STATUS", justify="center")
    
    st_30s = "✅ RUNNING" if state_30s["is_running"] else "❌ STOPPED"
    iss_30s = state_30s["current_issue"][-4:] if state_30s["current_issue"] else "Wait.."
    table.add_row("Wingo 30S", iss_30s, st_30s)
    
    history_panel = Panel("\n".join(state_30s["history"]) if state_30s["history"] else "No history yet...", title="30S Recent Results", style="green")
    return Panel(Align.center(Group(table, history_panel)), border_style="blue")

if __name__ == "__main__":
    os.system("clear" if os.name == "posix" else "cls")
    
    # स्टार्ट थ्रेड्स
    threading.Thread(target=telegram_listener, daemon=True).start()
    threading.Thread(target=run_loop, args=(state_30s, 1), daemon=True).start()
    
    with Live(build_ui(), refresh_per_second=1) as live:
        while True:
            live.update(build_ui())
            time.sleep(1)
