import os
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

try:
    client = MongoClient(MONGO_URI)
    client.admin.command('ping')
    print("✅ Kết nối MongoDB thành công!")
    db = client[DB_NAME]

except ConnectionFailure as e:
    print(f"Lỗi: Không thể kết nối đến MongoDB. {e}")
    db = None
except Exception as e:
    print(f"Lỗi không xác định: {e}")
    db = None

def get_database() -> Database:
    if db is None:
        raise ConnectionFailure("Database chưa được khởi tạo. Kiểm tra kết nối.")
    return db

def get_journal_collection():
    return get_database()["journal_entries"]

def get_user_collection():
    return get_database()["users"]
