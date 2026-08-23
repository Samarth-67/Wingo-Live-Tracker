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
TARGET_GROUP_ID = "-5407201060"  # <--- तुमचा नवीन अपडेट केलेला ग्रुप आयडी

# 🔐 सिक्रेट पासवर्ड्स
PASS_1M = "22222"   # १ मिनिटाच्या गेमसाठी
# ----------------------------------------

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        "bs_pred": None, "bs_level": 1, "bs_active": True, "bs_fails_in_row": 0,
        
        # --- NEW STRATEGY VARIABLES ---
        "l2_pred": None, # लेव्हल २ चे प्रेडिक्शन सेव्ह करण्यासाठी
        # ---------------------------------------
        
        "history": [],
        "stats": {"bs_win": 0, "bs_fail": 0, "bs_skip": 0, "total_trades": 0},
        "is_running": False,       
        "active_chat_id": None,   
        "live_records": []
    }

state_1m = create_state("WinGo 1M", "1M")

def send_telegram_message_direct(chat_id, text):
    if not chat_id: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except Exception:
        pass

def telegram_listener():
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

                    # --- START COMMANDS ---
                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2:
                            pwd = parts[1]
                            if pwd == PASS_1M:
                                state_1m["is_running"] = True
                                state_1m["active_chat_id"] = chat_id
                                send_telegram_message_direct(chat_id, f"✅ *[1M Strategy] Activated! Signals will be sent to your target group.*")
                            else:
                                send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    # --- STOP COMMANDS ---
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

def send_telegram_signal(state, issue, bs_pred, bs_level, prev_bs_res=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    game_name = state["name"]
    text = f"🚀 *VSR {game_name} Trend Follower* 🚀\n\n"
    
    if state["stats"]["total_trades"] > 0 and prev_bs_res:
        text += f"🔄 *Last Trade Result:*\n"
        if "SKIP" in prev_bs_res: text += f"📏 B/S: ⏸️ *SKIPPED (Waiting for Trend)*\n"
        else:
            text += f"📏 B/S: *{prev_bs_res}*\n"
            if "WIN" in prev_bs_res: text += f"\n🔥🎉 *CONGRATS! WIN!* 🎉🔥\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *New Issue:* {issue}\n\n"
    
    if state["bs_active"]:
        bs_pred_text = "🟠 Big" if bs_pred == "Big" else "🔵 Small"
        text += f"📏 *Prediction:* *{bs_pred_text}*\n"
        text += f"🎯 *Level:* L{bs_level}\n\n"
    else:
        # जर सलग 4 वेळा फेल झाले असेल तर Stop Loss मेसेज
        if state["bs_fails_in_row"] >= 4:
            text += f"🛑 *TRADING STOP! (Level 4 Failed)* 🛑\n"
            text += f"⏳ _Waiting for Circle Match to restart from Level 5..._\n\n"
        else:
            text += f"📏 *Prediction:* ⏸️ *WAIT FOR PATTERN*\n\n"
    
    send_telegram_message_direct(target_chat_id, text)

def fetch_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://draw.ar-lottery01.com/",
    }
    params = {"ts": int(time.time() * 1000)}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200: return response.json()
    except Exception:
        return None
    return None

def extract_records(data):
    if not data: return []
    if "data" in data and isinstance(data["data"], list): return data["data"]
    elif "list" in data and isinstance(data["list"], list): return data["list"]
    elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: return data["data"]["list"]
    return []

def process_strategy(state, records):
    if not records or len(records) < 2: return False
    state["live_records"] = records[:5]
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    prev_item = records[1]
    prev_number_str = str(prev_item.get("number") or prev_item.get("drawNumber") or "-")
    
    if latest_number_str.isdigit() and prev_number_str.isdigit():
        number = int(latest_number_str)
        latest_bs = "Big" if number >= 5 else "Small"
        prev_num = int(prev_number_str)
        prev_bs = "Big" if prev_num >= 5 else "Small"
    else:
        return False

    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        state["bs_pred"] = latest_bs
        next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
        if state["is_running"]:
            send_telegram_signal(state, next_issue, state["bs_pred"], state["bs_level"])
        return True

    if state["last_processed_issue"] != latest_issue:
        # =========================================================
        # 🛡️ API CACHE FIX 
        # =========================================================
        if state["last_processed_issue"].isdigit() and latest_issue.isdigit():
            if int(latest_issue) <= int(state["last_processed_issue"]):
                return False  
        # =========================================================

        bs_res_status = "-"
        state["stats"]["total_trades"] += 1
        
        # --- आधी जुन्या ट्रेडचा निकाल चेक करणे ---
        if state["bs_active"]:
            bs_win = (state["bs_pred"] == latest_bs)
            bs_emoji = "🟠" if state["bs_pred"] == "Big" else "🔵"
            if bs_win:
                state["stats"]["bs_win"] += 1
                state["bs_level"] = 1 # जिंकल्यावर पुन्हा लेव्हल १ वर येईल
                state["bs_fails_in_row"] = 0 
                bs_res_status = f"{bs_emoji} {state['bs_pred']} ✅ WIN"
            else:
                state["stats"]["bs_fail"] += 1
                state["bs_level"] += 1
                state["bs_fails_in_row"] += 1 
                bs_res_status = f"{bs_emoji} {state['bs_pred']} ❌ FAIL"
                
                # 🛑 STOP LOSS: फक्त लेव्हल ४ फेल झाल्यावरच थांबायचे आहे (म्हणजे bs_level 5 झाल्यावर).
                # ५ नंतरच्या लेव्हलसाठी थांबणार नाही. 
                if state["bs_level"] == 5:
                    state["bs_active"] = False
        else:
            state["stats"]["bs_skip"] += 1
            bs_res_status = "SKIP"
            # 🔄 जर बॉट थांबला असेल, आणि Circle ला Circle मॅच झाला (Big-Big किंवा Small-Small)
            if latest_bs == prev_bs:
                state["bs_active"] = True
                state["bs_fails_in_row"] = 0 
                state["bs_level"] = 5 # <--- लेव्हल १ ऐवजी आता थेट लेव्हल ५ पासून सुरू होईल
                
        bs_disp_pred = state["bs_pred"] if state["bs_active"] else "[yellow]WAIT[/]"
        bs_disp_lvl = f"L{state['bs_level']}" if state["bs_active"] else f"L{state['bs_level']}(Hold)"
        
        state["history"].append({
            "trade": state["stats"]["total_trades"], "issue": latest_issue[-4:],
            "bs_level": bs_disp_lvl, "bs_pred": bs_disp_pred,
            "bs_res": "[green]WIN[/]" if "WIN" in bs_res_status else ("[yellow]SKIP[/]" if "SKIP" in bs_res_status else "[red]FAIL[/]")
        })
        if len(state["history"]) > 3: state["history"].pop(0)

        # =======================================================
        # 🚀 STRATEGY LOGIC (TREND -> L4 takes L2's Prediction -> Continuous L5+) 🚀
        # =======================================================
        if state["bs_active"]:
            if state["bs_level"] <= 3 or state["bs_level"] >= 5:
                # Level 1, 2, 3 आणि Level 5 किंवा त्यापुढील सर्व लेव्हल्ससाठी Trend Follow
                state["bs_pred"] = latest_bs
                
                # जर Level 2 चे प्रेडिक्शन देत असू, तर ते सेव्ह करून ठेवणे (Level 4 साठी)
                if state["bs_level"] == 2:
                    state["l2_pred"] = state["bs_pred"]
                    
            elif state["bs_level"] == 4:
                # Level 4 साठी Level 2 चे सेव्ह केलेले प्रेडिक्शन वापरणे
                state["bs_pred"] = state["l2_pred"]
        # =======================================================

        next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
        
        if state["is_running"]:
            send_telegram_signal(state, next_issue, state["bs_pred"], state["bs_level"], bs_res_status)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def worker_1m():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
    while True:
        data = fetch_data(url)
        if data:
            records = extract_records(data)
            process_strategy(state_1m, records)
        time.sleep(5)

def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and state["last_processed_issue"].isdigit() else "Next"
    bs_color = "dark_orange" if state["bs_pred"] == "Big" else "bright_blue"
    
    ui_text = f"[{bs_color}]{state['bs_pred']}[/] (L{state['bs_level']})" if state["bs_active"] else f"[yellow]WAIT[/] (Pending Circle Match)"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n📏 [bold]Pred:[/] {ui_text}\n🕒 [bold]Status:[/] {timer_status}\n\n"
    panel_text += f"📊 [bold]W:[/] [green]{state['stats']['bs_win']}[/] | [bold]F:[/] [red]{state['stats']['bs_fail']}[/] | [bold]S:[/] [yellow]{state['stats']['bs_skip']}[/]\n"
    
    hist_table = Table(show_header=False, width=40)
    hist_table.add_column("Issue", justify="center")
    hist_table.add_column("Level", justify="center")
    hist_table.add_column("Pred", justify="center")
    hist_table.add_column("Res", justify="center")
    
    if not state["history"]:
        hist_table.add_row("-", "-", "-", "-")
    else:
        for h in state["history"]: 
            hist_table.add_row(str(h["issue"]), str(h["bs_level"]), str(h["bs_pred"]), str(h["bs_res"]))
    
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]{state['name']}[/]", border_style="cyan", width=45)

def create_master_ui():
    p_1m = render_game_panel(state_1m)
    return Group(
        Align.center("[bold yellow]🚀 1 MINUTE BOT (Trend -> L4=L2 -> Continuous L5+)[/bold yellow]\n"),
        Align.center(p_1m)
    )

if __name__ == "__main__":
    t_list = threading.Thread(target=telegram_listener, daemon=True)
    t_1m = threading.Thread(target=worker_1m, daemon=True)
    
    t_list.start(); t_1m.start()

    with Live(create_master_ui(), console=console, refresh_per_second=2, screen=False) as live:
        while True:
            live.update(create_master_ui())
            time.sleep(1)
