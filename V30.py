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
TARGET_GROUP_ID = "-5202202128"  # <--- चॅनेल/ग्रुपचा आयडी

# 🔐 सिक्रेट पासवर्ड
PASS_30S = "11111"   
# ----------------------------------------

api_session = requests.Session()

# 🚀 Updated Number Prediction Logic (Connecting Pair: 3, 6 etc.)
def get_number_prediction(curr_num_str, prev_num_str, r20_num_str):
    # १) जर २० व्या राऊंडला Violet (0 किंवा 5) आला असेल -> "0, 5"
    if r20_num_str and str(r20_num_str).isdigit():
        r20_num = int(r20_num_str)
        if r20_num in [0, 5]:
            return "0, 5"

    if not curr_num_str or not str(curr_num_str).isdigit():
        return "WAIT"

    curr_num = int(curr_num_str)
    
    # कनेक्टिंग/पेअर नंबर मॅपिंग (उदा. 1 -> 3, 8 -> 6)
    mapping = {
        1: 3, 3: 1,
        2: 4, 4: 2,
        6: 8, 8: 6,
        7: 9, 9: 7,
        0: 5, 5: 0
    }
    
    curr_mapped = mapping.get(curr_num, curr_num)
    
    if prev_num_str and str(prev_num_str).isdigit():
        prev_num = int(prev_num_str)
        prev_mapped = mapping.get(prev_num, prev_num)
        # दोन्ही नंबर एकत्र करून पेअर प्रेडिक्शन देणे (उदा. 3 आणि 6 -> "3, 6")
        return f"{curr_mapped}, {prev_mapped}"
    
    return str(curr_mapped)

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        "target_issue": "WAIT",
        
        "bs_pred": "WAIT", 
        "num_pred": "WAIT",
        
        "bs_level": 1, 
        "num_level": 1,
        
        "full_history": [], 
        "history": [],
        "pending_preds": {}, 
        "stats": {"bs_win": 0, "bs_fail": 0, "num_win": 0, "num_fail": 0, "total_trades": 0},
        "is_running": False,       
        "active_chat_id": None,   
        "live_records": []
    }

state_30s = create_state("WinGo 30S", "30S")

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

                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = True
                            state_30s["active_chat_id"] = chat_id
                            send_telegram_message_direct(chat_id, f"✅ *[30S Strategy] Activated! Live Prediction (Pair Mode) is ON.*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
                                
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *[30S Strategy] Stopped Successfully!*")
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.")
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, bs_pred, num_pred, bs_level, num_level, prev_res_text=None):
    target_chat_id = TARGET_GROUP_ID
    if not target_chat_id: return

    game_name = state["name"]
    text = f"🚀 *VSR {game_name} Follower* 🚀\n\n"
    
    if state["stats"]["total_trades"] > 0 and prev_res_text:
        text += f"🔄 *Last Trade Result:*\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *New Target Issue:* {issue}\n\n"
    
    if bs_pred == "WAIT" or num_pred == "WAIT":
        text += f"⏳ *Building History Data...*\n_Waiting for enough data to sync..._\n"
    else:
        bs_pred_text = "🟠 Big" if bs_pred == "Big" else "🔵 Small"
        text += f"📏 *B/S Pred:* *{bs_pred_text}* | 🎯 L{bs_level}\n"
        text += f"🔢 *Number Pred:* *{num_pred}* | 🎯 L{num_level}\n\n" 
        
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
        response = api_session.get(url, headers=headers, params=params, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and isinstance(data["data"], list): all_records.extend(data["data"])
            elif "list" in data and isinstance(data["list"], list): all_records.extend(data["list"])
            elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: all_records.extend(data["data"]["list"])
    except Exception:
        pass
    return all_records

def process_strategy(state, records):
    if not records or len(records) < 2: return False
    state["live_records"] = records[:5]
    
    latest_item = records[0] # उदा. 372
    prev_item = records[1]   # उदा. 371
    
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    prev_number_str = str(prev_item.get("number") or prev_item.get("drawNumber") or "-")
    
    if not (latest_number_str.isdigit() and latest_issue.isdigit()): return False
    latest_bs = "Big" if int(latest_number_str) >= 5 else "Small"

    # मेमरीमध्ये रेकॉर्ड्स सेव्ह करणे
    existing_issues = {x["issue"] for x in state["full_history"]}
    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss.isdigit() and num_str.isdigit() and iss not in existing_issues:
            bs_val = "Big" if int(num_str) >= 5 else "Small"
            state["full_history"].append({"issue": iss, "bs": bs_val, "num": num_str})
            existing_issues.add(iss)
                
    state["full_history"].sort(key=lambda x: int(x["issue"]), reverse=True)
    state["full_history"] = state["full_history"][:60]

    # बॉट पहिल्यांदा चालू झाल्यावर
    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        
        target_issue_int = int(latest_issue) + 2
        target_issue_str = str(target_issue_int)
        
        target_issue_for_bs = str(target_issue_int - 20)
        target_record = next((x for x in state["full_history"] if x["issue"] == target_issue_for_bs), None)
        
        r20_num = None
        if target_record:
            bs_pred = target_record["bs"]
            r20_num = target_record["num"]
        elif len(state["full_history"]) >= 20:
            bs_pred = state["full_history"][19]["bs"]
            r20_num = state["full_history"][19]["num"]
        else:
            bs_pred = "WAIT"

        # दोन्ही नंबर पास करणे (Latest आणि Previous)
        num_pred = get_number_prediction(latest_number_str, prev_number_str, r20_num)
        
        state["bs_pred"] = bs_pred
        state["num_pred"] = num_pred
        state["target_issue"] = target_issue_str
        
        state["pending_preds"][target_issue_str] = {
            "bs_pred": bs_pred,
            "num_pred": num_pred,
            "bs_level": state["bs_level"],
            "num_level": state["num_level"]
        }
        
        if state["is_running"]:
            send_telegram_signal(state, target_issue_str, state["bs_pred"], state["num_pred"], state["bs_level"], state["num_level"])
        return True

    # जेव्हा नवीन राऊंडचा निकाल येईल
    if state["last_processed_issue"] != latest_issue:
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        prev_res_text = ""
        
        if latest_issue in state["pending_preds"]:
            pred_data = state["pending_preds"][latest_issue]
            state["stats"]["total_trades"] += 1
            
            bs_win = (pred_data["bs_pred"] == latest_bs)
            bs_emoji = "🟠" if pred_data["bs_pred"] == "Big" else "🔵"

            num_win = str(latest_number_str) in [n.strip() for n in pred_data["num_pred"].split(",")]
            
            bs_mark = "✅" if bs_win else "❌"
            num_mark = "✅" if num_win else "❌" 
            
            prev_res_text = (
                f"📏 B/S: *{latest_bs}* {bs_mark}\n"
                f"🔢 Num: *{latest_number_str}* {num_mark}"
            )
            
            current_bs_level = pred_data["bs_level"]
            current_num_level = pred_data["num_level"] 
            
            if bs_win:
                state["stats"]["bs_win"] += 1
                state["bs_level"] = 1
                prev_res_text += f"\n\n🔥🎉 *CONGRATS! B/S WIN!* 🎉🔥"
            else:
                state["stats"]["bs_fail"] += 1
                state["bs_level"] += 1
                
            if num_win:
                state["stats"]["num_win"] += 1
                state["num_level"] = 1
                if not bs_win: prev_res_text += f"\n"
                prev_res_text += f"\n🔢🎉 *CONGRATS! NUMBER WIN!* 🎉🔢"
            else:
                state["stats"]["num_fail"] += 1
                state["num_level"] += 1
                    
            state["history"].append({
                "trade": state["stats"]["total_trades"], 
                "issue": latest_issue[-4:],
                "bs_level": f"L{current_bs_level}", 
                "bs_pred": pred_data["bs_pred"],
                "bs_res": "[green]✅ WIN[/]" if bs_win else "[red]❌ FAIL[/]",
                "num_level": f"L{current_num_level}",
                "num_pred": pred_data["num_pred"],
                "num_res": "[green]✅ WIN[/]" if num_win else "[red]❌ FAIL[/]"
            })
            if len(state["history"]) > 4: state["history"].pop(0)
            
            del state["pending_preds"][latest_issue]

        # --- नवीन प्रेडिक्शन जनरेट करणे (Latest Issue + 2) ---
        next_target_issue_int = int(latest_issue) + 2
        next_target_issue_str = str(next_target_issue_int)
        
        bs_target_issue_for_bs = str(next_target_issue_int - 20)
        target_record = next((x for x in state["full_history"] if x["issue"] == bs_target_issue_for_bs), None)
        
        r20_num = None
        if target_record:
            bs_pred = target_record["bs"]
            r20_num = target_record["num"]
        elif len(state["full_history"]) >= 20:
            bs_pred = state["full_history"][19]["bs"]
            r20_num = state["full_history"][19]["num"]
        else:
            bs_pred = "WAIT"

        num_pred = get_number_prediction(latest_number_str, prev_number_str, r20_num)

        state["bs_pred"] = bs_pred
        state["num_pred"] = num_pred
        state["target_issue"] = next_target_issue_str

        state["pending_preds"][next_target_issue_str] = {
            "bs_pred": bs_pred,
            "num_pred": num_pred,
            "bs_level": state["bs_level"],
            "num_level": state["num_level"]
        }

        if state["is_running"]:
            send_telegram_signal(state, next_target_issue_str, state["bs_pred"], state["num_pred"], state["bs_level"], state["num_level"], prev_res_text)

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
    target_iss = state.get("target_issue", "Wait")
    
    if state["bs_pred"] == "WAIT" or state["num_pred"] == "WAIT":
        ui_text = "[yellow]WAIT (Syncing...)[/]"
        num_text = "WAIT"
    else:
        bs_color = "dark_orange" if state["bs_pred"] == "Big" else "bright_blue"
        ui_text = f"[{bs_color}]{state['bs_pred']}[/] (L{state['bs_level']})"
        num_text = f"[bold magenta]{state['num_pred']}[/] (L{state['num_level']})" 
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Target Issue: {target_iss}[/]\n"
    panel_text += f"📏 [bold]B/S Pred:[/] {ui_text}\n"
    panel_text += f"🔢 [bold]Num Pred:[/] {num_text}\n"
    panel_text += f"🕒 [bold]Status:[/] {timer_status}\n\n"
    panel_text += f"📊 [bold]B/S Stats  - W:[/] [green]{state['stats']['bs_win']}[/] | [bold]F:[/] [red]{state['stats']['bs_fail']}[/]\n"
    panel_text += f"🔢 [bold]Num Stats  - W:[/] [green]{state['stats']['num_win']}[/] | [bold]F:[/] [red]{state['stats']['num_fail']}[/]\n" 
    
    hist_table = Table(show_header=True, width=70) 
    hist_table.add_column("Iss", justify="center")
    hist_table.add_column("B/S(L)", justify="center")
    hist_table.add_column("B-Res", justify="center")
    hist_table.add_column("Num(L)", justify="center") 
    hist_table.add_column("N-Res", justify="center") 
    
    if not state["history"]:
        hist_table.add_row("-", "-", "-", "-", "-")
    else:
        for h in state["history"]: 
            hist_table.add_row(
                str(h["issue"]), 
                f"{h['bs_pred'][0]}({h['bs_level']})", 
                str(h["bs_res"])[0:13],
                f"{h['num_pred']}({h['num_level']})",
                str(h["num_res"])[0:13] 
            )
    
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]{state['name']}[/]", border_style="cyan", width=76)

def create_master_ui():
    p_30s = render_game_panel(state_30s)
    return Group(
        Align.center("[bold yellow]🚀 30S SUPERFAST BOT (Connecting Pair Mode Fixed)[/bold yellow]\n"),
        Align.center(p_30s)
    )

if __name__ == "__main__":
    t_list = threading.Thread(target=telegram_listener, daemon=True)
    t_30s = threading.Thread(target=worker_30s, daemon=True)
    
    t_list.start(); t_30s.start()

    with Live(create_master_ui(), console=console, refresh_per_second=4, screen=False) as live:
        while True:
            live.update(create_master_ui())
            time.sleep(0.5)
