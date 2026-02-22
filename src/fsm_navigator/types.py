from pydantic import BaseModel


class Transition(BaseModel):
    from_state: str
    action: str
    to_state: str
    requires_flags: set[str] = set()
    sets_flags: set[str] = set()
    clears_flags: set[str] = set()
    corrupts: bool = False


class Problem(BaseModel):
    states: set[str]
    flags: set[str] = set()
    transitions: list[Transition]
    start_state: str
    goal_state: str


class VerifyResult(BaseModel):
    passed: bool
    reason: str | None = None
    step: int | None = None

    def __bool__(self) -> bool:
        return self.passed


class Solution(BaseModel):
    actions: list[str]
