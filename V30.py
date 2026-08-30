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
TELEGRAM_TOKEN = "8577275461:AAF8lWPac3WCgbHp8XPvU_lO289oHcMdOE8" 
TARGET_GROUP_ID = "-5202202128"  
PASS_30S = "11111"   
# ----------------------------------------

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        "bs_pred": "WAIT", 
        "bs_level": 1, 
        
        # 💰 फंड मॅनेजमेंट (Virtual Wallet, Safe Mode & Auto-Withdrawal)
        "balance": 20000.0,  # सुरुवातीचा फंड
        # 👇 नवीन ६ लेव्हल्स सेट केल्या आहेत (50, 120, 250, 600, 1200, 2400)
        "bet_amounts": {1: 50, 2: 120, 3: 250, 4: 600, 5: 1200, 6: 2400}, 
        "total_withdrawn": 0.0, # एकूण काढलेली रक्कम
        "withdrawal_count": 0,  # किती वेळा काढले
        
        "full_history": [], # 🚀 बॉटची स्वतःची अचूक मेमरी
        "history": [],
        "stats": {"bs_win": 0, "bs_fail": 0, "total_trades": 0},
        "is_running": False,       
        "active_chat_id": None,   
        "live_records": []
    }

state_30s = create_state("WinGo 30S", "30S")

def send_telegram_message_direct(chat_id, text):
    if not chat_id: return
    # 🚀 Async Background Sending (मेसेज फास्ट जाईल)
    def _send():
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=3)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()

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

                    # 🟢 START BOT
                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = True
                            state_30s["active_chat_id"] = chat_id
                            send_telegram_message_direct(chat_id, f"✅ *[30S Strategy] Activated! Live Prediction is ON.*\n💰 *Initial Fund:* ₹20,000")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    # 🔴 STOP BOT
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *[30S Strategy] Stopped Successfully!*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                    
                    # 🔄 RESET WALLET COMMAND
                    elif text.startswith("/reset"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["balance"] = 20000.0
                            state_30s["total_withdrawn"] = 0.0
                            state_30s["withdrawal_count"] = 0
                            state_30s["bs_level"] = 1
                            state_30s["bs_pred"] = "WAIT"
                            send_telegram_message_direct(chat_id, "🔄 *Wallet Reset Successfully!*\n💰 *Current Balance:* ₹20,000\n🏦 *Withdrawal History Cleared.*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, bs_pred, bs_level, prev_bs_res=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    game_name = state["name"]
    text = f"🚀 *VSR {game_name} Trend Follower* 🚀\n\n"
    
    if state["stats"]["total_trades"] > 0 and prev_bs_res and prev_bs_res != "-":
        text += f"🔄 *Last Trade Result:*\n"
        text += f"📏 B/S: *{prev_bs_res}*\n"
        if "WIN" in prev_bs_res: text += f"\n🔥🎉 *CONGRATS! WIN!* 🎉🔥\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *New Issue:* {issue}\n"
    text += f"💰 *Current Balance:* ₹{state['balance']:.2f}\n"
    
    # जर विड्रॉवल झाले असेल तरच दाखवा
    if state['total_withdrawn'] > 0:
        text += f"🏦 *Total Withdrawn:* ₹{state['total_withdrawn']:.0f} ({state['withdrawal_count']} times)\n"
    text += "\n"
    
    if bs_pred == "WAIT":
        text += f"⏳ *Building History Data...*\n_Waiting for issue {int(issue)-20} to sync..._\n"
    else:
        bs_pred_text = "🟠 Big" if bs_pred == "Big" else "🔵 Small"
        current_bet = state["bet_amounts"].get(bs_level, 0) # लेव्हल ७+ असेल तर रक्कम ० (Virtual Mode)
        
        text += f"📏 *Prediction:* *{bs_pred_text}*\n"
        text += f"🎯 *Level:* L{bs_level}\n"
        
        # 🛡️ Virtual Mode चा मेसेज 
        if current_bet > 0:
            text += f"💵 *Bet Amount:* ₹{current_bet}\n\n"
        else:
            text += f"🛡️ *Bet Amount:* ₹0 (Virtual Mode / Safe)\n\n"
        
    send_telegram_message_direct(target_chat_id, text)

def fetch_history_records(url, state):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://draw.ar-lottery01.com/",
    }
    all_records = []
    
    try:
        params = {"pageSize": 30, "pageNo": 1, "ts": int(time.time() * 1000)}
        response = requests.get(url, headers=headers, params=params, timeout=3)
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
                response = requests.get(url, headers=headers, params=params, timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and isinstance(data["data"], list): all_records.extend(data["data"])
                    elif "list" in data and isinstance(data["list"], list): all_records.extend(data["list"])
                    elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: all_records.extend(data["data"]["list"])
            except Exception:
                pass
            
    return all_records

def process_strategy(state, records):
    if not records: return False
    state["live_records"] = records[:5]
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if not (latest_number_str.isdigit() and latest_issue.isdigit()): return False
    latest_bs = "Big" if int(latest_number_str) >= 5 else "Small"

    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss.isdigit() and num_str.isdigit():
            if not any(x["issue"] == iss for x in state["full_history"]):
                bs_val = "Big" if int(num_str) >= 5 else "Small"
                state["full_history"].append({"issue": iss, "bs": bs_val})
                
    state["full_history"].sort(key=lambda x: int(x["issue"]), reverse=True)
    state["full_history"] = state["full_history"][:60]

    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        next_issue_int = int(latest_issue) + 1
        target_issue_str = str(next_issue_int - 20) 
        
        target_record = next((x for x in state["full_history"] if x["issue"] == target_issue_str), None)
        
        if target_record:
            state["bs_pred"] = target_record["bs"]
        elif len(state["full_history"]) >= 20:
            state["bs_pred"] = state["full_history"][19]["bs"] 
        else:
            state["bs_pred"] = "WAIT"
        
        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int), state["bs_pred"], state["bs_level"])
        return True

    if state["last_processed_issue"] != latest_issue:
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        bs_res_status = "-"
        
        if state["bs_pred"] != "WAIT":
            state["stats"]["total_trades"] += 1
            bs_win = (state["bs_pred"] == latest_bs)
            bs_emoji = "🟠" if state["bs_pred"] == "Big" else "🔵"
            
            # 💰 सध्याच्या लेव्हलचा फंड (लेव्हल ७ किंवा पुढे ० रुपये असेल)
            current_bet = state["bet_amounts"].get(state["bs_level"], 0)
            
            if bs_win:
                state["stats"]["bs_win"] += 1
                
                # जर रिअल ट्रेडिंग असेल (L1 ते L6)
                if current_bet > 0:
                    net_profit = current_bet * 0.96 # (०.९६ पट प्रॉफिट)
                    state["balance"] += net_profit
                    bs_res_status = f"{bs_emoji} {state['bs_pred']} ✅ WIN (+₹{net_profit:.0f})"
                else:
                    # जर Virtual Mode मध्ये जिंकला (L7+)
                    bs_res_status = f"{bs_emoji} {state['bs_pred']} ✅ WIN (Virtual Mode)"
                
                # जिंकल्यावर कोणतीही लेव्हल असो, पुन्हा लेव्हल १ वर रिसेट
                old_level = state["bs_level"]
                state["bs_level"] = 1 
            else:
                state["stats"]["bs_fail"] += 1
                
                # जर रिअल ट्रेडिंग असेल (L1 ते L6)
                if current_bet > 0:
                    state["balance"] -= current_bet
                    bs_res_status = f"{bs_emoji} {state['bs_pred']} ❌ FAIL (-₹{current_bet})"
                else:
                    # जर Virtual Mode मध्ये हरला (L7+)
                    bs_res_status = f"{bs_emoji} {state['bs_pred']} ❌ FAIL (Virtual Mode)"
                
                # हरल्यावर पुढची लेव्हल घेणे (७, ८, ९... Virtual मध्ये चालत राहील)
                old_level = state["bs_level"]
                state["bs_level"] += 1
            
            # 🏦 AUTO-WITHDRAWAL LOGIC (Principal २०,००० + Profit ४,००० = २४,०००)
            # जेव्हा बॅलन्स २४,००० किंवा त्याहून अधिक होईल, तेव्हाच ४,००० विड्रॉ होतील आणि २०,००० तसेच राहतील.
            while state["balance"] >= 24000.0:
                state["balance"] -= 4000.0
                state["total_withdrawn"] += 4000.0
                state["withdrawal_count"] += 1
                bs_res_status += "\n🎉 *AUTO-WITHDRAW: ₹4000 Transferred!*"

            state["history"].append({
                "trade": state["stats"]["total_trades"], "issue": latest_issue[-4:],
                "bs_level": f"L{old_level}", 
                "bs_pred": state["bs_pred"],
                "bs_res": "[green]WIN[/]" if "WIN" in bs_res_status else "[red]FAIL[/]"
            })
            if len(state["history"]) > 4: state["history"].pop(0)

        next_issue_int = int(latest_issue) + 1
        target_issue_str = str(next_issue_int - 20)
        
        target_record = next((x for x in state["full_history"] if x["issue"] == target_issue_str), None)
        
        if target_record:
            state["bs_pred"] = target_record["bs"]
        elif len(state["full_history"]) >= 20:
            state["bs_pred"] = state["full_history"][19]["bs"]
        else:
            state["bs_pred"] = "WAIT"

        if state["is_running"]:
            send_telegram_signal(state, str(next_issue_int), state["bs_pred"], state["bs_level"], bs_res_status)

        state["last_processed_issue"] = latest_issue
        return True
    return False

def worker_30s():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
    while True:
        records = fetch_history_records(url, state_30s)
        if records:
            process_strategy(state_30s, records)
        time.sleep(1)

def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and state["last_processed_issue"].isdigit() else "Next"
    
    if state["bs_pred"] == "WAIT":
        ui_text = "[yellow]WAIT (Syncing...)[/]"
    else:
        bs_color = "dark_orange" if state["bs_pred"] == "Big" else "bright_blue"
        current_bet = state["bet_amounts"].get(state["bs_level"], 0)
        ui_text = f"[{bs_color}]{state['bs_pred']}[/] (L{state['bs_level']} - ₹{current_bet})"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n📏 [bold]Pred:[/] {ui_text}\n"
    panel_text += f"💰 [bold green]Wallet:[/] ₹{state['balance']:.2f}\n"
    
    if state['total_withdrawn'] > 0:
        panel_text += f"🏦 [bold magenta]Withdrawn:[/] ₹{state['total_withdrawn']:.0f} ({state['withdrawal_count']}x)\n"
        
    panel_text += f"🕒 [bold]Status:[/] {timer_status}\n\n"
    panel_text += f"📊 [bold]W:[/] [green]{state['stats']['bs_win']}[/] | [bold]F:[/] [red]{state['stats']['bs_fail']}[/]\n"
    
    hist_table = Table(show_header=False, width=42)
    hist_table.add_column("Issue", justify="center")
    hist_table.add_column("Level", justify="center")
    hist_table.add_column("Pred", justify="center")
    hist_table.add_column("Res", justify="center")
    
    if not state["history"]:
        hist_table.add_row("-", "-", "-", "-")
    else:
        for h in state["history"]: 
            hist_table.add_row(str(h["issue"]), str(h["bs_level"]), str(h["bs_pred"]), str(h["bs_res"]))
    
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]{state['name']} (Fund Manager)[/]", border_style="cyan", width=48)

def create_master_ui():
    p_30s = render_game_panel(state_30s)
    return Group(
        Align.center("[bold yellow]🚀 30S BOT (6-Level Safe Mode)[/bold yellow]\n"),
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
