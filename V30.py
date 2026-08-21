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
TELEGRAM_TOKEN = "8577275461:AAFxaP6wBVTkpl4LrluRUCh0DRZwb4fejmw" 
TARGET_GROUP_ID = "-5202202128"  # <--- चॅनेल/ग्रुपचा आयडी

# 🔐 सिक्रेट पासवर्ड
PASS_30S = "11111"   # ३० सेकंदाच्या गेमसाठी
# ----------------------------------------

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        "bs_pred": None, "bs_level": 1, "bs_active": True, "bs_fails_in_row": 0,
        
        # --- 3-COMBINATION STRATEGY VARIABLES ---
        "mode": "normal",
        "circle_current_target": None, 
        "circle_count": 0,
        # ---------------------------------------
        
        # --- ZONE & REBOUND SIMULATOR VARIABLES ---
        "market_zone": "🟢 SAFE ZONE",
        "rebound_history": [],  # पास्ट १० रिबाउंड्सची लिस्ट
        # ---------------------------------------
        
        "history": [],
        "stats": {"bs_win": 0, "bs_fail": 0, "bs_skip": 0, "total_trades": 0},
        "is_running": False,       
        "active_chat_id": None,   
        "live_records": []
    }

state_30s = create_state("WinGo 30S", "30S")

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

                    # --- START COMMAND ---
                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2:
                            pwd = parts[1]
                            if pwd == PASS_30S:
                                state_30s["is_running"] = True
                                state_30s["active_chat_id"] = chat_id
                                send_telegram_message_direct(chat_id, f"✅ *[30S Strategy] Activated! Continuous Mode Running.*")
                            else:
                                send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    # --- STOP COMMAND ---
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2:
                            pwd = parts[1]
                            if pwd == PASS_30S:
                                state_30s["is_running"] = False
                                send_telegram_message_direct(chat_id, "🛑 *[30S Strategy] Stopped Successfully!*")
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
        if "SKIP" in prev_bs_res: 
            text += f"📏 B/S: ⏸️ *SKIPPED (Waiting for Trend)*\n"
        else:
            text += f"📏 B/S: *{prev_bs_res}*\n"
            if "WIN" in prev_bs_res: 
                text += f"\n🔥🎉 *CONGRATS! WIN!* 🎉🔥\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Prediction For Ticket:* {issue}\n\n"
    
    if state["bs_active"]:
        bs_pred_text = "🟠 Big" if bs_pred == "Big" else "🔵 Small"
        mode_text = ""
        if state["mode"] == "2-circle":
            mode_text = "(🔄 2-Circle Mode)"
        elif state["mode"] == "flip":
            mode_text = "(🔁 Flip Mode)"
            
        text += f"📏 *B/S Pred:* {bs_pred_text} (L{bs_level}) {mode_text}\n\n"
    else:
        text += f"📏 *Prediction:* ⏸️ *WAIT FOR PATTERN*\n"
        text += f"⚠️ *(Pending Level: L{bs_level})*\n\n"
        
    # =========================================================
    # ⚠️ SIMULATOR REPORT (Zone & Past Rebounds) ⚠️
    # =========================================================
    text += f"➖➖ *SIMULATOR REPORT* ➖➖\n"
    text += f"🌀 *Zone:* {state['market_zone']}\n"
    text += f"📈 *Past 10 Rebounds:* {state['rebound_history']}\n"
    text += f"➖➖➖➖➖➖➖➖➖➖➖➖\n"
    # =========================================================
    
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
        # 🛡️ API CACHE FIX (डबल मेसेज येणे कायमचे बंद करण्यासाठी) 🛡️
        # =========================================================
        if state["last_processed_issue"].isdigit() and latest_issue.isdigit():
            if int(latest_issue) <= int(state["last_processed_issue"]):
                return False  # जुना किंवा सेम तिकीट नंबर आल्यास दुर्लक्ष करेल
        # =========================================================

        bs_res_status = "-"
        state["stats"]["total_trades"] += 1
        
        if state["bs_active"]:
            bs_win = (state["bs_pred"] == latest_bs)
            bs_emoji = "🟠" if state["bs_pred"] == "Big" else "🔵"
            if bs_win:
                state["stats"]["bs_win"] += 1
                reached_lvl = state["bs_level"]
                
                # पास्ट रिबाउंड्स सेव्ह करणे (जास्तीत जास्त १०)
                state["rebound_history"].append(reached_lvl)
                if len(state["rebound_history"]) > 10:
                    state["rebound_history"].pop(0)
                
                # =========================================================
                # 🚀 EXACT ZONE LOGIC (State Machine) 🚀
                # =========================================================
                if 1 <= reached_lvl <= 4:
                    state["market_zone"] = "🟢 SAFE ZONE"
                elif 5 <= reached_lvl <= 6:
                    state["market_zone"] = f"⚠️ DIVERGENCE ZONE (Rebound at L{reached_lvl})"
                elif reached_lvl >= 7:
                    state["market_zone"] = f"🔴 DANGER ZONE (Rebound at L{reached_lvl})"
                # =========================================================
                
                state["bs_level"] = 1 
                state["bs_fails_in_row"] = 0 
                state["mode"] = "normal"  
                state["circle_count"] = 0
                bs_res_status = f"{bs_emoji} {state['bs_pred']} ✅ WIN"
            else:
                state["stats"]["bs_fail"] += 1
                state["bs_level"] += 1
                state["bs_fails_in_row"] += 1 
                
                # हरत असताना चालू लेव्हलनुसार झोन अपडेट करणे
                if state["bs_level"] >= 7:
                    state["market_zone"] = f"🔴 DANGER ZONE (Active L{state['bs_level']})"
                elif state["bs_level"] >= 5:
                    state["market_zone"] = f"⚠️ DIVERGENCE ZONE (Active L{state['bs_level']})"
                    
                bs_res_status = f"{bs_emoji} {state['bs_pred']} ❌ FAIL"
        else:
            state["stats"]["bs_skip"] += 1
            bs_res_status = "SKIP"
            if latest_bs == prev_bs:
                state["bs_active"] = True
                state["bs_fails_in_row"] = 0 
                
        bs_disp_pred = state["bs_pred"] if state["bs_active"] else "[yellow]WAIT[/]"
        bs_disp_lvl = f"L{state['bs_level']}" if state["bs_active"] else f"L{state['bs_level']}(Hold)"
        
        state["history"].append({
            "trade": state["stats"]["total_trades"], "issue": latest_issue[-4:],
            "bs_level": bs_disp_lvl, "bs_pred": bs_disp_pred,
            "bs_res": "[green]WIN[/]" if "WIN" in bs_res_status else ("[yellow]SKIP[/]" if "SKIP" in bs_res_status else "[red]FAIL[/]")
        })
        if len(state["history"]) > 3: state["history"].pop(0)

        # =======================================================
        # 🚀 3-COMBINATION STRATEGY LOGIC 🚀
        # =======================================================
        if state["mode"] == "normal":
            if state["bs_level"] >= 4: 
                state["mode"] = "2-circle"
                state["circle_current_target"] = latest_bs
                state["circle_count"] = 1
                state["bs_pred"] = state["circle_current_target"]
            else:
                state["bs_pred"] = latest_bs
                
        elif state["mode"] == "2-circle":
            if state["bs_level"] >= 7:
                state["mode"] = "flip"
                # L6 फेल गेल्यावर लगेच विरुद्ध (Flip) प्रेडिक्शन देणे
                state["bs_pred"] = "Small" if state["bs_pred"] == "Big" else "Big"
            else:
                state["circle_count"] += 1
                if state["circle_count"] > 2:
                    state["circle_current_target"] = "Small" if state["circle_current_target"] == "Big" else "Big"
                    state["circle_count"] = 1
                state["bs_pred"] = state["circle_current_target"]
                
        elif state["mode"] == "flip":
            # L7, L8 आणि त्यापुढे प्रत्येक वेळी विरुद्ध दिशा (Flip)
            state["bs_pred"] = "Small" if state["bs_pred"] == "Big" else "Big"
        # =======================================================

        next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
        
        if state["is_running"]:
            send_telegram_signal(state, next_issue, state["bs_pred"], state["bs_level"], bs_res_status)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def worker_30s():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
    while True:
        data = fetch_data(url)
        if data:
            records = extract_records(data)
            process_strategy(state_30s, records)
        time.sleep(2) 

def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and state["last_processed_issue"].isdigit() else "Next"
    bs_color = "dark_orange" if state["bs_pred"] == "Big" else "bright_blue"
    
    ui_text = f"[{bs_color}]{state['bs_pred']}[/] (L{state['bs_level']})" if state["bs_active"] else f"[yellow]WAIT[/] (Pending L{state['bs_level']})"
    
    if state["mode"] == "2-circle":
        ui_text += " [bold magenta]🔄 2-Circle[/]"
    elif state["mode"] == "flip":
        ui_text += " [bold yellow]🔁 Flip[/]"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    zone_color = "green" if "SAFE" in state["market_zone"] else ("red" if "DANGER" in state["market_zone"] else "yellow")
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n📏 [bold]Pred:[/] {ui_text}\n"
    panel_text += f"🌀 [bold]Zone:[/] [{zone_color}]{state['market_zone']}[/]\n"
    panel_text += f"📈 [bold]Rebounds:[/] {state['rebound_history']}\n"
    panel_text += f"🕒 [bold]Status:[/] {timer_status}\n\n"
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
    p_30s = render_game_panel(state_30s)
    return Group(
        Align.center("[bold yellow]🚀 30S BOT (3-Combination Strategy: Trend -> 2-Circle -> Flip)[/bold yellow]\n"),
        Align.center(p_30s)
    )

if __name__ == "__main__":
    t_list = threading.Thread(target=telegram_listener, daemon=True)
    t_30s = threading.Thread(target=worker_30s, daemon=True)
    
    t_list.start(); t_30s.start()

    with Live(create_master_ui(), console=console, refresh_per_second=2, screen=False) as live:
        while True:
            live.update(create_master_ui())
            time.sleep(1)
