import random

from src.fsm_navigator.types import Problem, Transition

SYSTEM_PROMPT = """You are an AI agent navigating a state machine.
You must find a sequence of actions to reach the goal state from the start state.

Rules:
- Transitions can require flags: you must have those flags set before the transition is allowed.
- Transitions can set flags (enabling later steps) or clear flags (soft-destructive: you lose progress and may need to redo setup).
- Some transitions are corrupting: taking them causes immediate, irreversible failure. Do not take them.
- Plan so you set required flags before using transitions that need them, and avoid any corrupting action.

Respond with only the list of actions in order."""


def format_transition(t: Transition) -> str:
    base = f"  {t.from_state} --[{t.action}]--> {t.to_state}"
    if t.requires_flags:
        base += f"  (requires: {', '.join(sorted(t.requires_flags))})"
    if t.sets_flags:
        base += f"  (sets: {', '.join(sorted(t.sets_flags))})"
    if t.clears_flags:
        base += f"  (clears: {', '.join(sorted(t.clears_flags))})"
    if t.corrupts:
        base += "  [CORRUPTS]"
    return base


def build_messages(problem: Problem) -> list[dict]:
    shuffled = problem.transitions.copy()
    random.shuffle(shuffled)
    transitions = "\n".join(format_transition(t) for t in shuffled)
    flags_str = ", ".join(sorted(problem.flags)) if problem.flags else "(none)"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Start state: {problem.start_state}
Goal state: {problem.goal_state}
Flags: {{{flags_str}}}

Available transitions:
{transitions}

Return the sequence of actions to reach the goal state.""",
        },
    ]
