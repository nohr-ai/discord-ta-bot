import os
import logging
import discord
from dotenv import load_dotenv
from typing import Optional, Any
from objects import Guild, Group
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
    """
    Get a database from name

    Parameters
    -----------
    name: str
        Name of database to retrievei
    """
    return manager.get_db(name)


async def get_guilds(db_name: str) -> Collection:
    """
    Get all guilds in a database as a MongoDB Collection

    Paramteres
    ----------
    db_name: str
        Name of database to retrieve from

    Returns
    --------
    Guilds: Collection
        MongoDB collection of all  guilds
    """
    db: Database = get_db(db_name)
    guilds: Collection = db.get_collection("Guilds")
    if not guilds.count_documents({}):
        raise KeyError("No guilds found")
    return guilds


async def get_guild(db_name: str, guild_id: int) -> dict:
    """
    Get guild from ID

    Parameters
    ----------
    db_name: str
        Name of database to search in
    guild_id: int
        Identifier for the discord Guild we're looking for

    Returns
    -------
    Guild: dict
        Dict representation of a Guild

    """
    guilds: Collection = await get_guilds(db_name)
    guild = guilds.find_one({"_id": guild_id})
    if not guild:
        raise KeyError(f"Guild {guild_id} not found")
    return guild


async def set_guild(db_name: str, guild: dict) -> None:
    """
    Insert a guild into the database

    Parameters
    ----------
    db_name: str
        Name of database to insert to
    guild: dict
        Serializeable Guild object(JSON)

    Returns
    -------
    None
    """
    db: Database = get_db(db_name)
    db.get_collection("Guilds").insert_one(guild)


async def set_field(
    db_name: str, guild_id: int, field: str, value: Any, upsert=True
) -> None:
    """
    Set field value in database for a specific guild.
    This overwrites any existing value for given key by default,
    performs an insert if document not found by default

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
    guilds: Collection = await get_guilds(db_name)
    guilds.update_one({"_id": guild_id}, {"$set": {f"{field}": value}}, upsert=upsert)


async def get_role_message(db_name: str, guild_id: int) -> Optional[int]:
    guild = await get_guild(db_name, guild_id)
    return guild["role_message"]


async def set_role_message(
    db_name: str, guild_id: int, message: Optional[discord.Message] = None
) -> None:
    """
    Set the role message associated to a guild
    Overwrites any existing message
    Set to None if no message provided

    Parameters
    ----------
    db_name: str
        Name of db to insert to
    guild_id: int
        Identifier for Discord Guild
    message: Optional[discord.Message]
        Message to insert

    Returns
    -------
    None
    """
    await set_field(db_name, guild_id, "role_message", message.id if message else None)


async def set_guild_groups(
    db_name: str, guild_id: int, groups: Optional[list[Group]] = None
) -> None:
    """
    Add groups to a guild
    This overwrites any existing groups for a guild
    Performs an insert if document not found.

    Parameters
    ----------
    db_name: str
        Name of DB to be inserted to
    guild_id: int
        Identifier for the discord Guild
    groups: list[Group]
        List of all Group(s) to be inserted into the database

    Returns
    -------
    None
    """
    await set_field(
        db_name,
        guild_id,
        "groups",
        [group.to_json() for group in groups] if groups else [],
    )


async def get_guild_groups(db_name: str, guild_id: int) -> list[dict]:
    """
    Get all groups for a guild
    returns Group object(s) as dictionaries

    Parameters
    ----------
    db_name: str
        Name of db to get from
    guild_id: int
        Identifier for Discord Guild

    Returns
    -------
    groups: list[dict]
        List of all groups for a guild as dicts

    """
    guild: dict = await get_guild(db_name, guild_id)
    return guild["groups"]


async def get_persistent_text_channels(db_name: str, guild_id: int) -> list[int]:
    """
        Get all persistent text channels for a guild
        Returns a list of text_channel identifiers(int)

    Parameters
    ----------
    db_name: str
        Name of database to get from
    guild_id: int
        Identifier for discord Guild

    Returns
    --------
    text_channels: list[int]
        Identifiers for all text_channels marked as persistent for the guild

    """
    guild = await get_guild(db_name, guild_id)
    return guild["persistent_text_channels"]


async def set_persistent_text_channels(
    db_name: str, guild_id: int, text_channels: list[int] = [], upsert=True
) -> None:
    """
        Set list of persistent text channels for a guild

    Parameters
    ----------
    db_name: str
        Name of db to be inserted to
    guild_id: int
        Identifier for discord Guild
    text_channels: list[int]
        Identifiers for text channels

    Returns
    -------
    None
    """

    guilds: Collection = await get_guilds(db_name)
    guilds.update_one(
        {"_id": guild_id},
        {"$set": {"persistent_text_channels": text_channels}},
        upsert=upsert,
    )


async def get_persistent_voice_channels(db_name: str, guild_id: int) -> list[int]:
    """
        Get all persistent voice channels for a guild
        Returns a list of voice channel identifiers(int)

    Parameters
    -----------
    db_name: str
        Name of database to get from
    guild_id: int
        Identifier for discord Guild

    Returns
    -------
    voice_channels: list[int]
        Identifiers for all voice channels marked as persistent for the guild

    """
    guild = await get_guild(db_name, guild_id)
    return guild["persistent_voice_channels"]


async def set_persistent_voice_channels(
    db_name: str, guild_id: int, voice_channels: list[int] = []
) -> None:
    """
    Set list of persistent voice channels for a guild

    Parameters
    ----------
    db_name: str
        Name of database to insert into
    guild_id: int
        Identifier for discord guild
    voice_channels: list[int]
        Identifiers for voice channels

    Returns
    -------
    None
    """
