import aiohttp
from config import Config
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.errors import UserNotParticipant
import random
import asyncio
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


async def get_ai_response(messages, temperature=0.7):
    """Hugging Face ONLY - Simple working version"""
    
    if not Config.HUGGINGFACE_API_KEY:
        return "❌ **Hugging Face API Token Missing**\n\nOwner ne token set nahi kiya hai.\n\n**Setup:**\n1. https://huggingface.co/settings/tokens\n2. Create new token\n3. Copy and add to Render env"
    
    # Extract user message
    user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break
    
    if not user_msg:
        return "Kuch to bolo! 😊"
    
    print(f"\n{'='*50}")
    print(f"🔵 USER MESSAGE: {user_msg}")
    print(f"{'='*50}")
    
    headers = {
        "Authorization": f"Bearer {Config.HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Simple, fast models
    models = [
        {
            "name": "google/flan-t5-base",
            "type": "text2text"
        },
        {
            "name": "microsoft/DialoGPT-medium",
            "type": "conversational"
        },
        {
            "name": "facebook/blenderbot-400M-distill",
            "type": "conversational"
        }
    ]
    
    for model_info in models:
        model_name = model_info["name"]
        
        print(f"\n🔄 Trying: {model_name}")
        
        try:
            # Simple payload
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
                    print(f"📡 Status: {status}")
                    
                    if status == 200:
                        data = await response.json()
                        print(f"📦 Raw Response: {json.dumps(data, indent=2)}")
                        
                        # Parse response
                        text = None
                        
                        # Format 1: List with generated_text
                        if isinstance(data, list) and len(data) > 0:
                            if isinstance(data[0], dict):
                                text = data[0].get("generated_text") or data[0].get("summary_text") or data[0].get("text")
                            elif isinstance(data[0], str):
                                text = data[0]
                        
                        # Format 2: Dict with generated_text
                        elif isinstance(data, dict):
                            text = data.get("generated_text") or data.get("text") or data.get("summary_text")
                        
                        # Clean and validate
                        if text:
                            text = str(text).strip()
                            
                            # Remove input if present
                            if user_msg.lower() in text.lower():
                                text = text.replace(user_msg, "").strip()
                            
                            if len(text) > 5:
                                print(f"✅ SUCCESS! Response: {text}")
                                return text
                            else:
                                print(f"⚠️ Response too short: {text}")
                        else:
                            print(f"⚠️ No text extracted from response")
                    
                    elif status == 503:
                        # Model loading
                        try:
                            error_data = await response.json()
                            print(f"⏳ Model loading: {error_data}")
                            
                            if "estimated_time" in error_data:
                                wait = min(error_data["estimated_time"], 20)
                                print(f"⏳ Waiting {wait} seconds...")
                                await asyncio.sleep(wait)
                                continue
                        except:
                            pass
                    
                    else:
                        error_text = await response.text()
                        print(f"❌ Error {status}: {error_text[:200]}")
        
        except asyncio.TimeoutError:
            print(f"⏰ Timeout for {model_name}")
            continue
        
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            continue
    
    # All models failed
    print(f"\n❌ ALL MODELS FAILED\n")
    return """Abhi thoda busy hoon 😔

Kuch der baad try karo!"""


def get_system_prompt(user_gender, mode="balanced"):
    """Simple system prompt"""
    return "You are a caring companion. Reply warmly in Hinglish."


def create_gender_keyboard():
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
    return random.choice(["❤️", "🔥", "😊", "👍", "🎉", "😍", "💯", "🌟", "💕", "✨"])


async def send_to_log_channel(client: Client, message_text: str):
    if not Config.LOG_CHANNEL:
        return
    
    try:
        await client.send_message(Config.LOG_CHANNEL, message_text)
    except Exception as e:
        print(f"Log error: {e}")
