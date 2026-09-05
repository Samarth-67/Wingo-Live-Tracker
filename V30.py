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

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        
        # Strategy 1 (2-Round Continuous Pattern: Big/Small Opposite Prediction)
        "s1_pred_bs": "WAIT",
        "s1_pred_color": "WAIT",
        "s1_pred_nums": [],
        "s1_level": 1,
        "s1_active": False,
        
        "full_history": [], 
        "history": [],
        "stats": {"s1_win": 0, "s1_fail": 0, "total_trades": 0},
        "is_running": False,        
        "active_chat_id": None,    
        "live_records": []
    }

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

                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = True
                            state_30s["active_chat_id"] = chat_id
                            send_telegram_message_direct(chat_id, f"✅ *[30S Strategy 1 (2-Round)] Activated! Live Prediction is ON.*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                            
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *[30S Strategy 1 (2-Round)] Stopped Successfully!*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, prev_res_text=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    game_name = state["name"]
    
    text = f"🚀 *{game_name} New Signal* 🚀\n\n"
    
    if prev_res_text:
        text += f"📊 *मागील निकाल (Previous Result):*\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Next Issue:* `{issue}`\n\n"
    
    # Strategy 1 Text (2-Round)
    if not state["s1_active"] or state["s1_pred_bs"] == "WAIT":
        text += f"📏 *Strategy 1 (2-Round):* ⏳ Waiting for 2 matching Big/Small...\n\n"
    else:
        s1_icon = "🟠 Big" if state["s1_pred_bs"] == "Big" else "🔵 Small"
        color_icon = "🟢 Green" if state["s1_pred_color"] == "Green" else "🔴 Red"
        nums_str = ", ".join(map(str, state["s1_pred_nums"]))
        text += f"📏 *Strategy 1 (2-Round):* *{s1_icon}* | *{color_icon}* | 🔢 *{nums_str}* | 🎯 L{state['s1_level']}\n\n"
        
    text += f"💡 _Bet according to your level._"
        
    send_telegram_message_direct(target_chat_id, text)

def fetch_history_records(url, state):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
    # Only evaluate new pattern if not currently active on a running chain
    if not state["s1_active"]:
        if len(state["full_history"]) >= 2:
            last_2_bs = [x["bs"] for x in state["full_history"][:2]]
            latest_color = state["full_history"][0]["color"]
            
            # Big/Small 2-Round Opposite Prediction (सलग २ वेळा बिग आल्यास स्मॉल, सलग २ वेळा स्मॉल आल्यास बिग)
            if last_2_bs == ["Big", "Big"]:
                pred_bs = "Small"
            elif last_2_bs == ["Small", "Small"]:
                pred_bs = "Big"
            else:
                pred_bs = "WAIT"
                
            if pred_bs != "WAIT":
                state["s1_active"] = True
                state["s1_pred_bs"] = pred_bs
                state["s1_level"] = 1
                
                # Color prediction based on latest opposite color to avoid WAIT
                pred_color = "Red" if latest_color == "Green" else "Green"
                state["s1_pred_color"] = pred_color
                
                # Number Prediction mapping
                if pred_bs == "Big" and pred_color == "Red":
                    state["s1_pred_nums"] = [8, 6]
                elif pred_bs == "Small" and pred_color == "Green":
                    state["s1_pred_nums"] = [1, 3]
                elif pred_bs == "Big" and pred_color == "Green":
                    state["s1_pred_nums"] = [7, 9]
                elif pred_bs == "Small" and pred_color == "Red":
                    state["s1_pred_nums"] = [2, 4]
                else:
                    state["s1_pred_nums"] = []
            else:
                state["s1_active"] = False
                state["s1_pred_bs"] = "WAIT"
                state["s1_pred_color"] = "WAIT"
                state["s1_pred_nums"] = []
        else:
            state["s1_active"] = False
            state["s1_pred_bs"] = "WAIT"
            state["s1_pred_color"] = "WAIT"
            state["s1_pred_nums"] = []

def process_strategy(state, records):
    if not records: return False
    state["live_records"] = records[:5]
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if not (latest_number_str.isdigit() and latest_issue.isdigit()): return False
    
    num_int = int(latest_number_str)
    latest_bs = "Big" if num_int >= 5 else "Small"
    latest_color = "Green" if num_int in [1, 3, 5, 7, 9] else "Red"

    # Update Full History
    existing_issues = {x["issue"] for x in state["full_history"]}
    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss.isdigit() and num_str.isdigit() and iss not in existing_issues:
            n_val = int(num_str)
            bs_val = "Big" if n_val >= 5 else "Small"
            col_val = "Green" if n_val in [1, 3, 5, 7, 9] else "Red"
            state["full_history"].append({
                "issue": iss, 
                "bs": bs_val, 
                "color": col_val,
                "num": num_str
            })
            existing_issues.add(iss)
                
    state["full_history"].sort(key=lambda x: int(x["issue"]), reverse=True)
    state["full_history"] = state["full_history"][:60] 

    # Initial Run
    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        next_issue_int = int(latest_issue) + 1
        
        update_predictions(state, next_issue_int)
        
        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int))
        return True

    # Check if New Issue Arrived
    if state["last_processed_issue"] != latest_issue:
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        prev_res_text = f"🎯 Result: *{latest_number_str}* ({latest_bs} | {latest_color})\n"
        s1_res_status = "-"
        
        current_logged_level = state["s1_level"]

        # --- Evaluate Strategy 1 ---
        if state["s1_active"] and state["s1_pred_bs"] != "WAIT":
            state["stats"]["total_trades"] += 1
            if state["s1_pred_bs"] == latest_bs:
                state["stats"]["s1_win"] += 1
                s1_res_status = f"{state['s1_pred_bs']} ✅ WIN"
                prev_res_text += f"🔹 S1: ✅ WIN\n"
                # WIN: Reset level, deactivate active chain so it looks for a new pattern
                state["s1_level"] = 1
                state["s1_active"] = False
                state["s1_pred_bs"] = "WAIT"
                state["s1_pred_color"] = "WAIT"
                state["s1_pred_nums"] = []
            else:
                state["stats"]["s1_fail"] += 1
                s1_res_status = f"{state['s1_pred_bs']} ❌ FAIL"
                prev_res_text += f"🔹 S1: ❌ FAIL\n"
                # FAIL: Increment level and KEEP s1_active = True to persist the same prediction for the next level
                state["s1_level"] += 1
                state["s1_active"] = True
        
        # Add to recent UI history
        state["history"].append({
            "issue": latest_issue[-4:],
            "s1_pred_bs": state["s1_pred_bs"] if state["s1_active"] or "WIN" in s1_res_status or "FAIL" in s1_res_status else "WAIT",
            "s1_level": f"L{current_logged_level}", 
            "s1_res": "[green]✅ WIN[/]" if "WIN" in s1_res_status else ("[red]❌ FAIL[/]" if "FAIL" in s1_res_status else "-")
        })
        if len(state["history"]) > 4: state["history"].pop(0)

        # Set Next Issue
        next_issue_int = int(latest_issue) + 1
        
        # If not active (because it won or hasn't started), try finding a new pattern
        if not state["s1_active"]:
            update_predictions(state, next_issue_int)

        # Send Telegram Msg
        if state["is_running"]:
            if prev_res_text == f"🎯 Result: *{latest_number_str}* ({latest_bs} | {latest_color})\n":
                prev_res_text = None 
            send_telegram_signal(state, str(next_issue_int), prev_res_text)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def worker_30s():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
    while True:
        records = fetch_history_records(url, state_30s)
        if records:
            process_strategy(state_30s, records)
        time.sleep(1)

def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and state["last_processed_issue"].isdigit() else "Next"
    
    # Strat 1 UI
    if not state["s1_active"] or state["s1_pred_bs"] == "WAIT":
        s1_ui_text = "[yellow]WAIT (Waiting for 2 matching)[/]"
    else:
        s1_color = "dark_orange" if state["s1_pred_bs"] == "Big" else "bright_blue"
        col_color = "green" if state["s1_pred_color"] == "Green" else "red"
        nums_str = ", ".join(map(str, state["s1_pred_nums"]))
        s1_ui_text = f"[{s1_color}]{state['s1_pred_bs']}[/] | [{col_color}]{state['s1_pred_color']}[/] | 🔢 [{nums_str}] (L{state['s1_level']})"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n"
    panel_text += f"📏 [bold]Strategy 1 (2-Round):[/] {s1_ui_text}\n"
    panel_text += f"🕒 [bold]Status:[/] {timer_status}\n\n"
    panel_text += f"📊 [bold]S1 Stats - W:[/] [green]{state['stats']['s1_win']}[/] | [bold]F:[/] [red]{state['stats']['s1_fail']}[/]\n"
    
    hist_table = Table(show_header=True, width=72)
    hist_table.add_column("Iss", justify="center")
    hist_table.add_column("S1 Pred (L)", justify="center")
    hist_table.add_column("S1 Res", justify="center")
    
    if not state["history"]:
        hist_table.add_row("-", "-", "-")
    else:
        for h in state["history"]: 
            s1_p = f"{h['s1_pred_bs'][0]}({h['s1_level']})" if h['s1_pred_bs'] != "WAIT" else "-"
            
            hist_table.add_row(
                str(h["issue"]), 
                s1_p, 
                str(h["s1_res"])[0:13]
            )
    
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]{state['name']}[/]", border_style="cyan", width=78)

def create_master_ui():
    p_30s = render_game_panel(state_30s)
    return Group(
        Align.center("[bold yellow]🚀 30S SUPERFAST 2-ROUND STRATEGY BOT[/bold yellow]\n"),
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
