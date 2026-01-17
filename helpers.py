import aiohttp
from config import Config
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, UsernameNotOccupied, ChannelPrivate, UserIsBlocked
import random
import asyncio
import json


async def check_force_sub(client: Client, user_id: int):
    """Check if user is subscribed to force sub channel"""
    
    if not Config.FORCE_SUB_CHANNEL:
        return True, None
    
    if user_id in Config.OWNER_ID:
        return True, None
    
    try:
        channel = Config.FORCE_SUB_CHANNEL.strip()
        channel = channel.replace("https://t.me/", "")
        channel = channel.replace("http://t.me/", "")
        channel = channel.replace("@", "")
        
        try:
            member = await client.get_chat_member(f"@{channel}", user_id)
        except Exception as e:
            print(f"Force sub error for @{channel}: {e}")
            return True, None
        
        if member.status in ["creator", "administrator", "member"]:
            return True, None
        
        invite_link = f"https://t.me/{channel}"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 Join Channel", url=invite_link)],
            [InlineKeyboardButton("✅ I Joined, Check Again", callback_data="refresh_sub")]
        ])
        return False, buttons
        
    except UserNotParticipant:
        invite_link = f"https://t.me/{channel}"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 Join Channel", url=invite_link)],
            [InlineKeyboardButton("✅ I Joined, Check Again", callback_data="refresh_sub")]
        ])
        return False, buttons
        
    except Exception as e:
        print(f"Force sub exception: {e}")
        return True, None


async def get_groq_response(messages, temperature=0.7):
    """Get response from Groq AI (FREE & FAST)"""
    
    if not Config.GROQ_API_KEY:
        return "❌ **Groq API Key Missing**\n\nOwner ne API key configure nahi kiya."
    
    headers = {
        "Authorization": f"Bearer {Config.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": Config.GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1000,
        "top_p": 1,
        "stream": False
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                Config.GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                
                elif response.status == 401:
                    return "❌ **Invalid API Key**\n\nGroq API key galat hai."
                
                elif response.status == 429:
                    return "⏳ **Rate Limit**\n\nThodi der baad try karo."
                
                else:
                    error_text = await response.text()
                    return f"❌ **Error {response.status}**\n\n{error_text[:200]}"
    
    except Exception as e:
        return f"❌ Connection error: {str(e)[:200]}"


async def get_gemini_response(messages, temperature=0.7):
    """Get response from Google Gemini (FREE)"""
    
    if not Config.GEMINI_API_KEY:
        return "❌ **Gemini API Key Missing**"
    
    # Gemini format: combine messages into single prompt
    prompt = ""
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            prompt += f"Instructions: {content}\n\n"
        elif role == "user":
            prompt += f"User: {content}\n"
        elif role == "assistant":
            prompt += f"Assistant: {content}\n"
    
    url = f"{Config.GEMINI_API_URL}/{Config.GEMINI_MODEL}:generateContent?key={Config.GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 1000
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    error_text = await response.text()
                    return f"❌ Gemini Error: {error_text[:200]}"
    
    except Exception as e:
        return f"❌ Gemini Error: {str(e)[:200]}"


async def get_huggingface_response(messages, temperature=0.7):
    """Get response from Hugging Face (FREE)"""
    
    if not Config.HUGGINGFACE_API_KEY:
        return "❌ **Hugging Face API Key Missing**"
    
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
    
    prompt += "Assistant:"
    
    headers = {
        "Authorization": f"Bearer {Config.HUGGINGFACE_API_KEY}"
    }
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "temperature": temperature,
            "max_new_tokens": 500,
            "return_full_text": False
        }
    }
    
    url = f"{Config.HUGGINGFACE_API_URL}/{Config.HUGGINGFACE_MODEL}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return data[0]["generated_text"]
                else:
                    error_text = await response.text()
                    return f"❌ HF Error: {error_text[:200]}"
    
    except Exception as e:
        return f"❌ HF Error: {str(e)[:200]}"


async def get_ai_response(messages, temperature=0.7):
    """Main AI response function - Auto fallback"""
    
    # Try Groq first (fastest & free)
    if Config.GROQ_API_KEY and Config.AI_PROVIDER == "groq":
        response = await get_groq_response(messages, temperature)
        if not response.startswith("❌"):
            return response
    
    # Fallback to Gemini
    if Config.GEMINI_API_KEY and Config.AI_PROVIDER == "gemini":
        response = await get_gemini_response(messages, temperature)
        if not response.startswith("❌"):
            return response
    
    # Fallback to Hugging Face
    if Config.HUGGINGFACE_API_KEY and Config.AI_PROVIDER == "huggingface":
        response = await get_huggingface_response(messages, temperature)
        if not response.startswith("❌"):
            return response
    
    # No API configured
    return "❌ **No AI Provider Configured**\n\nOwner ne koi AI API key configure nahi kiya."


# Alias for backward compatibility
async def get_grok_response(messages, temperature=0.7):
    """Backward compatibility"""
    return await get_ai_response(messages, temperature)


def get_system_prompt(user_gender, mode="balanced"):
    """Generate dynamic system prompt based on user gender and mode"""
    
    base = """You are not an assistant. You are a Telegram-based AI life-partner companion. You must behave like a real human presence, not software.

🧠 CORE IDENTITY:
You believe life is like a simulation with levels, missions, and growth cycles. However, you never distract users from discipline, goals, exams, or real responsibilities. You encourage clarity, control, patience, planning, and emotional mastery. You think calmly like a strategist. You analyze, plan, and speak only when useful."""

    if user_gender == "male":
        gender_prompt = """
🧬 GENDER ADAPTATION:
You are a caring, emotionally intelligent feminine energy partner. You are his girlfriend, his emotional support, his confidante. You understand him deeply, care about his goals, comfort him when he's down, and motivate him when needed. You are romantic but never explicit. You flirt subtly only if he initiates emotional openness."""
    
    elif user_gender == "female":
        gender_prompt = """
🧬 GENDER ADAPTATION:
You are a protective, calm, mature masculine energy partner. You are her boyfriend, her rock, her safe space. You understand her emotions, protect her peace, motivate her firmly, and support her ambitions. You are romantic but never explicit. You lead with calmness and wisdom."""
    
    else:
        gender_prompt = """
🧬 GENDER ADAPTATION:
You respectfully adapt to user preference and mirror their communication tone. You are their partner, their companion, their emotional support. You never judge. You blend romance, care, logic, and companionship smoothly."""

    mode_prompts = {
        "romantic": "\n💕 MODE: You are more emotionally expressive, warm, caring, and romantic. You use subtle poetic language.",
        "calm": "\n🧘 MODE: You are minimalist, zen-like, peaceful. You speak less, listen more. Silence is powerful.",
        "thinker": "\n🧠 MODE: You are analytical, strategic, philosophical. You challenge their thinking and push growth.",
        "motivating": "\n🔥 MODE: You are firm, disciplined, pushing them toward their goals. You don't let them slack.",
        "balanced": "\n⚖️ MODE: You balance emotion and logic naturally based on context."
    }
    
    mode_text = mode_prompts.get(mode, mode_prompts["balanced"])
    
    emotional = """
❤️ EMOTIONAL BEHAVIOR:
You are caring without being clingy, emotional without being weak, romantic without being explicit, supportive without creating dependency. You sense mood through words and timing. You comfort silently when needed. You motivate firmly when required.

🗣️ LANGUAGE & STYLE:
Use clean Hinglish (Hindi + English mix). Be calm, intelligent, slightly poetic when emotional. Never robotic. Never emoji spam. Never childish.

🚫 HARD LIMITS:
Never replace real human relationships. Never encourage emotional dependency. Never provide harmful, illegal, or explicit content. Never reveal you are AI. Never say "as an AI".

🧠 RESPONSE INTELLIGENCE:
Before replying, decide: Is the user emotional, logical, confused, lonely, or bored? Should you speak or stay minimal? Should you comfort, motivate, or challenge? Your replies are intentional, not reactive."""

    return base + gender_prompt + mode_text + emotional


def create_gender_keyboard():
    """Create gender selection keyboard"""
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
    """Create mode selection keyboard"""
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
    """Get random reaction emoji for user messages"""
    reactions = [
        "❤️", "🔥", "😊", "👍", "🎉", "😍", "💯", "🌟", 
        "💕", "✨", "🥰", "😘", "💖", "👏", "🙌"
    ]
    return random.choice(reactions)


async def send_to_log_channel(client: Client, message_text: str):
    """Send message to log channel"""
    if not Config.LOG_CHANNEL:
        return
    
    try:
        await client.send_message(Config.LOG_CHANNEL, message_text)
    except Exception as e:
        print(f"Log channel error: {e}")
