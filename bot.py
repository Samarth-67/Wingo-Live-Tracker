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

# --- 🚀 TELEGRAM BOT CONFIGURATION (पहिल्या कोडमधील अचूक डिटेल्स) 🚀 ---
TELEGRAM_TOKEN = "8886107397:AAHENOebGnrupxvGKqKh5cKC3SmujXJOV3w" 
TARGET_CHANNEL_ID = "-1004370895879"  
SECRET_PASSWORD = "12345"  
# ------------------------------------------------------------------------

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        "bs_pred": None, "bs_level": 1, "bs_active": True, "bs_fails_in_row": 0,
        
        # --- STRATEGY MODES ---
        "mode": "normal",
        
        "history": [],
        "stats": {"bs_win": 0, "bs_fail": 0, "bs_skip": 0, "total_trades": 0},
        "is_running": False,       
        "live_records": []
    }

state_30s = create_state("WinGo 30S", "30S")
state_1m = create_state("WinGo 1M", "1M")

# --- SUPER 8 & 4 Global States ---
tracker = {
    "se_active": False, "se_level": 0, "se_target": "4 & 6",
    "s4_active": False, "s4_level": 0, "s4_target": "8 & 6"
}

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
                        if len(parts) == 2 and parts[1] == SECRET_PASSWORD:
                            state_30s["is_running"] = True
                            state_1m["is_running"] = True
                            # चॅनेलवर मेसेज जाईल
                            send_telegram_message_direct(TARGET_CHANNEL_ID, "✅ *[Master AI] 30S & 1M Strategies Activated!*")
                            # ज्याने कमांड टाकली त्यालाही रिप्लाय मिळेल
                            if str(chat_id) != TARGET_CHANNEL_ID:
                                send_telegram_message_direct(chat_id, "✅ Bot Activated! Signals routing to target channel.")
                        elif len(parts) == 2 and parts[1] != SECRET_PASSWORD:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    # --- STOP COMMAND ---
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == SECRET_PASSWORD:
                            state_30s["is_running"] = False
                            state_1m["is_running"] = False
                            send_telegram_message_direct(TARGET_CHANNEL_ID, "🛑 *[Master AI] Stopped Successfully!*")
                            if str(chat_id) != TARGET_CHANNEL_ID:
                                send_telegram_message_direct(chat_id, "🛑 Stopped successfully!")
                        elif len(parts) == 2 and parts[1] != SECRET_PASSWORD:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(3)

def send_telegram_signal(state, issue, bs_pred, bs_level, prev_bs_res=None):
    target_chat_id = TARGET_CHANNEL_ID # आता मेसेज फक्त याच चॅनेलवर जाईल
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
        
        mode_text = ""
        if state["mode"] == "3-circle": mode_text = "(🔄 3-Circle)"
        elif state["mode"] == "zigzag": mode_text = "(⚡ ZigZag)"
        
        text += f"🎯 *Level:* L{bs_level} {mode_text}\n\n"
    else:
        text += f"📏 *Prediction:* ⏸️ *WAIT FOR PATTERN*\n"
        text += f"⚠️ *(Pending Level: L{bs_level})*\n\n"
    
    send_telegram_message_direct(target_chat_id, text)

def fetch_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
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
    global tracker
    
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
        bs_res_status = "-"
        state["stats"]["total_trades"] += 1
        
        # --- B/S Logic Evaluation ---
        if state["bs_active"]:
            bs_win = (state["bs_pred"] == latest_bs)
            bs_emoji = "🟠" if state["bs_pred"] == "Big" else "🔵"
            if bs_win:
                state["stats"]["bs_win"] += 1
                state["bs_level"] = 1 
                state["bs_fails_in_row"] = 0 
                state["mode"] = "normal" 
                state["bs_pred"] = latest_bs # Reset to normal
                bs_res_status = f"{bs_emoji} {state['bs_pred']} ✅ WIN"
            else:
                state["stats"]["bs_fail"] += 1
                
                # --- STRICT ZIGZAG LOGIC ---
                if state["bs_level"] >= 8: # STRICT L8 STOP LOSS
                    bs_res_status = f"{bs_emoji} {state['bs_pred']} ❌ FAIL [🛑 L8 STOP LOSS]"
                    state["bs_level"] = 1
                    state["mode"] = "normal"
                    state["bs_pred"] = latest_bs
                else:
                    state["bs_level"] += 1
                    state["bs_fails_in_row"] += 1 
                    bs_res_status = f"{bs_emoji} {state['bs_pred']} ❌ FAIL"
                    
                    if state["bs_level"] <= 3:
                        state["mode"] = "normal"
                        state["bs_pred"] = latest_bs
                    elif state["bs_level"] == 4:
                        state["mode"] = "3-circle"
                        state["bs_pred"] = latest_bs
                    elif state["bs_level"] == 5:
                        state["mode"] = "zigzag"
                        # चौथ्या लेव्हलचा जो रिझल्ट आलाय (latest_bs), त्याच्या अगदी उलट देईल!
                        state["bs_pred"] = "Big" if latest_bs == "Small" else "Small"
                    elif state["bs_level"] >= 6:
                        state["mode"] = "zigzag"
                        # मागच्या प्रेडिक्शनच्या अगदी उलट (Strict Alternation: Big, Small, Big, Small)
                        state["bs_pred"] = "Small" if state["bs_pred"] == "Big" else "Big"

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

        # --- Super 8 & 4 Tracking (Only for 1M game for alerts) ---
        se_res_status = ""
        s4_res_status = ""
        just_resolved = False

        if state["name"] == "WinGo 1M":
            if tracker["se_active"]:
                if number in [4, 6]:
                    se_res_status = f"🎱 ✅ WIN (L{tracker['se_level']} - Num {number})"
                    tracker["se_active"] = False
                    tracker["se_level"] = 0
                    just_resolved = True
                elif number == 8:
                    se_res_status = f"🎱 ❌ FAIL (Got 8, Restarting L1)"
                    tracker["se_level"] = 1
                else:
                    if tracker["se_level"] == 1:
                        se_res_status = f"🎱 ❌ FAIL (L1 Targets 4 & 6)"
                        tracker["se_level"] = 2
                    else:
                        se_res_status = f"🎱 ❌ FAIL L2 [🛑 STOP]"
                        tracker["se_active"] = False
                        tracker["se_level"] = 0

            if tracker["s4_active"]:
                if number in [8, 6]:
                    s4_res_status = f"🍀 ✅ WIN (L{tracker['s4_level']} - Num {number})"
                    tracker["s4_active"] = False
                    tracker["s4_level"] = 0
                    just_resolved = True
                elif number == 4:
                    s4_res_status = f"🍀 ❌ FAIL (Got 4, Restarting L1)"
                    tracker["s4_level"] = 1
                elif number in [0, 5]:
                    s4_res_status = f"🍀 ⏸️ SKIPPED (Violet Came, Holding L{tracker['s4_level']})"
                else:
                    if tracker["s4_level"] == 1:
                        s4_res_status = f"🍀 ❌ FAIL (L1 Targets 8 & 6)"
                        tracker["s4_level"] = 2
                    else:
                        s4_res_status = f"🍀 ❌ FAIL L2 [🛑 STOP]"
                        tracker["s4_active"] = False
                        tracker["s4_level"] = 0

            if not just_resolved:
                if not tracker["se_active"] and number == 8:
                    tracker["se_active"] = True
                    tracker["se_level"] = 1
                if not tracker["s4_active"] and number == 4:
                    tracker["s4_active"] = True
                    tracker["s4_level"] = 1

        next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else "Next"
        
        if state["is_running"]:
            if state["name"] == "WinGo 1M":
                # Custom message for 1M to include S8/S4 alerts
                msg = f"🚀 *VSR 1M Trend Follower* 🚀\n\n"
                msg += f"🔄 *Result for {latest_issue}:*\n"
                msg += f"📏 B/S: {bs_res_status}\n"
                if se_res_status: msg += f"🎱 Super 8: {se_res_status}\n"
                if s4_res_status: msg += f"🍀 Super 4: {s4_res_status}\n"
                msg += f"\n➖➖➖➖➖➖➖➖➖➖\n\n"
                msg += f"🎟️ *Prediction For Ticket:* {next_issue}\n\n"
                
                mode_text = ""
                if state["mode"] == "3-circle": mode_text = " *(🔄 3-Circle)*"
                elif state["mode"] == "zigzag": mode_text = " *(⚡ ZigZag)*"
                
                curr_bs_emoji = "🟠 Big" if state['bs_pred'] == "Big" else "🔵 Small"
                msg += f"📏 *B/S Pred:* {curr_bs_emoji} (L{state['bs_level']}){mode_text}\n\n"
                
                if tracker["se_active"]:
                    msg += f"⚠️ 🎱 *SUPER 8 ALERT!*\n"
                    msg += f"🎯 *Targets:* 4 & 6 (L{tracker['se_level']})\n\n"
                if tracker["s4_active"]:
                    msg += f"⚠️ 🍀 *SUPER 4 ALERT!*\n"
                    msg += f"🎯 *Targets:* 8 & 6 (L{tracker['s4_level']})\n\n"
                if not tracker["se_active"] and not tracker["s4_active"]:
                    msg += f"⏸️ *Number Pred:* Waiting for 8 or 4\n"
                    
                send_telegram_message_direct(TARGET_CHANNEL_ID, msg)
            else:
                # 30S normal flow
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
    elif state["mode"] == "zigzag": ui_text += " [bold yellow]⚡ ZigZag[/]"
        
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
    p_30s = render_game_panel(state_30s)
    p_1m = render_game_panel(state_1m)
    return Group(
        Align.center("[bold yellow]🚀 MASTER ALL-IN-ONE BOT (1M & 30S)[/bold yellow]\n"),
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
