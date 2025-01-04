import os
import discord
import asyncio
import json
import random
from Bot import Bot
from objects.group import Group
from objects.guild import Guild
from discord import app_commands, PermissionOverwrite
from discord.ext import commands
from discord.app_commands.checks import has_permissions

EMOJIS:dict = json.load(open("../assets/emojis.json", "r"))

class Role(commands.Cog):
    """
    Handles automatic role-assignments and setup of a discord server for
    teaching use at UiT.

    Parameters
    ----------
    bot : commands.Bot
        The bot object.
    """

    def __init__(self, bot):
        self.bot:Bot = bot

    @app_commands.command(
            name="start_semester2",
            description="delete groups",
    )
    @has_permissions(administrator=True)
    async def start_semester2(self, interaction: discord.Interaction)->None:
        guild = interaction.guild
        for role in guild.roles:
            if role.name.startswith("group_"):
                await role.delete()

        await interaction.response.send_message("OK")

    @app_commands.command(
        name="start_semester",
        description="Setup automatic role-assignment, expected format: "
    )
    @has_permissions(administrator=True)
    async def start_semester(self, interaction: discord.Interaction, number_of_groups:str)->None:
        '''
        Start a semester by
            Setting up groups with their private text and voice channels.
            Setting up landing reaction message to automagically assign roles after user reaction
        '''
        await interaction.response.defer(ephemeral=True,thinking=True)
        # msg = await interaction.followup.send(f"Setting up server for {number_of_groups} groups... hang on!",wait=True,ephemeral=True)
        response = discord.Embed(
            title="React to this post to get a role",
            color=discord.Color.green(),
        )
        guild = interaction.guild
        text_channels = await guild.create_category("group_text_channels")
        voice_channels = await guild.create_category("group_voice_channels")

        default_deny = PermissionOverwrite(view_channel=False)
        landing_channel = await text_channels.create_text_channel("landing🛬", overwrites={guild.default_role:default_deny})
        emoji_names = random.sample(list(EMOJIS.values()), k=int(number_of_groups))
        self.bot.log.warning(emoji_names)
        # We bundle discord roles, and groups/TA groups into a group object for easier reference later on.
        groups:list[Group] = []
        for id in range(1,int(number_of_groups)+1):
            name = f"group_{id}"
            role = await guild.create_role(name=name)
            groups.append(Group(name, emoji_names.pop(), role.id))
        for g in groups:
            print(g.to_json())
        # groups:list[Group] = [Group(f"group_{id}", emoji_names[id], await guild.create_role(name=f"group_{id}")) for id in range(int(number_of_groups))]
        # roles = [await guild.create_role(name=f"group_{id}") for id in range(int(number_of_groups))]
        # Discord now defaults to False for permissions, only need to set what we need to True
        group_text_permissions = PermissionOverwrite(read_messages=True,send_messages=True,read_message_history=True)
        group_voice_permissions = PermissionOverwrite(connect=True,speak=True,stream=True)
        try:
            for group in groups:
                role = guild.get_role(group.role_id)
                self.bot.log.info(role)
                await text_channels.create_text_channel(group.name, overwrites={
                    guild.default_role: default_deny,
                    role: group_text_permissions
                })

                await voice_channels.create_voice_channel(group.name,overwrites={
                    guild.default_role: default_deny,
                    role: group_voice_permissions
                })
                response.add_field(
                    name=f'{group.emoji} -> {group.name}',
                    value="",
                    inline=False,
                )

            await self.bot.set_groups(guild,groups)
            message = await landing_channel.send(embed=response)
            for group in groups:
                await message.add_reaction(group.emoji)

            await self.bot.set_role_message(guild, message)
            await interaction.followup.send("Setup complete")
        except Exception as e:
            self.bot.log.exception(e)
            for group in groups:
                role = guild.get_role(group.role_id)
                try:
                    await landing_channel.delete()
                    await role.delete()
                    tc = discord.utils.get(guild.text_channels,name=f"{group.name}")
                    await tc.delete()
                    vc = discord.utils.get(guild.voice_channels, name=f"{group.name}")
                    await vc.delete()
                    await text_channels.delete()
                    await voice_channels.delete()
                except Exception as ee:
                    self.bot.log.exception(ee)
            await interaction.followup.send(f"Setup abort: {e}")
            # await interaction.response.send_message(f"Setup abort: {e}", ephemeral=True)

    @app_commands.command(
        name="end_semester",
        description="Move old students to alumni and remove channels."
    )
    @has_permissions(administrator=True)
    async def end_semester(self, interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        groups = await self.bot.get_groups(guild)
        alumni = discord.utils.get(guild.roles, name="Alumni")
        if not alumni:
            alumni = await guild.create_role(name="Alumni")
        for group in groups:
            role = guild.get_role(group.role_id)
            members = role.members
            for member in members:
                await member.add_roles(alumni)
            text_channel = discord.utils.get(guild.text_channels, name=group.name)
            voice_channel = discord.utils.get(guild.voice_channels, name=group.name)
            await text_channel.delete()
            await voice_channel.delete()
            await role.delete()
        
        role_message = await self.bot.get_role_message(
            guild
        )
        landing_channel = discord.utils.get(guild.channels, name="landing🛬")
        async for m in landing_channel.history(limit=10):
            if m.id == role_message:
                await m.delete()
                await self.bot.set_role_message(guild)
        await landing_channel.delete()
        await discord.utils.get(guild.categories, name="group_text_channels").delete()
        await discord.utils.get(guild.categories, name='group_voice_channels').delete()

        await interaction.followup.send("Semester end, all groups removed and moved to alumni", ephemeral=True)

    async def get_reaction_role(self, guild:discord.Guild, emoji:discord.PartialEmoji) -> discord.Role:
        try:
            internal_guild:Guild = await self.bot.get_guild(guild.id)
            for group in internal_guild.groups:
                if group.emoji == emoji.name:
                    return discord.utils.get(guild.roles, name=group.name)
        except ValueError as ve:
            self.bot.log.exception(ve)



    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Automatically assign roles to users based on reactions

        Parameters
        ----------
        payload : discord.RawReactionActionEvent
            The reaction payload.
        """
        if payload.user_id == self.bot.user.id:
            return
        internal_guild = await self.bot.get_guild(payload.guild_id)
        if not internal_guild.role_message or payload.message_id != internal_guild.role_message:
            self.bot.log.debug(f"Message {payload.message_id} not role message")
            return
        discord_guild = discord.utils.get(self.bot.guilds, id=payload.guild_id)
        role = await self.get_reaction_role(discord_guild, payload.emoji)
        member = discord_guild.get_member(payload.user_id)
        self.bot.log.info(f"Adding role {role.name} to {member.name}")
        await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """
        Automatically remove roles from users based on reactions

        Parameters
        ----------
        payload : discord.RawReactionActionEvent
            The reaction payload.
        """
        if payload.user_id == self.bot.user.id:
            return
        guild = await self.bot.get_guild(payload.guild_id)
        if not guild.role_message or payload.message_id != guild.role_message:
            self.bot.log.debug(f"Message {payload.message_id} not found")
            return
        discord_guild = discord.utils.get(self.bot.guilds, id=payload.guild_id)
        role = await self.get_reaction_role(discord_guild, payload.emoji)
        member = discord_guild.get_member(payload.user_id)
        self.bot.log.info(f"Removing role {role.name} from {member.name}")
        await member.remove_roles(role)

async def setup(bot):
    await bot.add_cog(Role(bot))