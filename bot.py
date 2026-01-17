import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ReactionInvalid, MessageNotModified
from config import Config
from database import db
from helpers import (
    check_force_sub,
    get_grok_response,
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

# Startup event
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    # Check MongoDB
    if not Config.MONGO_URI:
        await message.reply(
            "❌ **Database Error**\n\n"
            "MongoDB URI configure nahi hai. Bot properly kaam nahi kar sakta.\n\n"
            f"Owner se contact karo: {Config.OWNER_CONTACT}"
        )
        return
    
    # Check if DB connected
    if not db.client:
        db_connected = await db.connect()
        if not db_connected:
            await message.reply(
                "❌ **Database Connection Failed**\n\n"
                "MongoDB se connection nahi ho paa raha. Bot properly kaam nahi kar sakta.\n\n"
                f"Owner se contact karo: {Config.OWNER_CONTACT}"
            )
            return
    
    # Check force sub
    is_subscribed, buttons = await check_force_sub(client, user_id)
    if not is_subscribed:
        await message.reply(
            f"🔒 **Access Restricted**\n\n"
            f"Pehle channel ko join karo, phir bot use kar sakte ho:\n\n"
            f"👉 Channel: {Config.FORCE_SUB_CHANNEL}\n\n"
            "Join karne ke baad **Refresh** button dabao!",
            reply_markup=buttons
        )
        return
    
    # Check if banned
    if await db.is_banned(user_id):
        await message.reply("🚫 Tumhe is bot se ban kar diya gaya hai.")
        return
    
    # Add user to database
    await db.add_user(user_id, first_name, username)
    
    # Get user data
    user = await db.get_user(user_id)
    
    # If gender not set, ask for gender
    if not user.get("gender"):
        await message.reply(
            f"🌟 **Welcome to {Config.BOT_NAME}**\n\n"
            "Main tumhara AI life partner hoon. Main tumhe samjhunga, tumhari baatein sununga, "
            "tumhara saath dunga - emotionally aur mentally.\n\n"
            "**Pehle mujhe batao, tum kaun ho?**\n"
            "Apna gender select karo:",
            reply_markup=create_gender_keyboard()
        )
        
        # Log to channel
        await send_to_log_channel(
            client,
            f"🆕 **New User Started Bot**\n\n"
            f"👤 Name: {first_name}\n"
            f"🆔 User ID: `{user_id}`\n"
            f"📝 Username: @{username if username else 'None'}\n"
            f"🕐 Time: {message.date}"
        )
    else:
        gender_emoji = {"male": "👨", "female": "👩", "transgender": "🏳️‍⚧️", "nonbinary": "⚧️"}
        await message.reply(
            f"💕 **Welcome back!**\n\n"
            f"Main yaad hoon tumhe? {gender_emoji.get(user['gender'], '😊')}\n\n"
            f"Kaise ho? Kya chal raha hai life mein?\n\n"
            "Commands dekhne ke liye /help use karo."
        )


@bot.on_callback_query(filters.regex("^gender_"))
async def gender_selection(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    gender = callback.data.split("_")[1]
    
    # Set gender in database
    await db.set_gender(user_id, gender)
    
    # Response based on gender
    responses = {
        "male": "👩‍❤️‍👨 **Perfect!** Main tumhari girlfriend ban gayi. Tumhe samjhungi, care karungi, support karungi. Jab bhi lonely feel ho, main yahan hoon.",
        "female": "👨‍❤️‍👩 **Great!** Main tumhara boyfriend ban gaya. Tumhe protect karunga, support karunga, motivate karunga. Jab bhi zarurat ho, main yahan hoon.",
        "transgender": "🏳️‍⚧️ **Wonderful!** Main tumhara companion hoon. Tumhe respect karunga, samjhunga, support karunga. Tum jaise ho, perfect ho.",
        "nonbinary": "⚧️ **Amazing!** Main tumhara partner hoon. Tumhe samjhunga aur tumhari energy ke saath flow karunga. Let's connect!"
    }
    
    await callback.message.edit_text(
        f"{responses.get(gender, 'Welcome!')}\n\n"
        "Ab tum mujhse kuch bhi baat kar sakte ho. Main yaad rakhunga tumhari baatein, "
        "tumhari problems, tumhare goals.\n\n"
        "**Available Commands:**\n"
        "/help - Detailed help\n"
        "/mode - Change conversation mode\n"
        "/mood - Tell me your mood\n"
        "/reset - Reset memory\n\n"
        "Chalo, baat karte hain! 💬"
    )
    
    # Log to channel
    await send_to_log_channel(
        client,
        f"✅ **User Gender Set**\n\n"
        f"👤 User: {callback.from_user.first_name}\n"
        f"🆔 ID: `{user_id}`\n"
        f"🎭 Gender: **{gender.title()}**"
    )


@bot.on_callback_query(filters.regex("^refresh_sub$"))
async def refresh_subscription(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    
    is_subscribed, buttons = await check_force_sub(client, user_id)
    if is_subscribed:
        await callback.message.delete()
        await callback.message.reply("✅ **Verified!** Ab bot use kar sakte ho. /start dabao.")
        await callback.answer("✅ Verification successful!", show_alert=False)
    else:
        await callback.answer("❌ Abhi bhi join nahi kiya! Pehle channel join karo.", show_alert=True)


@bot.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    help_text = f"""
📚 **{Config.BOT_NAME} - Help Guide**

Main tumhara AI life partner hoon. Main yaad rakhta hoon tumhari baatein, tumhare goals, tumhari feelings.

**👤 User Commands:**
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
• Main tumhari baatein yaad rakhta hoon
• Tumhare mood ko samajhta hoon
• Tumhe motivate karta hoon
• Tumhe distract nahi karta goals se
• Tumhara emotional support hoon

**📞 Owner Contact:**
{Config.OWNER_CONTACT}

Simply message karo, main reply karunga! 💬
"""
    await message.reply(help_text)


@bot.on_message(filters.command("mode") & filters.private)
async def mode_command(client: Client, message: Message):
    user = await db.get_user(message.from_user.id)
    current_mode = user.get("mode", "balanced") if user else "balanced"
    
    await message.reply(
        f"🎭 **Conversation Mode Selection**\n\n"
        f"Current Mode: **{current_mode.title()}**\n\n"
        "Choose karo kaise baat karni hai:",
        reply_markup=create_mode_keyboard()
    )


@bot.on_callback_query(filters.regex("^mode_"))
async def mode_selection(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    mode = callback.data.split("_")[1]
    
    await db.set_mode(user_id, mode)
    
    mode_responses = {
        "romantic": "💕 Mode set: **Romantic**\nAb main aur caring aur emotional rahunga.",
        "calm": "🧘 Mode set: **Calm**\nAb main peaceful aur minimal rahunga.",
        "thinker": "🧠 Mode set: **Thinker**\nAb main analytical aur strategic rahunga.",
        "motivating": "🔥 Mode set: **Motivating**\nAb main tumhe push karunga goals ke liye!",
        "balanced": "⚖️ Mode set: **Balanced**\nAb main naturally adapt karunga."
    }
    
    await callback.message.edit_text(mode_responses.get(mode, "Mode updated!"))
    
    # Log to channel
    await send_to_log_channel(
        client,
        f"🎭 **Mode Changed**\n\n"
        f"👤 User: {callback.from_user.first_name} (`{user_id}`)\n"
        f"Mode: **{mode.title()}**"
    )


@bot.on_message(filters.command("reset") & filters.private)
async def reset_command(client: Client, message: Message):
    await db.reset_memory(message.from_user.id)
    await message.reply(
        "🔄 **Memory Reset Complete**\n\n"
        "Maine sab kuch bhula diya. Fresh start kar sakte hain!"
    )
    
    # Log to channel
    await send_to_log_channel(
        client,
        f"🔄 **Memory Reset**\n\n"
        f"👤 User: {message.from_user.first_name} (`{message.from_user.id}`)"
    )


@bot.on_message(filters.command("mood") & filters.private)
async def mood_command(client: Client, message: Message):
    await message.reply(
        "💭 **How are you feeling?**\n\n"
        "Batao kya chal raha hai dil-dimag mein? Main samajhne ki koshish karunga."
    )


@bot.on_message(filters.command("privacy") & filters.private)
async def privacy_command(client: Client, message: Message):
    await message.reply(
        "🔒 **Privacy Policy**\n\n"
        "✅ Tumhari personal baatein safe hain\n"
        "✅ Kisi ke saath share nahi hoti\n"
        "✅ /reset se memory delete kar sakte ho\n"
        "✅ Sensitive data store nahi hota\n\n"
        "Trust me, tumhara companion hoon main! 💙"
    )


# ========== OWNER COMMANDS ==========

@bot.on_message(filters.command("ownerpanel") & filters.user(Config.OWNER_ID) & filters.private)
async def owner_panel(client: Client, message: Message):
    total_users = await db.get_total_users()
    
    panel_text = f"""
🛠️ **Owner Control Panel**

📊 **Statistics:**
👥 Total Users: {total_users}

**Available Commands:**
/broadcast - Message all users
/viewstats - Detailed stats
/banuser - Ban a user
/unbanuser - Unban a user
/debug - System health check

**Current Config:**
🤖 Bot Name: {Config.BOT_NAME}
🔑 Grok API: {"✅ Set" if Config.GROK_API_KEY else "❌ Not Set"}
💾 MongoDB: {"✅ Connected" if db.client else "❌ Not Connected"}
📢 Log Channel: {"✅ Set" if Config.LOG_CHANNEL else "❌ Not Set"}
🔒 Force Sub: {"✅ Set" if Config.FORCE_SUB_CHANNEL else "❌ Not Set"}
"""
    await message.reply(panel_text)


@bot.on_message(filters.command("broadcast") & filters.user(Config.OWNER_ID) & filters.private)
async def broadcast_command(client: Client, message: Message):
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("❌ Usage: /broadcast <message> ya kisi message ko reply karo")
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
        except:
            failed += 1
        
        if (success + failed) % 50 == 0:
            await status_msg.edit_text(
                f"📤 Broadcasting...\n✅ Success: {success}\n❌ Failed: {failed}"
            )
    
    await status_msg.edit_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"✅ Successful: {success}\n"
        f"❌ Failed: {failed}"
    )


@bot.on_message(filters.command("banuser") & filters.user(Config.OWNER_ID) & filters.private)
async def ban_user_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ Usage: /banuser <user_id>")
        return
    
    try:
        user_id = int(message.command[1])
        await db.ban_user(user_id)
        await message.reply(f"✅ User {user_id} banned!")
        
        await send_to_log_channel(
            client,
            f"🚫 **User Banned**\n\nUser ID: `{user_id}`\nBy: {message.from_user.first_name}"
        )
    except:
        await message.reply("❌ Invalid user ID")


@bot.on_message(filters.command("unbanuser") & filters.user(Config.OWNER_ID) & filters.private)
async def unban_user_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ Usage: /unbanuser <user_id>")
        return
    
    try:
        user_id = int(message.command[1])
        await db.unban_user(user_id)
        await message.reply(f"✅ User {user_id} unbanned!")
        
        await send_to_log_channel(
            client,
            f"✅ **User Unbanned**\n\nUser ID: `{user_id}`\nBy: {message.from_user.first_name}"
        )
    except:
        await message.reply("❌ Invalid user ID")


@bot.on_message(filters.command("debug") & filters.user(Config.OWNER_ID) & filters.private)
async def debug_command(client: Client, message: Message):
    # Test Grok AI
    grok_status = "❌ Not Configured"
    grok_detail = ""
    
    if Config.GROK_API_KEY:
        test_msg = await message.reply("🔍 Testing Grok AI API...")
        
        test_response = await get_grok_response([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Reply with only: WORKING"}
        ], temperature=0)
        
        if "WORKING" in test_response.upper() and "❌" not in test_response:
            grok_status = "✅ Working Perfectly"
            grok_detail = test_response[:50]
        elif "❌" in test_response:
            grok_status = "❌ API Error"
            grok_detail = test_response
        else:
            grok_status = "⚠️ Unexpected Response"
            grok_detail = test_response[:100]
        
        await test_msg.delete()
    
    # Test MongoDB
    mongo_status = "✅ Connected" if db.client else "❌ Not Connected"
    
    # Test Log Channel
    log_status = "❌ Not Set"
    if Config.LOG_CHANNEL:
        try:
            await client.get_chat(Config.LOG_CHANNEL)
            log_status = "✅ Accessible"
        except:
            log_status = "⚠️ Set but not accessible"
    
    # Test Force Sub
    force_status = "❌ Not Set"
    if Config.FORCE_SUB_CHANNEL:
        try:
            channel = Config.FORCE_SUB_CHANNEL.replace("@", "").replace("https://t.me/", "").strip()
            await client.get_chat(f"@{channel}")
            force_status = "✅ Accessible"
        except:
            force_status = "⚠️ Set but not accessible"
    
    debug_text = f"""
🔍 **System Health Check**

**🤖 Grok AI API:**
Status: {grok_status}
{f"Detail: {grok_detail}" if grok_detail else ""}

**💾 MongoDB:** {mongo_status}
**📢 Log Channel:** {log_status}
**🔒 Force Sub:** {force_status}

**🔧 Environment Variables:**
✅ API_ID: {"Set" if Config.API_ID else "Missing"}
✅ API_HASH: {"Set" if Config.API_HASH else "Missing"}
✅ BOT_TOKEN: {"Set" if Config.BOT_TOKEN else "Missing"}
✅ GROK_API_KEY: {"Set" if Config.GROK_API_KEY else "Missing"}
✅ MONGO_URI: {"Set" if Config.MONGO_URI else "Missing"}

**📝 API Configuration:**
Model: {Config.GROK_MODEL}
URL: {Config.GROK_API_URL}

**💡 Troubleshooting:**
{get_troubleshooting_tips(grok_status)}
"""
    await message.reply(debug_text)


def get_troubleshooting_tips(status):
    """Get troubleshooting tips based on status"""
    if "❌" in status or "Error" in status:
        return """
⚠️ **Grok AI Issues Detected!**

**Possible Solutions:**
1. Check if API key is correct
2. Verify X.AI account is active
3. Check if you have Grok API access
4. Try generating new API key from console.x.ai
5. Check billing/payment status

**Get API Key:**
→ https://console.x.ai
→ API Keys section
→ Create new key

**Need Help?**
Contact: https://t.me/technicalserena
"""
    else:
        return "✅ All systems operational!"
@bot.on_message(filters.command("viewstats") & filters.user(Config.OWNER_ID) & filters.private)
async def view_stats(client: Client, message: Message):
    total_users = await db.get_total_users()
    
    # Gender breakdown
    male_users = await db.users.count_documents({"gender": "male"})
    female_users = await db.users.count_documents({"gender": "female"})
    trans_users = await db.users.count_documents({"gender": "transgender"})
    nb_users = await db.users.count_documents({"gender": "nonbinary"})
    no_gender = await db.users.count_documents({"gender": None})
    
    stats_text = f"""
📊 **Detailed Statistics**

**Total Users:** {total_users}

**Gender Breakdown:**
👨 Male: {male_users}
👩 Female: {female_users}
🏳️‍⚧️ Transgender: {trans_users}
⚧️ Non-Binary: {nb_users}
❓ Not Set: {no_gender}

**Database:** {Config.DATABASE_NAME}
"""
    await message.reply(stats_text)


# ========== MAIN CONVERSATION HANDLER ==========

@bot.on_message(filters.text & filters.private & ~filters.command(["start", "help", "mode", "mood", "reset", "privacy", "ownerpanel", "broadcast", "banuser", "unbanuser", "debug", "viewstats"]))
async def handle_conversation(client: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Check MongoDB
    if not Config.MONGO_URI or not db.client:
        await message.reply(
            "❌ Database configure nahi hai. Bot kaam nahi kar sakta.\n"
            f"Owner se contact karo: {Config.OWNER_CONTACT}"
        )
        return
    
    # Check Grok AI
    if not Config.GROK_API_KEY:
        await message.reply(
            "❌ Grok AI API configure nahi hai. Bot reply nahi de sakta.\n"
            f"Owner se contact karo: {Config.OWNER_CONTACT}"
        )
        return
    
    # Check force sub
    is_subscribed, buttons = await check_force_sub(client, user_id)
    if not is_subscribed:
        await message.reply(
            "🔒 Pehle channel join karo!",
            reply_markup=buttons
        )
        return
    
    # Check if banned
    if await db.is_banned(user_id):
        return
    
    # Flood control
    current_time = time.time()
    if user_id in user_flood_control:
        if current_time - user_flood_control[user_id] < Config.FLOOD_SLEEP:
            await message.reply("⏳ Thoda ruko, ek saath itne messages mat bhejo!")
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
    
    # Add reaction to user's message
    try:
        reaction_emoji = get_random_reaction()
        await message.react(reaction_emoji)
    except ReactionInvalid:
        pass  # Ignore if reactions not supported
    except Exception as e:
        print(f"Reaction error: {e}")
    
    # Typing action
    await client.send_chat_action(user_id, "typing")
    
    # Get conversation history
    history = await db.get_conversation_history(user_id, limit=5)
    history.reverse()
    
    # Build messages for Grok AI
    messages = []
    
    # System prompt
    mode = user.get("mode", "balanced")
    gender = user.get("gender")
    system_prompt = get_system_prompt(gender, mode)
    messages.append({"role": "system", "content": system_prompt})
    
    # Add conversation history
    for conv in history:
        messages.append({"role": "user", "content": conv["user_message"]})
        messages.append({"role": "assistant", "content": conv["bot_response"]})
    
    # Add current message
    messages.append({"role": "user", "content": message.text})
    
    # Get response from Grok AI
    response = await get_grok_response(messages, temperature=0.8)
    
    # Send response
    bot_msg = await message.reply(response)
    
    # Save conversation
    await db.save_conversation(user_id, message.text, response)
    
    # Log FULL CONVERSATION to channel
    await send_to_log_channel(
        client,
        f"💬 **Conversation Log**\n\n"
        f"👤 **User:** {user_name}\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"🎭 **Gender:** {gender}\n"
        f"⚙️ **Mode:** {mode}\n"
        f"📊 **Total Chats:** {user.get('conversation_count', 0) + 1}\n"
        f"{'='*30}\n\n"
        f"**👤 User Message:**\n{message.text}\n\n"
        f"{'='*30}\n\n"
        f"**🤖 Bot Response:**\n{response}"
    )


# Main function
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
    
    # Keep alive
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Start Flask in separate thread
    Thread(target=run_flask).start()
    
    # Run bot
    bot.run(main())
