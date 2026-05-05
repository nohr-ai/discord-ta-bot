# Moved here from utils/db.py — no longer used by the bot.
# Retained for reference during the stateless redesign.
# Original path: discord-ta-bot/utils/db.py

import os
import logging
import discord
from dotenv import load_dotenv
from typing import Optional, Any
from pymongo.database import Database, Collection
from pymongo import MongoClient

load_dotenv()


class Manager:
    def __init__(self, db_uri: str):
        self.db_dict: dict[str, Database] = {}
        self.client: MongoClient = MongoClient(db_uri, tls=True)

    def get_db(self, name: str) -> Database:
        if name not in self.db_dict:
            self.db_dict[name] = self.client.get_database(name)
        return self.db_dict[name]


manager = Manager(os.getenv("DATABASE_URI", "mongodb://localhost:27017/"))


def get_db(name: str) -> Database:
    return manager.get_db(name)


async def get_guilds(db_name: str) -> Collection:
    db: Database = get_db(db_name)
    guilds: Collection = db.get_collection("Guilds")
    if not guilds.count_documents({}):
        raise KeyError("No guilds found")
    return guilds


async def get_guild(db_name: str, guild_id: int) -> dict:
    guilds: Collection = await get_guilds(db_name)
    guild = guilds.find_one({"_id": guild_id})
    if not guild:
        raise KeyError(f"Guild {guild_id} not found")
    return guild


async def set_guild(db_name: str, guild: dict) -> None:
    db: Database = get_db(db_name)
    db.get_collection("Guilds").insert_one(guild)


async def set_field(
    db_name: str, guild_id: int, field: str, value: Any, upsert=True
) -> None:
    guilds: Collection = await get_guilds(db_name)
    guilds.update_one({"_id": guild_id}, {"$set": {f"{field}": value}}, upsert=upsert)


async def get_role_message(db_name: str, guild_id: int) -> Optional[int]:
    guild = await get_guild(db_name, guild_id)
    return guild["role_message"]


async def set_role_message(
    db_name: str, guild_id: int, message: Optional[discord.Message] = None
) -> None:
    await set_field(db_name, guild_id, "role_message", message.id if message else None)


async def get_guild_groups(db_name: str, guild_id: int) -> list[dict]:
    guild: dict = await get_guild(db_name, guild_id)
    return guild["groups"]


async def get_persistent_text_channels(db_name: str, guild_id: int) -> list[int]:
    guild = await get_guild(db_name, guild_id)
    return guild["persistent_text_channels"]


async def set_persistent_text_channels(
    db_name: str, guild_id: int, text_channels: list[int] = [], upsert=True
) -> None:
    guilds: Collection = await get_guilds(db_name)
    guilds.update_one(
        {"_id": guild_id},
        {"$set": {"persistent_text_channels": text_channels}},
        upsert=upsert,
    )


async def add_persistent_text_channel(
    db_name: str, guild_id: int, text_channel: int, upsert=True
) -> None:
    guilds: Collection = await get_guilds(db_name)
    guilds.update_one(
        {"_id": guild_id},
        {"$push": {"persistent_text_channels": text_channel}},
        upsert=upsert,
    )


async def remove_persistent_text_channel(
    db_name: str, guild_id: int, text_channel: int, upsert=False
) -> None:
    guilds: Collection = await get_guilds(db_name)
    guilds.update_one(
        {"_id": guild_id},
        {"$pull": {"persistent_text_channels": text_channel}},
        upsert=upsert,
    )


async def get_persistent_voice_channels(db_name: str, guild_id: int) -> list[int]:
    guild = await get_guild(db_name, guild_id)
    return guild["persistent_voice_channels"]


async def set_persistent_voice_channels(
    db_name: str, guild_id: int, voice_channels: list[int] = []
) -> None:
    guilds: Collection = await get_guilds(db_name)
    guilds.update_one(
        {"_id": guild_id},
        {"$set": {"persistent_voice_channels": voice_channels}},
        upsert=True,
    )


async def add_persistent_voice_channel(
    db_name: str, guild_id: int, voice_channel: int, upsert=True
) -> None:
    guilds: Collection = await get_guilds(db_name)
    guilds.update_one(
        {"_id": guild_id},
        {"$push": {"persistent_voice_channels": voice_channel}},
        upsert=upsert,
    )


async def remove_persistent_voice_channel(
    db_name: str, guild_id: int, voice_channel: int, upsert=False
) -> None:
    guilds: Collection = await get_guilds(db_name)
    guilds.update_one(
        {"_id": guild_id},
        {"$pull": {"persistent_voice_channels": voice_channel}},
        upsert=upsert,
    )
