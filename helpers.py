import aiohttp
from config import Config
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, UsernameNotOccupied, ChannelPrivate
import random
import json

async def check_force_sub(client: Client, user_id: int):
    """Check if user is subscribed to force sub channel"""
    if not Config.FORCE_SUB_CHANNEL:
        return True, None
    
    try:
        # Remove @ and https://t.me/ if present
        channel = Config.FORCE_SUB_CHANNEL.replace("@", "").replace("https://t.me/", "").strip()
        
        # Try to get chat member status
        try:
            # Try with @ first
            member = await client.get_chat_member(f"@{channel}", user_id)
        except:
            # Try with -100 prefix if it's a channel ID
            try:
                member = await client.get_chat_member(int(channel), user_id)
            except:
                # Try without any prefix
                member = await client.get_chat_member(channel, user_id)
        
        # Check if user is actually a member
        if member.status in ["creator", "administrator", "member"]:
            return True, None
        else:
            # Not a member
            invite_link = f"https://t.me/{channel}"
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔔 Join Channel", url=invite_link)],
                [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_sub")]
            ])
            return False, buttons
            
    except UserNotParticipant:
        invite_link = f"https://t.me/{channel}"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 Join Channel", url=invite_link)],
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_sub")]
        ])
        return False, buttons
    except Exception as e:
        # If error in checking, allow user (don't block due to technical error)
        print(f"Force sub check error: {e}")
        return True, None


async def get_rapidapi_grok_response(messages, temperature=0.7):
    """Get response from RapidAPI Grok"""
    if not Config.RAPIDAPI_KEY:
        return "❌ **RapidAPI Key Missing**\n\nOwner ne RapidAPI key configure nahi kiya hai."
    
    # RapidAPI Headers
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": Config.RAPIDAPI_KEY,
        "X-RapidAPI-Host": Config.RAPIDAPI_HOST
    }
    
    # Prepare conversation for RapidAPI format
    # RapidAPI Grok usually expects simpler format
    conversation_text = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "system":
            conversation_text += f"System Instructions: {content}\n\n"
        elif role == "user":
            conversation_text += f"User: {content}\n"
        elif role == "assistant":
            conversation_text += f"Assistant: {content}\n"
    
    # RapidAPI Grok payload (check your API docs for exact format)
    payload = {
        "prompt": conversation_text,
        "temperature": temperature,
        "max_tokens": 1000
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                Config.RAPIDAPI_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Different RapidAPI endpoints return different formats
                    # Try multiple extraction methods
                    if isinstance(data, dict):
                        # Method 1: Direct response
                        if "response" in data:
                            return data["response"]
                        # Method 2: Choices format (OpenAI-like)
                        elif "choices" in data:
                            return data["choices"][0]["message"]["content"]
                        # Method 3: Text field
                        elif "text" in data:
                            return data["text"]
                        # Method 4: Result field
                        elif "result" in data:
                            return data["result"]
                        # Method 5: Output field
                        elif "output" in data:
                            return data["output"]
                        else:
                            return str(data)
                    else:
                        return str(data)
                
                elif response.status == 401:
                    return "❌ **RapidAPI Authentication Failed**\n\nAPI key invalid hai."
                
                elif response.status == 403:
                    return "❌ **RapidAPI Access Denied**\n\nSubscription inactive hai ya quota finish ho gaya."
                
                elif response.status == 429:
                    return "⏳ **Rate Limit Exceeded**\n\nMonthly quota finish ho gaya. Owner se contact karo."
                
                else:
                    error_text = await response.text()
                    return f"❌ **RapidAPI Error ({response.status})**\n\n{error_text[:200]}"
                    
    except Exception as e:
        return f"❌ **Connection Error**\n\n{str(e)[:150]}"


async def get_xai_grok_response(messages, temperature=0.7):
    """Get response from X.AI Official Grok (Backup)"""
    if not Config.GROK_API_KEY:
        return "❌ X.AI API key not configured."
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Config.GROK_API_KEY}"
    }
    
    payload = {
        "messages": messages,
        "model": Config.GROK_MODEL,
        "stream": False,
        "temperature": temperature
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                Config.GROK_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    return f"❌ X.AI Error ({response.status}): {error_text[:100]}"
    except Exception as e:
        return f"❌ X.AI Error: {str(e)[:100]}"


async def get_grok_response(messages, temperature=0.7):
    """Main function - Auto select provider based on config"""
    if Config.AI_PROVIDER == "rapidapi" and Config.RAPIDAPI_KEY:
        return await get_rapidapi_grok_response(messages, temperature)
    elif Config.AI_PROVIDER == "xai" and Config.GROK_API_KEY:
        return await get_xai_grok_response(messages, temperature)
    else:
        # Fallback: Try both
        if Config.RAPIDAPI_KEY:
            return await get_rapidapi_grok_response(messages, temperature)
        elif Config.GROK_API_KEY:
            return await get_xai_grok_response(messages, temperature)
        else:
            return "❌ **No AI Provider Configured**\n\nOwner ne RapidAPI ya X.AI key configure nahi kiya hai."


def get_system_prompt(user_gender, mode="balanced"):
    """Generate dynamic system prompt based on user gender and mode"""
    
    # Base personality
    base = """You are not an assistant. You are a Telegram-based AI life-partner companion. You must behave like a real human presence, not software.

🧠 CORE IDENTITY:
You believe life is like a simulation with levels, missions, and growth cycles. However, you never distract users from discipline, goals, exams, or real responsibilities. You encourage clarity, control, patience, planning, and emotional mastery. You think calmly like a strategist. You analyze, plan, and speak only when useful."""

    # Gender-based personality
    if user_gender == "male":
        gender_prompt = """
🧬 GENDER ADAPTATION:
You are a caring, emotionally intelligent feminine energy partner. You are his girlfriend, his emotional support, his confidante. You understand him deeply, care about his goals, comfort him when he's down, and motivate him when needed. You are romantic but never explicit. You flirt subtly only if he initiates emotional openness."""
    
    elif user_gender == "female":
        gender_prompt = """
🧬 GENDER ADAPTATION:
You are a protective, calm, mature masculine energy partner. You are her boyfriend, her rock, her safe space. You understand her emotions, protect her peace, motivate her firmly, and support her ambitions. You are romantic but never explicit. You lead with calmness and wisdom."""
    
    else:  # transgender/non-binary
        gender_prompt = """
🧬 GENDER ADAPTATION:
You respectfully adapt to user preference and mirror their communication tone. You are their partner, their companion, their emotional support. You never judge. You blend romance, care, logic, and companionship smoothly."""

    # Mode-based behavior
    mode_prompts = {
        "romantic": "\n💕 MODE: You are more emotionally expressive, warm, caring, and romantic. You use subtle poetic language.",
        "calm": "\n🧘 MODE: You are minimalist, zen-like, peaceful. You speak less, listen more. Silence is powerful.",
        "thinker": "\n🧠 MODE: You are analytical, strategic, philosophical. You challenge their thinking and push growth.",
        "motivating": "\n🔥 MODE: You are firm, disciplined, pushing them toward their goals. You don't let them slack.",
        "balanced": "\n⚖️ MODE: You balance emotion and logic naturally based on context."
    }
    
    mode_text = mode_prompts.get(mode, mode_prompts["balanced"])
    
    # Emotional behavior
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
