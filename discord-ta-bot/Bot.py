import os
import logging
from logging.handlers import RotatingFileHandler

import discord
from dotenv import load_dotenv, find_dotenv
from discord.ext import commands


class Bot(commands.Bot):
    """
    Main class for the bot.
    This class is used to interact with the discord API.
    It requires the following environment variables:
    - DISCORD_TOKEN
    - LOGFILE_FORMAT
    - LOGFILE_SIZE
    - LOGFILE_COUNT

    Optional environment variables:
    - CANVAS_TOKEN
    - GITHUB_PA_TOKEN

    It requires the following discord intents:
    - all

    Specific functionality is implemented in the cogs found under /cogs.
    The bot is fully stateless — all context is derived from the interaction
    guild at command time. Multiple guilds are supported without any shared
    state.
    """

    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        print(os.path.dirname(os.path.realpath(__file__)))
        self.handlers = [
            f"cogs.{handler.removesuffix('.py')}"
            for handler in os.listdir(
                os.path.dirname(os.path.realpath(__file__)) + ("/cogs")
            )
            if handler.endswith(".py") and not handler.startswith("_")
        ]
        self.log = self.setup_logging()

    def setup_logging(self) -> None:
        """
        Setup logging for the bot.
        Configures two rotating file loggers (WARNING and DEBUG level).
        Sizes and counts are controlled via LOGFILE_SIZE and LOGFILE_COUNT.
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

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        logger.addHandler(normal_handler)
        logger.addHandler(debug_handler)
        return logger

    async def setup_hook(self) -> None:
        """Load all cogs and sync slash commands globally."""
        for handler in self.handlers:
            await self.load_extension(handler)
        await self.tree.sync()

    async def unload_all(self) -> None:
        """Unload all cogs."""
        for c in self.handlers:
            await self.unload_extension(c)

    async def sync_commands(self) -> None:
        await self.tree.sync()


if __name__ == "__main__":
    load_dotenv(find_dotenv(".env"))
    client = Bot()
    client.run(os.getenv("DISCORD_TOKEN"))
