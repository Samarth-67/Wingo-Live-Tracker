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
TELEGRAM_TOKEN = "8966011835:AAG48y7RE27x2UkNB68T_7GwdCRKRJe_BpA"

# Telegram Channel ID
TARGET_GROUP_ID = "-1005453711390"  

REG_LINK = "https://www.DamanClub.win/#/register?invitationCode=1614313895334"

# 🔐 सिक्रेट पासवर्ड
PASS_30S = "11111"  
# ----------------------------------------

# ⚡ फास्ट इंटरनेट कनेक्शनसाठी Session
api_session = requests.Session()

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        
        # 🔄 Strategy Variables
        "current_strategy": 1,       # 1: Opposite Pair (S-S-B-B), 2: Trend Follow
        "strategy_start_time": time.time(),
        "wait_for_trigger": True,
        "trigger_type": None,          
        "last_trigger_issue": None,    
        
        "pattern_index": 0,             # 👈 NEW: पॅटर्न सलग चालवण्यासाठी
        "pred_bs": "WAIT",
        "pred_color": "WAIT",
        "pred_nums": [],
        "level": 1,
        
        "full_history": [], 
        "history": [],
        "stats": {"win": 0, "fail": 0, "total_trades": 0},
        "is_running": True,            
        "active_chat_id": None,    
        "live_records": [],
        "last_tg_status": "Ready"
    }

state_30s = create_state("WinGo 30S", "30S")

def send_telegram_message_direct(chat_id, text):
    if not chat_id: return
    
    # 🔗 प्रत्येक मेसेजमध्ये रजिस्ट्रेशन लिंक जोडली आहे
    final_text = f"{text}\n\n🔗 <b>Register Link:</b> {REG_LINK}" 
    
    def _send():
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": final_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True  # 🚫 डिस्क्रिप्शन बॉक्स / वेब प्रिव्ह्यू काढून टाकला आहे
        }
        try:
            res = api_session.post(url, json=payload, timeout=5)
            if res.status_code == 200:
                state_30s["last_tg_status"] = "✅ Sent Successfully"
            else:
                state_30s["last_tg_status"] = f"❌ Error {res.status_code}: {res.text[:30]}"
                if "-100" in str(chat_id):
                    fallback_id = str(chat_id).replace("-100", "-")
                    payload["chat_id"] = fallback_id
                    api_session.post(url, json=payload, timeout=5)
        except Exception as e:
            state_30s["last_tg_status"] = f"❌ Network Fail: {str(e)[:20]}"

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
                    
                    message = result.get("message") or result.get("channel_post") or {}
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "").strip()

                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = True
                            state_30s["active_chat_id"] = chat_id
                            send_telegram_message_direct(chat_id, "✅ <b>[Dual Strategy Bot]</b> Activated! Live Prediction is ON.")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                            
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 <b>Bot Stopped Successfully!</b>")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, prev_res_text=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    game_name = state["name"]
    strat_name = "Pair Pattern (S-S-B-B)" if state["current_strategy"] == 1 else "Trend Following"
    
    text = f"🚀 <b>{game_name} Signal</b> 🚀\n"
    text += f"⚙️ <b>Strategy {state['current_strategy']}:</b> {strat_name}\n\n"
    
    if prev_res_text:
        text += f"📊 <b>मागील निकाल:</b>\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ <b>Next Issue:</b> <code>{issue}</code>\n\n"
    
    if state["wait_for_trigger"] or state["pred_bs"] == "WAIT":
        text += f"⏳ Waiting for Trigger (2 Big or 2 Small)...\n\n"
    else:
        icon = "🟠 BIG" if state["pred_bs"] == "Big" else "🔵 SMALL"
        text += f"🎯 <b>Prediction:</b> <b>{icon}</b>\n"
        text += f"💰 <b>Level:</b> L{state['level']} (Max L6)\n\n"
        
    text += f"💡 <i>Bet according to your level progression.</i>"
    
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
    return all_records

def extract_digits(s):
    digits = ''.join(filter(str.isdigit, str(s)))
    return int(digits) if digits else 0

def check_time_shuffle(state):
    if time.time() - state["strategy_start_time"] >= 3600:
        old_strat = state["current_strategy"]
        state["current_strategy"] = 2 if state["current_strategy"] == 1 else 1
        state["strategy_start_time"] = time.time()
        state["wait_for_trigger"] = True
        state["level"] = 1
        state["pattern_index"] = 0
        if state["is_running"]:
            msg = f"⏱ <b>1 Hour Completed!</b> Strategy Auto-Shuffled from S{old_strat} to S{state['current_strategy']}.\nWaiting for new trigger..."
            send_telegram_message_direct(TARGET_GROUP_ID, msg)

def update_predictions(state, next_issue_int, latest_color):
    check_time_shuffle(state)
    
    if state["wait_for_trigger"]:
        if len(state["full_history"]) >= 2:
            last_2 = [x["bs"] for x in state["full_history"][:2]]
            last_2_issues = [x["issue"] for x in state["full_history"][:2]]
            
            if last_2[0] == last_2[1] and last_2_issues[0] != state["last_trigger_issue"]:
                state["wait_for_trigger"] = False
                state["trigger_type"] = last_2[0]
                state["last_trigger_issue"] = last_2_issues[0]
                state["level"] = 1
                state["pattern_index"] = 0 # 👈 नवीन ट्रिगर मिळताच पॅटर्न 0 पासून सुरू
        
        if state["wait_for_trigger"]:
            state["pred_bs"] = "WAIT"
            return

    # Strategy 1: Strict Pair Pattern (2 Small, 2 Big)
    if state["current_strategy"] == 1:
        if state["trigger_type"] == "Big":
            sequence = ["Small", "Small", "Big", "Big"] # 👈 हा लूप गोल गोल फिरत राहील
        else:
            sequence = ["Big", "Big", "Small", "Small"] # 👈 हा लूप गोल गोल फिरत राहील
            
        if state["level"] <= 6:
            # pattern_index % 4 केल्यामुळे तो 0,1,2,3 पुन्हा 0,1,2,3 असा फिरत राहील
            state["pred_bs"] = sequence[state["pattern_index"] % 4]
        else:
            state["pred_bs"] = "WAIT"

    # Strategy 2: Trend Following Strategy
    elif state["current_strategy"] == 2:
        if len(state["full_history"]) >= 1:
            state["pred_bs"] = state["full_history"][0]["bs"]
        else:
            state["pred_bs"] = "WAIT"

def process_strategy(state, records):
    if not records: return False
    state["live_records"] = records[:5]
    
    existing_issues = {x["issue"] for x in state["full_history"]}
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
        if state["is_running"]: 
            send_telegram_signal(state, str(next_issue_int))
        return True

    if state["last_processed_issue"] != latest_issue:
        if extract_digits(latest_issue) <= extract_digits(state["last_processed_issue"]): return False  

        prev_res_text = f"🎯 Result: <b>{latest_number_str}</b> ({latest_bs})\n"
        res_status = "-"
        current_logged_level = state["level"]

        if not state["wait_for_trigger"] and state["pred_bs"] != "WAIT":
            state["stats"]["total_trades"] += 1
            
            if state["pred_bs"] == latest_bs:
                state["stats"]["win"] += 1
                res_status = f"{state['pred_bs']} ✅ WIN"
                prev_res_text += f"🔹 Match: ✅ WIN (L{state['level']})\n🔄 <b>Continuing Pattern...</b>\n"
                
                state["level"] = 1
                state["pattern_index"] += 1 # 👈 WIN झाल्यावरही पॅटर्न पुढे जाईल (त्यामुळे ४ वेळा Small येणार नाही)
                
            else:
                state["stats"]["fail"] += 1
                res_status = f"{state['pred_bs']} ❌ FAIL"
                prev_res_text += f"🔹 Match: ❌ FAIL\n"
                
                state["level"] += 1
                state["pattern_index"] += 1 # 👈 FAIL झाल्यावरही पॅटर्न पुढे जाईल

                # ६ वी लेव्हल फेल केल्यास स्ट्रॅटेजी स्विच करणे
                if state["level"] > 6:
                    old_strat = state["current_strategy"]
                    state["current_strategy"] = 2 if state["current_strategy"] == 1 else 1
                    state["strategy_start_time"] = time.time()
                    state["wait_for_trigger"] = True
                    state["level"] = 1
                    state["pattern_index"] = 0
                    
                    prev_res_text += f"\n⚠️ <b>Level 6 Failed!</b> Switching Strategy from S{old_strat} to S{state['current_strategy']}.\n⏳ Waiting for New Trigger..."

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
            if prev_res_text == f"🎯 Result: <b>{latest_number_str}</b> ({latest_bs})\n":
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
        ui_text = f"[{s_color}]{state['pred_bs']}[/] | Level: L{state['level']} (Max: L6)"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    strat_name = "S-S-B-B Pattern" if state["current_strategy"] == 1 else "Trend Follow"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n"
    panel_text += f"⚙️ [bold]Strategy {state['current_strategy']}:[/] {strat_name}\n"
    panel_text += f"📏 [bold]Prediction:[/] {ui_text}\n"
    panel_text += f"🕒 [bold]Status:[/] {timer_status} | Stats - W: [green]{state['stats']['win']}[/] F: [red]{state['stats']['fail']}[/]\n"
    panel_text += f"📡 [bold]Telegram Status:[/] [cyan]{state['last_tg_status']}[/]\n\n"
    
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
            
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]Dual Strategy Continuous Bot[/]", border_style="cyan", width=78)

def create_master_ui():
    p_30s = render_game_panel(state_30s)
    return Group(
        Align.center("[bold yellow]🚀 30S DUAL STRATEGY BOT (NON-STOP)[/bold yellow]\n"),
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
