import os
import time
import threading
import requests
from rich.table import Table
from rich.console import Console, Group
from rich.panel import Panel
from rich.align import Align
from rich.layout import Layout

console = Console()

# --- 🚀 TELEGRAM BOT CONFIGURATION 🚀 ---
TELEGRAM_TOKEN = "8808901816:AAFTYigKQeeH5--jw6KDM_aAlsL9SIZCCXo" # तुझा नवीन मास्टर बॉट
TELEGRAM_CHAT_ID = "1052834817" # तुझा पर्सनल चॅट ID

# 🔐 सिक्रेट पासवर्ड्स (दोन वेगवेगळ्या गेम्ससाठी)
PASS_30S = "11111"  # ३० सेकंदाच्या गेमसाठी
PASS_1M = "22222"   # १ मिनिटाच्या गेमसाठी
# ----------------------------------------

# 🎯 STATES (दोन्ही गेम्सचा डेटा वेगळा ठेवण्यासाठी)
def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        "bs_pred": None, "bs_level": 1, "bs_active": True, "bs_fails_in_row": 0,
        "history": [],
        "stats": {"bs_win": 0, "bs_fail": 0, "bs_skip": 0, "total_trades": 0},
        "active_until": 0,       
        "notified_sleep": True,
        "live_records": []
    }

state_30s = create_state("WinGo 30S", "30S")
state_1m = create_state("WinGo 1M", "1M")

def send_telegram_message_direct(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except Exception:
        pass

def telegram_listener():
    """Background thread to listen for passwords and activate specific timers."""
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
                                state_30s["notified_sleep"] = False
                                send_telegram_message_direct(chat_id, "✅ *[30S Strategy] Activated for 1 Hour!*")
                            elif pwd == PASS_1M:
                                state_1m["active_until"] = time.time() + 3600
                                state_1m["notified_sleep"] = False
                                send_telegram_message_direct(chat_id, "✅ *[1M Strategy] Activated for 1 Hour!*")
                            else:
                                send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(3)

def send_telegram_signal(state, issue, bs_pred, bs_level, prev_bs_res=None):
    if not TELEGRAM_CHAT_ID: return

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
        text += f"📏 *Prediction:* ⏸️ *WAIT FOR PATTERN*\n"
        text += f"⚠️ *(Pending Level: L{bs_level})*\n\n"
    
    send_telegram_message_direct(TELEGRAM_CHAT_ID, text)

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
        if state["active_until"] > 0 and time.time() < state["active_until"]:
            send_telegram_signal(state, next_issue, state["bs_pred"], state["bs_level"])
        return True

    if state["last_processed_issue"] != latest_issue:
        bs_res_status = "-"
        state["stats"]["total_trades"] += 1
        
        if state["bs_active"]:
            bs_win = (state["bs_pred"] == latest_bs)
            bs_emoji = "🟠" if state["bs_pred"] == "Big" else "🔵"
            if bs_win:
                state["stats"]["bs_win"] += 1
                state["bs_level"] = 1 
                state["bs_fails_in_row"] = 0 
                bs_res_status = f"{bs_emoji} {state['bs_pred']} ✅ WIN"
            else:
                state["stats"]["bs_fail"] += 1
                state["bs_level"] += 1
                state["bs_fails_in_row"] += 1 
                bs_res_status = f"{bs_emoji} {state['bs_pred']} ❌ FAIL"
                if state["bs_fails_in_row"] >= 4:
                    state["bs_active"] = False
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

        state["bs_pred"] = latest_bs
        next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
        
        if state["active_until"] > 0 and time.time() < state["active_until"]:
            send_telegram_signal(state, next_issue, state["bs_pred"], state["bs_level"], bs_res_status)
        elif state["active_until"] > 0 and time.time() >= state["active_until"]:
            if not state["notified_sleep"]:
                send_telegram_message_direct(TELEGRAM_CHAT_ID, f"💤 *1 Hour Session Completed ({state['name']})! Sleeping now.*")
                state["notified_sleep"] = True
                state["active_until"] = 0

        state["last_processed_issue"] = latest_issue
        return True
    return False

# --- Background Workers ---
def worker_30s():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_30S.json"
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

# --- UI Renderer ---
def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and state["last_processed_issue"].isdigit() else "Next"
    bs_color = "dark_orange" if state["bs_pred"] == "Big" else "bright_blue"
    
    ui_text = f"[{bs_color}]{state['bs_pred']}[/] (L{state['bs_level']})" if state["bs_active"] else f"[yellow]WAIT[/] (Pending L{state['bs_level']})"
    timer_status = "[green]ACTIVE[/]" if (state["active_until"] > 0 and time.time() < state["active_until"]) else "[red]SLEEPING[/]"
    
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

if __name__ == "__main__":
    t_list = threading.Thread(target=telegram_listener, daemon=True)
    t_30s = threading.Thread(target=worker_30s, daemon=True)
    t_1m = threading.Thread(target=worker_1m, daemon=True)
    
    t_list.start(); t_30s.start(); t_1m.start()

    os.system('cls' if os.name == 'nt' else 'clear')
    console.print("[bold yellow]🚀 MASTER ALL-IN-ONE BOT STARTED... Press Ctrl + C to stop.[/bold yellow]\n")
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print("[bold yellow]🚀 MASTER ALL-IN-ONE BOT (1M & 30S)[/bold yellow]\n")
        
        p_30s = render_game_panel(state_30s)
        p_1m = render_game_panel(state_1m)
        
        console.print(Align.center(Group(p_30s, p_1m)))
        time.sleep(2)
