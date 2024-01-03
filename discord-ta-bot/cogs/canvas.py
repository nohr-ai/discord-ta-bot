import os
import discord
import asyncio
from discord import app_commands
from discord.app_commands.checks import has_permissions
from discord.ext import commands, tasks
from canvasapi import Canvas as cv
from objects.canvas_course import Course
from dateutil import parser
from datetime import datetime


class Canvas(commands.Cog):
    """
    Main class for the canvas module.
    This cog is used to interact with the canvas api.
    It requires the following environment variables:
    
    - CANVAS_URL(Base url for your canvas instance)
    - CANVAS_TOKEN

    Parameters
    ----------
    bot : commands.Bot
        The bot object.
    """

    def __init__(self, bot):
        self.bot = bot
        self.canvas_handle = cv(os.getenv("CANVAS_URL"), os.getenv("CANVAS_TOKEN"))

    @has_permissions(administrator=True)
    async def canvas_add_course_autocomplete(
        self, interaction: discord.Interaction, course_code: int
    ) -> list[app_commands.Choice[str]]:
        last_year = datetime.now().year - 1
        return [
            app_commands.Choice(name=o.name, value=str(o.id))
            for o in self.canvas_handle.get_courses()
            if o.created_at_date.year >= last_year
        ]

    @app_commands.command(
        name="canvas_add_course",
        description="Add a canvas course to the bot.",
    )
    @app_commands.autocomplete(course_code=canvas_add_course_autocomplete)
    @has_permissions(administrator=True)
    async def add_course(
        self, interaction: discord.Interaction, course_code: int
    ) -> None:
        """
        Add a canvas course to the bot.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction object.
        course_code : int
            The course code.
        """
        course = self.canvas_handle.get_course(course_code)
        await self.bot.add_canvas_course(
            interaction.guild.id, Course(course.name, course.id)
        )
        await interaction.response.send_message(
            f"Loaded {course_code}.", ephemeral=True
        )

    """
    TODO: Setup announcement relay. Use EP's code as a base?
    https://github.com/EdvardPedersen/CanvasHelper
    """


async def setup(bot):
    await bot.add_cog(Canvas(bot))
