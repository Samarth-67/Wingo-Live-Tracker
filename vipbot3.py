import os
import time
import threading
import requests
import re
from rich.table import Table
from rich.console import Console, Group
from rich.panel import Panel
from rich.align import Align
from rich.live import Live

console = Console()

# --- 🚀 NEW TELEGRAM BOT CONFIGURATION 🚀 ---
TELEGRAM_TOKEN = "8902202809:AAF126HOa2w4qpardCrA1cqs4vEsGUrzfAY"
TARGET_GROUP_ID = "-5356408789"  # <--- नवीन चॅनेल/ग्रुपचा आयडी

# 🔐 सिक्रेट पासवर्ड
PASS_30S = "11111"  

# 🔗 दमन रजिस्ट्रेशन लिंक (ही लिंक प्रत्येक टेलिग्राम मेसेजमध्ये खाली येईल)
DAMAN_REG_LINK = "https://damangames.in/" # <--- इथे तुमची दमनची खरी लिंक टाका
# ----------------------------------------

# ⚡ फास्ट इंटरनेट कनेक्शनसाठी Session
api_session = requests.Session()

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        
        # 🔄 4-Level Block & Trend Strategy System
        "wait_for_trigger": True,
        "block_base_level": 1,  # 1 -> 5 -> 9 -> 13 ...
        
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
            api_session.post(url, json={
                "chat_id": chat_id, 
                "text": text, 
                "parse_mode": "Markdown", 
                "disable_web_page_preview": True,
                "link_preview_options": {"is_disabled": True}  # 🚫 लिंकचे डिस्क्रिप्शन/प्रीव्ह्यू बंद करण्यासाठी
            }, timeout=3)
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
                            send_telegram_message_direct(chat_id, f"✅ *[Trend & 4-Level Bot]* Activated! Live Prediction is ON.\n\n🔗 *Register:* {DAMAN_REG_LINK}")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                            
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *Bot Stopped Successfully!*")
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
    text += f"⚙️ *Strategy:* Follow Last Trend (4-Level Block)\n\n"
    
    if prev_res_text:
        text += f"📊 *मागील निकाल:*\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Next Issue:* `{issue}`\n\n"
    
    if state["wait_for_trigger"] or state["pred_bs"] == "WAIT":
        text += f"⏳ Waiting for Trigger (Big-Big or Small-Small)...\n\n"
    else:
        icon = "🟠 Big" if state["pred_bs"] == "Big" else "🔵 Small"
        color_icon = "🟢 Green" if state["pred_color"] == "Green" else "🔴 Red"
        nums_str = ", ".join(map(str, state["pred_nums"]))
        text += f"🎯 *Prediction:* *{icon}* | *{color_icon}* | 🔢 *{nums_str}*\n"
        text += f"💰 *Level:* L{state['level']} (Block Base: L{state['block_base_level']})\n\n"
        
    text += f"💡 _Bet according to your level._\n\n"
    
    # 🔗 फक्त लिंक पाठवली जाईल (कोणतेही एक्स्ट्रा डिस्क्रिप्टिव्ह टेक्स्ट नसेल)
    text += f"🔗 *Register Link:* {DAMAN_REG_LINK}"
    
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
        for p in [2, 3]:
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

def extract_digits(s):
    digits = ''.join(filter(str.isdigit, str(s)))
    return int(digits) if digits else 0

def update_predictions(state, next_issue_int, latest_color):
    if state["wait_for_trigger"]:
        if len(state["full_history"]) >= 2:
            last_2 = [x["bs"] for x in state["full_history"][:2]]
            if last_2[0] == last_2[1]:
                state["wait_for_trigger"] = False
                state["level"] = state["block_base_level"]
        
        if state["wait_for_trigger"]:
            state["pred_bs"] = "WAIT"
            state["pred_color"] = "WAIT"
            state["pred_nums"] = []
            return

    if len(state["full_history"]) >= 1:
        state["pred_bs"] = state["full_history"][0]["bs"]
    else:
        state["pred_bs"] = "WAIT"

    if state["pred_bs"] != "WAIT":
        state["pred_color"] = "Red" if latest_color == "Green" else "Green"
        
        if state["pred_bs"] == "Big" and state["pred_color"] == "Red":
            state["pred_nums"] = [8, 6]
        elif state["pred_bs"] == "Small" and state["pred_color"] == "Green":
            state["pred_nums"] = [1, 3]
        elif state["pred_bs"] == "Big" and state["pred_color"] == "Green":
            state["pred_nums"] = [7, 9]
        elif state["pred_bs"] == "Small" and state["pred_color"] == "Red":
            state["pred_nums"] = [2, 4]
        else:
            state["pred_nums"] = []

def process_strategy(state, records):
    if not records: return False
    state["live_records"] = records[:5]
    
    existing_issues = {x["issue"] for x in state["full_history"]}
    added_new = False
    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss and num_str.isdigit() and iss not in existing_issues:
            n_val = int(num_str)
            state["full_history"].append({
                "issue": iss, 
                "bs": "Big" if n_val >= 5 else "Small", 
                "color": "Green" if n_val in [1, 3, 5, 7, 9] else "Red",
                "num": num_str
            })
            existing_issues.add(iss)
            added_new = True
                
    state["full_history"].sort(key=lambda x: extract_digits(x["issue"]), reverse=True)
    state["full_history"] = state["full_history"][:60] 

    if len(state["full_history"]) == 0:
        return False

    latest_item = state["full_history"][0]
    latest_issue = latest_item["issue"]
    latest_number_str = latest_item["num"]
    latest_bs = latest_item["bs"]
    latest_color = latest_item["color"]

    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        next_issue_int = extract_digits(latest_issue) + 1
        update_predictions(state, next_issue_int, latest_color)
        if state["is_running"]: send_telegram_signal(state, str(next_issue_int))
        return True

    if state["last_processed_issue"] != latest_issue:
        if extract_digits(latest_issue) <= extract_digits(state["last_processed_issue"]): return False  

        prev_res_text = f"🎯 Result: *{latest_number_str}* ({latest_bs} | {latest_color})\n"
        res_status = "-"
        current_logged_level = state["level"]

        if not state["wait_for_trigger"] and state["pred_bs"] != "WAIT":
            state["stats"]["total_trades"] += 1
            if state["pred_bs"] == latest_bs:
                state["stats"]["win"] += 1
                res_status = f"{state['pred_bs']} ✅ WIN"
                prev_res_text += f"🔹 Match: ✅ WIN\n"
                state["level"] = 1
                state["block_base_level"] = 1
            else:
                state["stats"]["fail"] += 1
                res_status = f"{state['pred_bs']} ❌ FAIL"
                prev_res_text += f"🔹 Match: ❌ FAIL\n"
                state["level"] += 1

                if state["level"] > state["block_base_level"] + 3:
                    prev_res_text += f"⚠️ Block of 4 Levels Failed! Waiting for Trigger..."
                    state["block_base_level"] += 4
                    state["wait_for_trigger"] = True
                    state["pred_bs"] = "WAIT"
                    if state["is_running"]:
                        send_telegram_message_direct(TARGET_GROUP_ID, f"🚨 *4 Levels Completed/Failed!* Bot paused. Waiting for Big-Big / Small-Small trigger to start next round at L{state['block_base_level']}...\n\n🔗 *Register Link:* {DAMAN_REG_LINK}")
                
        state["history"].append({
            "issue": str(extract_digits(latest_issue))[-4:],
            "pred": state["pred_bs"] if not state["wait_for_trigger"] else "WAIT",
            "level": f"L{current_logged_level}", 
            "res": "[green]✅ WIN[/]" if "WIN" in res_status else ("[red]❌ FAIL[/]" if "FAIL" in res_status else "-")
        })
        if len(state["history"]) > 4: state["history"].pop(0)

        next_issue_int = extract_digits(latest_issue) + 1
        update_predictions(state, next_issue_int, latest_color)

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
        try:
            records = fetch_history_records(url, state_30s)
            if records:
                process_strategy(state_30s, records)
        except Exception:
            pass
        time.sleep(1)

def render_game_panel(state):
    next_iss = str(extract_digits(state["last_processed_issue"]) + 1) if state["last_processed_issue"] else "Next"
    
    if state["wait_for_trigger"]:
        ui_text = "[yellow]WAITING FOR TRIGGER (2 Same)[/]"
    else:
        s_color = "dark_orange" if state["pred_bs"] == "Big" else "bright_blue"
        c_color = "green" if state["pred_color"] == "Green" else "red"
        ui_text = f"[{s_color}]{state['pred_bs']}[/] | [{c_color}]{state['pred_color']}[/] | L{state['level']} (Base: L{state['block_base_level']})"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n"
    panel_text += f"⚙️ [bold]Strategy:[/] Follow Last Trend (4-Level Progression)\n"
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
            
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]{state['name']} - Trend 4-Level Bot[/]", border_style="cyan", width=78)

def create_master_ui():
    p_30s = render_game_panel(state_30s)
    return Group(
        Align.center("[bold yellow]🚀 30S TREND 4-LEVEL PROGRESSION BOT[/bold yellow]\n"),
        Align.center(p_30s)
    )

if __name__ == "__main__":
    t_list = threading.Thread(target=telegram_listener, daemon=True)
    t_30s = threading.Thread(target=worker_30s, daemon=True)
    
    t_list.start()
    t_30s.start()

    with Live(create_master_ui(), console=console, refresh_per_second=4, screen=False) as live:
        while True:
            live.update(create_master_ui())
            time.sleep(0.5)
