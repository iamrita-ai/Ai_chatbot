import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ReactionInvalid
from config import Config
from database import db
from helpers import (
    check_force_sub,
    get_ai_response,
    get_system_prompt,
    create_gender_keyboard,
    create_mode_keyboard,
    get_random_reaction,
    send_to_log_channel
)
from flask import Flask
from threading import Thread
import time

# Flask for Render
app = Flask(__name__)

@app.route('/')
def home():
    return f"✅ {Config.BOT_NAME} is running!"

@app.route('/health')
def health():
    return {"status": "healthy", "bot": Config.BOT_NAME}

def run_flask():
    app.run(host="0.0.0.0", port=Config.PORT)

# Pyrogram Bot
bot = Client(
    "ai_companion_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Flood control
user_flood_control = {}

# ========== USER COMMANDS ==========

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    if not Config.MONGO_URI:
        await message.reply(
            "❌ **Database Error**\nMongoDB not configured.\n"
            f"Contact: {Config.OWNER_CONTACT}"
        )
        return
    
    if not db.client:
        db_connected = await db.connect()
        if not db_connected:
            await message.reply(
                "❌ **Database Connection Failed**\n"
                f"Contact: {Config.OWNER_CONTACT}"
            )
            return
    
    is_subscribed, buttons = await check_force_sub(client, user_id)
    if not is_subscribed:
        await message.reply(
            f"🔒 **Access Restricted**\n\n"
            f"Pehle channel join karo: @{Config.FORCE_SUB_CHANNEL}\n\n"
            "Join karke 'Check Again' dabao!",
            reply_markup=buttons
        )
        return
    
    if await db.is_banned(user_id):
        await message.reply("🚫 You are banned.")
        return
    
    await db.add_user(user_id, first_name, username)
    user = await db.get_user(user_id)
    
    if not user.get("gender"):
        await message.reply(
            f"🌟 **Welcome to {Config.BOT_NAME}**\n\n"
            "Main tumhara AI life partner hoon.\n\n"
            "**Pehle batao, tum kaun ho?**",
            reply_markup=create_gender_keyboard()
        )
        
        await send_to_log_channel(
            client,
            f"🆕 **New User**\n👤 {first_name}\n🆔 `{user_id}`\n📝 @{username or 'None'}"
        )
    else:
        gender_emoji = {"male": "👨", "female": "👩", "transgender": "🏳️‍⚧️", "nonbinary": "⚧️"}
        await message.reply(
            f"💕 **Welcome back!**\n\n"
            f"{gender_emoji.get(user['gender'], '😊')} Kaise ho?\n\n"
            "Commands: /help"
        )


@bot.on_callback_query(filters.regex("^gender_"))
async def gender_selection(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    gender = callback.data.split("_")[1]
    
    await db.set_gender(user_id, gender)
    
    responses = {
        "male": "👩‍❤️‍👨 Main tumhari girlfriend ban gayi!",
        "female": "👨‍❤️‍👩 Main tumhara boyfriend ban gaya!",
        "transgender": "🏳️‍⚧️ Main tumhara companion hoon!",
        "nonbinary": "⚧️ Main tumhara partner hoon!"
    }
    
    await callback.message.edit_text(
        f"{responses.get(gender, 'Welcome!')}\n\n"
        "Ab mujhse baat karo. Commands: /help"
    )
    
    await send_to_log_channel(
        client,
        f"✅ Gender Set\n👤 {callback.from_user.first_name} (`{user_id}`)\n🎭 {gender}"
    )


@bot.on_callback_query(filters.regex("^refresh_sub$"))
async def refresh_subscription(client: Client, callback: CallbackQuery):
    is_subscribed, _ = await check_force_sub(client, callback.from_user.id)
    if is_subscribed:
        await callback.message.delete()
        await callback.message.reply("✅ Verified! /start dabao.")
    else:
        await callback.answer("❌ Abhi bhi join nahi kiya!", show_alert=True)


@bot.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id in Config.OWNER_ID:
        help_text = f"""
📚 **Admin Help**

**User Commands:**
/start, /help, /mode, /mood, /reset, /privacy

**Admin Commands:**
/ownerpanel - Control panel
/broadcast <msg> - Broadcast
/viewstats - Statistics
/banuser <id> - Ban user
/unbanuser <id> - Unban user
/debug - System check
/aitest - Test AI

Total Users: {await db.get_total_users()}
"""
    else:
        help_text = f"""
📚 **{Config.BOT_NAME}**

Main tumhara AI companion hoon.

**Commands:**
/start - Start
/mode - Change mode
/mood - Share mood
/reset - Reset memory
/privacy - Privacy

**Modes:**
💕 Romantic | 🧘 Calm | 🧠 Thinker | 🔥 Motivating | ⚖️ Balanced

Simply message karo! 💬
"""
    
    await message.reply(help_text)


@bot.on_message(filters.command("mode") & filters.private)
async def mode_command(client: Client, message: Message):
    user = await db.get_user(message.from_user.id)
    current = user.get("mode", "balanced") if user else "balanced"
    
    await message.reply(
        f"🎭 **Mode Selection**\n\nCurrent: **{current.title()}**",
        reply_markup=create_mode_keyboard()
    )


@bot.on_callback_query(filters.regex("^mode_"))
async def mode_selection(client: Client, callback: CallbackQuery):
    mode = callback.data.split("_")[1]
    await db.set_mode(callback.from_user.id, mode)
    
    responses = {
        "romantic": "💕 Romantic mode set!",
        "calm": "🧘 Calm mode set!",
        "thinker": "🧠 Thinker mode set!",
        "motivating": "🔥 Motivating mode set!",
        "balanced": "⚖️ Balanced mode set!"
    }
    
    await callback.message.edit_text(responses.get(mode, "Mode updated!"))


@bot.on_message(filters.command("reset") & filters.private)
async def reset_command(client: Client, message: Message):
    await db.reset_memory(message.from_user.id)
    await message.reply("🔄 **Memory Reset**\nFresh start!")


@bot.on_message(filters.command("mood") & filters.private)
async def mood_command(client: Client, message: Message):
    await message.reply("💭 **How are you feeling?**\nBatao kya chal raha hai?")


@bot.on_message(filters.command("privacy") & filters.private)
async def privacy_command(client: Client, message: Message):
    await message.reply(
        "🔒 **Privacy**\n\n"
        "✅ Safe & private\n"
        "✅ Not shared\n"
        "✅ /reset to delete"
    )


# ========== OWNER COMMANDS ==========

@bot.on_message(filters.command("ownerpanel") & filters.user(Config.OWNER_ID) & filters.private)
async def owner_panel(client: Client, message: Message):
    total = await db.get_total_users()
    
    hf_status = "✅ Set" if Config.HUGGINGFACE_API_KEY else "❌ Not Set"
    
    panel = f"""
🛠️ **Owner Panel**

📊 Users: {total}

🤖 AI: Hugging Face {hf_status}

**Commands:**
/broadcast, /viewstats, /banuser, /unbanuser, /debug, /aitest
"""
    await message.reply(panel)


@bot.on_message(filters.command("broadcast") & filters.user(Config.OWNER_ID) & filters.private)
async def broadcast_command(client: Client, message: Message):
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("❌ /broadcast <message> or reply to message")
        return
    
    msg = message.reply_to_message if message.reply_to_message else " ".join(message.command[1:])
    users = await db.get_all_users()
    success = failed = 0
    
    status = await message.reply(f"📤 Broadcasting to {len(users)}...")
    
    for uid in users:
        try:
            if message.reply_to_message:
                await msg.copy(uid)
            else:
                await client.send_message(uid, msg)
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
        
        if (success + failed) % 50 == 0:
            try:
                await status.edit_text(f"📤 Progress\n✅ {success}\n❌ {failed}")
            except:
                pass
    
    await status.edit_text(f"✅ **Done!**\n✅ Success: {success}\n❌ Failed: {failed}")


@bot.on_message(filters.command("banuser") & filters.user(Config.OWNER_ID) & filters.private)
async def ban_user(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ /banuser <user_id>")
        return
    
    try:
        uid = int(message.command[1])
        await db.ban_user(uid)
        await message.reply(f"✅ Banned: `{uid}`")
    except:
        await message.reply("❌ Invalid ID")


@bot.on_message(filters.command("unbanuser") & filters.user(Config.OWNER_ID) & filters.private)
async def unban_user(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ /unbanuser <user_id>")
        return
    
    try:
        uid = int(message.command[1])
        await db.unban_user(uid)
        await message.reply(f"✅ Unbanned: `{uid}`")
    except:
        await message.reply("❌ Invalid ID")


@bot.on_message(filters.command("debug") & filters.user(Config.OWNER_ID) & filters.private)
async def debug_command(client: Client, message: Message):
    
    # MongoDB
    mongo = "✅ Connected" if db.client else "❌ Not Connected"
    
    # Log Channel
    log_status = "❌ Not Set"
    if Config.LOG_CHANNEL:
        try:
            chat = await client.get_chat(Config.LOG_CHANNEL)
            log_status = f"✅ {chat.title}"
        except Exception as e:
            log_status = f"⚠️ {str(e)[:30]}"
    
    # Force Sub
    force = "❌ Not Set"
    if Config.FORCE_SUB_CHANNEL:
        try:
            ch = Config.FORCE_SUB_CHANNEL.replace("@", "").strip()
            chat = await client.get_chat(f"@{ch}")
            force = f"✅ {chat.title}"
        except Exception as e:
            force = f"⚠️ {str(e)[:30]}"
    
    # AI Providers
    ai_status = []
    
    if Config.COHERE_API_KEY:
        ai_status.append(f"✅ Cohere: {Config.COHERE_API_KEY[:10]}...")
    else:
        ai_status.append("❌ Cohere: Not Set")
    
    if Config.HUGGINGFACE_API_KEY:
        ai_status.append(f"✅ HF: {Config.HUGGINGFACE_API_KEY[:10]}...")
    else:
        ai_status.append("❌ HF: Not Set")
    
    ai_info = "\n".join(ai_status)
    
    debug_text = f"""
🔍 **System Check**

**🤖 AI Providers:**
{ai_info}

**💾 MongoDB:** {mongo}
**📢 Log:** {log_status}
**🔒 Force Sub:** {force}

**📊 Users:** {await db.get_total_users()}

**Test:** /aitest

**Get FREE API Keys:**
• Cohere: https://dashboard.cohere.com
• HF: https://huggingface.co/settings/tokens
"""
    await message.reply(debug_text)


@bot.on_message(filters.command("aitest") & filters.user(Config.OWNER_ID) & filters.private)
async def ai_test(client: Client, message: Message):
    
    test_msg = await message.reply("🔍 Testing AI providers...")
    
    response = await get_ai_response([
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! How are you today?"}
    ], temperature=0.7)
    
    # Check response quality
    if response and len(response) > 10 and "❌" not in response and "busy" not in response.lower():
        status = "✅ **Working Perfectly!**"
    else:
        status = "❌ **Failed**"
    
    result = f"""
**AI Provider Test**

{status}

**Response:**
{response}

**Configured:**
{"✅ Cohere" if Config.COHERE_API_KEY else "❌ Cohere"}
{"✅ Hugging Face" if Config.HUGGINGFACE_API_KEY else "❌ Hugging Face"}
"""
    
    await test_msg.edit_text(result)

@bot.on_message(filters.command("viewstats") & filters.user(Config.OWNER_ID) & filters.private)
async def view_stats(client: Client, message: Message):
    total = await db.get_total_users()
    
    male = await db.users.count_documents({"gender": "male"})
    female = await db.users.count_documents({"gender": "female"})
    trans = await db.users.count_documents({"gender": "transgender"})
    nb = await db.users.count_documents({"gender": "nonbinary"})
    none = await db.users.count_documents({"gender": None})
    
    stats = f"""
📊 **Statistics**

**Total:** {total}

**Gender:**
👨 Male: {male}
👩 Female: {female}
🏳️‍⚧️ Trans: {trans}
⚧️ NB: {nb}
❓ Not Set: {none}
"""
    await message.reply(stats)


# ========== CONVERSATION HANDLER ==========

@bot.on_message(filters.text & filters.private & ~filters.command(["start", "help", "mode", "mood", "reset", "privacy", "ownerpanel", "broadcast", "banuser", "unbanuser", "debug", "viewstats", "aitest"]))
async def handle_conversation(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not Config.MONGO_URI or not db.client:
        await message.reply(f"❌ Database error\nContact: {Config.OWNER_CONTACT}")
        return
    
    is_subscribed, buttons = await check_force_sub(client, user_id)
    if not is_subscribed:
        await message.reply("🔒 Join channel first!", reply_markup=buttons)
        return
    
    if await db.is_banned(user_id):
        return
    
    # Flood control
    now = time.time()
    if user_id in user_flood_control:
        if now - user_flood_control[user_id] < Config.FLOOD_SLEEP:
            await message.reply("⏳ Wait!")
            return
    user_flood_control[user_id] = now
    
    user = await db.get_user(user_id)
    if not user:
        await message.reply("⚠️ /start first!")
        return
    
    if not user.get("gender"):
        await message.reply("⚠️ Set gender via /start")
        return
    
    # Reaction
    try:
        await message.react(get_random_reaction())
    except:
        pass
    
    # Typing
    try:
        await client.send_chat_action(user_id, enums.ChatAction.TYPING)
    except:
        pass
    
    # History
    history = await db.get_conversation_history(user_id, limit=5)
    history.reverse()
    
    # Build messages
    messages = []
    mode = user.get("mode", "balanced")
    gender = user.get("gender")
    messages.append({"role": "system", "content": get_system_prompt(gender, mode)})
    
    for conv in history:
        messages.append({"role": "user", "content": conv["user_message"]})
        messages.append({"role": "assistant", "content": conv["bot_response"]})
    
    messages.append({"role": "user", "content": message.text})
    
    # Get AI response
    response = await get_ai_response(messages, temperature=0.8)
    
    # Send
    await message.reply(response)
    
    # Save
    await db.save_conversation(user_id, message.text, response)
    
    # Log
    await send_to_log_channel(
        client,
        f"💬 **Chat**\n\n"
        f"👤 {message.from_user.first_name} (`{user_id}`)\n"
        f"🎭 {gender} | {mode}\n\n"
        f"**User:** {message.text}\n\n"
        f"**Bot:** {response[:400]}"
    )


# ========== MAIN ==========

async def main():
    # Connect to database
    if Config.MONGO_URI:
        connected = await db.connect()
        if connected:
            print("✅ MongoDB Connected")
        else:
            print("❌ MongoDB Failed")
    else:
        print("⚠️ MongoDB URI not set")
    
    # Start bot
    await bot.start()
    print(f"✅ {Config.BOT_NAME} Started!")
    print("🤖 AI: Hugging Face")
    
    # Keep alive
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Start Flask
    Thread(target=run_flask).start()
    
    # Run bot
    bot.run(main())
