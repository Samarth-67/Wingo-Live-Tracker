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
TARGET_GROUP_ID = "-1004331023441"  # <--- १ मिनिटाच्या चॅनेल/ग्रुपचा आयडी

# 🔐 सिक्रेट पासवर्ड्स
PASS_1M = "22222"   # १ मिनिटाच्या गेमसाठी
# ----------------------------------------

# ⚡ फास्ट इंटरनेट कनेक्शनसाठी Session
api_session = requests.Session()

# 💰 Betting Table (Level: Amount)
BET_TABLE = {
    1: 100,
    2: 200,
    3: 500,
    4: 1100
}

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        
        # Strategy 1 (3-Circle Continuous Pattern: 3 Big, 3 Small, 3 Big, 3 Small...)
        "s1_pred": "WAIT",
        "s1_level": 1,
        "s1_active": False,
        "s1_base_pred": None,
        "s1_count": 0,
        
        # Strategy 2 (3 Consecutive Opposite)
        "s2_pred": "WAIT",
        "s2_level": 1,
        "s2_active": False,
        
        # Virtual Wallet (₹20,000)
        "virtual_balance": 20000,
        
        "full_history": [], 
        "history": [],
        "stats": {"s1_win": 0, "s1_fail": 0, "s2_win": 0, "s2_fail": 0, "total_trades": 0},
        "is_running": False,       
        "active_chat_id": None,   
        "live_records": []
    }

# 1M साठी State
state_1m = create_state("WinGo 1M", "1M")

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
                        if len(parts) == 2:
                            pwd = parts[1]
                            if pwd == PASS_1M:
                                state_1m["is_running"] = True
                                state_1m["active_chat_id"] = chat_id
                                send_telegram_message_direct(chat_id, f"✅ *[1M Dual Strategy] Activated! Live Prediction is ON.*")
                            else:
                                send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    # --- STOP COMMAND ---
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2:
                            pwd = parts[1]
                            if pwd == PASS_1M:
                                state_1m["is_running"] = False
                                send_telegram_message_direct(chat_id, "🛑 *[1M Dual Strategy] Stopped Successfully!*")
                            else:
                                send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")

                    # --- RESET COMMAND ---
                    elif text.startswith("/reset"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_1M:
                            state_1m["s1_level"] = 1
                            state_1m["s1_pred"] = "WAIT"
                            state_1m["s1_active"] = False
                            state_1m["s1_base_pred"] = None
                            state_1m["s1_count"] = 0
                            state_1m["s2_level"] = 1
                            state_1m["s2_pred"] = "WAIT"
                            state_1m["s2_active"] = False
                            state_1m["stats"]["s1_win"] = 0
                            state_1m["stats"]["s1_fail"] = 0
                            state_1m["stats"]["s2_win"] = 0
                            state_1m["stats"]["s2_fail"] = 0
                            state_1m["virtual_balance"] = 20000
                            send_telegram_message_direct(chat_id, "🔄 *1M Bot Reset Successfully!*\nLevels are back to L1 and Wallet is ₹20,000.")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(3)

# 🚀 मेसेज पाठवण्याचे लॉजिक
def send_telegram_signal(state, issue, prev_res_text=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    game_name = state["name"]
    
    text = f"🚀 *{game_name} Dual Strategy Bot* 🚀\n\n"
    
    if prev_res_text:
        text += f"📊 *मागील निकाल (Previous Result):*\n"
        text += f"{prev_res_text}\n"
        text += f"💰 *Virtual Balance:* ₹{state['virtual_balance']}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Next Issue:* `{issue}`\n\n"
    
    # Strategy 1 Text
    if not state["s1_active"] or state["s1_pred"] == "WAIT":
        text += f"📏 *Strategy 1 (3-Circle):* ⏳ Waiting for 3 B/S...\n"
    else:
        s1_icon = "🟠 Big" if state["s1_pred"] == "Big" else "🔵 Small"
        s1_bet = BET_TABLE.get(min(state["s1_level"], 4), 1100)
        text += f"📏 *Strategy 1 (3-Circle):* *{s1_icon}* | 🎯 L{state['s1_level']} (₹{s1_bet})\n"

    # Strategy 2 Text (Stop Trading message when inactive)
    if not state["s2_active"] or state["s2_pred"] == "WAIT":
        text += f"📐 *Strategy 2 (3-Opp):* 🛑 *Stop Trading* (Waiting for 3 B/S)...\n\n"
    else:
        s2_icon = "🟠 Big" if state["s2_pred"] == "Big" else "🔵 Small"
        s2_bet = BET_TABLE.get(min(state["s2_level"], 4), 1100)
        text += f"📐 *Strategy 2 (3-Opp):* *{s2_icon}* | 🎯 L{state['s2_level']} (₹{s2_bet})\n\n"
        
    text += f"💡 _Auto Virtual Betting is ON._"
        
    send_telegram_message_direct(target_chat_id, text)

# 🚀 मल्टी-पेज फेचर
def fetch_history_records(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
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

def update_predictions(state, next_issue_int):
    # --- Strategy 1 Logic (3-Circle Continuous Pattern: 3 Big, 3 Small, 3 Big, 3 Small...) ---
    if not state["s1_active"] and len(state["full_history"]) >= 3:
        last_3_bs = [x["bs"] for x in state["full_history"][:3]]
        if last_3_bs == ["Big", "Big", "Big"]:
            state["s1_active"] = True
            state["s1_base_pred"] = "Small"  # Starts with 3 Smalls block
            state["s1_count"] = 0
            state["s1_level"] = 1
        elif last_3_bs == ["Small", "Small", "Small"]:
            state["s1_active"] = True
            state["s1_base_pred"] = "Big"   # Starts with 3 Bigs block
            state["s1_count"] = 0
            state["s1_level"] = 1
            
    if state["s1_active"]:
        block_idx = (state["s1_count"] // 3) % 2
        if state["s1_base_pred"] == "Small":
            state["s1_pred"] = "Small" if block_idx == 0 else "Big"
        else:
            state["s1_pred"] = "Big" if block_idx == 0 else "Small"
    else:
        state["s1_pred"] = "WAIT"

    # --- Strategy 2 Logic (Wait for 3 Consecutive) ---
    if not state["s2_active"] and len(state["full_history"]) >= 3:
        last_3_bs = [x["bs"] for x in state["full_history"][:3]]
        
        if last_3_bs == ["Big", "Big", "Big"]:
            state["s2_active"] = True
            state["s2_pred"] = "Small"
            state["s2_level"] = 1
        elif last_3_bs == ["Small", "Small", "Small"]:
            state["s2_active"] = True
            state["s2_pred"] = "Big"
            state["s2_level"] = 1
        else:
            state["s2_pred"] = "WAIT"

def process_strategy(state, records):
    if not records: 
        return False
    state["live_records"] = records[:5]
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if not (latest_number_str.isdigit() and latest_issue.isdigit()): return False
    latest_bs = "Big" if int(latest_number_str) >= 5 else "Small"

    existing_issues = {x["issue"] for x in state["full_history"]}
    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss.isdigit() and num_str.isdigit() and iss not in existing_issues:
            bs_val = "Big" if int(num_str) >= 5 else "Small"
            state["full_history"].append({
                "issue": iss, 
                "bs": bs_val, 
                "num": num_str
            })
            existing_issues.add(iss)
                
    state["full_history"].sort(key=lambda x: int(x["issue"]), reverse=True)
    state["full_history"] = state["full_history"][:60]

    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        next_issue_int = int(latest_issue) + 1
        
        update_predictions(state, next_issue_int)
        
        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int))
        return True

    if state["last_processed_issue"] != latest_issue:
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        prev_res_text = f"🎯 Result: *{latest_number_str}* ({latest_bs})\n"
        s1_res_status = "-"
        s2_res_status = "-"
        
        # --- Evaluate Strategy 1 ---
        if state["s1_active"] and state["s1_pred"] != "WAIT":
            state["stats"]["total_trades"] += 1
            s1_bet = BET_TABLE.get(min(state["s1_level"], 4), 1100)
            if state["s1_pred"] == latest_bs:
                state["stats"]["s1_win"] += 1
                state["virtual_balance"] += s1_bet
                state["s1_level"] = 1 # Reset level on Win, stays active continuously
                s1_res_status = f"{state['s1_pred']} ✅ WIN"
                prev_res_text += f"🔹 S1 (3-Circle): ✅ WIN (+₹{s1_bet})\n"
            else:
                state["stats"]["s1_fail"] += 1
                state["virtual_balance"] -= s1_bet
                if state["s1_level"] < 4:
                    state["s1_level"] += 1
                else:
                    state["s1_level"] = 1
                s1_res_status = f"{state['s1_pred']} ❌ FAIL"
                prev_res_text += f"🔹 S1 (3-Circle): ❌ FAIL (-₹{s1_bet})\n"
            
            # Increment count for the 3-circle pattern sequence
            state["s1_count"] += 1
        
        # --- Evaluate Strategy 2 ---
        if state["s2_active"] and state["s2_pred"] != "WAIT":
            s2_bet = BET_TABLE.get(min(state["s2_level"], 4), 1100)
            if state["s2_pred"] == latest_bs:
                state["stats"]["s2_win"] += 1
                state["virtual_balance"] += s2_bet
                state["s2_active"] = False 
                state["s2_level"] = 1
                state["s2_pred"] = "WAIT"
                s2_res_status = f"✅ WIN"
                prev_res_text += f"🔸 S2 (3-Opp): ✅ WIN (+₹{s2_bet}) (Reset to L1)\n"
            else:
                state["stats"]["s2_fail"] += 1
                state["virtual_balance"] -= s2_bet
                if state["s2_level"] < 4:
                    state["s2_level"] += 1  
                else:
                    state["s2_level"] = 1
                    state["s2_active"] = False
                    state["s2_pred"] = "WAIT"
                s2_res_status = f"❌ FAIL"
                prev_res_text += f"🔸 S2 (3-Opp): ❌ FAIL (-₹{s2_bet}) (Moving to L{state['s2_level']})\n"
                
        # Add to recent UI history
        state["history"].append({
            "issue": latest_issue[-4:],
            "s1_pred": state["s1_pred"] if state["s1_active"] else "WAIT",
            "s1_level": f"L{state['s1_level'] - 1 if s1_res_status != '-' else '-'}", 
            "s1_res": "[green]✅ WIN[/]" if "WIN" in s1_res_status else ("[red]❌ FAIL[/]" if "FAIL" in s1_res_status else "-"),
            "s2_pred": state["s2_pred"] if state["s2_active"] else "WAIT",
            "s2_level": f"L{state['s2_level'] - 1 if s2_res_status != '-' else '-'}",
            "s2_res": "[green]✅ WIN[/]" if "WIN" in s2_res_status else ("[red]❌ FAIL[/]" if "FAIL" in s2_res_status else "-")
        })
        if len(state["history"]) > 4: state["history"].pop(0)

        next_issue_int = int(latest_issue) + 1
        
        update_predictions(state, next_issue_int)

        if state["is_running"]:
            if prev_res_text == f"🎯 Result: *{latest_number_str}* ({latest_bs})\n":
                prev_res_text = None
            send_telegram_signal(state, str(next_issue_int), prev_res_text)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def worker_1m():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
    while True:
        records = fetch_history_records(url)
        if records:
            process_strategy(state_1m, records)
        time.sleep(2) 

def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and state["last_processed_issue"].isdigit() else "Next"
    
    # Strat 1 UI
    if not state["s1_active"] or state["s1_pred"] == "WAIT":
        s1_ui_text = "[yellow]WAIT (Waiting for 3 B/S)[/]"
    else:
        s1_color = "dark_orange" if state["s1_pred"] == "Big" else "bright_blue"
        s1_bet = BET_TABLE.get(min(state["s1_level"], 4), 1100)
        s1_ui_text = f"[{s1_color}]{state['s1_pred']}[/] (L{state['s1_level']} - ₹{s1_bet})"
        
    # Strat 2 UI (Stop Trading message when inactive)
    if not state["s2_active"] or state["s2_pred"] == "WAIT":
        s2_ui_text = "[red]🛑 Stop Trading[/] (Waiting for 3 B/S)"
    else:
        s2_color = "dark_orange" if state["s2_pred"] == "Big" else "bright_blue"
        s2_bet = BET_TABLE.get(min(state["s2_level"], 4), 1100)
        s2_ui_text = f"[{s2_color}]{state['s2_pred']}[/] (L{state['s2_level']} - ₹{s2_bet})"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n"
    panel_text += f"📏 [bold]Strategy 1 (3-Circle):[/] {s1_ui_text}\n"
    panel_text += f"📐 [bold]Strategy 2 (3-Opp):[/] {s2_ui_text}\n"
    panel_text += f"🕒 [bold]Status:[/] {timer_status}\n\n"
    panel_text += f"💰 [bold green]Virtual Balance:[/] [bold cyan]₹{state['virtual_balance']}[/]\n"
    panel_text += f"📊 [bold]S1 Stats - W:[/] [green]{state['stats']['s1_win']}[/] | [bold]F:[/] [red]{state['stats']['s1_fail']}[/]\n"
    panel_text += f"📊 [bold]S2 Stats - W:[/] [green]{state['stats']['s2_win']}[/] | [bold]F:[/] [red]{state['stats']['s2_fail']}[/]\n"
    
    hist_table = Table(show_header=True, width=72)
    hist_table.add_column("Iss", justify="center")
    hist_table.add_column("S1 (L)", justify="center")
    hist_table.add_column("S1 Res", justify="center")
    hist_table.add_column("S2 (L)", justify="center")
    hist_table.add_column("S2 Res", justify="center")
    
    if not state["history"]:
        hist_table.add_row("-", "-", "-", "-", "-")
    else:
        for h in state["history"]: 
            s1_p = f"{h['s1_pred'][0]}({h['s1_level']})" if h['s1_pred'] != "WAIT" else "-"
            s2_p = f"{h['s2_pred'][0]}({h['s2_level']})" if h['s2_pred'] != "WAIT" else "-"
            
            hist_table.add_row(
                str(h["issue"]), 
                s1_p, 
                str(h["s1_res"])[0:13],
                s2_p,
                str(h["s2_res"])[0:13]
            )
    
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]{state['name']}[/]", border_style="cyan", width=78)

def create_master_ui():
    p_1m = render_game_panel(state_1m)
    return Group(
        Align.center("[bold yellow]🚀 1 MINUTE DUAL STRATEGY BOT (Virtual Wallet)[/bold yellow]\n"),
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
