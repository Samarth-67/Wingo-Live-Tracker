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
TELEGRAM_TOKEN = "8577275461:AAF8lWPac3WCgbHp8XPvU_lO289oHcMdOE8" 
TARGET_GROUP_ID = "-5202202128"  # <--- ३० सेकंदाच्या चॅनेल/ग्रुपचा आयडी

# 🔐 सिक्रेट पासवर्ड
PASS_30S = "11111"   
# ----------------------------------------

# ⚡ फास्ट इंटरनेट कनेक्शनसाठी Session
api_session = requests.Session()

# 💰 Betting Table (Level: Amount)
BET_TABLE = {
    1: 100,
    2: 200,
    3: 500,
    4: 1100
}

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        
        # Strategy (2 Consecutive Opposite)
        "pred": "WAIT",
        "level": 1,
        "active": False,
        "rounds_left": 0,
        
        # Virtual Wallet
        "virtual_balance": 20000,
        
        "full_history": [], 
        "history": [],
        "stats": {"win": 0, "fail": 0, "total_trades": 0},
        
        "is_running": False,        
        "active_chat_id": None,   
        "live_records": [],
        "last_result_text": "Initializing..."
    }

# 30S साठी State
state_30s = create_state("WinGo 30S", "30S")

def send_telegram_message_direct(chat_id, text):
    if not chat_id: return
    def _send():
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try:
            api_session.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=3)
        except Exception:
            pass
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

                    # --- START COMMAND ---
                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2:
                            pwd = parts[1]
                            if pwd == PASS_30S:
                                state_30s["is_running"] = True
                                state_30s["active_chat_id"] = chat_id
                                send_telegram_message_direct(chat_id, f"✅ *[{state_30s['name']} (2-Opp) Strategy] Activated! Live Prediction is ON.*")
                            else:
                                send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    # --- STOP COMMAND ---
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2:
                            pwd = parts[1]
                            if pwd == PASS_30S:
                                state_30s["is_running"] = False
                                send_telegram_message_direct(chat_id, f"🛑 *[{state_30s['name']} (2-Opp) Strategy] Stopped Successfully!*")
                            else:
                                send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                    
                    # --- RESET COMMAND ---
                    elif text.startswith("/reset"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["level"] = 1
                            state_30s["pred"] = "WAIT"
                            state_30s["active"] = False
                            state_30s["rounds_left"] = 0
                            state_30s["stats"]["win"] = 0
                            state_30s["stats"]["fail"] = 0
                            state_30s["virtual_balance"] = 20000
                            state_30s["last_result_text"] = "Stats & Wallet Reset Successfully!"
                            send_telegram_message_direct(chat_id, "🔄 *Bot Reset Successfully!*\nLevels are back to L1 and Wallet is ₹20,000.")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(2)

# 🚀 मेसेज पाठवण्याचे लॉजिक
def send_telegram_signal(state, issue, prev_res_text=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    game_name = state["name"]
    
    text = f"🚀 *{game_name} (2-Opp) Auto Bot* 🚀\n\n"
    
    if prev_res_text:
        text += f"🔄 *Last Trade Result:*\n"
        text += f"{prev_res_text}\n"
        text += f"💰 *Virtual Balance:* ₹{state['virtual_balance']}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Next Issue:* `{issue}`\n\n"
    
    # Strategy Text
    if state["pred"] == "WAIT":
        text += f"📐 *Prediction:* ⏳ Waiting for 2 B/S...\n\n"
    else:
        icon = "🟠 Big" if state["pred"] == "Big" else "🔵 Small"
        bet_amt = BET_TABLE.get(state["level"], 0)
        text += f"📐 *Prediction:* *{icon}*\n"
        text += f"🎯 *Level:* L{state['level']}\n"
        text += f"💵 *Virtual Bet:* ₹{bet_amt}\n\n"
        
    text += f"💡 _Auto Virtual Betting is ON._"
        
    send_telegram_message_direct(target_chat_id, text)

# 🚀 मल्टी-पेज फेचर
def fetch_history_records(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
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
        
    if len(all_records) <= 10:
        for p in [2, 3]:
            try:
                params = {"pageSize": 10, "pageNo": p, "ts": int(time.time() * 1000)}
                response = api_session.get(url, headers=headers, params=params, timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and isinstance(data["data"], list): all_records.extend(data["data"])
                    elif "list" in data and isinstance(data["list"], list): all_records.extend(data["list"])
                    elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: all_records.extend(data["data"]["list"])
            except Exception:
                pass
            
    return all_records

def update_predictions(state, next_issue_int):
    # --- Strategy Logic (Wait for 2 Consecutive) ---
    if not state["active"] and len(state["full_history"]) >= 2:
        # Check last 2 records
        last_2_bs = [x["bs"] for x in state["full_history"][:2]]
        
        if last_2_bs == ["Big", "Big"]:
            state["active"] = True
            state["rounds_left"] = 4 # 4 Levels (100, 200, 500, 1100)
            state["pred"] = "Small"
            state["level"] = 1
        elif last_2_bs == ["Small", "Small"]:
            state["active"] = True
            state["rounds_left"] = 4
            state["pred"] = "Big"
            state["level"] = 1
        else:
            state["pred"] = "WAIT"

def process_strategy(state, records):
    if not records: 
        return False
    state["live_records"] = records[:5]
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if not (latest_number_str.isdigit() and latest_issue.isdigit()): return False
    latest_bs = "Big" if int(latest_number_str) >= 5 else "Small"

    existing_issues = {x["issue"] for x in state["full_history"]}
    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss.isdigit() and num_str.isdigit() and iss not in existing_issues:
            bs_val = "Big" if int(num_str) >= 5 else "Small"
            state["full_history"].append({
                "issue": iss, 
                "bs": bs_val, 
                "num": num_str
            })
            existing_issues.add(iss)
                
    state["full_history"].sort(key=lambda x: int(x["issue"]), reverse=True)
    state["full_history"] = state["full_history"][:60]

    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        next_issue_int = int(latest_issue) + 1  
        
        update_predictions(state, next_issue_int)
        
        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int))
        return True

    if state["last_processed_issue"] != latest_issue:
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        prev_res_text = f"🎯 Result: *{latest_number_str}* ({latest_bs})\n"
        res_status = "-"
        
        # --- Evaluate Strategy & Update Balance ---
        if state["active"] and state["pred"] != "WAIT":
            bet_amt = BET_TABLE.get(state["level"], 0)
            state["stats"]["total_trades"] += 1
            
            if state["pred"] == latest_bs:
                state["stats"]["win"] += 1
                state["virtual_balance"] += bet_amt
                
                res_status = f"✅ WIN"
                prev_res_text += f"✅ *WIN* (+₹{bet_amt})\n"
                
                # Reset for next pattern
                state["active"] = False
                state["level"] = 1
                state["pred"] = "WAIT"
            else:
                state["stats"]["fail"] += 1
                state["virtual_balance"] -= bet_amt
                
                res_status = f"❌ FAIL"
                prev_res_text += f"❌ *FAIL* (-₹{bet_amt})\n"
                
                state["level"] += 1
                state["rounds_left"] -= 1
                
                # If rounds completed (Level 4 failed), reset
                if state["level"] > 4 or state["rounds_left"] <= 0:
                    prev_res_text += f"⚠️ *Level 4 Failed. Waiting for new pattern.*\n"
                    state["active"] = False
                    state["level"] = 1
                    state["pred"] = "WAIT"
                    
        state["last_result_text"] = prev_res_text
                    
        # Add to recent UI history
        state["history"].append({
            "issue": latest_issue[-4:],
            "pred": state["pred"] if state["active"] else "WAIT",
            "level": f"L{state['level'] - 1 if res_status != '-' else '-'}",
            "res": "[green]✅ WIN[/]" if "WIN" in res_status else ("[red]❌ FAIL[/]" if "FAIL" in res_status else "-")
        })
        if len(state["history"]) > 5: state["history"].pop(0)

        next_issue_int = int(latest_issue) + 1
        
        update_predictions(state, next_issue_int)

        if state["is_running"]:
            if prev_res_text == f"🎯 Result: *{latest_number_str}* ({latest_bs})\n":
                prev_res_text = None
            send_telegram_signal(state, str(next_issue_int), prev_res_text)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def worker_30s():
    # 30S ची API URL
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
    while True:
        records = fetch_history_records(url)
        if records:
            process_strategy(state_30s, records)
        time.sleep(1) # 30S साठी फास्ट पोलिंग

def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and state["last_processed_issue"].isdigit() else "Next"
    
    # UI Text
    if state["pred"] == "WAIT":
        ui_text = "[yellow]WAIT (Waiting for 2 B/S)[/]"
        bet_ui = "₹0"
    else:
        color = "dark_orange" if state["pred"] == "Big" else "bright_blue"
        ui_text = f"[{color}]{state['pred']}[/] (L{state['level']})"
        bet_ui = f"₹{BET_TABLE.get(state['level'], 0)}"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n"
    panel_text += f"📐 [bold]Prediction:[/] {ui_text}\n"
    panel_text += f"💵 [bold]Virtual Bet:[/] {bet_ui}\n"
    panel_text += f"🕒 [bold]Bot Status:[/] {timer_status}\n\n"
    panel_text += f"💰 [bold green]Virtual Balance:[/] [bold cyan]₹{state['virtual_balance']}[/]\n"
    panel_text += f"📊 [bold]Stats - Won:[/] [green]{state['stats']['win']}[/] | [bold]Failed:[/] [red]{state['stats']['fail']}[/]\n"
    
    hist_table = Table(show_header=True, width=72)
    hist_table.add_column("Issue", justify="center")
    hist_table.add_column("Prediction (L)", justify="center")
    hist_table.add_column("Result", justify="center")
    
    if not state["history"]:
        hist_table.add_row("-", "-", "-")
    else:
        for h in state["history"]: 
            p = f"{h['pred'][0]}({h['level']})" if h['pred'] != "WAIT" else "-"
            hist_table.add_row(
                str(h["issue"]), 
                p,
                str(h["res"])[0:13]
            )
    
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]{state['name']}[/]", border_style="cyan", width=78)

def create_master_ui():
    p_30s = render_game_panel(state_30s)
    return Group(
        Align.center("[bold yellow]🚀 30 SECONDS VIRTUAL BOT (2-Opp)[/bold yellow]\n"),
        Align.center(p_30s)
    )

if __name__ == "__main__":
    t_list = threading.Thread(target=telegram_listener, daemon=True)
    t_30s = threading.Thread(target=worker_30s, daemon=True)
    
    t_list.start(); t_30s.start()

    with Live(create_master_ui(), console=console, refresh_per_second=4, screen=False) as live:
        while True:
            live.update(create_master_ui())
            time.sleep(0.5)
