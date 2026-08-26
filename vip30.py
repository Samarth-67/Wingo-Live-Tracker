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
TELEGRAM_TOKEN = "8813447942:AAFPBVlFoJnRNBKvCywTx7gSEg8EckzKFDg" 
TARGET_GROUP_ID = "-1004318545622"  # <--- ३० सेकंदाच्या चॅनेल/ग्रुपचा आयडी

# 🔐 सिक्रेट पासवर्ड
PASS_30S = "11111"   # ३० सेकंदाच्या गेमसाठी
# ----------------------------------------

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        "bs_pred": None, 
        "bs_level": 1, 
        
        "history": [],
        "stats": {"bs_win": 0, "bs_fail": 0, "total_trades": 0},
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
                                send_telegram_message_direct(chat_id, f"✅ *[30S Strategy] Activated! Live Prediction is ON.*")
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
        text += f"🔄 *Last Trade Result:*\n"
        text += f"📏 B/S: *{prev_bs_res}*\n"
        if "WIN" in prev_bs_res: text += f"\n🔥🎉 *CONGRATS! WIN!* 🎉🔥\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *New Issue:* {issue}\n\n"
    
    bs_pred_text = "🟠 Big" if bs_pred == "Big" else "🔵 Small"
    text += f"📏 *Prediction:* *{bs_pred_text}*\n"
    text += f"🎯 *Level:* L{bs_level}\n\n"
        
    send_telegram_message_direct(target_chat_id, text)

# 🔄 नविन Multi-Page Fetcher (API 10-10 चे रेकॉर्ड देत असल्यामुळे 3 पेजेस एकत्र डाउनलोड करेल)
def fetch_history_records(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://draw.ar-lottery01.com/",
    }
    all_records = []
    
    # 3 पेजेस लूप करून कमीत कमी 30 रेकॉर्ड्स मिळवणे
    for pageNo in [1, 2, 3]: 
        params = {"pageSize": 10, "pageNo": pageNo, "ts": int(time.time() * 1000)}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                recs = []
                if "data" in data and isinstance(data["data"], list): recs = data["data"]
                elif "list" in data and isinstance(data["list"], list): recs = data["list"]
                elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: recs = data["data"]["list"]
                
                all_records.extend(recs)
        except Exception:
            pass
            
    return all_records

def process_strategy(state, records):
    # आता आपल्याकडे 30 रेकॉर्ड्स असतील, त्यामुळे आपण अचूक 20 वा ट्रेड घेऊ शकतो.
    if not records or len(records) < 20: 
        return False
        
    state["live_records"] = records[:5]
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if latest_number_str.isdigit():
        number = int(latest_number_str)
        latest_bs = "Big" if number >= 5 else "Small"
    else:
        return False

    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        
        # बरोबर 20 वा रेकॉर्ड (Index 19) निवडणे
        round_20_item = records[19]
        round_20_num = str(round_20_item.get("number") or round_20_item.get("drawNumber") or "0")
        state["bs_pred"] = "Big" if round_20_num.isdigit() and int(round_20_num) >= 5 else "Small"
        
        next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
        if state["is_running"]:
            send_telegram_signal(state, next_issue, state["bs_pred"], state["bs_level"])
        return True

    if state["last_processed_issue"] != latest_issue:
        if state["last_processed_issue"].isdigit() and latest_issue.isdigit():
            if int(latest_issue) <= int(state["last_processed_issue"]):
                return False  

        state["stats"]["total_trades"] += 1
        
        bs_win = (state["bs_pred"] == latest_bs)
        bs_emoji = "🟠" if state["bs_pred"] == "Big" else "🔵"
        
        # --- जिंकले की लेव्हल १, हरले की पुढची लेव्हल (कंटिन्यूअस) ---
        if bs_win:
            state["stats"]["bs_win"] += 1
            state["bs_level"] = 1 
            bs_res_status = f"{bs_emoji} {state['bs_pred']} ✅ WIN"
        else:
            state["stats"]["bs_fail"] += 1
            state["bs_level"] += 1
            bs_res_status = f"{bs_emoji} {state['bs_pred']} ❌ FAIL"
                
        bs_disp_pred = state["bs_pred"]
        bs_disp_lvl = f"L{state['bs_level']}"
        
        state["history"].append({
            "trade": state["stats"]["total_trades"], "issue": latest_issue[-4:],
            "bs_level": bs_disp_lvl, "bs_pred": bs_disp_pred,
            "bs_res": "[green]WIN[/]" if "WIN" in bs_res_status else "[red]FAIL[/]"
        })
        if len(state["history"]) > 3: state["history"].pop(0)

        # =======================================================
        # 🚀 STRATEGY LOGIC: अचूक विसावा राऊंड (Index 19)
        # =======================================================
        round_20_item = records[19] 
        round_20_num = str(round_20_item.get("number") or round_20_item.get("drawNumber") or "0")
        if round_20_num.isdigit():
            state["bs_pred"] = "Big" if int(round_20_num) >= 5 else "Small"

        next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
        
        if state["is_running"]:
            send_telegram_signal(state, next_issue, state["bs_pred"], state["bs_level"], bs_res_status)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def worker_30s():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
    while True:
        records = fetch_history_records(url) # नविन फंक्शन कॉल
        if records:
            process_strategy(state_30s, records)
        time.sleep(2) 

def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and state["last_processed_issue"].isdigit() else "Next"
    bs_color = "dark_orange" if state["bs_pred"] == "Big" else "bright_blue"
    
    ui_text = f"[{bs_color}]{state['bs_pred']}[/] (L{state['bs_level']})"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n📏 [bold]Pred:[/] {ui_text}\n"
    panel_text += f"🕒 [bold]Status:[/] {timer_status}\n\n"
    panel_text += f"📊 [bold]W:[/] [green]{state['stats']['bs_win']}[/] | [bold]F:[/] [red]{state['stats']['bs_fail']}[/]\n"
    
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
        Align.center("[bold yellow]🚀 30S BOT (Pure 20th Round Strategy - Continuous Levels)[/bold yellow]\n"),
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
