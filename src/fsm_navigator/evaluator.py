import instructor
from src.fsm_navigator.types import Solution, Problem
from src.fsm_navigator.config import Config
from src.fsm_navigator.verifier import verify_problem
from src.fsm_navigator.prompts import build_messages

_config: Config | None = None
_client = None


def _get_client():
    global _config, _client
    if _client is None:
        _config = Config()
        _client = instructor.from_provider(
            f"openrouter/{_config.model}",
            api_key=_config.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            async_client=False,
        )
    return _client, _config


def evaluate(problem: Problem, n: int | None = None, optimal_steps: int | None = None) -> float:
    client, config = _get_client()
    n = n or config.num_evaluations
    successes = 0
    marks = []
    failures = []
    pass_steps = []
    fail_steps = []

    for i in range(n):
        try:
            solution = client.create(
                messages=build_messages(problem),
                response_model=Solution,
                extra_body={"provider": {"require_parameters": True}},
            )
            result = verify_problem(problem, solution.actions)
            if result:
                successes += 1
                marks.append("✓")
                pass_steps.append(len(solution.actions))
            else:
                marks.append("✗")
                fail_steps.append(len(solution.actions))
                failures.append((i + 1, result.reason, solution.actions))
        except Exception as e:
            marks.append("E")
            failures.append((i + 1, str(e), []))

    rate = successes / n
    print(f"  {''.join(marks)}")
    print(f"  {successes}/{n} passed ({rate:.0%})")

    if pass_steps:
        avg_pass = sum(pass_steps) / len(pass_steps)
        overhead = f"  (+{avg_pass - optimal_steps:.1f} vs optimal)" if optimal_steps is not None else ""
        print(f"    passing: avg {avg_pass:.1f} steps{overhead}")

    if fail_steps:
        avg_fail = sum(fail_steps) / len(fail_steps)
        print(f"    failing: avg {avg_fail:.1f} steps")

    if failures:
        print(f"  Failures:")
        for trial, reason, _ in failures[:5]:
            print(f"    #{trial}: {reason}")
        if len(failures) > 5:
            print(f"    ... and {len(failures) - 5} more")

    return rate
