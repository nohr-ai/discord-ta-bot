import os
import logging
import discord
from typing import Optional
from objects import Guild, Group
from pymongo.database import Database, Collection
from pymongo import MongoClient


class DB(Database):

class Manager:
    def __init__(self, default_db_uri:str):
        self.db_dict: dict[str, MongoClient] = {}
        self._setup(default_db_uri)

    def _setup(self,db_uri:str)->None:
        self.client = MongoClient(db_uri,tls=True)
        
        

    def get_db(self,name:str)->Database:
        if name not in self.db_dict:
            self.db_dict[name] = self.client.get_database(name)
        return self.db_dict[name]




def get_db(name:str) -> Database:
    return client[os.]


async def get_guilds() -> Optional[list[Guild]]:
    db = get_db()
    guilds: Collection = db.get_collection("Guilds")
    if not guilds:
        raise KeyError("No guilds found")
    return guilds


async def get_guild(guild_id: int) -> dict:
    guilds: Collection = await get_guilds()
    guild = guilds.find_one({"_id": guild_id})
    if not guild:
        raise KeyError(f"Guild {guild_id} not found")
    return guild


async def set_field(guild_id: int, field: str, value: any) -> None:
    """
    Set field value in database for a specific guild.
    This overwrites any existing value for given key by default,
    performs an insert if document not found.

    Paramters
    ---------
    guild_id: int
        Guild identifier
    field: str
        Key to update value for
    value: any
        Value for key, must be serializable

    Returns
    -------
    None
    """
    guilds: Collection = await get_guilds()
    guilds.update_one({"_id": guild_id}, {"$set": {f"{field}": value}}, upsert=True)


async def set_role_message(
    guild_id: int, message: Optional[discord.Message] = None
) -> None:
    await set_field(guild_id, "role_message", message)


async def set_roles(
    guild_id: int, emojis_roles: dict[discord.Emoji, discord.Role]
) -> None:
    """
    Add roles for a guild to the database
    This overwrites any existing roles for a guild

    Parameters
    ----------
    guild_id: int
        Guild identifier
    emoji_roles: dict[discord.Emoji, discord.Role]
        Disctionary for emoji -> role mappindg

    Returns
    -------
    None
    """
    await set_field(
        guild_id, "roles", {str(emoji): role.id for emoji, role in emojis_roles.items()}
    )


async def set_groups(guild_id: int, groups: list[Group] = None) -> None:
    set_field(
        guild_id, "groups", [group.to_json() for group in groups] if groups else []
    )


async def get_guild_groups(guild_id: int) -> list[Group]:
    guild: dict = get_guild(guild_id)
    return guild["roles"]


async def get_persistent_text_channels(guild_id: int) -> list[int]:
    guild = await get_guild(guild_id)
    return guild["persistent_text_channels"]


async def get_persistent_voice_channels(guild_id: int) -> list[int]:
    guild = await get_guild(guild_id)
    return guild["persistent_voice_channels"]

def get_db(name:str):
    return 