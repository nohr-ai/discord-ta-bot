import logging
import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands.checks import has_permissions


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
        self.logger = logging.getLogger(__name__)

    async def echo_autocomplete(
        self, interaction: discord.Interaction, name: str
    ) -> app_commands.Choice[str]:
        """
        Autocomplete for the echo command
        """
        return [app_commands.Choice(name=name, value=name)]

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
        await interaction.response.send_message(
            f"Hello {arg1} from {self.__class__.__name__}"
        )


async def setup(bot):
    """
    This function is called by the bot when the cog is loaded.
    """
    await bot.add_cog(Template(bot))
