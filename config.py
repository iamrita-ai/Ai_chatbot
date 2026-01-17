import os
from os import getenv

class Config:
    # Bot Configuration
    API_ID = int(getenv("API_ID", "0"))
    API_HASH = getenv("API_HASH", "")
    BOT_TOKEN = getenv("BOT_TOKEN", "")
    
    # Bot Name (Optional - Default set)
    BOT_NAME = getenv("BOT_NAME", "AI Life Partner")
    
    # RapidAPI Configuration (SIMPLIFIED)
    RAPIDAPI_KEY = getenv("RAPIDAPI_KEY", "")
    RAPIDAPI_APP_ID = getenv("RAPIDAPI_APP_ID", "8308057")
    
    # Auto-detect multiple Grok endpoints on RapidAPI
    RAPIDAPI_ENDPOINTS = [
        {
            "url": "https://grok-3-0-ai.p.rapidapi.com/v1/chat/completions",
            "host": "grok-3-0-ai.p.rapidapi.com",
            "name": "Grok 3.0 (Format 1)"
        },
        {
            "url": "https://grok-3-0-ai.p.rapidapi.com/api/chat",
            "host": "grok-3-0-ai.p.rapidapi.com",
            "name": "Grok 3.0 (Format 2)"
        },
        {
            "url": "https://grok-ai2.p.rapidapi.com/v1/chat/completions",
            "host": "grok-ai2.p.rapidapi.com",
            "name": "Grok AI v2"
        },
        {
            "url": "https://grok2-ai.p.rapidapi.com/chat",
            "host": "grok2-ai.p.rapidapi.com",
            "name": "Grok 2 AI"
        }
    ]
    
    # Database Configuration
    MONGO_URI = getenv("MONGO_URI", "")
    DATABASE_NAME = getenv("DATABASE_NAME", "ai_companion_bot")
    
    # Channel & Logging Configuration
    LOG_CHANNEL = int(getenv("LOG_CHANNEL", "0"))
    FORCE_SUB_CHANNEL = getenv("FORCE_SUB_CHANNEL", "")  # username without @
    
    # Owner Configuration
    OWNER_ID = list(map(int, getenv("OWNER_ID", "6518065496 1598576202").split()))
    OWNER_CONTACT = getenv("OWNER_CONTACT", "https://t.me/technicalserena")
    
    # Flood Control
    FLOOD_SLEEP = int(getenv("FLOOD_SLEEP", "3"))
    
    # Flask Configuration (for Render)
    PORT = int(getenv("PORT", "8080"))
