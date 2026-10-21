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

# ----------------- TELEGRAM CREDENTIALS -----------------
TELEGRAM_TOKEN = "8774822707:AAHTXG3lJfY8EBrG092ugDIeUHr8MfWFZHs"
TARGET_GROUP_ID = "-3992547967" 
PASS_30S = "1234"  # Telegram bot start/stop password
# --------------------------------------------------------

api_session = requests.Session()

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        
        # --- नवीन स्ट्रॅटेजी व्हेरिएबल्स ---
        "pred_bs": "WAIT",
        "level": 1,
        
        "full_history": [], 
        "history": [],
        "stats": {"win": 0, "fail": 0, "total_trades": 0},
        "is_running": False,        
        "active_chat_id": None,    
        "live_records": [],
        "telegram_status": "Waiting for command..."
    }

state_30s = create_state("WinGo 30S", "30S")

def send_telegram_message_direct(chat_id, text, state):
    if not chat_id: return
    
    # 🔗 रजिस्ट्रेशन लिंक 
    reg_link = "\n\n🔗 *Register Here:* https://www.DamanClub.win/#/register?invitationCode=1614313895334"
    if reg_link not in text:
        text += reg_link

    def _send():
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try:
            response = api_session.post(url, json={
                "chat_id": chat_id, 
                "text": text, 
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }, timeout=5)
            
            if response.status_code != 200:
                state["telegram_status"] = f"[red]Error {response.status_code}: {response.text}[/red]"
            else:
                state["telegram_status"] = "[green]OK (Message Sent)[/green]"
        except Exception as e:
            state["telegram_status"] = f"[red]Network Error: {e}[/red]"
            
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
                            send_telegram_message_direct(chat_id, f"✅ *[Target -20th Round Bot]* Activated!\nबॉट सुरू झाला आहे. आता तो अखंडपणे जुन्या 20 व्या राउंडचा रिझल्ट प्रेडिक्ट करेल.", state_30s)
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.", state_30s)
                            
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_30S:
                            state_30s["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *Bot Stopped Successfully!*", state_30s)
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.", state_30s)
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, prev_res_text=None, target_issue=None):
    target_chat_id = state.get("active_chat_id") or TARGET_GROUP_ID
    if not target_chat_id: return

    text = f"🚀 *{state['name']} Signal* 🚀\n"
    text += f"⚙️ *Strategy:* -20th Round Result\n\n"
    
    if prev_res_text:
        text += f"📊 *मागील निकाल:*\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Next Issue:* `{issue}`\n"
    if target_issue:
        text += f"🔍 *Targeting Issue:* `{target_issue}`\n\n"
    else:
        text += "\n"
    
    if state["pred_bs"] == "WAIT":
         text += f"⏳ *Waiting for sufficient history (at least 20 rounds)...\n\n"
    else:
        icon = "🟠 Big" if state["pred_bs"] == "Big" else "🔵 Small"
        text += f"🎯 *Prediction:* *{icon}*\n"
        text += f"💰 *Level:* L{state['level']}\n\n"
        text += f"💡 _Bet according to your level._"
        
    send_telegram_message_direct(target_chat_id, text, state)

def fetch_history_records(url, state):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://draw.ar-lottery01.com/",
    }
    all_records = []
    try:
        params = {"pageSize": 50, "pageNo": 1, "ts": int(time.time() * 1000)} # PageSize 50 केलाय जेणेकरून 20 राउंड मागे बघता येईल
        response = api_session.get(url, headers=headers, params=params, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and isinstance(data["data"], list): all_records.extend(data["data"])
            elif "list" in data and isinstance(data["list"], list): all_records.extend(data["list"])
            elif "data" in data and isinstance(data["data"], dict) and "list" in data["data"]: all_records.extend(data["data"]["list"])
    except Exception:
        pass
    return all_records

def get_target_result(state, target_issue_str):
    """
    history मधून विशिष्ट issue चा रिझल्ट (Big/Small) शोधून काढणे.
    """
    for item in state["full_history"]:
        if item["issue"] == target_issue_str:
            return item["bs"]
    return None

def process_strategy(state, records):
    if not records: return False
    state["live_records"] = records[:5]
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if not (latest_number_str.isdigit() and latest_issue.isdigit()): return False
    
    num_int = int(latest_number_str)
    latest_bs = "Big" if num_int >= 5 else "Small"

    # History Update
    existing_issues = {x["issue"] for x in state["full_history"]}
    for rec in records:
        iss = str(rec.get("issueNumber") or rec.get("issue") or "")
        num_str = str(rec.get("number") or rec.get("drawNumber") or "")
        if iss.isdigit() and num_str.isdigit() and iss not in existing_issues:
            n_val = int(num_str)
            state["full_history"].append({
                "issue": iss, 
                "bs": "Big" if n_val >= 5 else "Small", 
                "num": num_str
            })
            existing_issues.add(iss)
                
    state["full_history"].sort(key=lambda x: int(x["issue"]), reverse=True)
    state["full_history"] = state["full_history"][:100] # जास्त रेकॉर्ड्स साठवा

    next_issue_int = int(latest_issue) + 1
    # नवीन स्ट्रॅटेजी: चालू असलेल्या इश्यूमधून 20 वजा करून त्या राउंडचा रिझल्ट प्रेडिक्ट करा
    # जर next_issue_int 550 असेल, तर target_issue_int 530 असायला हवा.
    target_issue_int = next_issue_int - 20 
    target_issue_str = str(target_issue_int)

    # Initial Setup
    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        
        target_bs = get_target_result(state, target_issue_str)
        if target_bs:
            state["pred_bs"] = target_bs
        else:
            state["pred_bs"] = "WAIT" # जर 20 राउंडची हिस्ट्री नसेल तर WAIT करेल
            
        if state["is_running"]: send_telegram_signal(state, str(next_issue_int), target_issue=target_issue_str)
        return True

    # Process New Issue
    if state["last_processed_issue"] != latest_issue:
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        prev_res_text = f"🎯 Result: *{latest_number_str}* ({latest_bs})\n"
        res_status = "-"
        current_logged_level = state["level"]

        # 1. प्रेडिक्शनचे मूल्यमापन (Win/Loss चेक करणे)
        if state["pred_bs"] != "WAIT":
            state["stats"]["total_trades"] += 1
            
            if state["pred_bs"] == latest_bs:
                state["stats"]["win"] += 1
                res_status = f"{state['pred_bs']} ✅ WIN"
                prev_res_text += f"🔹 Match: ✅ WIN (L{state['level']})\n"
                
                # जिंकल्यावर लेव्हल 1 होईल
                state["level"] = 1 
            else:
                state["stats"]["fail"] += 1
                res_status = f"{state['pred_bs']} ❌ FAIL"
                prev_res_text += f"🔹 Match: ❌ FAIL (L{state['level']})\n"
                
                # हरल्यावर लेव्हल पुढे जाईल
                state["level"] += 1
                
        # 2. नवीन प्रेडिक्शन सेट करणे (-20 व्या राउंडचा रिझल्ट शोधणे)
        target_bs = get_target_result(state, target_issue_str)
        if target_bs:
             state["pred_bs"] = target_bs
        else:
             state["pred_bs"] = "WAIT"

        # UI साठी हिस्ट्री अपडेट
        state["history"].append({
            "issue": latest_issue[-4:],
            "pred": state["pred_bs"],
            "level": f"L{current_logged_level}", 
            "res": "[green]✅ WIN[/]" if "WIN" in res_status else ("[red]❌ FAIL[/]" if "FAIL" in res_status else "-")
        })
        if len(state["history"]) > 4: state["history"].pop(0)

        if state["is_running"]:
            if prev_res_text == f"🎯 Result: *{latest_number_str}* ({latest_bs})\n":
                prev_res_text = None 
            send_telegram_signal(state, str(next_issue_int), prev_res_text, target_issue=target_issue_str)

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
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and str(state["last_processed_issue"]).isdigit() else "Next"
    target_iss = str(int(next_iss) - 20) if next_iss.isdigit() else "-"
    
    if state["pred_bs"] == "WAIT":
        ui_text = "[yellow]WAITING FOR HISTORY[/]"
    else:
        s_color = "dark_orange" if state["pred_bs"] == "Big" else "bright_blue"
        ui_text = f"[{s_color}]{state['pred_bs']}[/] | L{state['level']}"
        
    timer_status = "[green]RUNNING[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n"
    panel_text += f"⚙️ [bold]Strategy:[/] -20th Round Continuous\n"
    panel_text += f"🔍 [bold]Targeting Issue:[/] {target_iss}\n"
    panel_text += f"📏 [bold]Prediction:[/] {ui_text}\n"
    panel_text += f"🕒 [bold]Status:[/] {timer_status} | Stats - W: [green]{state['stats']['win']}[/] F: [red]{state['stats']['fail']}[/]\n"
    panel_text += f"📱 [bold]Telegram Status:[/] {state['telegram_status']}\n\n"
    
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
            
    return Panel(Group(Align.center(panel_text), Align.center(hist_table)), title=f"🤖 [bold cyan]{state['name']}[/]", border_style="cyan", width=78)

def create_master_ui():
    p_30s = render_game_panel(state_30s)
    return Group(
        Align.center("[bold yellow]🚀 30S CONTINUOUS -20TH ROUND BOT[/bold yellow]\n"),
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
