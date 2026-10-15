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

# ----------------- TELEGRAM CREDENTIALS -----------------
TELEGRAM_TOKEN = "8774822707:AAEXqZWpgkxpS50BTNLjR230aJX6JI4p6Yo"
TARGET_GROUP_ID = "-3992547967" 
PASS_30S = "1234"  # Telegram bot start/stop password
# --------------------------------------------------------

api_session = requests.Session()

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        
        # --- नवीन स्ट्रॅटेजी व्हेरिएबल्स ---
        "wait_for_trigger": True, 
        "ignore_trigger_until_issue": 0, 
        "current_target_bs": "WAIT", # प्रेडिक्शन काय द्यायचे (Big की Small)
        "pred_bs": "WAIT",
        "level": 1,
        
        # --- 1 Hour Cycle व्हेरिएबल्स ---
        "cycle_start_time": time.time(),
        "is_paused_phase": False, # True असेल तेव्हा बॉट 1 तासासाठी झोपलेला असेल
        
        "full_history": [], 
        "history": [],
        "stats": {"win": 0, "fail": 0, "total_trades": 0},
        "is_running": False,        
        "active_chat_id": None,    
        "live_records": [],
        "telegram_status": "Waiting for command..."
    }

state_30s = create_state("WinGo 30S", "30S")

def send_telegram_message_direct(chat_id, text, state):
    if not chat_id: return
    
    # 🔗 रजिस्ट्रेशन लिंक 
    reg_link = "\n\n🔗 *Register Here:* https://www.DamanClub.win/#/register?invitationCode=1614313895334"
    if reg_link not in text:
        text += reg_link

    def _send():
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try:
            response = api_session.post(url, json={
                "chat_id": chat_id, 
                "text": text, 
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }, timeout=5)
            
            if response.status_code != 200:
                state["telegram_status"] = f"[red]Error {response.status_code}: {response.text}[/red]"
            else:
                state["telegram_status"] = "[green]OK (Message Sent)[/green]"
        except Exception as e:
            state["telegram_status"] = f"[red]Network Error: {e}[/red]"
            
    threading.Thread(target=_send, daemon=True).start()

def telegram_listener():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=2"
            response = api_session.get(url, timeout=5)
            if response.status_code == 200:
                for result in response.json().get("result", []):
                    offset = result["update_id"] + 1
                    message = result.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "").strip()

                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = True
                            state_30s["active_chat_id"] = chat_id 
                            send_telegram_message_direct(chat_id, f"✅ *[Continuous 3-Pattern Break Bot]* Activated! 1-Hour Cycle Started.", state_30s)
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.", state_30s)
                            
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *Bot Stopped Successfully!*", state_30s)
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.", state_30s)
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, prev_res_text=None):
    target_chat_id = state.get("active_chat_id") or TARGET_GROUP_ID
    if not target_chat_id: return
    
    if state["is_paused_phase"] and prev_res_text is None:
        return # जर झोपलेला असेल आणि मागचा रिझल्ट सांगायचा नसेल, तर मेसेज करू नका.

    text = f"🚀 *{state['name']} Signal* 🚀\n"
    text += f"⚙️ *Strategy:* 3 Pattern Break (Continuous)\n\n"
    
    if prev_res_text:
        text += f"📊 *मागील निकाल:*\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Next Issue:* `{issue}`\n\n"
    
    if state["is_paused_phase"]:
         text += f"💤 *Bot is Resting for 1 Hour.*\n⏳ Please wait for the next active cycle.\n\n"
    elif state["wait_for_trigger"] or state["pred_bs"] == "WAIT":
         text += f"⏳ *Waiting for Pattern (3 Big or 3 Small)...*\n\n"
    else:
        icon = "🟠 Big" if state["pred_bs"] == "Big" else "🔵 Small"
        text += f"🎯 *Prediction:* *{icon}*\n"
        text += f"💰 *Level:* L{state['level']}\n\n"
        text += f"💡 _Bet according to your level._"
        
    send_telegram_message_direct(target_chat_id, text, state)

def fetch_history_records(url, state):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
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
    return all_records

def check_time_cycle(state):
    elapsed = time.time() - state["cycle_start_time"]
    if elapsed >= 3600: # 3600 सेकंद = 1 तास
        state["cycle_start_time"] = time.time()
        state["is_paused_phase"] = not state["is_paused_phase"] 
        state["wait_for_trigger"] = True
        state["current_target_bs"] = "WAIT"
        state["pred_bs"] = "WAIT"
        state["level"] = 1
        
        target_chat_id = state.get("active_chat_id") or TARGET_GROUP_ID
        if state["is_running"] and target_chat_id:
            if state["is_paused_phase"]:
                send_telegram_message_direct(target_chat_id, "⏳ *1 Hour Active Phase Completed.*\n💤 Bot is now sleeping for 1 Hour. No trades will be given.", state)
            else:
                send_telegram_message_direct(target_chat_id, "✅ *1 Hour Sleep Completed.*\n🚀 Bot is now ACTIVE and waiting for 3 Big / 3 Small pattern.", state)

def update_predictions(state):
    if state["is_paused_phase"]:
        state["pred_bs"] = "WAIT"
        return

    # 1. ट्रिगर चेक करणे (3 Big किंवा 3 Small)
    if state["wait_for_trigger"]:
        if len(state["full_history"]) >= 3:
            latest_issue_in_history = int(state["full_history"][0]["issue"])
            
            # जिंकल्यावर जुने रिझल्ट इग्नोर करण्यासाठी
            if latest_issue_in_history >= state.get("ignore_trigger_until_issue", 0):
                last_3 = [x["bs"] for x in state["full_history"][:3]]
                
                if last_3 == ["Big", "Big", "Big"]:
                    state["wait_for_trigger"] = False
                    state["current_target_bs"] = "Small" # 3 Big आले, आता
