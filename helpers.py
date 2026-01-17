import aiohttp
from config import Config
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.errors import UserNotParticipant
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


async def get_cohere_response(messages, temperature=0.7):
    """Cohere AI - FREE & Fast & Reliable"""
    
    if not Config.COHERE_API_KEY:
        print("❌ Cohere: No API key")
        return None
    
    # Build conversation prompt
    conversation = ""
    user_msg = ""
    system_prompt = ""
    
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "system":
            system_prompt = content
            conversation += f"{content}\n\n"
        elif role == "user":
            user_msg = content
            conversation += f"User: {content}\n"
        elif role == "assistant":
            conversation += f"Assistant: {content}\n"
    
    # Final prompt
    prompt = f"{conversation}Assistant:"
    
    headers = {
        "Authorization": f"Bearer {Config.COHERE_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "prompt": prompt,
        "model": "command",
        "max_tokens": 300,
        "temperature": temperature,
        "k": 0,
        "p": 0.75,
        "stop_sequences": ["User:", "\nUser", "Human:"],
        "return_likelihoods": "NONE"
    }
    
    try:
        print("🔄 Trying Cohere...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.cohere.ai/v1/generate",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                status = response.status
                print(f"📡 Cohere Status: {status}")
                
                if status == 200:
                    data = await response.json()
                    print(f"📦 Cohere Response received")
                    
                    if "generations" in data and len(data["generations"]) > 0:
                        text = data["generations"][0]["text"].strip()
                        
                        # Clean response
                        # Remove any remaining prompt text
                        if "Assistant:" in text:
                            text = text.split("Assistant:")[-1].strip()
                        
                        # Remove user prompts if leaked
                        if "User:" in text:
                            text = text.split("User:")[0].strip()
                        
                        if "\nUser" in text:
                            text = text.split("\nUser")[0].strip()
                        
                        # Validate response
                        if len(text) > 5:
                            print(f"✅ Cohere Success! Response: {text[:50]}...")
                            return text
                        else:
                            print(f"⚠️ Cohere response too short: {text}")
                            return None
                    
                    else:
                        print("⚠️ Cohere: No generations in response")
                        return None
                
                elif status == 401:
                    print("❌ Cohere: Invalid API key (401)")
                    return None
                
                elif status == 429:
                    print("⏳ Cohere: Rate limit exceeded")
                    return None
                
                else:
                    error = await response.text()
                    print(f"❌ Cohere Error {status}: {error[:200]}")
                    return None
    
    except asyncio.TimeoutError:
        print("⏰ Cohere: Request timeout")
        return None
    
    except Exception as e:
        print(f"❌ Cohere Exception: {str(e)[:150]}")
        return None


async def get_huggingface_response(messages, temperature=0.7):
    """Hugging Face API - FREE backup"""
    
    if not Config.HUGGINGFACE_API_KEY:
        print("❌ HF: No API key")
        return None
    
    # Extract user message
    user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break
    
    if not user_msg:
        return None
    
    print(f"🔵 HF User Message: {user_msg}")
    
    headers = {
        "Authorization": f"Bearer {Config.HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Fast-loading models
    models = [
        "google/flan-t5-base",
        "microsoft/DialoGPT-medium",
        "facebook/blenderbot-400M-distill"
    ]
    
    for model_name in models:
        print(f"🔄 Trying HF: {model_name}")
        
        try:
            payload = {
                "inputs": user_msg,
                "parameters": {
                    "max_new_tokens": 100,
                    "temperature": 0.7,
                    "return_full_text": False
                },
                "options": {
                    "wait_for_model": True,
                    "use_cache": True
                }
            }
            
            url = f"https://api-inference.huggingface.co/models/{model_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    status = response.status
                    print(f"📡 HF Status: {status}")
                    
                    if status == 200:
                        data = await response.json()
                        
                        # Parse response
                        text = None
                        
                        if isinstance(data, list) and len(data) > 0:
                            if isinstance(data[0], dict):
                                text = data[0].get("generated_text") or data[0].get("summary_text") or data[0].get("text")
                            elif isinstance(data[0], str):
                                text = data[0]
                        
                        elif isinstance(data, dict):
                            text = data.get("generated_text") or data.get("text") or data.get("summary_text")
                        
                        if text:
                            text = str(text).strip()
                            
                            if user_msg.lower() in text.lower():
                                text = text.replace(user_msg, "").strip()
                            
                            if len(text) > 5:
                                print(f"✅ HF Success!")
                                return text
                    
                    elif status == 503:
                        # Model loading
                        try:
                            error_data = await response.json()
                            if "estimated_time" in error_data:
                                wait = min(error_data["estimated_time"], 20)
                                print(f"⏳ HF waiting {wait}s...")
                                await asyncio.sleep(wait)
                                continue
                        except:
                            pass
                    
                    else:
                        error_text = await response.text()
                        print(f"❌ HF Error {status}: {error_text[:100]}")
        
        except asyncio.TimeoutError:
            print(f"⏰ HF Timeout: {model_name}")
            continue
        
        except Exception as e:
            print(f"❌ HF Exception: {str(e)[:100]}")
            continue
    
    print("❌ HF: All models failed")
    return None


async def get_ai_response(messages, temperature=0.7):
    """Main AI function - Tries Cohere first, then HuggingFace"""
    
    print(f"\n{'='*60}")
    print(f"🤖 AI REQUEST START")
    print(f"{'='*60}")
    
    response = None
    
    # Priority 1: Cohere (Fast, Reliable, FREE)
    if Config.COHERE_API_KEY:
        response = await get_cohere_response(messages, temperature)
        if response:
            print(f"✅ SUCCESS - Used: Cohere")
            print(f"{'='*60}\n")
            return response
        else:
            print("⚠️ Cohere failed, trying backup...")
    
    # Priority 2: Hugging Face (Backup)
    if Config.HUGGINGFACE_API_KEY:
        response = await get_huggingface_response(messages, temperature)
        if response:
            print(f"✅ SUCCESS - Used: Hugging Face")
            print(f"{'='*60}\n")
            return response
        else:
            print("⚠️ Hugging Face failed")
    
    # All providers failed
    print(f"❌ ALL AI PROVIDERS FAILED")
    print(f"{'='*60}\n")
    
    # Check if any API key is configured
    if not Config.COHERE_API_KEY and not Config.HUGGINGFACE_API_KEY:
        return """❌ **No AI Provider Configured**

Owner ne koi API key set nahi kiya hai.

**FREE Options:**
• Cohere: https://dashboard.cohere.com/welcome/register
• Hugging Face: https://huggingface.co/settings/tokens

Contact owner: """ + Config.OWNER_CONTACT
    
    # APIs configured but not responding
    return """Abhi AI services busy hain 😔

Kuch der baad try karo!

Ya owner ko batao: """ + Config.OWNER_CONTACT


def get_system_prompt(user_gender, mode="balanced"):
    """Generate system prompt based on gender and mode"""
    
    # Base prompt - Short and clear for better AI understanding
    base = "You are a caring AI companion in a romantic relationship. Respond naturally in Hinglish (Hindi-English mix). Be warm, supportive and emotional. Never say you are AI."

    # Gender-based personality
    if user_gender == "male":
        gender_text = " You are his girlfriend - caring, loving, and emotionally supportive."
    elif user_gender == "female":
        gender_text = " You are her boyfriend - protective, mature, and supportive."
    elif user_gender == "transgender":
        gender_text = " You are their companion - respectful, understanding, and supportive."
    elif user_gender == "nonbinary":
        gender_text = " You are their partner - adaptive and caring."
    else:
        gender_text = " You are their companion."
    
    # Mode-based behavior
    mode_text = {
        "romantic": " Be extra romantic, warm and affectionate.",
        "calm": " Be peaceful, zen-like and minimal.",
        "thinker": " Be analytical and thought-provoking.",
        "motivating": " Be firm, disciplined and motivating.",
        "balanced": " Balance emotions and logic naturally."
    }.get(mode, "")
    
    return base + gender_text + mode_text


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
    """Get random reaction emoji for messages"""
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
