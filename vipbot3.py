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
TELEGRAM_TOKEN = "8671287480:AAFXRiJpzJuPNeHP_k08cxdBt3A7B9q7YWw"
TARGET_GROUP_ID = "-4435776391" 
PASS_1M = "12345"  # Telegram bot start/stop password
# --------------------------------------------------------

api_session = requests.Session()

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        
        # --- स्ट्रॅटेजी व्हेरिएबल्स ---
        "wait_for_trigger": True, 
        "ignore_trigger_until_issue": 0, # L4 फेल झाल्यावर जुने रिझल्ट्स इग्नोर करण्यासाठी
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

state_1m = create_state("WinGo 1M", "1M")

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
                        if len(parts) == 2 and parts[1] == PASS_1M:
                            state_1m["is_running"] = True
                            state_1m["active_chat_id"] = chat_id 
                            send_telegram_message_direct(chat_id, f"✅ *[Trend Follower Bot]* Activated! Bot is running continuously.", state_1m)
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.", state_1m)
                            
                    elif text.startswith("/stop"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == PASS_1M:
                            state_1m["is_running"] = False
                            send_telegram_message_direct(chat_id, "🛑 *Bot Stopped Successfully!*", state_1m)
                        else:
                            send_telegram_message_direct(chat_id, "❌ Access Denied! Wrong Password.", state_1m)
        except Exception:
            pass
        time.sleep(2)

def send_telegram_signal(state, issue, prev_res_text=None):
    target_chat_id = state.get("active_chat_id") or TARGET_GROUP_ID
    if not target_chat_id: return

    text = f"🚀 *{state['name']} Signal* 🚀\n"
    text += f"⚙️ *Strategy:* Trend Follower (Big-Big / Small-Small)\n\n"
    
    if prev_res_text:
        text += f"📊 *मागील निकाल:*\n"
        text += f"{prev_res_text}\n"
        text += f"➖➖➖➖➖➖➖➖➖➖\n\n"
        
    text += f"🎟️ *Next Issue:* `{issue}`\n\n"
    
    if state["wait_for_trigger"] or state["pred_bs"] == "WAIT":
        if state["level"] > 1:
             text += f"⏳ *Waiting for NEW Pattern (2 Same) to Resume at L{state['level']}...*\n\n"
        else:
             text += f"⏳ *Waiting for Pattern (Big-Big or Small-Small)...*\n\n"
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

def update_predictions(state):
    # 1. ट्रिगर चेक करणे (2 Big किंवा 2 Small)
    if state["wait_for_trigger"]:
        if len(state["full_history"]) >= 2:
            issue_new = int(state["full_history"][0]["issue"])
            issue_old = int(state["full_history"][1]["issue"])
            
            # जुना रिझल्ट L4 फेल झालेल्या issue पेक्षा मोठा असला पाहिजे (जेणेकरून तोच जुना पॅटर्न पुन्हा वाचला जाणार नाही)
            if issue_old > state.get("ignore_trigger_until_issue", 0):
                if state["full_history"][0]["bs"] == state["full_history"][1]["bs"]: # 2 समान आले
                    state["wait_for_trigger"] = False

    # 2. प्रेडिक्शन सेट करणे
    if state["wait_for_trigger"]:
        state["pred_bs"] = "WAIT"
    else:
        # Trend Follower: जो रिझल्ट आलाय तोच पुढे कॅरी करा (मग तो बिग असो वा स्मॉल)
        if len(state["full_history"]) >= 1:
            state["pred_bs"] = state["full_history"][0]["bs"]

def process_strategy(state, records):
    if not records: return False
    state["live_records"] = records[:5]
    
    latest_item = records[0]
    latest_issue = str(latest_item.get("issueNumber") or latest_item.get("issue") or "-")
    latest_number_str = str(latest_item.get("number") or latest_item.get("drawNumber") or "-")
    
    if not (latest_number_str.isdigit() and latest_issue.isdigit()): return False
    
    num_int = int(latest_number_str)
    latest_bs = "Big" if num_int >= 5 else "Small"

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
    state["full_history"] = state["full_history"][:60] 

    if state["last_processed_issue"] is None:
        state["last_processed_issue"] = latest_issue
        next_issue_int = int(latest_issue) + 1
        update_predictions(state)
        if state["is_running"]: send_telegram_signal(state, str(next_issue_int))
        return True

    if state["last_processed_issue"] != latest_issue:
        if int(latest_issue) <= int(state["last_processed_issue"]): return False  

        prev_res_text = f"🎯 Result: *{latest_number_str}* ({latest_bs})\n"
        res_status = "-"
        current_logged_level = state["level"]

        if not state["wait_for_trigger"] and state["pred_bs"] != "WAIT":
            state["stats"]["total_trades"] += 1
            if state["pred_bs"] == latest_bs:
                state["stats"]["win"] += 1
                res_status = f"{state['pred_bs']} ✅ WIN"
                prev_res_text += f"🔹 Match: ✅ WIN (L{state['level']})\n"
                
                # जिंकल्यावर पुन्हा L1 वर जा, पण नवीन ट्रिगरची वाट पाहू नका. ट्रेड कंटिन्यू राहील.
                state["level"] = 1 
                state["wait_for_trigger"] = False 
            else:
                state["stats"]["fail"] += 1
                res_status = f"{state['pred_bs']} ❌ FAIL"
                prev_res_text += f"🔹 Match: ❌ FAIL (L{state['level']})\n"
                state["level"] += 1

                # 🚨 L4 फेल झाल्यावर बॉट थांबेल आणि नवीन ट्रिगरची वाट पाहील
                if state["level"] == 5:
                    prev_res_text += f"⚠️ *Level 4 Failed!* Bot Paused.\n⏳ Waiting for NEW pattern (Big-Big or Small-Small) to resume Level 5..."
                    state["wait_for_trigger"] = True
                    # ज्या issue वर L4 फेल झालाय, त्याच्या पुढच्याच issue पासून नवीन पॅटर्न शोधायला हवा
                    state["ignore_trigger_until_issue"] = int(latest_issue)
                
        state["history"].append({
            "issue": latest_issue[-4:],
            "pred": state["pred_bs"] if not state["wait_for_trigger"] else "WAIT",
            "level": f"L{current_logged_level}", 
            "res": "[green]✅ WIN[/]" if "WIN" in res_status else ("[red]❌ FAIL[/]" if "FAIL" in res_status else "-")
        })
        if len(state["history"]) > 4: state["history"].pop(0)

        next_issue_int = int(latest_issue) + 1
        update_predictions(state)

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
        records = fetch_history_records(url, state_1m)
        if records:
            process_strategy(state_1m, records)
        time.sleep(2)

def render_game_panel(state):
    next_iss = str(int(state["last_processed_issue"]) + 1) if state["last_processed_issue"] and str(state["last_processed_issue"]).isdigit() else "Next"

    if state["wait_for_trigger"]:
        if state["level"] > 1:
            ui_text = f"[yellow]WAITING NEW TRIGGER (2 Same) FOR L{state['level']}[/]"
        else:
            ui_text = "[yellow]WAITING FOR 2 SAME (B-B / S-S)[/]"
    else:
        s_color = "dark_orange" if state["pred_bs"] == "Big" else "bright_blue"
        ui_text = f"[{s_color}]{state['pred_bs']}[/] | L{state['level']}"
        
    timer_status = "[green]RUNNING CONTINUOUSLY[/]" if state["is_running"] else "[red]STOPPED[/]"
    
    panel_text = f"🎯 [bold white]Issue: {next_iss}[/]\n"
    panel_text += f"⚙️ [bold]Strategy:[/] Trend Follower (1M)\n"
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
    p_1m = render_game_panel(state_1m)
    return Group(
        Align.center("[bold yellow]🚀 1M TREND FOLLOWER BOT[/bold yellow]\n"),
        Align.center(p_1m)
    )

if __name__ == "__main__":
    t_list = threading.Thread(target=telegram_listener, daemon=True)
    t_1m = threading.Thread(target=worker_1m, daemon=True)
    
    t_list.start()
    t_1m.start()

    with Live(create_master_ui(), console=console, refresh_per_second=4, screen=False) as live:
        while True:
            live.update(create_master_ui())
            time.sleep(0.5)
