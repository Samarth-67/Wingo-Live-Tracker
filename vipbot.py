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
TARGET_GROUP_ID = "-1004331023441"  # तुमच्या ग्रुपचा आयडी

# 🔐 सिक्रेट पासवर्ड (30S साठी)
PASS_30S = "33333"
# -----------------------------------------------------------

api_session = requests.Session()

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        "current_strategy": 1,  # 1: Three Circle (Reverse), 2: Trend Follower
        "strategy_start_time": time.time(),
        "locked_pred": None, 
        "pred_bs": "WAIT",
        "pred_color": "WAIT",
        "pred_nums": [],
        "level": 1,
        "full_history": [], 
        "history": [],
        "stats": {"win": 0, "fail": 0, "total_trades": 0},
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
            api_session.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
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
                            send_telegram_message_direct(chat_id, "✅ *[30S Bot]* Activated! Three-Circle & Trend Follower is ON.")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                            
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *[30S Bot] Stopped Successfully!*")

                    elif text.startswith("/reset"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["level"] = 1
                            state_30s["pred_bs"] = "WAIT"
                            state_30s["locked_pred"] = None
                            send_telegram_message_direct(chat_id, "🔄 *30S Bot Reset Successfully!*")
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, prev_res_text=None):
    if not TARGET_GROUP_ID: return

    game_name = state["name"]
    strat_names = {1: "Three Circle (Reverse)", 2: "Trend Follower"}
    current_s_name = strat_names[state["current_strategy"]]
    
    text = f"🚀 *{game_name} Signal* 🚀\n"
    text += f"⚙️ *Active Strategy:* {state['current_strategy']} - {current_s_name}\n\n"
    
    if prev_res_text:
        text += f"📊 *मागील निकाल (Previous Result):*\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Next Issue:* `{issue}`\n\n"
    
    if state["pred_bs"] == "WAIT":
        text += "⏳ Waiting for pattern (3 same results needed)...\n\n"
    else:
        icon = "🟠 Big" if state["pred_bs"] == "Big" else "🔵 Small"
        color_icon = "🟢 Green" if state["pred_color"] == "Green" else "🔴 Red"
        text += f"🎯 *Prediction:* *{icon}* | *{color_icon}* \n"
        text += f"💰 *Level:* L{state['level']}\n\n"
        
    text += "💡 _Auto Prediction Bot is ON._"
    send_telegram_message_direct(TARGET_GROUP_ID, text)

def fetch_history_records(url, state):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://draw.ar-lottery01.com/",
    }
    all_records = []
    try:
        params = {"pageSize": 30, "pageNo": 1, "ts": int(time.time() * 1000)}
        response = api_session.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and isinstance(data["data"], list): all_records.extend(data["data"])
            elif "list" in data and isinstance(data["list"], list): all_records.extend(data["list"])
            elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: all_records.extend(data["data"]["list"])
    except Exception:
        pass
    return all_records

def shift_strategy(state, reason_text):
    state["current_strategy"] = 2 if state["current_strategy"] == 1 else 1
    state["strategy_start_time"] = time.time()
    state["pred_bs"] = "WAIT"
    state["locked_pred"] = None
    state["level"] = 1
    
    if state["is_running"]:
        send_telegram_message_direct(TARGET_GROUP_ID, f"⚠️ *STRATEGY SHIFTED!*\n{reason_text}\n➡️ Now using Strategy {state['current_strategy']}")

def update_predictions(state, next_issue_int, latest_color, latest_bs):
    if state["current_strategy"] == 1:
        if state["level"] == 1:
            if len(state["full_history"]) >= 3:
                h1 = state["full_history"][0]["bs"]
                h2 = state["full_history"][1]["bs"]
                h3 = state["full_history"][2]["bs"]
                
                if h1 == "Big" and h2 == "Big" and h3 == "Big":
                    state["pred_bs"] = "Small"
                    state["locked_pred"] = "Small"
                elif h1 == "Small" and h2 == "Small" and h3 == "Small":
                    state["pred_bs"] = "Big"
                    state["locked_pred"] = "Big"
                else:
                    state["pred_bs"] = "WAIT"
                    state["locked_pred"] = None
            else:
                state["pred_bs"] = "WAIT"
        else:
            state["pred_bs"] = state.get("locked_pred", "WAIT")
            
    elif state["current_strategy"] == 2:
        state["pred_bs"] = latest_bs

    if state["pred_bs"] == "Big":
        state["pred_color"] = "Green"
        state["pred_nums"] = [7, 9]
    elif state["pred_bs"] == "Small":
        state["pred_color"] = "Red"
        state["pred_nums"] = [2, 4]
    else:
        state["pred_color"] = "WAIT"
        state["pred_nums"] = []

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

    existing_issues = {x["issue"] for x in state["full_history"]}
    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss.isdigit() and num_str.isdigit() and iss not in existing_issues:
            n_val = int(num_str)
            state["full_history"].append({
                "issue": iss, 
                "bs": "Big" if n_val >= 5 else "Small", 
                "color": "Green" if n_val in [1, 3, 5, 7, 9] else "Red"
            })
            existing_issues.add(iss)
                
    state["full_history"].sort(key=lambda x: int(x["issue"]), reverse=True)
    state["full_history"] = state["full_history"][:60] 

    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        next_issue_int = int(latest_issue) + 1
        update_predictions(state, next_issue_int, latest_color, latest_bs)
        if state["is_running"]: send_telegram_signal(state, str(next_issue_int))
        return True

    if state["last_processed_issue"] != latest_issue:
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        if time.time() - state["strategy_start_time"] >= 3600:
            shift_strategy(state, "⏳ 1 Hour Completed.")

        prev_res_text = f"🎯 Result: *{latest_number_str}* ({latest_bs} | {latest_color})\n"
        res_status = "-"
        current_logged_level = state["level"]

        if state["pred_bs"] != "WAIT":
            state["stats"]["total_trades"] += 1
            if state["pred_bs"] == latest_bs:
                state["stats"]["win"] += 1
                res_status = f"{state['pred_bs']} ✅ WIN"
                prev_res_text += f"🔹 Match: ✅ WIN\n"
                state["level"] = 1
                state["locked_pred"] = None 
            else:
                state["stats"]["fail"] += 1
                res_status = f"{state['pred_bs']} ❌ FAIL"
                prev_res_text += f"🔹 Match: ❌ FAIL\n"
                state["level"] += 1

            if state["level"] > 6:
                prev_res_text += "⚠️ L6 Failed! Switching Strategy..."
                shift_strategy(state, "🚨 Level 6 Failed!")
                
        state["history"].append({
            "issue": latest_issue[-4:],
            "pred": state["pred_bs"],
            "level": f"L{current_logged_level}", 
            "res": "[green]✅ WIN[/]" if "WIN" in res_status else ("[red]❌ FAIL[/]" if "FAIL" in res_status else "-")
        })
        if len(state["history"]) > 4: state["history"].pop(0)

        next_issue_int = int(latest_issue) + 1
        update_predictions(state, next_issue_int, latest_color, latest_bs)

        if state["is_running"]:
            if prev_res_text == f"🎯 Result: *{latest_number_str}* ({latest_bs} | {latest_color})\n":
                prev_res_text = None 
            send_telegram_signal(state, str(next_issue_int), prev_res_text)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def worker_30s():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_30s/GetHistoryIssuePage.json"
    while True:
        records = fetch_history_records(url, state_30s)
        if records:
            process_strategy(state_30s, records)
        time.sleep(1.5)

def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and state["last_processed_issue"].isdigit() else "Next"
    time_left = max(0, int(3600 - (time.time() - state["strategy_start_time"])))
    mins, secs = divmod(time_left, 60)
    strat_names = {1: "Three Circle (Reverse)", 2: "Trend Follower"}
    
    if state["pred_bs"] == "WAIT":
        ui_text = "[yellow]WAITING FOR 3 CIRCLE[/]" if state["current_strategy"] == 1 else "[yellow]WAITING[/]"
    else:
        s_color = "dark_orange" if state["pred_bs"] == "Big" else "bright_blue"
        c_color = "green" if state["pred_color"] == "Green" else "red"
        ui_text = f"[{s_color}]{state['pred_bs']}[/] | [{c_color}]{state['pred_color']}[/] | L{state['level']}"
        
    timer_status = "[green]RUNNING (Sending Signals)[/]" if state["is_running"] else "[red]STOPPED (Waiting for /signal 33333)[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n"
    panel_text += f"⚙️ [bold]Active Strat:[/] {state['current_strategy']} ({strat_names[state['current_strategy']]})\n"
    panel_text += f"⏳ [bold]Next Shift In:[/] {mins}m {secs}s\n"
    panel_text += f"📏 [bold]Prediction:[/] {ui_text}\n"
    panel_text += f"🕒 [bold]Status:[/] {timer_status} \n\n"
    
    hist_table = Table(show_header=True, width=72)
    hist_table.add_column("Iss", justify="center")
    hist_table.add_column("Pred (L)", justify="center")
    hist_table.add_column("Result", justify="center")
    
    if not state["history"]:
        hist_table.add_row("-", "-", "-")
    else:
        for h in state["history"]: 
            p = f"{h['pred'][0]}({h['level']})" if h['pred'] != "WAIT" else "-"
            hist_table.add_row(str(h["issue"]), p, str(h["res"])[0:13])
            
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]{state['name']} - Auto Bot[/]", border_style="cyan", width=78)

def create_master_ui():
    p_30s = render_game_panel(state_30s)
    return Group(
        Align.center("[bold yellow]🚀 30S 3-CIRCLE & TREND BOT[/bold yellow]\n"),
        Align.center(p_30s),
        Align.center("[bold cyan]To start sending signals, type /signal 33333 in your Telegram Bot[/bold cyan]\n")
    )

if __name__ == "__main__":
    t_list = threading.Thread(target=telegram_listener, daemon=True)
    t_30s = threading.Thread(target=worker_30s, daemon=True)
    
    t_list.start(); t_30s.start()

    with Live(create_master_ui(), console=console, refresh_per_second=4, screen=False) as live:
        while True:
            live.update(create_master_ui())
            time.sleep(0.5)
