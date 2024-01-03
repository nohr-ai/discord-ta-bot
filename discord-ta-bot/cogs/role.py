import os
import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from discord.app_commands.checks import has_permissions


class Role(commands.Cog):
    """
    Handles automatic role-assignments

    Parameters
    ----------
    bot : commands.Bot
        The bot object.
    """

    def __init__(self, bot):
        self.bot = bot

    async def setup_roles_autocomplete(
        self, interaction: discord.Interaction, role_emoji_pairs: str
    ) -> list[app_commands.Choice[str]]:
        """
        Autocomplete for the setup_roles command

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object.
        role_emoji_pairs : str
            The role-emoji pairs.

        Returns
        -------
        list[app_commands.Choice[str]]
            The autocomplete choices.
        """
        
        guild = self.bot.get_guild(interaction.guild_id)
        return [
            app_commands.Choice(name=f"{r.name}/{e}", value=f"{r.name}/{e}")
            for r in guild.roles
            for e in guild.emojis
        ]

    @app_commands.command(
        name="setup_roles",
        description="setup automatic role-assignment for the server. Expected format: `role_name:emoji_name`",
    )
    @has_permissions(administrator=True)
    async def setup_roles(
        self, interaction: discord.Interaction, role_emoji_pairs: str
    ) -> None:
        """
        setup automatic role-assignment for the server. Expected format: `role_name:emoji_name`

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object.
        role_emoji_pairs : str
            The role-emoji pairs.

        role_emoji_pairs: t1/<:AdminGun_Blue:941478333525393469> t2/<:MrMurphy:1025117523118673970>
        """
        roles_emojis = {}
        response = discord.Embed(
            title="React to this post to get a role",
            color=discord.Color.green(),
        )
        role_emoji_pairs = role_emoji_pairs.split(" ")
        self.bot.log.debug(f"{role_emoji_pairs}")
        guild = interaction.guild
        for role_emoji_pair in role_emoji_pairs:
            self.bot.log.debug(f"{role_emoji_pair}")
            role_name, emoji_name = role_emoji_pair.split("/")
            self.bot.log.debug(f"{role_name} {str(emoji_name)}")
            try:
                # Custom emojis
                _, emoji_name, _ = emoji_name.split(":")
                emoji = discord.utils.get(guild.emojis, name=emoji_name)
            except ValueError:
                # Unicode emojis
                emoji = emoji_name
            role = discord.utils.get(guild.roles, name=role_name)
            self.bot.log.debug(f"{role} {emoji}")
            if role and emoji:
                response.add_field(
                    name=f"{emoji} -> {role.name}",
                    value=f"",
                    inline=False,
                )
                self.bot.log.debug(f"{role.name} {emoji}")
                roles_emojis[emoji] = role
        self.bot.log.debug(f"Roles and emojis: {roles_emojis}")

        await interaction.response.send_message(embed=response)

        # Parse out the message to add reactions to
        message = None
        async for m in interaction.channel.history(limit=10):
            if m.embeds and m.embeds[0].title == response.title:
                message = m
                break
        if message:
            for emoji in roles_emojis:
                await message.add_reaction(emoji)
            if not await self.bot.add_roles(guild, message, roles_emojis):
                self.bot.log.error("Failed to add roles")
                await message.delete()
        else:
            self.bot.log.error("Message not found")

    async def get_reaction_role_member(
        self, reaction: discord.RawReactionActionEvent
    ) -> (discord.Role, discord.Member):
        """
        Finds the role and member for a reaction

        Parameters
        ----------
        reaction : discord.RawReactionActionEvent
            The reaction payload.

        Returns
        -------
        (discord.Role, discord.Member)
            The role and member.
        """
        guild = await self.bot.get_guild(reaction.guild_id)
        emoji = str(reaction.emoji)
        self.bot.log.debug(
            f"Guild/User {reaction.guild_id}/{reaction.user_id} reacting with emoji: {guild.roles.keys()}"
        )
        if not emoji or emoji not in guild.roles.keys():
            self.bot.log.debug(f"Emoji {emoji} not found")
            raise ValueError("Unknown emoji for role request")
        role_name = guild.roles[emoji]
        guild = discord.utils.get(self.bot.guilds, id=reaction.guild_id)
        role = discord.utils.get(guild.roles, id=role_name)
        if not role:
            self.bot.log.debug(f"Role {role_name} not found")
            raise ValueError("Requested role not found")
        member = discord.utils.get(guild.members, id=reaction.user_id)
        if not member:
            self.bot.log.debug(f"Member {reaction.user_id} not found for role request")
            raise ValueError("Member not found")
        return role, member

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
        guild = await self.bot.get_guild(payload.guild_id)
        if not guild.role_message or payload.message_id != guild.role_message:
            self.bot.log.debug(f"Message {payload.message_id} not found")
            return
        role, member = await self.get_reaction_role_member(payload)
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
        role, member = await self.get_reaction_role_member(payload)
        self.bot.log.info(f"Removing role {role.name} from {member.name}")
        await member.remove_roles(role)


async def setup(bot):
    await bot.add_cog(Role(bot))
