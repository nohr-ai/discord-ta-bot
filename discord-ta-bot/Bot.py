import os
import logging
from logging.handlers import RotatingFileHandler
from pymongo.database import Database
from pymongo import MongoClient
import pymongo
from typing import Optional
from objects.canvas_course import Course
from objects import Guild
from objects.group import Group
from utils.db import *

import discord
from dotenv import load_dotenv, find_dotenv
from discord.ext import commands
from discord import app_commands, TextChannel, VoiceChannel


class Bot(commands.Bot):
    """
    Main class for the bot.
    This class is used to interact with the discord api.
    It requires the following environment variables:
    - DISCORD_TOKEN
    - DATABASE_URI
    - DATABASE_NAME
    - LOGFILE_FORMAT
    - LOGFILE_SIZE
    - LOGFILE_COUNT

    Optional environment variables:
    - CANVAS_TOKEN
    - GITHUB_PA_TOKEN

    It requires the following discord intents
    - all

    Specific functionality is implemented in the cogs found under /cogs

    """

    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.handlers = [
            f"cogs.{handler.removesuffix('.py')}"
            for handler in os.listdir(
                os.path.dirname(os.path.realpath(__file__)) + ("/cogs")
            )
            if handler.endswith(".py") and not handler.startswith("_")
        ]
        self.db_name = os.getenv("DATABASE_NAME", "")
        self.db: Database = get_db(self.db_name)
        self._guilds: dict[int, Guild] = {}
        self.log = self.setup_logging()

    def setup_logging(self) -> logging.Logger:
        """
        Setup logging for the bot
        Will setup two file-loggers, one for debug and one for normal logging
        Bytes per file and number of files are set in the .env file
        - LOGFILE_SIZE
        - LOGFILE_COUNT
        """
        formatter = logging.Formatter(os.getenv("LOGFILE_FORMAT"))
        normal_handler = RotatingFileHandler(
            f"{self.__class__.__name__}.log",
            maxBytes=int(os.getenv("LOGFILE_SIZE", 100)),
            backupCount=int(os.getenv("LOGFILE_COUNT", 1)),
        )
        normal_handler.setFormatter(formatter)
        normal_handler.setLevel(logging.WARNING)

        debug_handler = RotatingFileHandler(
            f"{self.__class__.__name__}.debug.log",
            maxBytes=int(os.getenv("LOGFILE_SIZE", 100)),
            backupCount=int(os.getenv("LOGFILE_COUNT", 1)),
        )
        debug_handler.setFormatter(formatter)
        debug_handler.setLevel(logging.DEBUG)

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        logger.addHandler(normal_handler)
        logger.addHandler(debug_handler)
        return logger

    def get_member(self, id) -> discord.member.Member | None:
        """
        Get a member from any guild by id
        DEPRECATED: Not sure this is wanted anymore

        Parameters
        ----------
        id : int
            The member id

        Returns
        -------
        discord.member.Member
            The member object
        """
        member = None
        for m in self.get_all_members():
            if m.id == id:
                member = m
                break

        return member

    async def setup_hook(self) -> None:
        """
        Load all cogs and sync commands
        This can take upto an hour if done globally!

        """
        for handler in self.handlers:
            await self.load_extension(handler)

        await self.tree.sync()

    async def sync_commands(self) -> None:
        await self.tree.sync()

    async def on_ready(self) -> None:
        """
        After backend is up and running, setup frontend and load all guilds
        """
        guilds = await get_guilds(self.db_name)
        guilds = guilds.find()
        guild_ids = [int(guild["_id"]) for guild in guilds]

        # Guilds with the bot installed
        for guild in self.guilds:
            if guild.id not in guild_ids:
                await set_guild(
                    self.db_name, Guild(_id=guild.id, name=guild.name).to_json()
                )

    async def unload_all(self) -> None:
        """
        Unload all cogs
        """
        for c in self.handlers:
            await self.unload_extension(c)

    # async def get_guilds(self) -> list[Guild]:
    #     """
    #     Get all guilds from the database

    #     Returns
    #     -------
    #     list[Guild]
    #         List of guilds
    #     """
    #     guilds = self.db.get_collection("Guilds")
    #     return [Guild(**g) for g in guilds.find()]

    async def add_canvas_course(self, guild_id: int, course: Course) -> None:
        """
        TODO: move to DB sdk
        Add a canvas course to the bot.
        It might seem counter-intuitive to have this function in the bot class,
        but it's placed here as it's the only place where we have access to the
        database.

        Parameters
        ----------
        guild_id : int
            The guild id.
        course : Course
            The course object.

        Returns
        -------
        None
        """
        guild = self._guilds[guild_id]
        # If course already exists, don't add it
        if course.id not in [c.id for c in guild.canvas_courses]:
            guild.canvas_courses.append(course)
            guilds = self.db.get_collection("Guilds")
            guilds.update_one({"_id": guild_id}, {"$set": guild.to_json()}, upsert=True)

    # async def set_roles(
    #     self,
    #     guild: discord.Guild,
    #     emojis_roles: dict[discord.Emoji, discord.Role],
    # ) -> None:
    #     """
    #     TODO: move to DB sdk
    #     Add roles to the database
    #     This overwrites any existing roles for a guild

    #     Parameters
    #     ----------
    #     guild : discord.Guild
    #         The guild object.
    #     emojis_roles : dict[discord.Emoji,discord.Role]
    #         Dictionary of emojis and roles

    #     Returns
    #     -------
    #     bool
    #         True if successful, False otherwise
    #     """
    #     guild = await self.get_guild(guild.id)
    #     if not guild:
    #         raise ValueError(f"Guild {guild.id} not found!")

    #     db = self.db.get_collection("Guilds")
    #     db.update_one(
    #         {"_id": guild.id},
    #         {"$set": {"roles": {str(k): v.id for k, v in emojis_roles.items()}}},
    #         upsert=True,
    #     )

    # async def get_all_roles(self) -> dict[dict[discord.Emoji, discord.Role]]:
    #     """
    #     TOOD: move to db sdk
    #     Get all roles from the database

    #     Returns
    #     -------
    #     dict[dict[discord.Emoji,discord.Role]]
    #         Dictionary of emoji-role dictionaries
    #     """
    #     db = self.db.get_collection("Guilds")
    #     return {g["_id"]: g["roles"] for g in db.find()}

    # async def get_groups(self, guild: discord.Guild) -> list[Group]:
    #     """
    #     TODO: move to db sdk
    #     """
    #     db = self.db.get_collection("Guilds")
    #     guild = db.find_one({"_id": guild.id})
    #     return Guild(**guild).groups

    # async def get_persistent_text_channels(
    #     self, guild: discord.Guild
    # ) -> list[TextChannel]:
    #     """
    #     TODO: move to db sdk
    #     """
    #     db = self.db.get_collection("Guilds")
    #     _guild = Guild(**db.find_one({"_id": guild.id}))
    #     return _guild.persistent_text_channels

    # async def set_persistent_text_channels(
    #     self, guild: discord.Guild, persistent_text_channels: list[int] = []
    # ) -> list[TextChannel]:
    #     """
    #     TODO: move to db sdk
    #     """
    #     guild = self.get_guild(guild.id)
    #     if not guild:
    #         raise ValueError(f"Guild: {guild.id} not found")
    #     db = self.db.get_collection("Guilds")
    #     db.update_one(
    #         {"_id": guild.id},
    #         {"$set": {"persistent_text_channels": persistent_text_channels}},
    #         upsert=True,
    #     )guilds = get_guilds(self.db_name)


if __name__ == "__main__":
    load_dotenv(find_dotenv(".env"))
    client = Bot()
    client.run(os.getenv("DISCORD_TOKEN"))
