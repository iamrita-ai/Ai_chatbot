import aiohttp
from config import Config
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, UsernameNotOccupied, ChannelPrivate, UserIsBlocked
import random
import asyncio

# Global variable to store working endpoint
WORKING_ENDPOINT = None


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
    """Get response from RapidAPI Grok - Auto-detect working endpoint"""
    global WORKING_ENDPOINT
    
    if not Config.RAPIDAPI_KEY:
        return "❌ **RapidAPI Key Missing**\n\nOwner ne API key configure nahi kiya."
    
    # Prepare message content
    conversation = ""
    user_message = ""
    
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "system":
            conversation += f"{content}\n\n"
        elif role == "user":
            user_message = content
            conversation += f"User: {content}\n"
        elif role == "assistant":
            conversation += f"Assistant: {content}\n"
    
    # If we already found a working endpoint, use it
    if WORKING_ENDPOINT:
        endpoints_to_try = [WORKING_ENDPOINT] + [e for e in Config.RAPIDAPI_ENDPOINTS if e != WORKING_ENDPOINT]
    else:
        endpoints_to_try = Config.RAPIDAPI_ENDPOINTS
    
    # Try each endpoint
    for endpoint_config in endpoints_to_try:
        try:
            headers = {
                "content-type": "application/json",
                "X-RapidAPI-Key": Config.RAPIDAPI_KEY,
                "X-RapidAPI-Host": endpoint_config["host"]
            }
            
            # Try different payload formats
            payloads = [
                # Format 1: OpenAI-like
                {
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 1000
                },
                # Format 2: Simple prompt
                {
                    "prompt": conversation,
                    "temperature": temperature
                },
                # Format 3: Query format
                {
                    "query": user_message,
                    "context": conversation,
                    "temperature": temperature
                },
                # Format 4: Message format
                {
                    "message": user_message,
                    "temperature": temperature
                }
            ]
            
            for payload in payloads:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            endpoint_config["url"],
                            headers=headers,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=20)
                        ) as response:
                            
                            if response.status == 200:
                                data = await response.json()
                                
                                # Try to extract response from different formats
                                result = None
                                
                                if isinstance(data, dict):
                                    # Try different response keys
                                    for key in ["response", "text", "message", "output", "result", "answer", "completion"]:
                                        if key in data:
                                            result = data[key]
                                            break
                                    
                                    # Try OpenAI format
                                    if not result and "choices" in data:
                                        try:
                                            result = data["choices"][0]["message"]["content"]
                                        except:
                                            pass
                                    
                                    # Try nested response
                                    if not result and "data" in data:
                                        if isinstance(data["data"], dict):
                                            for key in ["response", "text", "message"]:
                                                if key in data["data"]:
                                                    result = data["data"][key]
                                                    break
                                
                                elif isinstance(data, str):
                                    result = data
                                
                                # If we got a valid response
                                if result and len(str(result).strip()) > 0:
                                    # Save working endpoint
                                    WORKING_ENDPOINT = endpoint_config
                                    print(f"✅ Working endpoint found: {endpoint_config['name']}")
                                    return str(result).strip()
                            
                            elif response.status == 404:
                                # Wrong endpoint, try next
                                continue
                                
                except asyncio.TimeoutError:
                    continue
                except aiohttp.ClientError:
                    continue
                except Exception as e:
                    print(f"Payload attempt failed: {e}")
                    continue
        
        except Exception as e:
            print(f"Endpoint {endpoint_config['name']} failed: {e}")
            continue
    
    # If all endpoints failed
    return """❌ **RapidAPI Connection Failed**

Possible issues:
• API key invalid hai
• Subscription inactive hai
• Monthly quota khatam ho gaya
• Wrong Grok API select kiya RapidAPI par

**Solution:**
1. RapidAPI dashboard check karo: https://rapidapi.com/
2. Grok 3.0 AI subscription verify karo
3. API key regenerate karke phir se try karo

Owner contact: https://t.me/technicalserena"""


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
