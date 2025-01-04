from .canvas_course import Course
from .group import Group
import discord


class Guild:
    def __init__(
        self,
        _id: int = None,
        name: str = None,
        canvas_courses: list[dict] = [],
        github_orgs: list[str] = [],
        role_message: discord.Message = None,
        groups: list[Group] = [],
    ):
        self.id = _id
        self.name = name
        self.canvas_courses = [Course(**course) for course in canvas_courses]
        self.github_orgs = github_orgs
        self.role_message = role_message
        self.groups = [Group(**group) for group in groups]

    def to_json(self):
        return {
            "_id": self.id,
            "name": self.name,
            "canvas_courses": [course.__dict__ for course in self.canvas_courses],
            "github_orgs": self.github_orgs,
            "role_message": self.role_message.id if self.role_message else None,
            "groups": [group.__dict__ for group in self.groups]
        }
