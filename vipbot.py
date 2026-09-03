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
TARGET_GROUP_ID = "-1004331023441"  

# 🔐 सिक्रेट पासवर्ड्स
PASS_1M = "22222"   # १ मिनिटाच्या गेमसाठी
# ----------------------------------------

# ⚡ फास्ट इंटरनेट कनेक्शनसाठी Session
api_session = requests.Session()

# 🚀 नवीन Number Prediction Logic
def get_number_prediction(target_num_str):
    if not target_num_str or not str(target_num_str).isdigit():
        return "WAIT"
    
    num = int(target_num_str)
    
    if num == 0: return "0"
    if num == 5: return "5"
        
    if num == 1: return "3, 1"
    elif num == 3: return "1, 3"
    
    elif num == 2: return "4, 2"
    elif num == 4: return "2, 4"
    
    elif num == 6: return "8, 6"
    elif num == 8: return "6, 8"
    
    elif num == 7: return "9, 7"
    elif num == 9: return "7, 9"
    
    return "WAIT"

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        "bs_pred": "WAIT", 
        "num_pred": "WAIT",
        "bs_level": 1, 
        "num_level": 1,
        "full_history": [], 
        "history": [],
        "stats": {"bs_win": 0, "bs_fail": 0, "num_win": 0, "num_fail": 0, "total_trades": 0},
        "is_running": False,       
        "active_chat_id": None,   
        "live_records": []
    }

# 1M साठी State
state_1m = create_state("WinGo 1M", "1M")

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
                            if pwd == PASS_1M:
                                state_1m["is_running"] = True
                                state_1m["active_chat_id"] = chat_id
                                send_telegram_message_direct(chat_id, f"✅ *[1M Strategy] Activated! Live Prediction is ON.*")
                            else:
                                send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    # --- STOP COMMAND ---
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2:
                            pwd = parts[1]
                            if pwd == PASS_1M:
                                state_1m["is_running"] = False
                                send_telegram_message_direct(chat_id, "🛑 *[1M Strategy] Stopped Successfully!*")
                            else:
                                send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(3)

# 🚀 मेसेज पाठवण्याचे नवीन सिंगल फॉरमॅट लॉजिक
def send_telegram_signal(state, issue, bs_pred, num_pred, bs_level, num_level, prev_res_text=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    game_name = state["name"]
    
    # फक्त एकच मेसेज ब्लॉक
    text = f"🚀 *{game_name} New Signal* 🚀\n\n"
    
    if state["stats"]["total_trades"] > 0 and prev_res_text:
        text += f"📊 *मागील निकाल (Previous Result):*\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Next Issue:* `{issue}`\n\n"
    
    if bs_pred == "WAIT" or num_pred == "WAIT":
        text += f"⏳ *Data Syncing...*\n_कृपया वाट पहा..._\n"
    else:
        bs_pred_text = "🟠 Big" if bs_pred == "Big" else "🔵 Small"
        text += f"📏 *B/S Pred:* *{bs_pred_text}*  | 🎯 L{bs_level}\n"
        text += f"🔢 *Num Pred:* *{num_pred}*  | 🎯 L{num_level}\n\n"
        text += f"💡 _Bet according to your level._"
        
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
        
        target_issue_str = str(next_issue_int - 20) 
        target_record = next((x for x in state["full_history"] if x["issue"] == target_issue_str), None)
        
        if target_record:
            state["bs_pred"] = target_record["bs"]
            state["num_pred"] = get_number_prediction(target_record["num"])
        elif len(state["full_history"]) >= 20:
            state["bs_pred"] = state["full_history"][19]["bs"]
            state["num_pred"] = get_number_prediction(state["full_history"][19]["num"])
        else:
            state["bs_pred"] = "WAIT"
            state["num_pred"] = "WAIT"
        
        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int), state["bs_pred"], state["num_pred"], state["bs_level"], state["num_level"])
        return True

    if state["last_processed_issue"] != latest_issue:
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        prev_res_text = ""
        
        if state["bs_pred"] != "WAIT" and state["num_pred"] != "WAIT":
            state["stats"]["total_trades"] += 1
            
            bs_win = (state["bs_pred"] == latest_bs)
            num_win = str(latest_number_str) in state["num_pred"]
            
            bs_mark = "✅ WIN" if bs_win else "❌ FAIL"
            num_mark = "✅ WIN" if num_win else "❌ FAIL" 
            
            prev_res_text = (
                f"🎯 Result: *{latest_number_str}* ({latest_bs})\n"
                f"🔹 B/S: {bs_mark}\n"
                f"🔸 Num: {num_mark}"
            )
            
            current_bs_level = state["bs_level"]
            current_num_level = state["num_level"]
            
            if bs_win:
                state["stats"]["bs_win"] += 1
                state["bs_level"] = 1 
                bs_res_status = f"{state['bs_pred']} ✅ WIN"
            else:
                state["stats"]["bs_fail"] += 1
                state["bs_level"] += 1
                bs_res_status = f"{state['bs_pred']} ❌ FAIL"

            if num_win:
                state["stats"]["num_win"] += 1
                state["num_level"] = 1 
                num_res_status = f"{state['num_pred']} ✅ WIN"
            else:
                state["stats"]["num_fail"] += 1
                state["num_level"] += 1
                num_res_status = f"{state['num_pred']} ❌ FAIL"
                    
            state["history"].append({
                "trade": state["stats"]["total_trades"], 
                "issue": latest_issue[-4:],
                "bs_level": f"L{current_bs_level}", 
                "bs_pred": state["bs_pred"],
                "bs_res": "[green]✅ WIN[/]" if "WIN" in bs_res_status else "[red]❌ FAIL[/]",
                "num_level": f"L{current_num_level}",
                "num_pred": state["num_pred"],
                "num_res": "[green]✅ WIN[/]" if "WIN" in num_res_status else "[red]❌ FAIL[/]"
            })
            if len(state["history"]) > 4: state["history"].pop(0)

        next_issue_int = int(latest_issue) + 1
        
        target_issue_str = str(next_issue_int - 20)
        target_record = next((x for x in state["full_history"] if x["issue"] == target_issue_str), None)
        
        if target_record:
            state["bs_pred"] = target_record["bs"]
            state["num_pred"] = get_number_prediction(target_record["num"])
        elif len(state["full_history"]) >= 20:
            state["bs_pred"] = state["full_history"][19]["bs"]
            state["num_pred"] = get_number_prediction(state["full_history"][19]["num"])
        else:
            state["bs_pred"] = "WAIT"
            state["num_pred"] = "WAIT"

        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int), state["bs_pred"], state["num_pred"], state["bs_level"], state["num_level"], prev_res_text)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def worker_1m():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
    while True:
        records = fetch_history_records(url)
        if records:
            process_strategy(state_1m, records)
        time.sleep(2) 

def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and state["last_processed_issue"].isdigit() else "Next"
    
    if state["bs_pred"] == "WAIT" or state["num_pred"] == "WAIT":
        ui_text = "[yellow]WAIT (Syncing...)[/]"
        num_text = "WAIT"
    else:
        bs_color = "dark_orange" if state["bs_pred"] == "Big" else "bright_blue"
        ui_text = f"[{bs_color}]{state['bs_pred']}[/] (L{state['bs_level']})"
        num_text = f"[bold magenta]{state['num_pred']}[/] (L{state['num_level']})" 
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n"
    panel_text += f"📏 [bold]B/S Pred:[/] {ui_text}\n"
    panel_text += f"🔢 [bold]Num Pred:[/] {num_text}\n"
    panel_text += f"🕒 [bold]Status:[/] {timer_status}\n\n"
    panel_text += f"📊 [bold]B/S Stats  - W:[/] [green]{state['stats']['bs_win']}[/] | [bold]F:[/] [red]{state['stats']['bs_fail']}[/]\n"
    panel_text += f"🔢 [bold]Num Stats  - W:[/] [green]{state['stats']['num_win']}[/] | [bold]F:[/] [red]{state['stats']['num_fail']}[/]\n" 
    
    hist_table = Table(show_header=True, width=72)
    hist_table.add_column("Iss", justify="center")
    hist_table.add_column("B/S(L)", justify="center")
    hist_table.add_column("B-Res", justify="center")
    hist_table.add_column("Num(L)", justify="center") 
    hist_table.add_column("N-Res", justify="center") 
    
    if not state["history"]:
        hist_table.add_row("-", "-", "-", "-", "-")
    else:
        for h in state["history"]: 
            hist_table.add_row(
                str(h["issue"]), 
                f"{h['bs_pred'][0]}({h['bs_level']})", 
                str(h["bs_res"])[0:13],
                f"{h['num_pred']}({h['num_level']})",
                str(h["num_res"])[0:13]
            )
    
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]{state['name']}[/]", border_style="cyan", width=78)

def create_master_ui():
    p_1m = render_game_panel(state_1m)
    return Group(
        Align.center("[bold yellow]🚀 1 MINUTE BOT (Single Output Message)[/bold yellow]\n"),
        Align.center(p_1m)
    )

if __name__ == "__main__":
    t_list = threading.Thread(target=telegram_listener, daemon=True)
    t_1m = threading.Thread(target=worker_1m, daemon=True)
    
    t_list.start(); t_1m.start()

    with Live(create_master_ui(), console=console, refresh_per_second=4, screen=False) as live:
        while True:
            live.update(create_master_ui())
            time.sleep(0.5)
