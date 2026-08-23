import os
import time
import threading
import requests
import random  # <--- Random logic साठी ऍड केले
from rich.table import Table
from rich.console import Console, Group
from rich.panel import Panel
from rich.align import Align
from rich.live import Live

console = Console()

# --- 🚀 TELEGRAM BOT CONFIGURATION 🚀 ---
TELEGRAM_TOKEN = "8577275461:AAF8lWPac3WCgbHp8XPvU_lO289oHcMdOE8" 
TARGET_GROUP_ID = "-5202202128"  # <--- तुझा ग्रुप आयडी
PASS_30S = "11111"   # ३० सेकंदाच्या गेमसाठी
# ----------------------------------------

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        "bs_pred": None, "bs_level": 1, "bs_active": True, "bs_fails_in_row": 0,
        
        # --- NEW RANDOM & NUMBER LOGIC VARIABLES ---
        "pred_type": "Trend",
        "num_pred": None,
        "missing_numbers": "",
        "special_patterns": {},
        # -------------------------------------------
        
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
                                send_telegram_message_direct(chat_id, f"✅ *Bot Activated!*")
                            else:
                                send_telegram_message_direct(chat_id, "❌ Wrong Password.")
                                
                    # --- STOP COMMAND ---
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2:
                            pwd = parts[1]
                            if pwd == PASS_30S:
                                state_30s["is_running"] = False
                                send_telegram_message_direct(chat_id, "🛑 *Bot Stopped!*")
                            else:
                                send_telegram_message_direct(chat_id, "❌ Wrong Password.")
        except Exception:
            pass
        time.sleep(3)

def send_telegram_signal(state, issue, bs_pred, bs_level, prev_bs_res=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    text = ""
    
    # १. मागील निकाल
    if state["stats"]["total_trades"] > 0 and prev_bs_res:
        if "WIN" in prev_bs_res:
            text += f"📊 *Last Result:* ✅ WIN\n\n"
        elif "FAIL" in prev_bs_res:
            text += f"📊 *Last Result:* ❌ FAIL\n\n"
        else:
            text += f"📊 *Last Result:* ⏸️ SKIP\n\n"
            
    # २. टोकन नंबर (Issue)
    text += f"🎟️ *Issue:* {issue}\n"
    
    # ३. Big/Small आणि प्रेडिक्शन प्रकार (Trend किंवा Random)
    if state["bs_active"]:
        bs_pred_text = "Big" if bs_pred == "Big" else "Small"
        pred_mode = "📈 Trend" if state.get("pred_type") == "Trend" else "🎲 Random"
        text += f"🎯 *BS Pred:* *{bs_pred_text}* (L{bs_level}) [{pred_mode}]\n"
    else:
        text += f"🎯 *BS Pred:* ⏸️ *WAIT* (L{bs_level})\n"
        
    # ४. Number Prediction
    if state.get("num_pred") is not None:
        text += f"🔢 *Number Pred:* *{state['num_pred']}*\n\n"
        
    # ५. Missing Numbers & Special Patterns
    if state.get("missing_numbers"):
        text += f"🔍 *Missing in Last 10:* {state['missing_numbers']}\n"
        
    sp_patterns = state.get("special_patterns", {})
    if sp_patterns:
        pat_str = " | ".join([f"{k}➡️{v}" for k, v in sp_patterns.items()])
        text += f"✨ *Special (4,6,8) Check:* {pat_str}\n"

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

    if state["last_processed_issue"] == latest_issue:
        return False

    if state["last_processed_issue"] is not None:
        if state["last_processed_issue"].isdigit() and latest_issue.isdigit():
            if int(latest_issue) <= int(state["last_processed_issue"]):
                return False  

        bs_res_status = "-"
        state["stats"]["total_trades"] += 1
        
        if state["bs_active"]:
            bs_win = (state["bs_pred"] == latest_bs)
            if bs_win:
                state["stats"]["bs_win"] += 1
                state["bs_level"] = 1 
                state["bs_fails_in_row"] = 0 
                bs_res_status = "WIN"
            else:
                state["stats"]["bs_fail"] += 1
                state["bs_level"] += 1
                state["bs_fails_in_row"] += 1 
                bs_res_status = "FAIL"
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
    else:
        bs_res_status = None

    # =======================================================
    # 🚀 STRATEGY LOGIC: TREND (L1-3) -> RANDOM + NUMBERS 🚀
    # =======================================================
    # १. Big/Small Prediction
    if state["bs_level"] <= 3:
        state["bs_pred"] = latest_bs  # लेव्हल ३ पर्यंत मागील ट्रेंड फॉलो करेल
        state["pred_type"] = "Trend"
    else:
        state["bs_pred"] = random.choice(["Big", "Small"]) # लेव्हल ३ च्या पुढे संपूर्ण रँडम
        state["pred_type"] = "Random"

    # २. मागील रेकॉर्ड्समधून नंबर्स वेगळे करणे
    history_numbers = []
    for r in records:
        n_str = str(r.get("number") or r.get("drawNumber") or "-")
        if n_str.isdigit():
            history_numbers.append(int(n_str))

    # ३. मागील १० राऊंडमधील Missing Numbers
    if len(history_numbers) >= 10:
        last_10 = history_numbers[:10]
        missing_nums = list(set(range(10)) - set(last_10))
        state["missing_numbers"] = ", ".join(map(str, missing_nums)) if missing_nums else "None"
    else:
        state["missing_numbers"] = "Wait..."

    # ४. Special Numbers (4, 6, 8) पॅटर्न (मागील रेकॉर्ड्समध्ये शोधणे)
    special_nums = [4, 6, 8]
    sp_patterns = {}
    
    # इतिहास तपासून पाहणे (records[0] हा सर्वात नवीन निकाल आहे)
    # म्हणून जेव्हा history_numbers[i] मध्ये ४,६,८ येतो, तेव्हा त्याच्या नंतर आलेला निकाल history_numbers[i-1] असतो.
    for sp in special_nums:
        for i in range(1, len(history_numbers)):
            if history_numbers[i] == sp:
                sp_patterns[sp] = history_numbers[i-1] 
                break # सर्वात लेटेस्ट पॅटर्न मिळाल्यावर ब्रेक करणे

    state["special_patterns"] = sp_patterns

    # ५. Exact Number Prediction
    if sp_patterns:
        # जर ४, ६ किंवा ८ च्या पॅटर्नमधून काही ट्रिगर झाले असेल, तर तो नंबर प्रेडिक्ट कर
        # सर्वात अलीकडे जो स्पेशल नंबर आला होता, त्याचा निकाल
        predicted_num = random.randint(0, 9)
        for i in range(1, len(history_numbers)):
            if history_numbers[i] in special_nums:
                predicted_num = history_numbers[i-1]
                break
        state["num_pred"] = predicted_num
    else:
        # जर पॅटर्न नसेल तर रँडम नंबर
        state["num_pred"] = random.randint(0, 9)
    # =======================================================

    next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
    
    if state["is_running"]:
        send_telegram_signal(state, next_issue, state["bs_pred"], state["bs_level"], bs_res_status)

    state["last_processed_issue"] = latest_issue
    return True

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
    mode_text = f"[[green]Trend[/]]" if state.get("pred_type") == "Trend" else f"[[magenta]Random[/]]"
    ui_text += f" {mode_text}"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n"
    panel_text += f"📏 [bold]BS Pred:[/] {ui_text}\n"
    panel_text += f"🔢 [bold]Num Pred:[/] [yellow]{state.get('num_pred', '-')}[/]\n"
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
        Align.center("[bold yellow]🚀 30S BOT (Trend + Random Strategy)[/bold yellow]\n"),
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
