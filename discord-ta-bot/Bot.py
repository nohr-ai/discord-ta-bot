import os
import logging
from logging.handlers import RotatingFileHandler
from pymongo.database import Database
from pymongo import MongoClient
from typing import Optional
from objects.canvas_course import Course
from objects import Guild
import discord
from dotenv import load_dotenv, find_dotenv
from discord.ext import commands
from discord import app_commands


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

    It requires the following discord intents
    - all

    Specific functionality is implemented in the cogs.

    """

    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.handlers = [
            f"cogs.{handler[:-3]}"
            for handler in os.listdir("cogs")
            if handler.endswith(".py") and not handler.startswith("_")
        ]
        self.db: Database = MongoClient(os.getenv("DATABASE_URI"))[
            os.getenv("DATABASE_NAME")
        ]
        self._guilds: dict[int, Guild] = {}
        self.log = None

    def setup_logging(self) -> None:
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
            maxBytes=int(os.getenv("LOGFILE_SIZE")),
            backupCount=int(os.getenv("LOGFILE_COUNT")),
        )
        normal_handler.setFormatter(formatter)
        normal_handler.setLevel(logging.WARNING)

        debug_handler = RotatingFileHandler(
            f"{self.__class__.__name__}.debug.log",
            maxBytes=int(os.getenv("LOGFILE_SIZE")),
            backupCount=int(os.getenv("LOGFILE_COUNT")),
        )
        debug_handler.setFormatter(formatter)
        debug_handler.setLevel(logging.DEBUG)

        self.log = logging.getLogger()
        self.log.setLevel(logging.DEBUG)
        self.log.propagate = False
        self.log.addHandler(normal_handler)
        self.log.addHandler(debug_handler)

    def get_member(self, id) -> discord.member.Member:
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

    async def on_ready(self) -> None:
        """
        After backend is up and running, setup frontend and load all guilds
        """
        self.setup_logging()
        for g in self.db.get_collection("Guilds").find():
            self._guilds[g["_id"]] = Guild(**g)
        for guild in self.guilds:
            if guild.id not in self._guilds:
                self._guilds[guild.id] = Guild(_id=guild.id, name=guild.name)
                self.db.get_collection("Guilds").insert_one(
                    self._guilds[guild.id].to_json()
                )

    async def unload_all(self) -> None:
        """
        Unload all cogs
        """
        for c in self.handlers:
            await self.unload_extension(c)

    async def get_guilds(self) -> list[Guild]:
        """
        Get all guilds from the database

        Returns
        -------
        list[Guild]
            List of guilds
        """
        guilds = self.db.get_collection("Guilds")
        return [Guild(**g) for g in guilds.find()]

    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        """
        Get a guild from the database

        Parameters
        ----------
        guild_id : int
            The guild id

        Returns
        -------
        Optional[Guild]
            The guild object
        """
        guilds = self.db.get_collection("Guilds")
        guild = guilds.find_one({"_id": guild_id})
        if guild:
            return Guild(**guild)
        else:
            return None

    async def add_canvas_course(self, guild_id: int, course: Course) -> None:
        """
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

    async def add_roles(
        self,
        guild: discord.Guild,
        message: discord.Message,
        emojis_roles: dict[discord.Emoji, discord.Role],
    ) -> bool:
        """
        Add roles to the database
        This overwrites any existing roles for a guild

        Parameters
        ----------
        guild : discord.Guild
            The guild object.
        emojis_roles : dict[discord.Emoji,discord.Role]
            Dictionary of emojis and roles

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        guild = await self.get_guild(guild.id)
        if not guild:
            return False
        # Insert emoji-role dict into database
        db = self.db.get_collection("Guilds")
        db.update_one(
            {"_id": guild.id},
            {"$set": {"role_message": message.id}},
            upsert=True,
        )
        db.update_one(
            {"_id": guild.id},
            {"$set": {"roles": {str(k): v.id for k, v in emojis_roles.items()}}},
            upsert=True,
        )
        return True

    async def get_all_roles(self) -> dict[dict[discord.Emoji, discord.Role]]:
        """
        Get all roles from the database

        Returns
        -------
        dict[dict[discord.Emoji,discord.Role]]
            Dictionary of emoji-role dictionaries
        """
        db = self.db.get_collection("Guilds")
        return {g["_id"]: g["emojis_roles"] for g in db.find()}


if __name__ == "__main__":
    load_dotenv(find_dotenv(".env"))
    client = Bot()
    client.run(os.getenv("DISCORD_TOKEN"))
