# 🤖 AI Life Partner Telegram Bot

A caring, emotional AI companion bot built with Grok AI and Pyrogram.

## 🌟 Features

- Gender-adaptive personality (Male → Female GF, Female → Male BF, etc.)
- Long-term conversation memory
- Multiple conversation modes (Romantic, Calm, Thinker, Motivating, Balanced)
- Force subscription support
- MongoDB database integration
- Owner panel with broadcast, ban/unban, stats
- Flood protection
- Full error handling with user-friendly messages

## 🚀 Deployment on Render

### Step 1: Upload to GitHub

1. Create new repository on GitHub
2. Upload all files
3. Push to GitHub

### Step 2: Deploy on Render

1. Go to [render.com](https://render.com)
2. Create new **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name:** ai-life-partner-bot
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`

### Step 3: Environment Variables

Add these in Render Environment Variables:

API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
GROK_API_KEY=xai-your-key-here
MONGO_URI=mongodb+srv://...
LOG_CHANNEL=-1003508789207
FORCE_SUB_CHANNEL=serenaunzipbot
OWNER_ID=6518065496 1598576202
OWNER_CONTACT=https://t.me/technicalserena
BOT_NAME=AI Life Partner
PORT=8080

#

### Step 4: Deploy!

Click **Deploy** and wait for build to complete.

## 📝 Commands

### User Commands
- `/start` - Start the bot
- `/help` - Get help
- `/mode` - Change conversation mode
- `/mood` - Share your mood
- `/reset` - Reset memory
- `/privacy` - Privacy policy

### Owner Commands
- `/ownerpanel` - Control panel
- `/broadcast` - Broadcast message
- `/viewstats` - View statistics
- `/banuser` - Ban user
- `/unbanuser` - Unban user
- `/debug` - System health check

## 💝 Made with love by Technical Serena

Contact: https://t.me/technicalserena


✅ Final Steps for Deployment:
GitHub Upload:

Create repository
Upload all 8 files
Commit and push
Render Setup:

Connect GitHub repo
Set environment variables
Deploy as Web Service
MongoDB Setup:

Create free cluster on MongoDB Atlas
Get connection URI
Add to Render env vars
Telegram Setup:

Get API_ID and API_HASH from https://my.telegram.org
Create bot with @BotFather
Get bot token
Grok AI Setup:

Use your Grok API key in env vars
