import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Monad Mainnet Configuration
MONAD_RPC_URL = os.getenv("MONAD_RPC_URL", "https://sepolia-rpc.monad.xyz")
MONAD_CHAIN_ID = int(os.getenv("MONAD_CHAIN_ID", "10143"))

# Tracking Configuration
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "10"))  # seconds
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot.db")

