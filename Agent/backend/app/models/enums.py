import enum


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class SelectionStatus(str, enum.Enum):
    SELECTED = "SELECTED"
    SUPERSEDED = "SUPERSEDED"
    REMOVED = "REMOVED"
