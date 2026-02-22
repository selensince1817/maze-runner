from collections import deque

from src.fsm_navigator.types import Problem, VerifyResult


def verify_problem(problem: Problem, solution: list[str]) -> VerifyResult:
    current_state = problem.start_state
    active_flags: set[str] = set()

    for i, action in enumerate(solution):
        transition = next(
            (t for t in problem.transitions if t.from_state == current_state and t.action == action),
            None,
        )
        if transition is None:
            return VerifyResult(
                passed=False,
                reason=f"no transition '{action}' from '{current_state}'",
                step=i,
            )
        missing = transition.requires_flags - active_flags
        if missing:
            return VerifyResult(
                passed=False,
                reason=f"missing flags {sorted(missing)} for '{action}'",
                step=i,
            )
        if transition.corrupts:
            return VerifyResult(
                passed=False,
                reason=f"'{action}' corrupts — terminal failure",
                step=i,
            )

        current_state = transition.to_state
        active_flags |= transition.sets_flags
        active_flags -= transition.clears_flags

    if current_state != problem.goal_state:
        return VerifyResult(
            passed=False,
            reason=f"ended at '{current_state}', not goal '{problem.goal_state}'",
            step=len(solution),
        )

    return VerifyResult(passed=True)


def solve_bfs(problem: Problem) -> list[str] | None:
    """Return the shortest valid action sequence, or None if unsolvable."""
    start = (problem.start_state, frozenset())
    queue: deque[tuple[tuple[str, frozenset], list[str]]] = deque([(start, [])])
    visited: set[tuple[str, frozenset]] = {start}

    while queue:
        (state, flags), path = queue.popleft()

        if state == problem.goal_state:
            return path

        for t in problem.transitions:
            if t.from_state != state:
                continue
            if t.corrupts:
                continue
            if not t.requires_flags.issubset(flags):
                continue

            next_flags = frozenset((flags | t.sets_flags) - t.clears_flags)
            next_node = (t.to_state, next_flags)

            if next_node not in visited:
                visited.add(next_node)
                queue.append((next_node, path + [t.action]))

    return None
