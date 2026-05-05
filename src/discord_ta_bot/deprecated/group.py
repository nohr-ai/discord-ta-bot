import discord


class Group:
    '''
    Group AKA TA group

    Discord looks at this as 'roles' and hence the group object holds a reference
    to the corresponding Discord role. 
    '''
    def __init__(
        self,
        name: str = None,
        emoji: str = None,
        role_id: int = None
    ):
        self.name = name
        self.emoji = emoji
        self.role_id = role_id

    def to_json(self):
        
        return {
            "name": self.name,
            "emoji": self.emoji,
            "role_id": self.role_id,
        }
