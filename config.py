import os
from os import getenv

class Config:
    # Bot Configuration
    API_ID = int(getenv("API_ID", "0"))
    API_HASH = getenv("API_HASH", "")
    BOT_TOKEN = getenv("BOT_TOKEN", "")
    
    # Bot Name
    BOT_NAME = getenv("BOT_NAME", "AI Life Partner")
    
    # AI Provider Selection
    AI_PROVIDER = getenv("AI_PROVIDER", "groq")  # groq, gemini, huggingface
    
    # Groq AI Configuration (FREE - RECOMMENDED)
    GROQ_API_KEY = getenv("GROQ_API_KEY", "")
    GROQ_API_URL = getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
    GROQ_MODEL = getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    
    # Google Gemini (BACKUP - FREE)
    GEMINI_API_KEY = getenv("GEMINI_API_KEY", "")
    GEMINI_API_URL = getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models")
    GEMINI_MODEL = getenv("GEMINI_MODEL", "gemini-pro")
    
    # Hugging Face (BACKUP 2 - FREE)
    HUGGINGFACE_API_KEY = getenv("HUGGINGFACE_API_KEY", "")
    HUGGINGFACE_API_URL = getenv("HUGGINGFACE_API_URL", "https://api-inference.huggingface.co/models")
    HUGGINGFACE_MODEL = getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-2-70b-chat-hf")
    
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
