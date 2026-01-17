import aiohttp
from config import Config
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, UsernameNotOccupied, ChannelPrivate, UserIsBlocked
import random
import asyncio
import json


async def check_force_sub(client: Client, user_id: int):
    """Check if user is subscribed to force sub channel - IMPROVED VERSION"""
    
    # If no force sub channel set, allow everyone
    if not Config.FORCE_SUB_CHANNEL:
        return True, None
    
    # Owner bypass - owners ko verification skip
    if user_id in Config.OWNER_ID:
        return True, None
    
    try:
        # Clean channel username
        channel = Config.FORCE_SUB_CHANNEL.strip()
        channel = channel.replace("https://t.me/", "")
        channel = channel.replace("http://t.me/", "")
        channel = channel.replace("@", "")
        
        # Try to get member info
        try:
            member = await client.get_chat_member(f"@{channel}", user_id)
        except Exception as e:
            print(f"Force sub error for @{channel}: {e}")
            # If error in checking, allow user (don't block)
            return True, None
        
        # Check member status
        if member.status in ["creator", "administrator", "member"]:
            return True, None
        
        # User is not a member - show join button
        invite_link = f"https://t.me/{channel}"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 Join Channel", url=invite_link)],
            [InlineKeyboardButton("✅ I Joined, Check Again", callback_data="refresh_sub")]
        ])
        return False, buttons
        
    except UserNotParticipant:
        # User not in channel
        invite_link = f"https://t.me/{channel}"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 Join Channel", url=invite_link)],
            [InlineKeyboardButton("✅ I Joined, Check Again", callback_data="refresh_sub")]
        ])
        return False, buttons
        
    except Exception as e:
        # Any other error - allow user (don't block due to technical issues)
        print(f"Force sub exception: {e}")
        return True, None


async def get_rapidapi_grok_response(messages, temperature=0.7):
    """Get response from RapidAPI Grok 3.0 - EXACT FORMAT FROM CODE SNIPPET"""
    
    if not Config.RAPIDAPI_KEY:
        return "❌ **RapidAPI Key Missing**\n\nOwner ne API key configure nahi kiya."
    
    # Prepare messages in exact format
    formatted_messages = []
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # RapidAPI Grok accepts: user, assistant, system
        formatted_messages.append({
            "role": role,
            "content": content
        })
    
    # Exact payload format from code snippet
    payload = {
        "model": Config.RAPIDAPI_MODEL,  # "Grok-3"
        "messages": formatted_messages
    }
    
    # Exact headers from code snippet
    headers = {
        "x-rapidapi-key": Config.RAPIDAPI_KEY,
        "x-rapidapi-host": Config.RAPIDAPI_HOST,
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                Config.RAPIDAPI_URL,  # https://grok-3-0-ai.p.rapidapi.com/
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                print(f"✅ RapidAPI Status: {response.status}")  # Debug log
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ RapidAPI Response received")  # Debug log
                    
                    # Try to extract response from different possible formats
                    try:
                        # Format 1: OpenAI-like (most common)
                        if "choices" in data and len(data["choices"]) > 0:
                            return data["choices"][0]["message"]["content"]
                        
                        # Format 2: Direct response field
                        elif "response" in data:
                            return data["response"]
                        
                        # Format 3: Text field
                        elif "text" in data:
                            return data["text"]
                        
                        # Format 4: Message field
                        elif "message" in data:
                            if isinstance(data["message"], str):
                                return data["message"]
                            elif isinstance(data["message"], dict) and "content" in data["message"]:
                                return data["message"]["content"]
                        
                        # Format 5: Completion field
                        elif "completion" in data:
                            return data["completion"]
                        
                        # Format 6: Result field
                        elif "result" in data:
                            return data["result"]
                        
                        # If none matched, return raw data for debugging
                        else:
                            return f"⚠️ Response format unknown:\n\n{json.dumps(data, indent=2)[:500]}"
                    
                    except Exception as e:
                        return f"❌ Error parsing response: {str(e)}\n\nRaw data: {str(data)[:300]}"
                
                elif response.status == 401:
                    return "❌ **Invalid API Key**\n\nRapidAPI key invalid hai. Check karo."
                
                elif response.status == 403:
                    error_text = await response.text()
                    return f"❌ **Access Denied**\n\nSubscription inactive ho sakta hai.\n\n{error_text[:200]}"
                
                elif response.status == 429:
                    return "⏳ **Rate Limit Exceeded**\n\nMonthly quota khatam ho gaya. Dashboard check karo."
                
                elif response.status == 500:
                    return "⚠️ **Server Error**\n\nGrok API server issue hai. Thodi der baad try karo."
                
                else:
                    error_text = await response.text()
                    return f"❌ **HTTP Error {response.status}**\n\n{error_text[:300]}"
    
    except asyncio.TimeoutError:
        return "⏳ **Timeout**\n\nRequest mein bahut time lag raha hai. Phir try karo."
    
    except aiohttp.ClientError as e:
        return f"❌ **Network Error**\n\n{str(e)[:200]}"
    
    except Exception as e:
        return f"❌ **Unknown Error**\n\n{str(e)[:200]}"


async def get_grok_response(messages, temperature=0.7):
    """Main AI response function"""
    return await get_rapidapi_grok_response(messages, temperature)


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
