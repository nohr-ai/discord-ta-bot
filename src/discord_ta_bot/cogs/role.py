import re
import discord
import logging
from datetime import datetime, timezone
from ..Bot import Bot
from discord import app_commands
from discord.ext import commands
from discord.app_commands.checks import has_permissions


GROUP_ROLE_PATTERN = re.compile(r"^(\d{4})_group_(\d+)$")
ONBOARDING_PROMPT_TITLE = "Which group are you in?"


class Role(commands.Cog):
    """
    Handles semester setup and teardown for a Discord server used for
    teaching at UiT.

    Role and channel access control is delegated entirely to Discord's
    native permission system. The bot creates ``<year>_group_<n>`` roles and
    channels each semester and manages group membership via Discord Onboarding.

    At the end of a semester, channels are archived (renamed, moved,
    set read-only) and the onboarding prompt is removed. Roles are left as-is
    so members retain access to their archived channel automatically.

    The bot is fully stateless — all context is derived from
    ``interaction.guild`` at command time. Multiple guilds are supported
    without any shared state.

    Parameters
    ----------
    bot : commands.Bot
        The bot object.
    """

    def __init__(self, bot):
        self.bot: Bot = bot
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.group_text_permissions = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_messages=True,
            read_message_history=True,
            embed_links=True,
            attach_files=True,
            send_messages_in_threads=True,
            create_public_threads=True,
            add_reactions=True,
        )
        self.group_voice_permissions = discord.PermissionOverwrite(
            view_channel=True,
            connect=True,
            speak=True,
            stream=True,
            use_voice_activation=True,
        )

    async def get_or_create_category(
        self, guild: discord.Guild, name: str
    ) -> discord.CategoryChannel:
        category = discord.utils.get(guild.categories, name=name)
        if not category:
            category = await guild.create_category(name)
        return category

    def _check_bot_permissions(self, guild: discord.Guild) -> str | None:
        """Return an error message if the bot lacks required permissions, else None."""
        perms = guild.me.guild_permissions
        missing = []
        if not perms.manage_roles:
            missing.append("`manage_roles`")
        if not perms.manage_guild:
            missing.append("`manage_guild`")
        if not perms.manage_channels:
            missing.append("manage channels")
        if missing:
            return f"Bot is missing required permissions: {', '.join(missing)}."
        return None

    async def create_groups(
        self, guild: discord.Guild, year: int, number_of_roles: int
    ) -> tuple[list[discord.Role], list[str]]:
        """
        Create ``<year>_group_1`` … ``<year>_group_n`` roles for the semester.

        Roles that already exist are skipped with a warning (this normally
        should not happen — roles from a previous semester have a different
        year prefix). Returns a tuple of ``(roles, warnings)``.
        """
        roles: list[discord.Role] = []
        warnings: list[str] = []
        for n in range(1, number_of_roles + 1):
            name = f"{year}_group_{n}"
            existing = discord.utils.get(guild.roles, name=name)
            if existing:
                msg = f"Role `{name}` already exists — skipped."
                self.logger.warning(msg)
                warnings.append(msg)
                roles.append(existing)
            else:
                role = await guild.create_role(name=name)
                self.logger.info(f"Created role: {role.name}")
                roles.append(role)
        return roles, warnings

    async def setup_group_channels(
        self, guild: discord.Guild, roles: list[discord.Role]
    ) -> list[str]:
        """
        Create private text and voice channels for each group role under
        dedicated categories. @everyone is denied view access on both
        categories; each group role is granted access only to its own
        channels.

        Channels that already exist inside the respective category are
        skipped with a warning. Returns a list of warning strings.
        """
        default_deny = discord.PermissionOverwrite(view_channel=False)
        warnings: list[str] = []

        text_category = await self.get_or_create_category(guild, "group_text_channels")
        await text_category.set_permissions(guild.default_role, overwrite=default_deny)

        voice_category = await self.get_or_create_category(
            guild, "group_voice_channels"
        )
        await voice_category.set_permissions(guild.default_role, overwrite=default_deny)

        existing_text_names = {ch.name for ch in text_category.text_channels}
        existing_voice_names = {ch.name for ch in voice_category.voice_channels}

        for role in roles:
            if role.name in existing_text_names:
                msg = f"Text channel `{role.name}` already exists in `group_text_channels` — skipped."
                self.logger.warning(msg)
                warnings.append(msg)
            else:
                await text_category.create_text_channel(
                    role.name,
                    overwrites={
                        guild.default_role: default_deny,
                        role: self.group_text_permissions,
                    },
                )
                self.logger.info(f"Created text channel: {role.name}")

            if role.name in existing_voice_names:
                msg = f"Voice channel `{role.name}` already exists in `group_voice_channels` — skipped."
                self.logger.warning(msg)
                warnings.append(msg)
            else:
                await voice_category.create_voice_channel(
                    role.name,
                    overwrites={
                        guild.default_role: default_deny,
                        role: self.group_voice_permissions,
                    },
                )
                self.logger.info(f"Created voice channel: {role.name}")

        return warnings

    async def _upsert_onboarding_prompt(
        self, guild: discord.Guild, roles: list[discord.Role]
    ) -> None:
        """
        Update the Discord Onboarding prompt titled ``ONBOARDING_PROMPT_TITLE``
        so its options match ``roles`` exactly (one option per role).

        Each option assigns both the group role and the ``students`` role, so
        that selecting any group automatically grants both roles to the member.
        If the ``students`` role does not exist it is omitted from the options
        with a warning.

        If the prompt does not exist it is created and appended to the
        existing prompts. All other prompts are left untouched.

        Pass an empty ``roles`` list to remove the prompt entirely (e.g. at
        end of semester). Discord does not allow prompts with zero options,
        so removal deletes the prompt.
        """
        onboarding = await guild.onboarding()

        students_role = discord.utils.get(guild.roles, name="students")
        if roles and not students_role:
            self.logger.warning(
                "'students' role not found — group options will not assign it."
            )

        options = [
            discord.OnboardingPromptOption(
                title=role.name,
                roles=[role, students_role] if students_role else [role],
            )
            for role in roles
        ]

        existing = next(
            (p for p in onboarding.prompts if p.title == ONBOARDING_PROMPT_TITLE),
            None,
        )

        # Discord requires 1–50 options per prompt. If roles is empty (e.g.
        # end_semester), remove the prompt entirely instead of sending 0 options.
        if not roles:
            if existing is None:
                self.logger.info(
                    f"Onboarding prompt '{ONBOARDING_PROMPT_TITLE}' not found; nothing to remove."
                )
                return
            new_prompts = [
                p for p in onboarding.prompts if p.title != ONBOARDING_PROMPT_TITLE
            ]
            await guild.edit_onboarding(
                prompts=new_prompts,
                reason="Semester end — group prompt removed by bot",
            )
            self.logger.info(f"Onboarding prompt '{ONBOARDING_PROMPT_TITLE}' removed.")
            return

        if existing is not None:
            updated_prompt = discord.OnboardingPrompt(
                type=existing.type,
                title=existing.title,
                options=options,
                single_select=existing.single_select,
                required=existing.required,
                in_onboarding=existing.in_onboarding,
            )
            new_prompts = [
                updated_prompt if p.title == ONBOARDING_PROMPT_TITLE else p
                for p in onboarding.prompts
            ]
        else:
            new_prompt = discord.OnboardingPrompt(
                type=discord.OnboardingPromptType.multiple_choice,
                title=ONBOARDING_PROMPT_TITLE,
                options=options,
                single_select=True,
                required=True,
                in_onboarding=True,
            )
            new_prompts = list(onboarding.prompts) + [new_prompt]

        await guild.edit_onboarding(
            prompts=new_prompts,
            reason="Semester update by bot",
        )
        self.logger.info(
            f"Onboarding prompt '{ONBOARDING_PROMPT_TITLE}' updated "
            f"with {len(options)} option(s)."
        )

    @app_commands.command(
        name="start_semester",
        description="Create group roles and private channels for the new semester.",
    )
    @has_permissions(administrator=True)
    async def start_semester(
        self, interaction: discord.Interaction, number_of_groups: int
    ) -> None:
        """
        Start a new semester by:
        - Creating ``<year>_group_1`` … ``<year>_group_n`` roles, where year
          is the current UTC year.
        - Creating a private text and voice channel per group.
        - Creating or updating the Discord Onboarding group-selection prompt
          (each option assigns both the group role and ``students``).

        Role assignment to students is handled via Discord Onboarding.
        The ``students`` role and ``shared_channels`` category must exist
        beforehand (one-time manual setup — see Conventions.md).
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        guild = interaction.guild

        perm_error = self._check_bot_permissions(guild)
        if perm_error:
            await interaction.followup.send(perm_error, ephemeral=True)
            return

        year = datetime.now(timezone.utc).year
        roles, role_warnings = await self.create_groups(guild, year, number_of_groups)
        channel_warnings = await self.setup_group_channels(guild, roles)
        await self._upsert_onboarding_prompt(guild, roles)

        all_warnings = role_warnings + channel_warnings
        summary = f"Semester {year} started: {number_of_groups} group(s) ready."
        if all_warnings:
            summary += "\n\nWarnings:\n" + "\n".join(f"- {w}" for w in all_warnings)

        await interaction.followup.send(summary, ephemeral=True)

    @app_commands.command(
        name="end_semester",
        description="Archive group channels and remove the onboarding prompt.",
    )
    @has_permissions(administrator=True)
    async def end_semester(self, interaction: discord.Interaction) -> None:
        """
        End the current semester by:
        - Finding all ``<year>_group_<n>`` roles matching the current UTC year.
        - Assigning the ``Alumni`` role to every member of each group
          (created if it does not exist).
        - Archiving each group's text channel (from ``group_text_channels``
          only): renamed to ``<year>-group_<n>``, moved to
          ``Archived_text_channels``, with overwrites: deny ``@everyone``,
          allow ``<year>_group_<n>`` (read-only). Members with
          ``administrator`` permission bypass overwrites automatically.
        - Deleting each group's voice channel (from ``group_voice_channels``
          only).
        - Deleting the ``group_text_channels`` and ``group_voice_channels``
          categories.
        - Removing the ``students`` role from every member who holds it.
        - Removing the Discord Onboarding group-selection prompt.

        Group roles are not deleted — members retain them and automatically
        keep read-only access to their own archived channel.
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        guild = interaction.guild

        perm_error = self._check_bot_permissions(guild)
        if perm_error:
            await interaction.followup.send(perm_error, ephemeral=True)
            return

        year = datetime.now(timezone.utc).year
        year_prefix = f"{year}_group_"

        group_roles = [
            role for role in guild.roles if role.name.startswith(year_prefix)
        ]

        if not group_roles:
            await interaction.followup.send(
                f"No group roles found for {year} "
                f"(expected names matching `{year_prefix}<n>`).",
                ephemeral=True,
            )
            return

        # Ensure archive category exists
        archived_category = await self.get_or_create_category(
            guild, "Archived_text_channels"
        )

        # Resolve active channel categories (may be None if already deleted)
        text_category = discord.utils.get(guild.categories, name="group_text_channels")
        voice_category = discord.utils.get(
            guild.categories, name="group_voice_channels"
        )

        # Ensure Alumni role exists
        alumni_role = discord.utils.get(guild.roles, name="Alumni")
        if alumni_role is None:
            alumni_role = await guild.create_role(
                name="Alumni",
                reason=f"Created by bot at end of semester {year}",
            )
            self.logger.info("Created Alumni role")

        warnings: list[str] = []

        for role in group_roles:

            # Assign Alumni to every member of this group
            for member in list(role.members):
                await member.add_roles(alumni_role)
                self.logger.info(
                    f"Assigned Alumni to {member.name} (was in {role.name})"
                )

            # Archive text channel (category-scoped lookup by current role name)
            text_channel = None
            if text_category:
                text_channel = discord.utils.get(
                    text_category.text_channels, name=role.name
                )
            if text_channel:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(
                        read_messages=False
                    ),
                    role: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=False,
                        add_reactions=False,
                    ),
                }
                await text_channel.edit(
                    name=role.name,
                    category=archived_category,
                    overwrites=overwrites,
                )
                self.logger.info(
                    f"Archived text channel `{role.name}` "
                    f"(read-only for {role.name})"
                )
            else:
                msg = f"Text channel `{role.name}` not found in `group_text_channels` — skipped."
                self.logger.warning(msg)
                warnings.append(msg)

            # Delete voice channel (category-scoped lookup)
            voice_channel = None
            if voice_category:
                voice_channel = discord.utils.get(
                    voice_category.voice_channels, name=role.name
                )
            if voice_channel:
                await voice_channel.delete()
                self.logger.info(f"Deleted voice channel: {role.name}")
            else:
                msg = f"Voice channel `{role.name}` not found in `group_voice_channels` — skipped."
                self.logger.warning(msg)
                warnings.append(msg)

        # Remove students role from every member who holds it
        students_role = discord.utils.get(guild.roles, name="students")
        if students_role:
            for member in list(students_role.members):
                await member.remove_roles(students_role)
                self.logger.info(f"Removed students role from {member.name}")

        # Delete the now-empty active categories
        for category in (text_category, voice_category):
            if category:
                await category.delete()

        # Remove the onboarding group-selection prompt
        await self._upsert_onboarding_prompt(guild, [])

        summary = (
            f"Semester {year} ended: {len(group_roles)} group(s) archived. "
            f"Run `/start_semester` to begin the next semester."
        )
        if warnings:
            summary += "\n\nWarnings:\n" + "\n".join(f"- {w}" for w in warnings)

        await interaction.followup.send(summary, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Role(bot))
