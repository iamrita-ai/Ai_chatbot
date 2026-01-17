from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
from datetime import datetime

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.users = None
        self.conversations = None
        
    async def connect(self):
        """Connect to MongoDB"""
        if not Config.MONGO_URI:
            return False
        try:
            self.client = AsyncIOMotorClient(Config.MONGO_URI)
            self.db = self.client[Config.DATABASE_NAME]
            self.users = self.db['users']
            self.conversations = self.db['conversations']
            # Test connection
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            print(f"MongoDB Connection Error: {e}")
            return False
    
    async def add_user(self, user_id, first_name, username=None):
        """Add new user to database"""
        user_data = {
            "user_id": user_id,
            "first_name": first_name,
            "username": username,
            "gender": None,
            "mode": "balanced",
            "joined_date": datetime.now(),
            "banned": False,
            "memory": {},
            "conversation_count": 0
        }
        await self.users.update_one(
            {"user_id": user_id},
            {"$setOnInsert": user_data},
            upsert=True
        )
    
    async def get_user(self, user_id):
        """Get user data"""
        return await self.users.find_one({"user_id": user_id})
    
    async def set_gender(self, user_id, gender):
        """Set user gender"""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"gender": gender}}
        )
    
    async def update_memory(self, user_id, memory_data):
        """Update user memory"""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"memory": memory_data}}
        )
    
    async def get_memory(self, user_id):
        """Get user memory"""
        user = await self.get_user(user_id)
        return user.get("memory", {}) if user else {}
    
    async def reset_memory(self, user_id):
        """Reset user memory"""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"memory": {}}}
        )
    
    async def set_mode(self, user_id, mode):
        """Set user conversation mode"""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"mode": mode}}
        )
    
    async def save_conversation(self, user_id, user_message, bot_response):
        """Save conversation history"""
        conversation = {
            "user_id": user_id,
            "user_message": user_message,
            "bot_response": bot_response,
            "timestamp": datetime.now()
        }
        await self.conversations.insert_one(conversation)
        await self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"conversation_count": 1}}
        )
    
    async def get_conversation_history(self, user_id, limit=10):
        """Get recent conversation history"""
        cursor = self.conversations.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def ban_user(self, user_id):
        """Ban a user"""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"banned": True}}
        )
    
    async def unban_user(self, user_id):
        """Unban a user"""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"banned": False}}
        )
    
    async def is_banned(self, user_id):
        """Check if user is banned"""
        user = await self.get_user(user_id)
        return user.get("banned", False) if user else False
    
    async def get_total_users(self):
        """Get total users count"""
        return await self.users.count_documents({})
    
    async def get_all_users(self):
        """Get all user IDs"""
        cursor = self.users.find({}, {"user_id": 1})
        return [doc["user_id"] async for doc in cursor]

db = Database()
