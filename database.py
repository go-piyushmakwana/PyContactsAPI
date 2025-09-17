import motor.motor_asyncio as motor
from config import config


class Database:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = motor.AsyncIOMotorClient(config.MONGO_URI)
        return cls._instance


def get_db():
    client = Database.get_instance()
    return client["Contacts"]


db = get_db()
helplines_collection = db["Helplines"]
accounts_collection = db["Accounts"]
user_contacts_collection = db["User_contacts"]
labels_collection = db["Labels"]
trash_collection = db["Trash"]
