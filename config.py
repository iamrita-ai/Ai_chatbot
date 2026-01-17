import os
from os import getenv

class Config:
    # Bot Configuration
    API_ID = int(getenv("API_ID", "0"))
    API_HASH = getenv("API_HASH", "")
    BOT_TOKEN = getenv("BOT_TOKEN", "")
    
    # Bot Name (Optional - Default set)
    BOT_NAME = getenv("BOT_NAME", "AI Life Partner")
    
    # RapidAPI Configuration (EXACT FORMAT)
    RAPIDAPI_KEY = getenv("RAPIDAPI_KEY", "6ef0d24418msh3a1b343f7442477p124655jsn22dd56479bdd")
    RAPIDAPI_HOST = getenv("RAPIDAPI_HOST", "grok-3-0-ai.p.rapidapi.com")
    RAPIDAPI_URL = getenv("RAPIDAPI_URL", "https://grok-3-0-ai.p.rapidapi.com/")
    RAPIDAPI_MODEL = getenv("RAPIDAPI_MODEL", "Grok-3")
    
    # Database Configuration
    MONGO_URI = getenv("MONGO_URI", "")
    DATABASE_NAME = getenv("DATABASE_NAME", "ai_companion_bot")
    
    # Channel & Logging Configuration
    LOG_CHANNEL = int(getenv("LOG_CHANNEL", "0"))
    FORCE_SUB_CHANNEL = getenv("FORCE_SUB_CHANNEL", "")
    
    # Owner Configuration
    OWNER_ID = list(map(int, getenv("OWNER_ID", "6518065496 1598576202").split()))
    OWNER_CONTACT = getenv("OWNER_CONTACT", "https://t.me/technicalserena")
    
    # Flood Control
    FLOOD_SLEEP = int(getenv("FLOOD_SLEEP", "3"))
    
    # Flask Configuration (for Render)
    PORT = int(getenv("PORT", "8080"))
    
    # X.AI Grok (BACKUP - Optional)
    GROK_API_KEY = getenv("GROK_API_KEY", "")
    GROK_API_URL = getenv("GROK_API_URL", "https://api.x.ai/v1/chat/completions")
    GROK_MODEL = getenv("GROK_MODEL", "grok-4-latest")
