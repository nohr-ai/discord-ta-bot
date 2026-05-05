import os
import pathlib
import logging
from logging.handlers import RotatingFileHandler

import discord
from dotenv import load_dotenv, find_dotenv
from discord.ext import commands

_DEFAULT_LOG_PATH = pathlib.Path.home() / ".local" / "state" / "discord-ta-bot"

__all__ = ["Bot"]


class Bot(commands.Bot):
    """
    Main class for the bot.
    This class is used to interact with the discord API.
    It requires the following environment variables:
    - DISCORD_TOKEN
    - LOGFILE_FORMAT
    - LOGFILE_SIZE
    - LOGFILE_COUNT

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

        self.cog_modules = [
            f"discord_ta_bot.cogs.{cog.name.removesuffix('.py')}"
            for cog in (pathlib.Path(__file__).parent / "cogs").iterdir()
            if cog.name.endswith(".py") and not cog.name.startswith("_")
        ]
        self.setup_logging()

    def setup_logging(self) -> None:
        """
        Setup logging for the bot.
        Configures two rotating file loggers (WARNING and DEBUG level).
        Sizes and counts are controlled via LOGFILE_SIZE and LOGFILE_COUNT.
        """
        formatter = logging.Formatter(os.getenv("LOGFILE_FORMAT"))

        log_path = (
            pathlib.Path.home()
            / os.getenv("LOGFILE_BASE_PATH", _DEFAULT_LOG_PATH)
            / f"{self.__class__.__name__}.log"
        )
        log_path.parent.mkdir(parents=True, exist_ok=True)

        normal_handler = RotatingFileHandler(
            log_path,
            maxBytes=int(os.getenv("LOGFILE_SIZE", 100)),
            backupCount=int(os.getenv("LOGFILE_COUNT", 1)),
        )
        normal_handler.setFormatter(formatter)
        normal_handler.setLevel(logging.WARNING)

        debug_path = (
            pathlib.Path.home()
            / os.getenv("LOGFILE_BASE_PATH", _DEFAULT_LOG_PATH)
            / "debug"
            / f"{self.__class__.__name__}.debug.log"
        )
        debug_path.parent.mkdir(parents=True, exist_ok=True)

        debug_handler = RotatingFileHandler(
            debug_path,
            maxBytes=int(os.getenv("LOGFILE_SIZE", 100)),
            backupCount=int(os.getenv("LOGFILE_COUNT", 1)),
        )
        debug_handler.setFormatter(formatter)
        debug_handler.setLevel(logging.DEBUG)

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(normal_handler)
        logger.addHandler(debug_handler)
        return logger

    async def setup_hook(self) -> None:
        """Load all cogs and sync slash commands globally."""
        for cog in self.cog_modules:
            await self.load_extension(cog)
        await self.tree.sync()

    async def unload_all(self) -> None:
        """Unload all cogs."""
        for cog in self.cog_modules:
            await self.unload_extension(cog)

    async def sync_commands(self) -> None:
        await self.tree.sync()


def main():
    load_dotenv(find_dotenv(".env"))
    client = Bot()
    client.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()
