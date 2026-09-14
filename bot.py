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

# ---------------- TELEGRAM BOT CONFIGURATION ----------------
TELEGRAM_BOT_TOKEN = "8886107397:AAHENOebGnrupxvGKqKh5cKC3SmujXJOV3w"
TARGET_GROUP_ID = "-1004370895879"
SECRET_PASSWORD = "12345"
# ------------------------------------------------------------

# ⚡ फास्ट इंटरनेट कनेक्शनसाठी Session
api_session = requests.Session()

def create_state(name, interval):
    return {
        "name": name,
        "interval": interval,
        "last_processed_issue": None,
        
        # 🔄 Multi-Strategy System (3 Strategies)
        "current_strategy": 1,  # 1: 2 Circle (2x2), 2: 3 Circle (3x3), 3: 20th Round Mirror
        "strategy_start_time": time.time(),
        "wait_for_trigger": True,
        "pattern_bs": None,
        "pattern_count": 0,
        
        "pred_bs": "WAIT",
        "pred_color": "WAIT",
        "pred_nums": [],
        "level": 1,
        
        "full_history": [], 
        "history": [],
        "stats": {"win": 0, "fail": 0, "total_trades": 0},
        "is_running": False,        
        "active_chat_id": None,    
        "live_records": []
    }

state_1m = create_state("WinGo 1M", "1M")

def send_telegram_message_direct(chat_id, text):
    if not chat_id: return
    def _send():
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            api_session.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=3)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()

def telegram_listener():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=2"
            response = api_session.get(url, timeout=5)
            if response.status_code == 200:
                for result in response.json().get("result", []):
                    offset = result["update_id"] + 1
                    message = result.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "").strip()

                    if text.startswith("/signal"):
                        parts = text.split()
                        if len(parts) == 2 and parts[1] == SECRET_स्क्रीनशॉट पाहिल्यावर लक्षात येतंय की तुमच्या `bot.py` फाईलमध्ये काय चूक झाली आहे. 

**हा एरर का येत आहे?**
तुमच्या `bot.py` फाईलच्या **लाईन 48** वर चुकून काही मराठी स्पष्टीकरणाचा मजकूर (Explanation text) पेस्ट झाला आहे. 

तुम्ही एररमध्ये पाहू शकता की, `state_1m = create_state` च्या पुढे लगेच *"नमस्कार! तुम्ही दिलेल्या कोडमध्ये..."* हा मजकूर आला आहे. Python ला हा मजकूर कोड म्हणून समजत नाही, त्यामुळे तो तिथे **`SyntaxError: invalid syntax`** हा एरर देत आहे.

**हे कसे दुरुस्त करावे?**

हा एरर घालवण्यासाठी तुम्हाला तो मराठी मजकूर फाईलमधून काढून टाकावा लागेल:

1. तुमच्या Termux मध्ये तुमची फाईल एडिट करण्यासाठी ओपन करा. त्यासाठी खालील कमांड वापरा:
   `nano bot.py`
2. फाईलमध्ये खाली जाऊन **लाईन नंबर 48** शोधा.
3. तिथे असलेला **संपूर्ण मराठी मजकूर डिलीट करा**. तिथे फक्त तुमचा मूळ कोड असायला हवा (उदा. `state_1m = create_state(...)`).
4. फाईल सेव्ह करून बाहेर या. (जर तुम्ही `nano` एडिटर वापरत असाल, तर सेव्ह करण्यासाठी `Ctrl + X` दाबा, त्यानंतर `Y` दाबा आणि मग `Enter` दाबा).
5. आता पुन्हा तुमचा बॉट रन करण्यासाठी `python bot.py` कमांड टाईप करा.

**एक छोटी टीप:** वरती जो दुसरा एरर दिसतोय (`invalid non-printable character U+00A0`), तो सुद्धा कोड कॉपी-पेस्ट करताना आलेल्या चुकीच्या अदृश्य स्पेसेसमुळे (invisible spaces) येतो. यापुढे चॅटमधून कोड कॉपी करताना फक्त 'कोड ब्लॉक' (Code Block) मधील मजकूर कॉपी करा, बाहेरचे स्पष्टीकरण किंवा मजकूर कोडमध्ये पेस्ट करू नका. 

हे करून पहा आणि अजून काही अडचण आल्यास नक्की सांगा!
