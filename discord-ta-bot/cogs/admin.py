import os
import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from discord.app_commands.checks import has_permissions


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="load",
        description="Load a module.",
    )
    @has_permissions(administrator=True)
    async def load(self, interaction: discord.Interaction, module: str):
        try:
            await self.bot.load_extension(f"cogs.{module}")
        except commands.ExtensionError as e:
            await interaction.response.send_message(
                f"Error loading {module}: {e}", ephemeral=True
            )
        else:
            await interaction.response.send_message(f"Loaded {module}.", ephemeral=True)

    @app_commands.command(
        name="unload",
        description="Unload a module.",
    )
    @has_permissions(administrator=True)
    async def unload(self, interaction: discord.Interaction, module: str):
        try:
            await self.bot.unload_extension(f"cogs.{module}")
        except commands.ExtensionError as e:
            await interaction.response.send_message(
                f"Error loading {module}: {e}", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Unloaded {module}.", ephemeral=True
            )

    @has_permissions(administrator=True)
    async def get_all_extensions(
        self, interaction: discord.Interaction, module: str
    ) -> list[app_commands.Choice[str]]:
        extensions = [
            app_commands.Choice(name=file[:-3], value=file[:-3])
            for file in os.listdir("cogs")
            if file.startswith(module) and file.endswith(".py")
        ]
        return extensions

    @app_commands.command(
        name="reload_extension",
        description="Reload an extension.",
    )
    @app_commands.autocomplete(module=get_all_extensions)
    @has_permissions(administrator=True)
    async def reload_extension(
        self, interaction: discord.Interaction, module: str
    ) -> None:
        """
        Reloads an extension

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object.
        module : str
            The module to reload

        Returns
        -------
        None
        """
        try:
            self.bot.log.info(f"Reloading {module}")
            self.bot.log.debug(
                f"User [{interaction.user.id}] from [{interaction.guild_id}] reloading {module}"
            )
            await self.bot.reload_extension(f"cogs.{module}")
        except commands.ExtensionError as e:
            self.bot.log.error(f"Error loading {module}: {e}")
            await interaction.response.send_message(
                f"Error loading {module}: {e}", ephemeral=True
            )
        else:
            self.bot.log.info(f"Reloaded {module}")
            await interaction.response.send_message(f"Loaded {module}.", ephemeral=True)

    @app_commands.command(
        name="sync",
        description="Sync commands.",
    )
    @has_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        """
        Syncs commands with the discord API.
        Will make breaking changes to your bot visible to users.
        """
        await self.bot.tree.sync()
        await interaction.response.send_message("Commands synced.", ephemeral=True)

    @app_commands.command(
        name="timer",
        description="Set a timer.",
    )
    @has_permissions(administrator=True)
    async def timer(self, interaction: discord.Interaction, time: int):
        """
        Set a timer for yourself
        """
        await interaction.response.send_message(
            f"Timer set for {time} seconds.", ephemeral=True
        )
        await asyncio.sleep(time)
        await interaction.followup.send("Timer expired.", ephemeral=True)

    @app_commands.command(
        name="reboot",
        description="Reboots the bot",
    )
    @has_permissions(administrator=True)
    async def reboot(self, interaction: discord.Interaction):
        """
        Reboots the bot if hosted as a service or similar
        Otherwise the bot will only shut down
        """
        await interaction.response.send_message("Rebooting", ephemeral=True)
        await self.bot.close()


async def setup(bot):
    await bot.add_cog(Admin(bot))
