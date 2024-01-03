import os
import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import has_permissions


class Template(commands.Cog):
    """
    Template class for a cog.
    Copy paste this into a new cog and change the name.

    Parameters
    ----------
    bot : commands.Bot
        The bot object.
    """

    def __init__(self, bot):
        self.bot = bot

    async def echo_autocomplete(
        self, interaction: discord.Interaction, name: str
    ) -> list[app_commands.Choice[str]]:
        """
        Autocomplete for the echo command
        """
        return [
            app_commands.Choice(name="test", value="test"),
            app_commands.Choice(name="test2", value="test2"),
        ]

    @app_commands.command(
        name="echo",
        description="echo",
    )
    @app_commands.autocomplete(arg1=echo_autocomplete)
    @has_permissions(administrator=True)
    async def echo(self, interaction: discord.Interaction, arg1: str) -> None:
        """
        echo
        """
        interaction.response.send_message(
            f"Hello {arg1} from {self.__class__.__name__}"
        )


async def setup(bot):
    """
    This function is called by the bot when the cog is loaded.
    """
    await bot.add_cog(Template(bot))
