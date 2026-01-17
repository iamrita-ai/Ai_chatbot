import aiohttp
from config import Config
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from pyrogram.errors import UserNotParticipant
import random
import asyncio


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
    """Hugging Face - Simple & Working approach"""
    
    if not Config.HUGGINGFACE_API_KEY:
        print("❌ HF: No API key")
        return None
    
    # Extract conversation context
    conversation_text = ""
    system_context = ""
    user_message = ""
    
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "system":
            system_context = content
        elif role == "user":
            user_message = content
            conversation_text += f"{content} "
        elif role == "assistant":
            conversation_text += f"{content} "
    
    # Build prompt
    if system_context:
        prompt = f"{system_context}\n\nConversation: {conversation_text}\n\nReply:"
    else:
        prompt = f"{conversation_text}\n\nReply:"
    
    # Keep it short for faster response
    if len(prompt) > 500:
        prompt = f"{system_context[:200]}\n\nUser: {user_message}\n\nReply:"
    
    headers = {
        "Authorization": f"Bearer {Config.HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Fast-loading models (already warm)
    models = [
        "mistralai/Mistral-7B-Instruct-v0.2",
        "google/flan-t5-base",
        "facebook/blenderbot-400M-distill",
        "microsoft/DialoGPT-medium"
    ]
    
    for model_name in models:
        try:
            print(f"🔄 Trying HF model: {model_name}")
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 150,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "do_sample": True,
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
                    timeout=aiohttp.ClientTimeout(total=45)
                ) as response:
                    
                    status = response.status
                    print(f"📡 HF Response Status: {status}")
                    
                    if status == 200:
                        data = await response.json()
                        print(f"📦 HF Data: {data}")
                        
                        # Parse response
                        text = None
                        
                        if isinstance(data, list) and len(data) > 0:
                            first = data[0]
                            
                            if isinstance(first, dict):
                                text = (
                                    first.get("generated_text") or
                                    first.get("summary_text") or
                                    first.get("translation_text") or
                                    first.get("text")
                                )
                            elif isinstance(first, str):
                                text = first
                        
                        elif isinstance(data, dict):
                            text = (
                                data.get("generated_text") or
                                data.get("text") or
                                data.get("summary_text")
                            )
                        
                        # Clean response
                        if text:
                            text = str(text).strip()
                            
                            # Remove the input prompt if included
                            if prompt in text:
                                text = text.replace(prompt, "").strip()
                            
                            # Check if valid response
                            if len(text) > 3 and text != user_message:
                                print(f"✅ HF Success! Response: {text[:50]}...")
                                return text
                        
                        print(f"⚠️ HF: Empty or invalid response")
                    
                    elif status == 503:
                        error_data = await response.json()
                        print(f"⏳ HF: Model loading - {error_data}")
                        
                        # If estimated time is short, wait
                        if "estimated_time" in error_data:
                            wait_time = error_data["estimated_time"]
                            if wait_time < 20:
                                print(f"⏳ Waiting {wait_time}s for model...")
                                await asyncio.sleep(wait_time + 2)
                                # Retry this model once
                                continue
                    
                    else:
                        error_text = await response.text()
                        print(f"❌ HF Error {status}: {error_text[:100]}")
        
        except asyncio.TimeoutError:
            print(f"⏰ HF Timeout: {model_name}")
            continue
        
        except Exception as e:
            print(f"❌ HF Exception ({model_name}): {str(e)[:100]}")
            continue
    
    print("❌ HF: All models failed")
    return None


async def get_gemini_response(messages, temperature=0.7):
    """Google Gemini"""
    
    if not Config.GEMINI_API_KEY:
        print("❌ Gemini: No API key")
        return None
    
    # Build prompt
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
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={Config.GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 800
        }
    }
    
    try:
        print("🔄 Trying Gemini...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                status = response.status
                print(f"📡 Gemini Status: {status}")
                
                if status == 200:
                    data = await response.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"✅ Gemini Success!")
                    return text
                
                else:
                    error = await response.text()
                    print(f"❌ Gemini Error {status}: {error[:100]}")
                    return None
    
    except Exception as e:
        print(f"❌ Gemini Exception: {str(e)[:100]}")
        return None


async def get_groq_response(messages, temperature=0.7):
    """Groq AI"""
    
    if not Config.GROQ_API_KEY:
        print("❌ Groq: No API key")
        return None
    
    headers = {
        "Authorization": f"Bearer {Config.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1000
    }
    
    try:
        print("🔄 Trying Groq...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                status = response.status
                print(f"📡 Groq Status: {status}")
                
                if status == 200:
                    data = await response.json()
                    text = data["choices"][0]["message"]["content"]
                    print(f"✅ Groq Success!")
                    return text
                else:
                    error = await response.text()
                    print(f"❌ Groq Error {status}: {error[:100]}")
                    return None
    
    except Exception as e:
        print(f"❌ Groq Exception: {str(e)[:100]}")
        return None


async def get_ai_response(messages, temperature=0.7):
    """Main AI function - tries all providers"""
    
    print("\n🤖 Starting AI request...")
    response = None
    
    # Try in order: HuggingFace -> Gemini -> Groq
    
    # 1. Hugging Face (Priority for you)
    if Config.HUGGINGFACE_API_KEY:
        response = await get_huggingface_response(messages, temperature)
        if response:
            return response
    
    # 2. Gemini
    if Config.GEMINI_API_KEY:
        response = await get_gemini_response(messages, temperature)
        if response:
            return response
    
    # 3. Groq
    if Config.GROQ_API_KEY:
        response = await get_groq_response(messages, temperature)
        if response:
            return response
    
    # All failed
    print("❌ All AI providers failed")
    return """Sorry yaar, abhi AI services busy hain 😔

Kuch der baad try karo ya owner ko batao!

Contact: """ + Config.OWNER_CONTACT


def get_system_prompt(user_gender, mode="balanced"):
    """System prompt - SHORT VERSION for HF"""
    
    # Shorter prompt for Hugging Face (works better)
    base = "You are a caring companion. Reply naturally in Hinglish. Be warm and supportive."

    if user_gender == "male":
        return base + " You are his girlfriend."
    elif user_gender == "female":
        return base + " You are her boyfriend."
    else:
        return base + " You are their partner."


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
