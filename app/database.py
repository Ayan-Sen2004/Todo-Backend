from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

# import os

# load_dotenv()

# MONGO_URL = os.getenv("MONGO_URL")
# DATABASE_NAME = os.getenv("DATABASE_NAME")

client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.database_name]