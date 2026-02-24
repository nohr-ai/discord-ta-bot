import os
from typing import Optional
import discord
import asyncio
import logging
from discord import ChannelFlags, app_commands
from discord.ext import commands
from discord.app_commands.checks import has_permissions
from discord.ext.commands.parameters import CurrentChannel

import utils.db as db


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

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
        name="delete_groups",
        description="Delete groups with a prefix",
    )
    @has_permissions(administrator=True)
    async def delete_gruops(
        self, interaction: discord.Interaction, prefix: str
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild

        for role in guild.roles:
            if role.name.startswith(prefix):
                await role.delete()

        await interaction.followup.send("Done", ephemeral=True)

    @app_commands.command(
        name="delete_channels",
        description="Delete channels(text and voice) with prefix",
    )
    @has_permissions(administrator=True)
    async def delete_chats(self, interaction: discord.Interaction, prefix: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        tc = [
            textch for textch in guild.text_channels if textch.name.startswith(prefix)
        ]
        vc = [
            voicech
            for voicech in guild.voice_channels
            if voicech.name.startswith(prefix)
        ]
        for channel in tc:
            await channel.delete()
        for channel in vc:
            await channel.delete()
        await interaction.followup.send(
            f"Deleted {len(tc)} text channels and {len(vc)} voice channels starting with: {prefix}",
            ephemeral=True,
        )

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
            for file in os.listdir(os.path.dirname(os.path.realpath(__file__)))
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
            self.logger.info(f"Reloading {module}")
            self.logger.debug(
                f"User [{interaction.user.id}] from [{interaction.guild_id}] reloading {module}"
            )
            await self.bot.reload_extension(f"cogs.{module}")
        except commands.ExtensionError as e:
            self.logger.error(f"Error loading {module}: {e}")
            await interaction.response.send_message(
                f"Error loading {module}: {e}", ephemeral=True
            )
        else:
            self.logger.info(f"Reloaded {module}")
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
        await interaction.response.defer(ephemeral=True, thinking=True)

        await self.bot.sync_commands()
        await interaction.followup.send("Commands synced.", ephemeral=True)

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

    @has_permissions(administrator=True)
    async def list_text_channels(
        self, interaction: discord.Interaction, name: str
    ) -> list[app_commands.Choice[str]]:
        # Get all individual channels, remove ongoing autocomplete for next
        already_chosen = [
            name
            for name in [nm.strip() for nm in name.split(",") if name]
            if name in [ch.name for ch in interaction.guild.text_channels]
        ]
        already_chosen_ids = [
            str(channel.id)
            for channel in interaction.guild.text_channels
            if channel.name in already_chosen
        ]

        channels = [
            app_commands.Choice(
                name=(
                    ",".join(already_chosen + [channel.name]) if name else channel.name
                ),
                value=(
                    ",".join(already_chosen_ids + [str(channel.id)])
                    if name
                    else str(channel.id)
                ),
            )
            for channel in interaction.guild.text_channels
            if channel.name.startswith(name.split(",")[-1])
            and channel.name not in already_chosen
        ]
        return channels

    @app_commands.command(
        name="set_persistent_text_channels",
        description="Overwrite current text_channels kept persistent over the semesters",
    )
    @app_commands.autocomplete(channels=list_text_channels)
    @has_permissions(administrator=True)
    async def set_persistent_text_channels(
        self, interaction: discord.Interaction, channels: Optional[str]
    ) -> None:
        print(f"in set_p_t_c input:{channels}")
        if channels:
            existing_channels = [ch.id for ch in interaction.guild.text_channels]
            channels = [int(ch.strip()) for ch in channels.split(",")]
            channels = [ch for ch in channels if ch in existing_channels]
        else:
            channels = []
        await db.set_persistent_text_channels(
            self.bot.db_name, interaction.guild.id, channels
        )
        await interaction.response.send_message(f"in s_p_t_c got list of; {channels}")

    @has_permissions(administrator=True)
    async def list_not_persistent_text_channels(
        self, interaction: discord.Interaction, name: str
    ) -> list[app_commands.Choice[str]]:
        print("In lsitnot autocompl")
        existing = await db.get_persistent_text_channels(
            self.bot.db_name, interaction.guild.id
        )
        print(name)
        self.logger.warning(name)
        possible = []
        for ch in interaction.guild.text_channels:
            if ch.id not in existing:
                possible.append((ch.name, ch.id))
        print(possible)
        self.logger.warning(possible)
        channels = [
            app_commands.Choice(
                name=chname,
                value=str(chid),
            )
            for chname, chid in possible
            if chname.startswith(name)
        ]
        print(channels)
        self.logger.warning(channels)
        return channels

    @app_commands.command(
        name="add_persistent_text_channel",
        description="Add a text channel to the list of persistent text channels",
    )
    @app_commands.autocomplete(channel=list_not_persistent_text_channels)
    @has_permissions(administrator=True)
    async def add_persistent_text_channel(
        self, interaction: discord.Interaction, channel: str
    ) -> None:
        channel = int(channel)
        print(f"aptc in: {channel}")
        persisted_channels = await db.get_persistent_text_channels(
            self.bot.db_name, interaction.guild.id
        )
        print(f"aptc pers: {persisted_channels}")
        if channel not in persisted_channels:
            await db.add_persistent_text_channel(
                self.bot.db_name, interaction.guild.id, channel
            )

        await interaction.response.send_message(f"Input apvc: {channel}")

    @has_permissions(administrator=True)
    async def list_persisted_text_channels(
        self, interaction: discord.Interaction, name: str
    ) -> list[app_commands.Choice[str]]:
        persistent = await db.get_persistent_text_channels(
            self.bot.db_name, interaction.guild.id
        )
        persistent = [
            (channel.name, channel.id)
            for channel in interaction.guild.text_channels
            if channel.id in persistent
        ]
        channels = [
            app_commands.Choice(
                name=chname,
                value=str(chid),
            )
            for chname, chid in persistent
        ]
        return channels

    @app_commands.command(
        name="remove_persistent_text_channel",
        description="Remove a text channel from list of persistent text channel",
    )
    @app_commands.autocomplete(channel=list_persisted_text_channels)
    @has_permissions(administrator=True)
    async def remove_persistent_text_channel(
        self, interaction: discord.Interaction, channel: str
    ) -> None:
        print(f"in rptc: {channel}")
        persistent = await db.get_persistent_text_channels(
            self.bot.db_name, interaction.guild.id
        )
        channel = int(channel)
        if channel in persistent:
            await db.remove_persistent_text_channel(
                self.bot.db_name, interaction.guild.id, channel
            )
        await interaction.response.send_message(f"Input rptc: {channel}")

    @has_permissions(administrator=True)
    async def list_voice_channels(
        self, interaction: discord.Interaction, name: str
    ) -> list[app_commands.Choice[str]]:

        # Get all individual channels, remove ongoing autocomplete for next
        already_chosen = [
            name
            for name in [nm.strip() for nm in name.split(",") if name]
            if name in [ch.name for ch in interaction.guild.voice_channels]
        ]
        already_chosen_ids = [
            str(channel.id)
            for channel in interaction.guild.voice_channels
            if channel.name in already_chosen
        ]

        channels = [
            app_commands.Choice(
                name=(
                    ",".join(already_chosen + [channel.name]) if name else channel.name
                ),
                value=(
                    ",".join(already_chosen_ids + [str(channel.id)])
                    if name
                    else str(channel.id)
                ),
            )
            for channel in interaction.guild.voice_channels
            if channel.name.startswith(name.split(",")[-1])
            and channel.name not in already_chosen
        ]
        return channels

    @app_commands.command(
        name="set_persistent_voice_channels",
        description="Overwrite persistent voice channels",
    )
    @app_commands.autocomplete(channels=list_voice_channels)
    @has_permissions(administrator=True)
    async def set_persistent_voice_channels(
        self, interaction: discord.Interaction, channels: Optional[str]
    ) -> None:
        self.logger.debug(f"in set_p_v_c input: {channels}")
        # Safeguard for gibberish channels
        if channels:
            available_channels = [ch.id for ch in interaction.guild.voice_channels]
            channels = [int(ch.strip()) for ch in channels.split(",")]
            channels = [ch for ch in channels if ch in available_channels]
        else:
            channels = []
        await db.set_persistent_voice_channels(
            self.bot.db_name, interaction.guild.id, channels
        )

        await interaction.response.send_message(f"in s_p_v_c input: {channels}")

    @has_permissions(administrator=True)
    async def list_not_persisted_voice_channels(
        self, interaction: discord.Interaction, name: str
    ) -> list[app_commands.Choice[str]]:
        existing = await db.get_persistent_voice_channels(
            self.bot.db_name, interaction.guild.id
        )
        possible = []
        for ch in interaction.guild.voice_channels:
            if ch.id not in existing:
                possible.append((ch.name, ch.id))

        channels = [
            app_commands.Choice(
                name=chname,
                value=str(chid),
            )
            for chname, chid in possible
            if chname.startswith(name)
        ]

        return channels

    @app_commands.command(
        name="add_persistent_voice_channel",
        description="Overwrite current voice channels kept persistent over the semesters",
    )
    @app_commands.autocomplete(channel=list_not_persisted_voice_channels)
    @has_permissions(administrator=True)
    async def add_persistent_voice_channel(
        self, interaction: discord.Interaction, channel: str
    ) -> None:
        if not channel:
            await interaction.response.send_message(
                "Please provide a channel ID", ephemeral=True
            )
            return

        channel = int(channel)
        persisted_channels = await db.get_persistent_voice_channels(
            self.bot.db_name, interaction.guild.id
        )
        if channel not in persisted_channels:
            await db.add_persistent_voice_channel(
                self.bot.db_name, interaction.guild.id, channel
            )

        await interaction.response.send_message(f"Channel {channel} persisted")

    @has_permissions(administrator=True)
    async def list_persisted_voice_channels(
        self, interaction: discord.Interaction, name: str
    ) -> list[app_commands.Choice[str]]:
        persistent = await db.get_persistent_voice_channels(
            self.bot.db_name, interaction.guild.id
        )
        persistent = [
            (channel.name, channel.id)
            for channel in interaction.guild.voice_channels
            if channel.id in persistent
        ]
        channels = [
            app_commands.Choice(
                name=chname,
                value=str(chid),
            )
            for chname, chid in persistent
        ]
        return channels

    @app_commands.command(
        name="remove_persistent_voice_channel",
        description="Remove a channel from list of persistent channels",
    )
    @app_commands.autocomplete(channel=list_persisted_voice_channels)
    @has_permissions(administrator=True)
    async def remove_persistent_voice_channels(
        self, interaction: discord.Interaction, channel: str
    ) -> None:
        if not channel:
            await interaction.response.send_message("Please provide a channel ID")
            return

        persistent_channels = await db.get_persistent_voice_channels(
            self.bot.db_name, interaction.guild.id
        )
        channel = int(channel)
        if channel in persistent_channels:
            await db.remove_persistent_voice_channel(
                self.bot.db_name, interaction.guild.id, channel
            )
            await interaction.response.send_message(f"Removed {channel}")
        else:
            await interaction.response.send_message(f"Channel {channel} not found")


async def setup(bot):
    await bot.add_cog(Admin(bot))
