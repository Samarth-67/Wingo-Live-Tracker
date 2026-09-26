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

# --- 🚀 TELEGRAM BOT CONFIGURATION (YOUR ORIGINAL SETTINGS) 🚀 ---
TELEGRAM_TOKEN = "8886107397:AAHENOebGnrupxvGKqKh5cKC3SmujXJOV3w"
TARGET_GROUP_ID = "-1004370895879"  

# 🔐 सिक्रेट पासवर्ड
PASS_1M = "12345"  
# -----------------------------------------------------------

# ⚡ फास्ट इंटरनेट कनेक्शनसाठी Session
api_session = requests.Session()

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        
        # 🔄 New Data: Weightage System
        "wait_for_trigger": True, # Will wait until 20 records are collected
        "scores": {"Red": 0, "Green": 0, "Big": 0, "Small": 0},
        
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

state_1m = create_state("WinGo 1M Weightage", "1M")

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
                        if len(parts) == 2 and parts[1] == PASS_1M:
                            state_1m["is_running"] = True
                            state_1m["active_chat_id"] = chat_id
                            send_telegram_message_direct(chat_id, f"✅ *[1M Weightage Bot]* Activated! Live Prediction based on 20-Round Stats is ON.")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                            
                    # --- STOP COMMAND ---
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_1M:
                            state_1m["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *[1M Bot] Stopped Successfully!*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")

                    # --- RESET COMMAND ---
                    elif text.startswith("/reset"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_1M:
                            state_1m["level"] = 1
                            state_1m["stats"]["win"] = 0
                            state_1m["stats"]["fail"] = 0
                            state_1m["stats"]["total_trades"] = 0
                            send_telegram_message_direct(chat_id, "🔄 *Bot Stats & Level Reset Successfully!*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, prev_res_text=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    game_name = state["name"]
    
    text = f"🚀 *{game_name} Signal* 🚀\n"
    text += f"📊 *Strategy:* 20-Round Weightage Data\n\n"
    
    if prev_res_text:
        text += f"📉 *मागील निकाल (Previous Result):*\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Next Issue:* `{issue}`\n\n"
    
    if state["wait_for_trigger"] or state["pred_bs"] == "WAIT":
        text += f"⏳ Collecting Data... (Need 20 records)\n\n"
    else:
        # Show calculated scores so you know WHY the bot gave this signal
        sc = state["scores"]
        text += f"🧮 *Weightage Scores:*\n"
        text += f"🔴 Red: {sc['Red']} | 🟢 Green: {sc['Green']}\n"
        text += f"🟠 Big: {sc['Big']} | 🔵 Small: {sc['Small']}\n\n"

        icon = "🟠 Big" if state["pred_bs"] == "Big" else "🔵 Small"
        color_icon = "🟢 Green" if state["pred_color"] == "Green" else "🔴 Red"
        nums_str = ", ".join(map(str, state["pred_nums"]))
        
        text += f"🎯 *Final Prediction:* \n"
        text += f"➡️ *{icon}* | *{color_icon}*\n"
        text += f"🔢 Numbers: *{nums_str}*\n"
        text += f"💰 *Level:* L{state['level']}\n\n"
        
    text += f"💡 _Auto Prediction Bot is ON._"
        
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
        
    if len(all_records) <= 20:
        for p in [2]:
            try:
                params = {"pageSize": 20, "pageNo": p, "ts": int(time.time() * 1000)}
                response = api_session.get(url, headers=headers, params=params, timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and isinstance(data["data"], list): all_records.extend(data["data"])
                    elif "list" in data and isinstance(data["list"], list): all_records.extend(data["list"])
                    elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: all_records.extend(data["data"]["list"])
            except Exception:
                pass
            
    return all_records

def update_predictions(state):
    history = state["full_history"]
    
    # 20 रेकॉर्ड्सची वाट पाहणे
    if len(history) < 20:
        state["wait_for_trigger"] = True
        state["pred_bs"] = "WAIT"
        state["pred_color"] = "WAIT"
        return

    state["wait_for_trigger"] = False

    # स्कोर्स रिसेट करा
    sc_red = sc_green = sc_big = sc_small = 0

    # मागील 20 रेकॉर्ड्स लूप करून वेटेज लावणे
    for i in range(20):
        record = history[i] # i=0 म्हणजे सर्वात अलीकडील
        color = record["color"]
        bs = record["bs"]

        # वेटेज पॉइंट्स (Weightage Allocation)
        if i < 5:        # डाव 1 ते 5 (Most Recent)
            weight = 3
        elif i < 10:     # डाव 6 ते 10
            weight = 2
        else:            # डाव 11 ते 20
            weight = 1

        # कलर स्कोर कॅल्क्युलेशन
        if color == "Red": sc_red += weight
        elif color == "Green": sc_green += weight
        
        # साईज स्कोर कॅल्क्युलेशन
        if bs == "Big": sc_big += weight
        elif bs == "Small": sc_small += weight

    # स्कोर्स सेव करणे (UI आणि Telegram साठी)
    state["scores"] = {"Red": sc_red, "Green": sc_green, "Big": sc_big, "Small": sc_small}

    # --- प्रेडिक्शन ठरवणे (ज्याचा स्कोर जास्त तो जिंकणार) ---
    pred_color = "Red" if sc_red >= sc_green else "Green"
    pred_bs = "Big" if sc_big >= sc_small else "Small"

    state["pred_color"] = pred_color
    state["pred_bs"] = pred_bs
    
    # --- नंबर मॅपिंग (Two-Tier Filter) ---
    if pred_bs == "Big" and pred_color == "Red":
        state["pred_nums"] = [6, 8]
    elif pred_bs == "Small" and pred_color == "Green":
        state["pred_nums"] = [1, 3]
    elif pred_bs == "Big" and pred_color == "Green":
        state["pred_nums"] = [7, 9]
    elif pred_bs == "Small" and pred_color == "Red":
        state["pred_nums"] = [2, 4]
    else:
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

    # नवीन डेटाबेस अपडेट करणे
    existing_issues = {x["issue"] for x in state["full_history"]}
    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss.isdigit() and num_str.isdigit() and iss not in existing_issues:
            n_val = int(num_str)
            state["full_history"].append({
                "issue": iss, 
                "bs": "Big" if n_val >= 5 else "Small", 
                "color": "Green" if n_val in [1, 3, 5, 7, 9] else "Red",
                "num": num_str
            })
            existing_issues.add(iss)
                
    state["full_history"].sort(key=lambda x: int(x["issue"]), reverse=True)
    state["full_history"] = state["full_history"][:60] 

    # Initial Run
    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        next_issue_int = int(latest_issue) + 1
        update_predictions(state)
        if state["is_running"]: send_telegram_signal(state, str(next_issue_int))
        return True

    # New Issue Arrived
    if state["last_processed_issue"] != latest_issue:
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        prev_res_text = f"🎯 Result: *{latest_number_str}* ({latest_bs} | {latest_color})\n"
        res_status = "-"
        current_logged_level = state["level"]

        # --- निकाल तपासणे (Level Management based on Size B/S) ---
        if not state["wait_for_trigger"] and state["pred_bs"] != "WAIT":
            state["stats"]["total_trades"] += 1
            if state["pred_bs"] == latest_bs:
                state["stats"]["win"] += 1
                res_status = f"{state['pred_bs']} ✅ WIN"
                prev_res_text += f"🔹 B/S Match: ✅ WIN\n"
                state["level"] = 1
            else:
                state["stats"]["fail"] += 1
                res_status = f"{state['pred_bs']} ❌ FAIL"
                prev_res_text += f"🔹 B/S Match: ❌ FAIL\n"
                state["level"] += 1

            # 7th लेव्हल फेल झाल्यावर रिसेट
            if state["level"] > 7:
                prev_res_text += f"⚠️ Max Level Reached! Resetting to L1..."
                state["level"] = 1
                
        state["history"].append({
            "issue": latest_issue[-4:],
            "pred": state["pred_bs"] if not state["wait_for_trigger"] else "WAIT",
            "level": f"L{current_logged_level}", 
            "res": "[green]✅ WIN[/]" if "WIN" in res_status else ("[red]❌ FAIL[/]" if "FAIL" in res_status else "-")
        })
        if len(state["history"]) > 4: state["history"].pop(0)

        next_issue_int = int(latest_issue) + 1
        update_predictions(state)

        if state["is_running"]:
            if prev_res_text == f"🎯 Result: *{latest_number_str}* ({latest_bs} | {latest_color})\n":
                prev_res_text = None 
            send_telegram_signal(state, str(next_issue_int), prev_res_text)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def worker_1m():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
    while True:
        records = fetch_history_records(url, state_1m)
        if records:
            process_strategy(state_1m, records)
        time.sleep(2)

def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and state["last_processed_issue"].isdigit() else "Next"
    
    if state["wait_for_trigger"]:
        ui_text = "[yellow]COLLECTING DATA (Wait 20 Rounds)[/]"
    else:
        s_color = "dark_orange" if state["pred_bs"] == "Big" else "bright_blue"
        c_color = "green" if state["pred_color"] == "Green" else "red"
        ui_text = f"[{s_color}]{state['pred_bs']}[/] | [{c_color}]{state['pred_color']}[/] | L{state['level']}"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    sc = state["scores"]
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n"
    panel_text += f"📊 [bold]Weightage Scores:[/] \n[red]R:{sc['Red']}[/] | [green]G:{sc['Green']}[/] | [dark_orange]B:{sc['Big']}[/] | [bright_blue]S:{sc['Small']}[/]\n"
    panel_text += f"📏 [bold]Prediction:[/] {ui_text}\n"
    panel_text += f"🕒 [bold]Status:[/] {timer_status} | Stats - W: [green]{state['stats']['win']}[/] F: [red]{state['stats']['fail']}[/]\n\n"
    
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
            
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]{state['name']}[/]", border_style="cyan", width=78)

def create_master_ui():
    p_1m = render_game_panel(state_1m)
    return Group(
        Align.center("[bold yellow]🚀 1M DATA ANALYTICS & WEIGHTAGE BOT[/bold yellow]\n"),
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
