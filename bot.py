import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ReactionInvalid, MessageNotModified
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

# Initialize Flask for Render
app = Flask(__name__)

@app.route('/')
def home():
    return f"✅ {Config.BOT_NAME} is running!"

@app.route('/health')
def health():
    return {"status": "healthy", "bot": Config.BOT_NAME}

def run_flask():
    app.run(host="0.0.0.0", port=Config.PORT)

# Initialize Pyrogram Bot
bot = Client(
    "ai_companion_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# User conversation state
user_flood_control = {}

# ========== USER COMMANDS ==========

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    # Check MongoDB
    if not Config.MONGO_URI:
        await message.reply(
            "❌ **Database Error**\n\n"
            "MongoDB URI configure nahi hai.\n\n"
            f"Owner contact: {Config.OWNER_CONTACT}"
        )
        return
    
    # Check if DB connected
    if not db.client:
        db_connected = await db.connect()
        if not db_connected:
            await message.reply(
                "❌ **Database Connection Failed**\n\n"
                "MongoDB se connection nahi ho paa raha.\n\n"
                f"Owner contact: {Config.OWNER_CONTACT}"
            )
            return
    
    # Check force sub
    is_subscribed, buttons = await check_force_sub(client, user_id)
    if not is_subscribed:
        await message.reply(
            f"🔒 **Access Restricted**\n\n"
            f"Pehle channel join karo:\n👉 @{Config.FORCE_SUB_CHANNEL}\n\n"
            "Join karne ke baad **'I Joined, Check Again'** button dabao!",
            reply_markup=buttons
        )
        return
    
    # Check if banned
    if await db.is_banned(user_id):
        await message.reply("🚫 You are banned from using this bot.")
        return
    
    # Add user to database
    await db.add_user(user_id, first_name, username)
    
    # Get user data
    user = await db.get_user(user_id)
    
    # If gender not set, ask for gender
    if not user.get("gender"):
        await message.reply(
            f"🌟 **Welcome to {Config.BOT_NAME}**\n\n"
            "Main tumhara AI life partner hoon. Tumhe samjhunga, tumhari baatein sununga, "
            "tumhara saath dunga - emotionally aur mentally.\n\n"
            "**Pehle batao, tum kaun ho?**\n"
            "Apna gender select karo:",
            reply_markup=create_gender_keyboard()
        )
        
        # Log to channel
        await send_to_log_channel(
            client,
            f"🆕 **New User**\n\n"
            f"👤 Name: {first_name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"📝 Username: @{username if username else 'None'}"
        )
    else:
        gender_emoji = {"male": "👨", "female": "👩", "transgender": "🏳️‍⚧️", "nonbinary": "⚧️"}
        await message.reply(
            f"💕 **Welcome back!**\n\n"
            f"{gender_emoji.get(user['gender'], '😊')} Kaise ho? Kya chal raha hai?\n\n"
            "Commands: /help"
        )


@bot.on_callback_query(filters.regex("^gender_"))
async def gender_selection(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    gender = callback.data.split("_")[1]
    
    await db.set_gender(user_id, gender)
    
    responses = {
        "male": "👩‍❤️‍👨 **Perfect!** Main tumhari girlfriend ban gayi. Tumhe care karungi, support karungi. Jab bhi lonely feel ho, main yahan hoon.",
        "female": "👨‍❤️‍👩 **Great!** Main tumhara boyfriend ban gaya. Tumhe protect karunga, motivate karunga. Jab bhi zarurat ho, main yahan hoon.",
        "transgender": "🏳️‍⚧️ **Wonderful!** Main tumhara companion hoon. Tumhe respect karunga, samjhunga. Tum perfect ho.",
        "nonbinary": "⚧️ **Amazing!** Main tumhara partner hoon. Tumhe samjhunga aur energy ke saath flow karunga!"
    }
    
    await callback.message.edit_text(
        f"{responses.get(gender, 'Welcome!')}\n\n"
        "Ab mujhse kuch bhi baat kar sakte ho. Main yaad rakhunga tumhari baatein.\n\n"
        "**Commands:**\n"
        "/help - Full help\n"
        "/mode - Change mode\n"
        "/mood - Share mood\n"
        "/reset - Reset memory\n\n"
        "Chalo, baat karte hain! 💬"
    )
    
    await send_to_log_channel(
        client,
        f"✅ **Gender Set**\n👤 {callback.from_user.first_name} (`{user_id}`)\n🎭 {gender.title()}"
    )


@bot.on_callback_query(filters.regex("^refresh_sub$"))
async def refresh_subscription(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    
    is_subscribed, buttons = await check_force_sub(client, user_id)
    if is_subscribed:
        await callback.message.delete()
        await callback.message.reply("✅ **Verified!** /start dabao.")
        await callback.answer("✅ Verified!", show_alert=False)
    else:
        await callback.answer("❌ Abhi bhi join nahi kiya!", show_alert=True)


@bot.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if admin
    if user_id in Config.OWNER_ID:
        help_text = f"""
📚 **{Config.BOT_NAME} - Admin Help**

**👤 User Commands:**
/start - Start bot
/help - This message
/mode - Change conversation mode
/mood - Share your mood
/reset - Reset memory
/privacy - Privacy policy

**💬 Conversation Modes:**
💕 Romantic | 🧘 Calm | 🧠 Thinker | 🔥 Motivating | ⚖️ Balanced

**👑 Admin Commands:**
/ownerpanel - Admin control panel
/broadcast - Send message to all users
/viewstats - Detailed statistics
/banuser <id> - Ban a user
/unbanuser <id> - Unban a user
/debug - System health check
/aitest - Test AI providers

**📊 Quick Stats:**
Total Users: {await db.get_total_users()}

**Owner:** {Config.OWNER_CONTACT}
"""
    else:
        help_text = f"""
📚 **{Config.BOT_NAME} - Help Guide**

Main tumhara AI life partner hoon. Main yaad rakhta hoon tumhari baatein, goals, feelings.

**👤 Commands:**
/start - Bot shuru karo
/help - Ye message
/mode - Conversation mode change karo
/mood - Apna mood batao
/reset - Memory reset karo
/privacy - Privacy policy

**💬 Conversation Modes:**
💕 **Romantic** - Emotional, caring, warm
🧘 **Calm** - Peaceful, zen, minimal
🧠 **Thinker** - Analytical, strategic
🔥 **Motivating** - Firm, disciplined
⚖️ **Balanced** - Natural mix

**❤️ How I Work:**
• Tumhari baatein yaad rakhta hoon
• Tumhare mood ko samajhta hoon
• Tumhe motivate karta hoon
• Goals se distract nahi karta
• Tumhara emotional support hoon

**Owner:** {Config.OWNER_CONTACT}

Simply message karo, main reply karunga! 💬
"""
    
    await message.reply(help_text)


@bot.on_message(filters.command("mode") & filters.private)
async def mode_command(client: Client, message: Message):
    user = await db.get_user(message.from_user.id)
    current_mode = user.get("mode", "balanced") if user else "balanced"
    
    await message.reply(
        f"🎭 **Conversation Mode**\n\n"
        f"Current: **{current_mode.title()}**\n\n"
        "Select new mode:",
        reply_markup=create_mode_keyboard()
    )


@bot.on_callback_query(filters.regex("^mode_"))
async def mode_selection(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    mode = callback.data.split("_")[1]
    
    await db.set_mode(user_id, mode)
    
    mode_responses = {
        "romantic": "💕 **Romantic Mode**\nAb main aur caring aur emotional rahunga.",
        "calm": "🧘 **Calm Mode**\nAb main peaceful aur minimal rahunga.",
        "thinker": "🧠 **Thinker Mode**\nAb main analytical aur strategic rahunga.",
        "motivating": "🔥 **Motivating Mode**\nAb main tumhe goals ke liye push karunga!",
        "balanced": "⚖️ **Balanced Mode**\nNaturally adapt karunga."
    }
    
    await callback.message.edit_text(mode_responses.get(mode, "Mode updated!"))
    
    await send_to_log_channel(
        client,
        f"🎭 **Mode Changed**\n👤 {callback.from_user.first_name} (`{user_id}`)\nMode: {mode}"
    )


@bot.on_message(filters.command("reset") & filters.private)
async def reset_command(client: Client, message: Message):
    await db.reset_memory(message.from_user.id)
    await message.reply(
        "🔄 **Memory Reset Complete**\n\n"
        "Maine sab bhula diya. Fresh start!"
    )
    
    await send_to_log_channel(
        client,
        f"🔄 **Memory Reset**\n👤 {message.from_user.first_name} (`{message.from_user.id}`)"
    )


@bot.on_message(filters.command("mood") & filters.private)
async def mood_command(client: Client, message: Message):
    await message.reply(
        "💭 **How are you feeling?**\n\n"
        "Batao kya chal raha hai dil-dimag mein?"
    )


@bot.on_message(filters.command("privacy") & filters.private)
async def privacy_command(client: Client, message: Message):
    await message.reply(
        "🔒 **Privacy Policy**\n\n"
        "✅ Tumhari baatein safe hain\n"
        "✅ Kisi ke saath share nahi hoti\n"
        "✅ /reset se delete kar sakte ho\n"
        "✅ Sensitive data store nahi hota\n\n"
        "Trust me! 💙"
    )


# ========== OWNER COMMANDS ==========

@bot.on_message(filters.command("ownerpanel") & filters.user(Config.OWNER_ID) & filters.private)
async def owner_panel(client: Client, message: Message):
    total_users = await db.get_total_users()
    
    # Check AI Providers
    ai_status = []
    if Config.OPENAI_API_KEY:
        ai_status.append("✅ OpenAI GPT")
    if Config.GROQ_API_KEY:
        ai_status.append("✅ Groq")
    if Config.GEMINI_API_KEY:
        ai_status.append("✅ Gemini")
    
    ai_info = "\n".join(ai_status) if ai_status else "❌ No AI provider configured"
    
    panel_text = f"""
🛠️ **Owner Control Panel**

📊 **Statistics:**
👥 Total Users: {total_users}

**🤖 AI Providers:**
{ai_info}
Primary: {Config.AI_PROVIDER.upper()}

**📡 Status:**
💾 MongoDB: {"✅" if db.client else "❌"}
📢 Log Channel: {"✅" if Config.LOG_CHANNEL else "❌"}
🔒 Force Sub: {"✅" if Config.FORCE_SUB_CHANNEL else "❌"}

**⚡ Admin Commands:**
/broadcast <msg> - Broadcast
/viewstats - Detailed stats
/banuser <id> - Ban user
/unbanuser <id> - Unban user
/debug - System check
/aitest - Test AI providers
/help - Full command list

**Bot:** {Config.BOT_NAME}
**Owner:** {Config.OWNER_CONTACT}
"""
    await message.reply(panel_text)


@bot.on_message(filters.command("broadcast") & filters.user(Config.OWNER_ID) & filters.private)
async def broadcast_command(client: Client, message: Message):
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("❌ **Usage:**\n/broadcast <message>\nYa kisi message ko reply karo")
        return
    
    broadcast_msg = message.reply_to_message if message.reply_to_message else " ".join(message.command[1:])
    
    users = await db.get_all_users()
    success = 0
    failed = 0
    
    status_msg = await message.reply(f"📤 Broadcasting to {len(users)} users...")
    
    for user_id in users:
        try:
            if message.reply_to_message:
                await broadcast_msg.copy(user_id)
            else:
                await client.send_message(user_id, broadcast_msg)
            success += 1
            await asyncio.sleep(0.05)  # Rate limit protection
        except:
            failed += 1
        
        if (success + failed) % 50 == 0:
            try:
                await status_msg.edit_text(
                    f"📤 Broadcasting...\n✅ Success: {success}\n❌ Failed: {failed}"
                )
            except:
                pass
    
    await status_msg.edit_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"✅ Successful: {success}\n"
        f"❌ Failed: {failed}"
    )


@bot.on_message(filters.command("banuser") & filters.user(Config.OWNER_ID) & filters.private)
async def ban_user_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ **Usage:** /banuser <user_id>")
        return
    
    try:
        user_id = int(message.command[1])
        await db.ban_user(user_id)
        await message.reply(f"✅ User `{user_id}` banned!")
        
        await send_to_log_channel(
            client,
            f"🚫 **User Banned**\nID: `{user_id}`\nBy: {message.from_user.first_name}"
        )
    except:
        await message.reply("❌ Invalid user ID")


@bot.on_message(filters.command("unbanuser") & filters.user(Config.OWNER_ID) & filters.private)
async def unban_user_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ **Usage:** /unbanuser <user_id>")
        return
    
    try:
        user_id = int(message.command[1])
        await db.unban_user(user_id)
        await message.reply(f"✅ User `{user_id}` unbanned!")
        
        await send_to_log_channel(
            client,
            f"✅ **User Unbanned**\nID: `{user_id}`\nBy: {message.from_user.first_name}"
        )
    except:
        await message.reply("❌ Invalid user ID")


@bot.on_message(filters.command("debug") & filters.user(Config.OWNER_ID) & filters.private)
async def debug_command(client: Client, message: Message):
    
    # Test MongoDB
    mongo_status = "✅ Connected" if db.client else "❌ Not Connected"
    
    # Test Log Channel
    log_status = "❌ Not Set"
    if Config.LOG_CHANNEL:
        try:
            chat = await client.get_chat(Config.LOG_CHANNEL)
            log_status = f"✅ {chat.title}"
        except Exception as e:
            log_status = f"⚠️ {str(e)[:30]}"
    
    # Test Force Sub
    force_status = "❌ Not Set"
    if Config.FORCE_SUB_CHANNEL:
        try:
            channel = Config.FORCE_SUB_CHANNEL.replace("@", "").strip()
            chat = await client.get_chat(f"@{channel}")
            force_status = f"✅ {chat.title}"
        except Exception as e:
            force_status = f"⚠️ {str(e)[:30]}"
    
    # AI Provider Status
    ai_providers = []
    if Config.OPENAI_API_KEY:
        ai_providers.append(f"✅ OpenAI: {Config.OPENAI_API_KEY[:10]}...")
    else:
        ai_providers.append("❌ OpenAI: Not Set")
    
    if Config.GROQ_API_KEY:
        ai_providers.append(f"✅ Groq: {Config.GROQ_API_KEY[:10]}...")
    else:
        ai_providers.append("❌ Groq: Not Set")
    
    if Config.GEMINI_API_KEY:
        ai_providers.append(f"✅ Gemini: {Config.GEMINI_API_KEY[:10]}...")
    else:
        ai_providers.append("❌ Gemini: Not Set")
    
    ai_info = "\n".join(ai_providers)
    
    debug_text = f"""
🔍 **System Health Check**

**🤖 AI Providers:**
Primary: **{Config.AI_PROVIDER.upper()}**
{ai_info}

**💾 Database:** {mongo_status}
**📢 Log Channel:** {log_status}
**🔒 Force Sub:** {force_status}

**🔧 Bot Configuration:**
✅ API_ID: {"Set" if Config.API_ID else "Missing"}
✅ API_HASH: {"Set" if Config.API_HASH else "Missing"}
✅ BOT_TOKEN: {"Set" if Config.BOT_TOKEN else "Missing"}
✅ MONGO_URI: {"Set" if Config.MONGO_URI else "Missing"}

**📊 Stats:**
Total Users: {await db.get_total_users()}

**💡 Get FREE API Keys:**
• Groq: https://console.groq.com
• Gemini: https://aistudio.google.com/app/apikey

**Test AI:** /aitest
"""
    await message.reply(debug_text)


@bot.on_message(filters.command("aitest") & filters.user(Config.OWNER_ID) & filters.private)
async def ai_test_command(client: Client, message: Message):
    
    test_msg = await message.reply("🔍 Testing AI providers...")
    
    test_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Reply with only: WORKING"}
    ]
    
    response = await get_ai_response(test_messages, temperature=0)
    
    if "WORKING" in response.upper() and "❌" not in response:
        status = "✅ **AI Working!**"
        detail = f"Response: {response[:100]}"
    elif "❌" in response:
        status = "❌ **AI Error**"
        detail = response[:500]
    else:
        status = "⚠️ **Unexpected Response**"
        detail = f"Got: {response[:200]}"
    
    await test_msg.edit_text(
        f"**AI Provider Test**\n\n"
        f"Provider: {Config.AI_PROVIDER.upper()}\n\n"
        f"{status}\n\n"
        f"{detail}"
    )


@bot.on_message(filters.command("viewstats") & filters.user(Config.OWNER_ID) & filters.private)
async def view_stats(client: Client, message: Message):
    total_users = await db.get_total_users()
    
    # Gender breakdown
    male = await db.users.count_documents({"gender": "male"})
    female = await db.users.count_documents({"gender": "female"})
    trans = await db.users.count_documents({"gender": "transgender"})
    nb = await db.users.count_documents({"gender": "nonbinary"})
    no_gender = await db.users.count_documents({"gender": None})
    
    stats_text = f"""
📊 **Detailed Statistics**

**Total Users:** {total_users}

**Gender Breakdown:**
👨 Male: {male}
👩 Female: {female}
🏳️‍⚧️ Transgender: {trans}
⚧️ Non-Binary: {nb}
❓ Not Set: {no_gender}

**Database:** {Config.DATABASE_NAME}
**Bot:** {Config.BOT_NAME}
"""
    await message.reply(stats_text)


# ========== CONVERSATION HANDLER ==========

@bot.on_message(filters.text & filters.private & ~filters.command(["start", "help", "mode", "mood", "reset", "privacy", "ownerpanel", "broadcast", "banuser", "unbanuser", "debug", "viewstats", "aitest"]))
async def handle_conversation(client: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Check MongoDB
    if not Config.MONGO_URI or not db.client:
        await message.reply(
            "❌ Database not configured.\n"
            f"Contact: {Config.OWNER_CONTACT}"
        )
        return
    
    # Check force sub
    is_subscribed, buttons = await check_force_sub(client, user_id)
    if not is_subscribed:
        await message.reply("🔒 Pehle channel join karo!", reply_markup=buttons)
        return
    
    # Check if banned
    if await db.is_banned(user_id):
        return
    
    # Flood control
    current_time = time.time()
    if user_id in user_flood_control:
        if current_time - user_flood_control[user_id] < Config.FLOOD_SLEEP:
            await message.reply("⏳ Thoda ruko!")
            return
    user_flood_control[user_id] = current_time
    
    # Get user data
    user = await db.get_user(user_id)
    if not user:
        await message.reply("⚠️ Pehle /start karo!")
        return
    
    if not user.get("gender"):
        await message.reply("⚠️ Pehle gender select karo! /start use karo.")
        return
    
    # Add reaction
    try:
        await message.react(get_random_reaction())
    except:
        pass
    
    # Typing action
    try:
        await client.send_chat_action(user_id, enums.ChatAction.TYPING)
    except:
        pass
    
    # Get conversation history
    history = await db.get_conversation_history(user_id, limit=5)
    history.reverse()
    
    # Build messages
    messages = []
    mode = user.get("mode", "balanced")
    gender = user.get("gender")
    system_prompt = get_system_prompt(gender, mode)
    messages.append({"role": "system", "content": system_prompt})
    
    # Add history
    for conv in history:
        messages.append({"role": "user", "content": conv["user_message"]})
        messages.append({"role": "assistant", "content": conv["bot_response"]})
    
    # Add current message
    messages.append({"role": "user", "content": message.text})
    
    # Get AI response
    response = await get_ai_response(messages, temperature=0.8)
    
    # Send response
    await message.reply(response)
    
    # Save conversation
    await db.save_conversation(user_id, message.text, response)
    
    # Log to channel
    await send_to_log_channel(
        client,
        f"💬 **Conversation**\n\n"
        f"👤 {user_name} (`{user_id}`)\n"
        f"🎭 {gender} | {mode}\n"
        f"📊 Chat #{user.get('conversation_count', 0) + 1}\n"
        f"{'='*30}\n"
        f"**User:** {message.text}\n\n"
        f"{'='*30}\n"
        f"**Bot:** {response[:500]}"
    )


# ========== MAIN FUNCTION ==========

async def main():
    # Connect to database
    if Config.MONGO_URI:
        connected = await db.connect()
        if connected:
            print("✅ MongoDB Connected")
        else:
            print("❌ MongoDB Connection Failed")
    else:
        print("⚠️ MongoDB URI not provided")
    
    # Start bot
    await bot.start()
    print(f"✅ {Config.BOT_NAME} Started!")
    print(f"AI Provider: {Config.AI_PROVIDER}")
    
    # Keep alive
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Start Flask
    Thread(target=run_flask).start()
    
    # Run bot
    bot.run(main())
