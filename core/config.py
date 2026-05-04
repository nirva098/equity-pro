import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Trading Constants
CAPITAL = 1000000
MAX_RISK_PER_TRADE = 0.02
DB_PATH = "trades.db"

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
