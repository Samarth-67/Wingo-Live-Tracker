import os
import time
import threading
import requests
from rich.table import Table
from rich.console import Console, Group
from rich.panel import Panel
from rich.align import Align

console = Console()

# --- 🚀 TELEGRAM BOT CONFIGURATION 🚀 ---
TELEGRAM_TOKEN = "8942327560:AAEPv5Nd40PHxk3m1Yezmv6CQRmgpWVcZ8M"
TELEGRAM_CHAT_ID = "-1004437303447" # तुझा चॅनेल ID
SECRET_PASSWORD = "67890" # या बॉटसाठी नवीन पासवर्ड
# ----------------------------------------

# Strategy, Level, and History State (Only Big/Small)
state = {
    "last_processed_issue": None,
    "status": "WAITING",  
    "bs_pred": None, "bs_step": 0, "bs_level": 1,
    "history": [],
    "stats": {"bs_win": 0, "bs_fail": 0, "total_trades": 0},
    "active_until": 0,       # टायमरसाठी
    "notified_sleep": True   # १ तास संपल्यावर नोटिफिकेशन देण्यासाठी
}

def send_telegram_message_direct(chat_id, text):
    """Direct message sending function for commands and alerts."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except Exception:
        pass

def telegram_listener():
    """Background thread to listen for the secret password."""
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=2"
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
                            state["active_until"] = time.time() + 3600 # १ तासासाठी (3600 सेकंद) ॲक्टिव्हेट
                            state["notified_sleep"] = False
                            send_telegram_message_direct(chat_id, "✅ *Bot 2 (Big/Small) Activated for 1 Hour!*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(3)

def send_telegram_signal(issue, bs_pred, bs_level, prev_bs_res=None):
    """Sends the prediction signal and previous result to the Telegram Bot."""
    if not TELEGRAM_CHAT_ID:
        return

    text = f"🚀 *VSR WINGO Signals (Big/Small)* 🚀\n\n"
    
    # जर मागील ट्रेडचा रिझल्ट असेल, तर तो मेसेजमध्ये ॲड करणे
    if prev_bs_res:
        bs_won = "WIN" in prev_bs_res
        
        text += f"🔄 *Last Trade Result:*\n"
        text += f"📏 B/S: *{prev_bs_res}*\n\n"
        
        if bs_won:
            text += f"🔥🎉 *CONGRATS! WIN!* 🎉🔥\n"
            
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    # 🎯 टेलिग्राम मेसेजमध्ये रंग दाखवण्यासाठी इमोजी सेट करणे
    bs_pred_text = "🟠 Big" if bs_pred == "Big" else "🔵 Small"
    
    # नवीन प्रेडिक्शन
    text += (
        f"🎟️ *New Issue:* {issue}\n\n"
        f"📏 *Prediction:* *{bs_pred_text}*\n"
        f"🎯 *Level:* L{bs_level}\n"
    )
    
    send_telegram_message_direct(TELEGRAM_CHAT_ID, text)

def fetch_data():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
    }
    params = {"ts": int(time.time() * 1000)}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        return None
    return None

def extract_records(data):
    if not data: return []
    if "data" in data and isinstance(data["data"], list): return data["data"]
    elif "list" in data and isinstance(data["list"], list): return data["list"]
    elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: return data["data"]["list"]
    return []

def update_strategy(records):
    if not records:
        return False
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or latest_item.get("period") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if latest_number_str.isdigit():
        number = int(latest_number_str)
        latest_bs = "Big" if number >= 5 else "Small"
    else:
        return False

    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        return True

    if state["last_processed_issue"] != latest_issue:
        
        bs_res_status = None
        
        # Check Results and Update Levels
        if state["status"] == "PREDICTING":
            bs_win = (state["bs_pred"] == latest_bs)
            
            # 🎯 रिझल्टच्या मेसेजमध्ये रंगांचे इमोजी ॲड करणे
            bs_emoji = "🟠" if state["bs_pred"] == "Big" else "🔵"
            
            bs_res_status = f"{bs_emoji} {state['bs_pred']} ✅ WIN" if bs_win else f"{bs_emoji} {state['bs_pred']} ❌ FAIL"
            
            state["stats"]["total_trades"] += 1
            if bs_win: state["stats"]["bs_win"] += 1
            else: state["stats"]["bs_fail"] += 1
            
            state["history"].append({
                "trade": state["stats"]["total_trades"],
                "issue": latest_issue,
                "bs_level": f"L{state['bs_level']}",
                "bs_pred": state["bs_pred"],
                "bs_res": "WIN" if bs_win else "FAIL"
            })
            
            if bs_win: state["bs_level"] = 1
            else: state["bs_level"] += 1
            
        # Strategy Rotation (3 Circle) - Only for B/S
        if state["status"] == "WAITING":
            state["bs_pred"] = latest_bs
            state["bs_step"] = 1
            state["status"] = "PREDICTING"
            
        elif state["status"] == "PREDICTING":
            if state["bs_step"] < 3: state["bs_step"] += 1
            else:
                state["bs_pred"] = "Small" if state["bs_pred"] == "Big" else "Big"
                state["bs_step"] = 1
        
        # Calculate Next Issue Number
        next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
        
        # 📲 SEND TELEGRAM SIGNAL (Only if Timer is Active)
        if state["active_until"] > 0 and time.time() < state["active_until"]:
            send_telegram_signal(
                issue=next_issue,
                bs_pred=state["bs_pred"],
                bs_level=state["bs_level"],
                prev_bs_res=bs_res_status
            )
        elif state["active_until"] > 0 and time.time() >= state["active_until"]:
            if not state["notified_sleep"]:
                send_telegram_message_direct(TELEGRAM_CHAT_ID, "💤 *1 Hour Session Completed (Big/Small Bot)! Sleeping now.*")
                state["notified_sleep"] = True
                state["active_until"] = 0

        state["last_processed_issue"] = latest_issue
        return True
        
    return False

def create_ui(records):
    if state["last_processed_issue"] and state["last_processed_issue"].isdigit():
        next_issue = str(int(state["last_processed_issue"]) + 1)
    else:
        next_issue = "Next"

    if state["status"] == "WAITING":
        pred_text = "👀 [bold yellow]Waiting for the next Live Trade...\nStrategy will start shortly.[/bold yellow]"
    else:
        bs_color = "bold cyan" if state["bs_pred"] == "Big" else "bold yellow"
        
        pred_text = (
            f"🎯 [bold white]LIVE PREDICTIONS (Issue: {next_issue}):[/bold white]\n\n"
            f"📏 [bold]B/S:[/bold] [{bs_color}]{state['bs_pred']}[/{bs_color}] [bold magenta](Circle {state['bs_step']}/3)[/bold magenta]  ➡️  [bold cyan]Trade Level: L{state['bs_level']}[/bold cyan]"
        )
    
    # टायमर स्टेटस डॅशबोर्डवर दाखवणे
    timer_status = "[bold green]ACTIVE[/]" if (state["active_until"] > 0 and time.time() < state["active_until"]) else "[bold red]INACTIVE (Sleeping)[/]"
    
    pred_panel = Panel(Align.center(f"{pred_text}\n\n🕒 Signal Status: {timer_status}"), border_style="bright_green", expand=False, width=80, title="🤖 [bold green]Auto Series & Level Strategy (B/S Only)[/bold green] 🤖")

    stats_text = (
        f"📊 [bold white]Total Trades:[/bold white] {state['stats']['total_trades']} | "
        f"📏 [bold white]B/S:[/bold white] [green]{state['stats']['bs_win']} W[/green], [red]{state['stats']['bs_fail']} F[/red]"
    )
    
    hist_table = Table(title=stats_text, style="yellow", border_style="yellow", header_style="bold yellow", width=80)
    columns = ["Trade", "Issue", "B/S Level", "B/S Pred", "B/S Result"]
    for col in columns:
        hist_table.add_column(col, justify="center", style="cyan" if "Level" in col else None)

    if not state["history"]:
        hist_table.add_row("-", "-", "-", "-", "-")
    else:
        for h in state["history"][-5:]:
            bs_res_style = "[bold green]WIN[/]" if h["bs_res"] == "WIN" else "[bold red]FAIL[/]"
            hist_table.add_row(str(h["trade"]), h["issue"], f"[bold]{h['bs_level']}[/bold]", h["bs_pred"], bs_res_style)

    live_table = Table(title="🔥 [bold cyan]WinGo 1M Live Results (Last 5)[/bold cyan] 🔥", style="cyan", border_style="blue", header_style="bold bright_white", width=80)
    live_table.add_column("🎟️ Ticket Number", style="magenta", justify="center")
    live_table.add_column("🔢 Number", style="yellow", justify="center", width=10)
    live_table.add_column("📏 Big / Small", style="white", justify="center", width=15)

    if records:
        for item in records[:5]:
            ticket = str(item.get("issueNumber") or item.get("issue") or item.get("period") or "-")
            number = str(item.get("number") or item.get("drawNumber") or "-")
            if number.isdigit():
                num_val = int(number)
                big_small = "[bold cyan]Big[/bold cyan]" if num_val >= 5 else "[bold yellow]Small[/bold yellow]"
            else:
                big_small = "-"
            live_table.add_row(ticket, number, big_small)
            
    return Group(Align.center(pred_panel), Align.center(hist_table), Align.center(live_table))

if __name__ == "__main__":
    # Telegram Listener थ्रेड सुरू करणे
    t_listener = threading.Thread(target=telegram_listener, daemon=True)
    t_listener.start()
    
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print("[bold yellow]🚀 Live Level Strategy Tracker + Telegram Bot Started... Press Ctrl + C to stop.[/bold yellow]\n")
    
    while True:
        live_data = fetch_data()
        if live_data:
            records = extract_records(live_data)
            needs_update = update_strategy(records)
            
            if needs_update:
                os.system('cls' if os.name == 'nt' else 'clear')
                console.print("[bold yellow]🚀 Live Level Strategy Tracker + Telegram Bot Started... Press Ctrl + C to stop.[/bold yellow]\n")
                console.print(create_ui(records))
        time.sleep(2)
