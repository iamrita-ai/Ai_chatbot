import os
from os import getenv

class Config:
    # Bot Configuration
    API_ID = int(getenv("API_ID", "0"))
    API_HASH = getenv("API_HASH", "")
    BOT_TOKEN = getenv("BOT_TOKEN", "")
    
    # Bot Name
    BOT_NAME = getenv("BOT_NAME", "AI Life Partner")
    
    # Cohere AI (FREE - RECOMMENDED)
    COHERE_API_KEY = getenv("COHERE_API_KEY", "")
    
    # Hugging Face (Backup)
    HUGGINGFACE_API_KEY = getenv("HUGGINGFACE_API_KEY", "")
    
    # Database
    MONGO_URI = getenv("MONGO_URI", "")
    DATABASE_NAME = getenv("DATABASE_NAME", "ai_companion_bot")
    
    # Channels
    LOG_CHANNEL = int(getenv("LOG_CHANNEL", "0"))
    FORCE_SUB_CHANNEL = getenv("FORCE_SUB_CHANNEL", "")
    
    # Owners
    OWNER_ID = list(map(int, getenv("OWNER_ID", "6518065496 1598576202").split()))
    OWNER_CONTACT = getenv("OWNER_CONTACT", "https://t.me/technicalserena")
    
    # Settings
    FLOOD_SLEEP = int(getenv("FLOOD_SLEEP", "3"))
    PORT = int(getenv("PORT", "8080"))
