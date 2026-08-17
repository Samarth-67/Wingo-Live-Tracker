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
# ---------------- TELEGRAM BOT CONFIGURATION ----------------
TELEGRAM_BOT_TOKEN = "8886107397:AAHENOebGnrupxvGKqKh5cKC3SmujXJOV3w"
SECRET_PASSWORD = "12345"
TARGET_CHANNEL_ID = "-1004370895879"  # <--- तुझा चॅनेल आयडी
# ------------------------------------------------------------

# 🔐 सिक्रेट पासवर्ड्स
PASS_30S = "11111"  # ३० सेकंदाच्या गेमसाठी
PASS_1M = "12345"   # १ मिनिटाच्या गेमसाठी (नवीन बदल)
# ----------------------------------------

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        
        # --- Big/Small Variables ---
        "bs_pred": None, "bs_level": 1, "bs_active": True, "bs_fails_in_row": 0,
        "mode": "normal",
        "circle_current_target": None, 
        "circle_count": 0,
        
        # --- AI Violet Strategy Variables ---
        "violet_gap": 0,
        "full_history": [],
        "hot_gap": None,
        "hot_number": None,
        "violet_alert_active": False,   
        "violet_alert_type": "None",      
        "violet_level": 0,              
        "violet_mega_win": False,
        "last_violet_res": None,
        
        # --- System Variables ---
        "history": [],
        "stats": {"bs_win": 0, "bs_fail": 0, "bs_skip": 0, "total_trades": 0},
        "active_until": 0,       
        "active_chat_id": None,
        "notified_sleep": True,
        "live_records": []
    }

state_30s = create_state("WinGo 30S", "30S")
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

                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2:
                            pwd = parts[1]
                            if pwd == PASS_30S:
                                state_30s["active_until"] = time.time() + 3600
                                state_30s["active_chat_id"] = chat_id
                                state_30s["notified_sleep"] = False
                                send_telegram_message_direct(chat_id, "✅ *[30S Strategy] Activated for 1 Hour (Master B/S + AI Violet)!*")
                            elif pwd == PASS_1M:
                                state_1m["active_until"] = time.time() + 3600
                                state_1m["active_chat_id"] = chat_id
                                state_1m["notified_sleep"] = False
                                send_telegram_message_direct(chat_id, "✅ *[1M Strategy] Activated for 1 Hour (Master B/S + AI Violet)!*")
                            else:
                                send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(3)

def analyze_violet_history(full_history):
    if not full_history or len(full_history) < 20:
        return None, None
        
    gaps = []
    preceding_numbers = {}
    last_violet_idx = -1
    
    for i in range(len(full_history)):
        num = full_history[i]['number']
        is_violet = (num == 0 or num == 5)
        
        if is_violet:
            if i + 1 < len(full_history):
                prev_num = full_history[i+1]['number']
                preceding_numbers[prev_num] = preceding_numbers.get(prev_num, 0) + 1
            
            if last_violet_idx != -1:
                gap = i - last_violet_idx - 1
                gaps.append(gap)
            
            last_violet_idx = i
            
    hot_gap = max(set(gaps), key=gaps.count) if gaps else None
    hot_number = max(preceding_numbers, key=preceding_numbers.get) if preceding_numbers else None
    return hot_gap, hot_number

def send_telegram_signal(state, issue, bs_pred, bs_level, prev_bs_res=None, prev_violet_res=None):
    target_chat_id = state.get("active_chat_id")
    if not target_chat_id: return

    game_name = state["name"]
    text = f"🚀 *VSR {game_name} Master Trend* 🚀\n\n"
    
    # AI Data Banner
    text += f"🧠 *AI DATA:* Hot Gap [{state['hot_gap']}] | Hot Num [{state['hot_number']}]\n\n"
    
    if state["stats"]["total_trades"] > 0 and (prev_bs_res or prev_violet_res):
        text += f"🔄 *Last Trade Result:*\n"
        
        if prev_bs_res:
            if "SKIP" in prev_bs_res: text += f"📏 B/S: ⏸️ *SKIPPED (Waiting for Trend)*\n"
            else: text += f"📏 B/S: *{prev_bs_res}*\n"
            
        if prev_violet_res:
            text += f"🟣 Violet: {prev_violet_res}\n"
            
        if "WIN" in prev_bs_res or state["violet_mega_win"]: 
            text += f"\n🔥🎉 *CONGRATS! WIN!* 🎉🔥\n"
            
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *New Issue:* {issue}\n\n"
    
    # Big/Small Signal
    if state["bs_active"]:
        bs_pred_text = "🟠 Big" if bs_pred == "Big" else "🔵 Small"
        mode_text = "(3-Circle Mode)" if state["mode"] == "3-circle" else ""
        text += f"📏 *Prediction:* *{bs_pred_text}* | 🎯 *Level:* L{bs_level} {mode_text}\n\n"
    else:
        text += f"📏 *Prediction:* ⏸️ *WAIT FOR PATTERN*\n\n"
        
    # Violet Signal
    if state["violet_alert_active"]:
        text += f"⚠️ 🟣 *{state['violet_alert_type'].upper()}*\n"
        text += f"🎯 *Violet Level:* L{state['violet_level']}\n"
    else:
        text += f"⏸️ *Violet Status:* Analyzing Pattern (Gap: {state['violet_gap']})\n"
    
    send_telegram_message_direct(target_chat_id, text)

def fetch_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
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
    
    # ---------------- 1. Update Full History for AI ----------------
    for r in records:
        iss = str(r.get("issueNumber") or r.get("issue") or "")
        num_str = str(r.get("number") or r.get("drawNumber") or "")
        if iss and num_str.isdigit():
            if not any(x['issue'] == iss for x in state["full_history"]):
                state["full_history"].append({'issue': iss, 'number': int(num_str)})
    
    state["full_history"].sort(key=lambda x: x['issue'], reverse=True)
    state["full_history"] = state["full_history"][:100]
    
    h_gap, h_num = analyze_violet_history(state["full_history"])
    state["hot_gap"] = h_gap
    state["hot_number"] = h_num
    # ---------------------------------------------------------------
    
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
        is_violet = (number == 0 or number == 5)
    else:
        return False

    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        state["bs_pred"] = latest_bs
        
        # Calculate initial Violet Gap
        gap = 0
        for r in records:
            n_str = str(r.get("number", "-"))
            if n_str.isdigit() and (int(n_str) == 0 or int(n_str) == 5): break
            gap += 1
        state["violet_gap"] = gap
        
        next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
        if state["active_until"] > 0 and time.time() < state["active_until"]:
            send_telegram_signal(state, next_issue, state["bs_pred"], state["bs_level"])
        return True

    if state["last_processed_issue"] != latest_issue and latest_issue > state["last_processed_issue"]:
        bs_res_status = "-"
        violet_res_status = None
        state["stats"]["total_trades"] += 1
        
        # --- BIG/SMALL EVALUATION ---
        if state["bs_active"]:
            bs_win = (state["bs_pred"] == latest_bs)
            bs_emoji = "🟠" if state["bs_pred"] == "Big" else "🔵"
            if bs_win:
                state["stats"]["bs_win"] += 1
                state["bs_level"] = 1 
                state["bs_fails_in_row"] = 0 
                state["mode"] = "normal" 
                bs_res_status = f"{bs_emoji} {state['bs_pred']} ✅ WIN"
            else:
                state["stats"]["bs_fail"] += 1
                state["bs_level"] += 1
                state["bs_fails_in_row"] += 1 
                bs_res_status = f"{bs_emoji} {state['bs_pred']} ❌ FAIL"
        else:
            state["stats"]["bs_skip"] += 1
            bs_res_status = "SKIP"
            if latest_bs == prev_bs:
                state["bs_active"] = True
                state["bs_fails_in_row"] = 0 
                
        # --- VIOLET EVALUATION ---
        state["violet_mega_win"] = False
        if is_violet:
            if state["violet_alert_active"]:
                violet_res_status = f"🟣 ✅ AI WIN (L{state['violet_level']})"
                state["violet_mega_win"] = True
            else:
                violet_res_status = "🟣 ✅ Normal Win"
                
            state["violet_gap"] = 0 
            state["violet_alert_active"] = False
            state["violet_alert_type"] = "None"
            state["violet_level"] = 0
        else:
            state["violet_gap"] += 1
            if state["violet_alert_active"]:
                violet_res_status = f"🟣 ❌ FAIL ({state['violet_alert_type']} L{state['violet_level']})"
                
                # Stop Loss for Violet AI (Max L2)
                if state["violet_level"] >= 2:
                    violet_res_status += " [🛑 STOP]"
                    state["violet_alert_active"] = False
                    state["violet_alert_type"] = "None"
                    state["violet_level"] = 0
                else:
                    state["violet_level"] += 1

        state["last_violet_res"] = violet_res_status

        bs_disp_pred = state["bs_pred"] if state["bs_active"] else "[yellow]WAIT[/]"
        bs_disp_lvl = f"L{state['bs_level']}" if state["bs_active"] else f"L{state['bs_level']}(Hold)"
        
        state["history"].append({
            "trade": state["stats"]["total_trades"], "issue": latest_issue[-4:],
            "bs_level": bs_disp_lvl, "bs_pred": bs_disp_pred,
            "bs_res": "[green]WIN[/]" if "WIN" in bs_res_status else ("[yellow]SKIP[/]" if "SKIP" in bs_res_status else "[red]FAIL[/]")
        })
        if len(state["history"]) > 3: state["history"].pop(0)

        # --- NEXT ROUND BIG/SMALL PREDICTION ---
        if state["mode"] == "normal":
            if state["bs_level"] >= 4: 
                state["mode"] = "3-circle"
                state["circle_current_target"] = latest_bs
                state["circle_count"] = 1
                state["bs_pred"] = state["circle_current_target"]
            else:
                state["bs_pred"] = latest_bs
        elif state["mode"] == "3-circle":
            state["circle_count"] += 1
            if state["circle_count"] > 3:
                state["circle_current_target"] = "Small" if state["circle_current_target"] == "Big" else "Big"
                state["circle_count"] = 1
            state["bs_pred"] = state["circle_current_target"]

        # --- NEXT ROUND VIOLET AI TRIGGER ---
        if not state["violet_alert_active"] and len(state["full_history"]) >= 20:
            if state["hot_gap"] is not None and state["violet_gap"] == state["hot_gap"]:
                state["violet_alert_active"] = True
                state["violet_alert_type"] = f"AI Hot Gap ({state['hot_gap']})"
                state["violet_level"] = 1
            elif state["hot_number"] is not None and number == state["hot_number"]:
                state["violet_alert_active"] = True
                state["violet_alert_type"] = f"AI Hot Num ({state['hot_number']})"
                state["violet_level"] = 1

        next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
        
        if state["active_until"] > 0 and time.time() < state["active_until"]:
            send_telegram_signal(state, next_issue, state["bs_pred"], state["bs_level"], bs_res_status, violet_res_status)
        elif state["active_until"] > 0 and time.time() >= state["active_until"]:
            if not state["notified_sleep"]:
                send_telegram_message_direct(state["active_chat_id"], f"💤 *1 Hour Session Completed ({state['name']})! Sleeping now.*")
                state["notified_sleep"] = True
                state["active_until"] = 0

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
    
    ui_text = f"[{bs_color}]{state['bs_pred']}[/] (L{state['bs_level']})" if state["bs_active"] else f"[yellow]WAIT[/] (Pending L{state['bs_level']})"
    if state["mode"] == "3-circle": ui_text += " [bold magenta]🔄 3-Circle[/]"
        
    ai_status = f"[cyan]Hot Gap:[/] {state['hot_gap']} | [cyan]Hot Num:[/] {state['hot_number']}"
    if state["violet_alert_active"]:
        v_pred = f"[bold purple]🟣 {state['violet_alert_type']} (L{state['violet_level']})[/]"
    else:
        v_pred = f"[dim]⏸️ Wait (Gap {state['violet_gap']})[/]"
        
    timer_status = "[green]ACTIVE[/]" if (state["active_until"] > 0 and time.time() < state["active_until"]) else "[red]SLEEPING[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n🕒 [bold]Status:[/] {timer_status}\n"
    panel_text += f"🧠 [bold]AI Data:[/] {ai_status}\n\n"
    panel_text += f"📏 [bold]B/S Pred:[/] {ui_text}\n"
    panel_text += f"🟣 [bold]Vio Pred:[/] {v_pred}\n\n"
    
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
    p_1m = render_game_panel(state_1m)
    return Group(
        Align.center("[bold yellow]🚀 MASTER ALL-IN-ONE BOT (1M & 30S + AI VIOLET)[/bold yellow]\n"),
        Align.center(Group(p_30s, p_1m))
    )

if __name__ == "__main__":
    t_list = threading.Thread(target=telegram_listener, daemon=True)
    t_30s = threading.Thread(target=worker_30s, daemon=True)
    t_1m = threading.Thread(target=worker_1m, daemon=True)
    
    t_list.start(); t_30s.start(); t_1m.start()

    with Live(create_master_ui(), console=console, refresh_per_second=2, screen=False) as live:
        while True:
            live.update(create_master_ui())
            time.sleep(1)
