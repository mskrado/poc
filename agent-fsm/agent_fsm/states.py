from enum import Enum, auto


class AgentState(Enum):
    INIT = auto()
    EXTRACTING = auto()
    VALIDATING = auto()
    ROUTING = auto()
    ESCALATING = auto()
    DONE = auto()
    ERROR = auto()
