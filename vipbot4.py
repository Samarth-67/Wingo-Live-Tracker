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
        "current_pred_bs": "WAIT", # सध्याचे प्रेडिक्शन काय आहे
        "pattern_count": 0,        # सध्याचे प्रेडिक्शन किती वेळा दिले गेले (३ वेळा द्यायचे आहे)
        "pred_bs": "WAIT",
        "level": 1,
        
        # --- 1 Hour Cycle व्हेरिएबल्स ---
        "cycle_start_time": time.time(),
        
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
                            send_telegram_message_direct(chat_id, f"✅ *[Continuous 3-Pattern Bot]* Activated! 1-Hour Cycle Started.", state_30s)
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.", state_30s)
                            
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
