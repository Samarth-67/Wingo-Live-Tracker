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
PASS_30S = "11111"   # ३० सेकंदाच्या गेमसाठी
# ----------------------------------------

# ⚡ फास्ट इंटरनेट कनेक्शनसाठी Session तयार करणे (यामुळे स्पीड वाढतो)
api_session = requests.Session()

# कलर ओळखण्यासाठी फंक्शन
def get_color(num_str):
    num = int(num_str)
    if num in [1, 3, 7, 9]: return "Green 🟢"
    elif num in [2, 4, 6, 8]: return "Red 🔴"
    elif num == 0: return "Red & Violet 🔴🟣"
    elif num == 5: return "Green & Violet 🟢🟣"
    return "Unknown"

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        
        "bs_pred": "WAIT", 
        "color_pred": "WAIT",
        "num_pred": "WAIT",
        
        "bs_level": 1, 
        "color_level": 1, 
        
        "full_history": [], 
        "history": [],
        "stats": {"bs_win": 0, "bs_fail": 0, "color_win": 0, "color_fail": 0, "total_trades": 0},
        "is_running": False,       
        "active_chat_id": None,   
        "live_records": []
    }

state_30s = create_state("WinGo 30S", "30S")

def send_telegram_message_direct(chat_id, text):
    if not chat_id: return
    # 🚀 Async Background Sending (मेसेज अजिबात अडकणार नाही)
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
                            send_telegram_message_direct(chat_id, f"✅ *[30S Strategy] Activated! Live Prediction is ON.*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *[30S Strategy] Stopped Successfully!*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, bs_pred, color_pred, num_pred, bs_level, color_level, prev_res_text=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    game_name = state["name"]
    text = f"🚀 *VSR {game_name} Follower* 🚀\n\n"
    
    if state["stats"]["total_trades"] > 0 and prev_res_text:
        text += f"🔄 *Last Trade Result:*\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *New Issue:* {issue}\n\n"
    
    if bs_pred == "WAIT" or color_pred == "WAIT":
        text += f"⏳ *Building History Data...*\n_Waiting for enough data to sync..._\n"
    else:
        bs_pred_text = "🟠 Big" if bs_pred == "Big" else "🔵 Small"
        text += f"📏 *B/S Pred:* *{bs_pred_text}* | 🎯 L{bs_level}\n"
        text += f"🎨 *Color Pred:* *{color_pred}* | 🎯 L{color_level}\n"
        text += f"🔢 *Number Pred:* *{num_pred}*\n\n"
        
    send_telegram_message_direct(target_chat_id, text)

def fetch_history_records(url, state):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://draw.ar-lottery01.com/",
    }
    all_records = []
    
    # आधी ३० रेकॉर्ड्स एकत्र आणण्याचा प्रयत्न
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
        
    # जर API ने फक्त १० च रेकॉर्ड्स दिले, तर पेज २ आणि ३ पण आणेल
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
    if not records: return False
    state["live_records"] = records[:5]
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if not (latest_number_str.isdigit() and latest_issue.isdigit()): return False
    latest_bs = "Big" if int(latest_number_str) >= 5 else "Small"
    latest_color = get_color(latest_number_str)

    # मेमरीमध्ये रेकॉर्ड्स अत्यंत वेगाने सेव्ह करणे
    existing_issues = {x["issue"] for x in state["full_history"]}
    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss.isdigit() and num_str.isdigit() and iss not in existing_issues:
            bs_val = "Big" if int(num_str) >= 5 else "Small"
            state["full_history"].append({
                "issue": iss, 
                "bs": bs_val, 
                "num": num_str, 
                "color": get_color(num_str)
            })
            existing_issues.add(iss)
                
    state["full_history"].sort(key=lambda x: int(x["issue"]), reverse=True)
    state["full_history"] = state["full_history"][:60] # मेमरीमध्ये ६० राऊंड्स सुरक्षित राहतील

    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        next_issue_int = int(latest_issue) + 1
        
        # 🚀 ANTI-WAIT SYSTEM for B/S and Num (20th round logic)
        target_issue_str = str(next_issue_int - 20) 
        target_record = next((x for x in state["full_history"] if x["issue"] == target_issue_str), None)
        
        if target_record:
            state["bs_pred"] = target_record["bs"]
            state["num_pred"] = target_record["num"]
        elif len(state["full_history"]) >= 20:
            state["bs_pred"] = state["full_history"][19]["bs"]
            state["num_pred"] = state["full_history"][19]["num"]
        else:
            state["bs_pred"] = "WAIT"
            state["num_pred"] = "WAIT"

        # 🎨 New Color Logic: (Skip one round back) e.g. 576 -> predict for 577 based on 574
        target_color_issue_str = str(next_issue_int - 3) 
        target_color_record = next((x for x in state["full_history"] if x["issue"] == target_color_issue_str), None)
        
        if target_color_record:
            state["color_pred"] = target_color_record["color"]
        elif len(state["full_history"]) >= 3:
            state["color_pred"] = state["full_history"][2]["color"]
        else:
            state["color_pred"] = "WAIT"
        
        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int), state["bs_pred"], state["color_pred"], state["num_pred"], state["bs_level"], state["color_level"])
        return True

    if state["last_processed_issue"] != latest_issue:
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        prev_res_text = ""
        
        if state["bs_pred"] != "WAIT":
            state["stats"]["total_trades"] += 1
            
            # --- B/S Win/Fail Logic ---
            bs_win = (state["bs_pred"] == latest_bs)
            bs_emoji = "🟠" if state["bs_pred"] == "Big" else "🔵"
            
            # --- Color Win/Fail Logic ---
            color_win = False
            # "Green" आला किंवा "Green & Violet" आला तरीही Green ची प्रेडिक्शन Win होते
            if "Green" in state["color_pred"] and "Green" in latest_color:
                color_win = True
            elif "Red" in state["color_pred"] and "Red" in latest_color:
                color_win = True
            
            # ✅/❌ चिन्हे सेट करणे
            bs_mark = "✅" if bs_win else "❌"
            color_mark = "✅" if color_win else "❌"
            
            # मागील राऊंडचा निकाल
            prev_res_text = (
                f"📏 B/S: *{latest_bs}* {bs_mark}\n"
                f"🎨 Color: *{latest_color}* {color_mark}\n"
                f"🔢 Num: *{latest_number_str}*"
            )
            
            current_bs_level = state["bs_level"]
            current_color_level = state["color_level"]
            
            # B/S Level Update
            if bs_win:
                state["stats"]["bs_win"] += 1
                state["bs_level"] = 1 
                bs_res_status = f"{bs_emoji} {state['bs_pred']} ✅ WIN"
                prev_res_text += f"\n\n🔥🎉 *CONGRATS! B/S WIN!* 🎉🔥"
            else:
                state["stats"]["bs_fail"] += 1
                state["bs_level"] += 1
                bs_res_status = f"{bs_emoji} {state['bs_pred']} ❌ FAIL"
                
            # Color Level Update
            if color_win:
                state["stats"]["color_win"] += 1
                state["color_level"] = 1 
                color_res_status = f"{state['color_pred']} ✅ WIN"
                if not bs_win: prev_res_text += f"\n" 
                prev_res_text += f"\n🎨🎉 *CONGRATS! COLOR WIN!* 🎉🎨"
            else:
                state["stats"]["color_fail"] += 1
                state["color_level"] += 1
                color_res_status = f"{state['color_pred']} ❌ FAIL"
                    
            state["history"].append({
                "trade": state["stats"]["total_trades"], 
                "issue": latest_issue[-4:],
                "bs_level": f"L{current_bs_level}", 
                "bs_pred": state["bs_pred"],
                "bs_res": "[green]✅ WIN[/]" if "WIN" in bs_res_status else "[red]❌ FAIL[/]",
                "color_level": f"L{current_color_level}",
                "color_pred": state["color_pred"].split()[0], # Only shows 'Green' or 'Red'
                "color_res": "[green]✅ WIN[/]" if "WIN" in color_res_status else "[red]❌ FAIL[/]"
            })
            if len(state["history"]) > 3: state["history"].pop(0)

        next_issue_int = int(latest_issue) + 1
        
        # 🚀 ANTI-WAIT SYSTEM for B/S and Num (20th round logic)
        target_issue_str = str(next_issue_int - 20)
        target_record = next((x for x in state["full_history"] if x["issue"] == target_issue_str), None)
        
        if target_record:
            state["bs_pred"] = target_record["bs"]
            state["num_pred"] = target_record["num"]
        elif len(state["full_history"]) >= 20:
            state["bs_pred"] = state["full_history"][19]["bs"]
            state["num_pred"] = state["full_history"][19]["num"]
        else:
            state["bs_pred"] = "WAIT"
            state["num_pred"] = "WAIT"

        # 🎨 New Color Logic: (Skip one round back)
        target_color_issue_str = str(next_issue_int - 3) 
        target_color_record = next((x for x in state["full_history"] if x["issue"] == target_color_issue_str), None)
        
        if target_color_record:
            state["color_pred"] = target_color_record["color"]
        elif len(state["full_history"]) >= 3:
            state["color_pred"] = state["full_history"][2]["color"]
        else:
            state["color_pred"] = "WAIT"

        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int), state["bs_pred"], state["color_pred"], state["num_pred"], state["bs_level"], state["color_level"], prev_res_text)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def worker_30s():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
    while True:
        records = fetch_history_records(url, state_30s)
        if records:
            process_strategy(state_30s, records)
        time.sleep(1) # ३० सेकंदाच्या गेमसाठी १ सेकंदाचा रिफ्रेश रेट अगदी योग्य आहे

def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and state["last_processed_issue"].isdigit() else "Next"
    
    if state["bs_pred"] == "WAIT" or state["color_pred"] == "WAIT":
        ui_text = "[yellow]WAIT (Syncing...)[/]"
        color_text = "WAIT"
        num_text = "WAIT"
    else:
        bs_color = "dark_orange" if state["bs_pred"] == "Big" else "bright_blue"
        ui_text = f"[{bs_color}]{state['bs_pred']}[/] (L{state['bs_level']})"
        color_text = f"[bold]{state['color_pred']}[/] (L{state['color_level']})"
        num_text = f"[bold magenta]{state['num_pred']}[/]"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n"
    panel_text += f"📏 [bold]B/S Pred:[/] {ui_text}\n"
    panel_text += f"🎨 [bold]Color:[/] {color_text}  |  🔢 [bold]Num:[/] {num_text}\n"
    panel_text += f"🕒 [bold]Status:[/] {timer_status}\n\n"
    panel_text += f"📊 [bold]B/S Stats   - W:[/] [green]{state['stats']['bs_win']}[/] | [bold]F:[/] [red]{state['stats']['bs_fail']}[/]\n"
    panel_text += f"🎨 [bold]Color Stats - W:[/] [green]{state['stats']['color_win']}[/] | [bold]F:[/] [red]{state['stats']['color_fail']}[/]\n"
    
    # Table updated to show both B/S Level and Color Level
    hist_table = Table(show_header=True, width=55)
    hist_table.add_column("Iss", justify="center")
    hist_table.add_column("B/S(L)", justify="center")
    hist_table.add_column("B-Res", justify="center")
    hist_table.add_column("Col(L)", justify="center")
    hist_table.add_column("C-Res", justify="center")
    
    if not state["history"]:
        hist_table.add_row("-", "-", "-", "-", "-")
    else:
        for h in state["history"]: 
            hist_table.add_row(
                str(h["issue"]), 
                f"{h['bs_pred'][0]}({h['bs_level']})", 
                str(h["bs_res"]),
                f"{h['color_pred'][:3]}({h['color_level']})",
                str(h["color_res"])
            )
    
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]{state['name']}[/]", border_style="cyan", width=60)

def create_master_ui():
    p_30s = render_game_panel(state_30s)
    return Group(
        Align.center("[bold yellow]🚀 30S SUPERFAST BOT (B/S: 20th | Color: Skip 1)[/bold yellow]\n"),
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
