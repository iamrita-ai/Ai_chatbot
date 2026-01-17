import os
from os import getenv

class Config:
    # Bot Configuration
    API_ID = int(getenv("API_ID", "0"))
    API_HASH = getenv("API_HASH", "")
    BOT_TOKEN = getenv("BOT_TOKEN", "")
    
    # Bot Name
    BOT_NAME = getenv("BOT_NAME", "AI Life Partner")
    
    # AI Provider Priority
    AI_PROVIDER = getenv("AI_PROVIDER", "gemini")  # gemini recommended
    
    # Google Gemini (FREE - RECOMMENDED)
    GEMINI_API_KEY = getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = getenv("GEMINI_MODEL", "gemini-pro")
    
    # Hugging Face (FREE)
    HUGGINGFACE_API_KEY = getenv("HUGGINGFACE_API_KEY", "")
    
    # Together AI (FREE)
    TOGETHER_API_KEY = getenv("TOGETHER_API_KEY", "")
    TOGETHER_MODEL = getenv("TOGETHER_MODEL", "meta-llama/Llama-2-70b-chat-hf")
    
    # Groq (FREE)
    GROQ_API_KEY = getenv("GROQ_API_KEY", "")
    GROQ_MODEL = getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    
    # OpenAI (Paid)
    OPENAI_API_KEY = getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = getenv("OPENAI_MODEL", "gpt-4")
    
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
