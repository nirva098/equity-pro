import requests
from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_message(text: str) -> bool:
    """
    Send a message via Telegram Bot API.
    Returns True on success, False otherwise.
    Silently skips if keys are not configured.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Warning: Telegram keys not set. Skipping notification.")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram message sent successfully.")
            return True
        else:
            print(f"Telegram API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False
