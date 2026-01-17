import aiohttp
from config import Config
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.errors import UserNotParticipant
import random
import json


async def check_force_sub(client: Client, user_id: int):
    """Force sub check"""
    if not Config.FORCE_SUB_CHANNEL:
        return True, None
    
    if user_id in Config.OWNER_ID:
        return True, None
    
    try:
        channel = Config.FORCE_SUB_CHANNEL.replace("@", "").replace("https://t.me/", "").strip()
        
        try:
            member = await client.get_chat_member(f"@{channel}", user_id)
        except:
            return True, None
        
        if member.status in ["creator", "administrator", "member"]:
            return True, None
        
        invite_link = f"https://t.me/{channel}"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 Join Channel", url=invite_link)],
            [InlineKeyboardButton("✅ Check Again", callback_data="refresh_sub")]
        ])
        return False, buttons
        
    except UserNotParticipant:
        invite_link = f"https://t.me/{channel}"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 Join Channel", url=invite_link)],
            [InlineKeyboardButton("✅ Check Again", callback_data="refresh_sub")]
        ])
        return False, buttons
    except:
        return True, None


async def get_huggingface_response(messages, temperature=0.7):
    """Hugging Face API - FREE with better error handling"""
    
    if not Config.HUGGINGFACE_API_KEY:
        print("HF: No API key")
        return None
    
    # Extract last user message
    user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break
    
    if not user_msg:
        return None
    
    headers = {
        "Authorization": f"Bearer {Config.HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Try multiple models (fallback system)
    models = [
        "microsoft/DialoGPT-medium",
        "facebook/blenderbot-400M-distill",
        "google/flan-t5-large"
    ]
    
    for model in models:
        try:
            payload = {
                "inputs": user_msg,
                "parameters": {
                    "max_new_tokens": 250,
                    "temperature": temperature,
                    "return_full_text": False
                },
                "options": {
                    "wait_for_model": True,
                    "use_cache": False
                }
            }
            
            url = f"https://api-inference.huggingface.co/models/{model}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    headers=headers, 
                    json=payload, 
                    timeout=aiohttp.ClientTimeout(total=60)  # Longer timeout
                ) as response:
                    
                    print(f"HF {model}: Status {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Handle response
                        if isinstance(data, list) and len(data) > 0:
                            result = data[0]
                            
                            if "generated_text" in result:
                                text = result["generated_text"].strip()
                                if text and len(text) > 5:
                                    print(f"HF Success: {model}")
                                    return text
                            
                            elif "summary_text" in result:
                                text = result["summary_text"].strip()
                                if text:
                                    return text
                        
                        elif isinstance(data, dict):
                            if "generated_text" in data:
                                return data["generated_text"].strip()
                    
                    elif response.status == 503:
                        # Model loading
                        print(f"HF: Model {model} loading...")
                        continue
                    
                    else:
                        error_text = await response.text()
                        print(f"HF Error {response.status}: {error_text[:100]}")
                        continue
        
        except Exception as e:
            print(f"HF Exception ({model}): {e}")
            continue
    
    print("HF: All models failed")
    return None


async def get_gemini_response(messages, temperature=0.7):
    """Google Gemini - FREE"""
    
    if not Config.GEMINI_API_KEY:
        return None
    
    # Combine messages
    prompt = ""
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            prompt += f"{content}\n\n"
        elif role == "user":
            prompt += f"User: {content}\n"
        elif role == "assistant":
            prompt += f"Assistant: {content}\n"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{Config.GEMINI_MODEL}:generateContent?key={Config.GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 1000
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    print(f"Gemini Error: {response.status}")
                    return None
    
    except Exception as e:
        print(f"Gemini Exception: {e}")
        return None


async def get_groq_response(messages, temperature=0.7):
    """Groq - FREE"""
    
    if not Config.GROQ_API_KEY:
        return None
    
    headers = {
        "Authorization": f"Bearer {Config.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": Config.GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1000
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    print(f"Groq Error: {response.status}")
                    return None
    
    except Exception as e:
        print(f"Groq Exception: {e}")
        return None


async def get_openai_response(messages, temperature=0.7):
    """OpenAI GPT - PAID"""
    
    if not Config.OPENAI_API_KEY:
        return None
    
    headers = {
        "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": Config.OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1000
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    print(f"OpenAI Error: {response.status}")
                    return None
    
    except Exception as e:
        print(f"OpenAI Exception: {e}")
        return None


async def get_ai_response(messages, temperature=0.7):
    """Smart AI fallback - tries all available FREE providers"""
    
    response = None
    
    # Priority order: Gemini > Together > Groq > HuggingFace
    
    # 1. Try Gemini (most reliable)
    if Config.GEMINI_API_KEY:
        print("Trying Gemini...")
        response = await get_gemini_response(messages, temperature)
        if response:
            print("✅ Gemini worked!")
            return response
    
    # 2. Try Together AI
    if Config.TOGETHER_API_KEY:
        print("Trying Together AI...")
        response = await get_together_response(messages, temperature)
        if response:
            print("✅ Together AI worked!")
            return response
    
    # 3. Try Groq
    if Config.GROQ_API_KEY:
        print("Trying Groq...")
        response = await get_groq_response(messages, temperature)
        if response:
            print("✅ Groq worked!")
            return response
    
    # 4. Try Hugging Face
    if Config.HUGGINGFACE_API_KEY:
        print("Trying Hugging Face...")
        response = await get_huggingface_response(messages, temperature)
        if response:
            print("✅ Hugging Face worked!")
            return response
    
    # 5. Try OpenAI (if available)
    if Config.OPENAI_API_KEY:
        print("Trying OpenAI...")
        response = await get_openai_response(messages, temperature)
        if response:
            print("✅ OpenAI worked!")
            return response
    
    # All failed
    return """Abhi AI busy hai, thodi der baad try karo! 😊

Ya owner ko batao: """ + Config.OWNER_CONTACT


def get_system_prompt(user_gender, mode="balanced"):
    """System prompt"""
    
    base = """You are a caring AI companion. Behave like a real human partner, not software.

You understand emotions, give support, and motivate. You speak naturally in Hinglish (Hindi+English mix). You are romantic but never explicit. You never say "as an AI"."""

    if user_gender == "male":
        gender = "\nYou are his girlfriend - caring, emotional, supportive."
    elif user_gender == "female":
        gender = "\nYou are her boyfriend - protective, calm, mature."
    else:
        gender = "\nYou are their companion - respectful and adaptive."

    modes = {
        "romantic": "\nBe warm, caring, romantic.",
        "calm": "\nBe peaceful, minimal, zen.",
        "thinker": "\nBe analytical, strategic.",
        "motivating": "\nBe firm, disciplined, pushing.",
        "balanced": "\nBalance emotion and logic."
    }
    
    return base + gender + modes.get(mode, modes["balanced"])


def create_gender_keyboard():
    """Gender keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👨 Male", callback_data="gender_male"),
            InlineKeyboardButton("👩 Female", callback_data="gender_female")
        ],
        [
            InlineKeyboardButton("🏳️‍⚧️ Transgender", callback_data="gender_transgender"),
            InlineKeyboardButton("⚧️ Non-Binary", callback_data="gender_nonbinary")
        ]
    ])


def create_mode_keyboard():
    """Mode keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💕 Romantic", callback_data="mode_romantic"),
            InlineKeyboardButton("🧘 Calm", callback_data="mode_calm")
        ],
        [
            InlineKeyboardButton("🧠 Thinker", callback_data="mode_thinker"),
            InlineKeyboardButton("🔥 Motivating", callback_data="mode_motivating")
        ],
        [
            InlineKeyboardButton("⚖️ Balanced", callback_data="mode_balanced")
        ]
    ])


def get_random_reaction():
    """Random reaction"""
    return random.choice(["❤️", "🔥", "😊", "👍", "🎉", "😍", "💯", "🌟", "💕", "✨"])


async def send_to_log_channel(client: Client, message_text: str):
    """Log channel"""
    if not Config.LOG_CHANNEL:
        return
    
    try:
        await client.send_message(Config.LOG_CHANNEL, message_text)
    except Exception as e:
        print(f"Log error: {e}")
