class Course:
    def __init__(self, name: str, id: int) -> None:
        self.name: str = name
        self.id: int = id

    def __str__(self) -> str:
        return f"{self.name}: {str(self.id)}"
