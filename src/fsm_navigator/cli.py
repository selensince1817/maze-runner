from pathlib import Path
import typer

from src.fsm_navigator.types import Problem
from src.fsm_navigator.generator import generate_problem
from src.fsm_navigator.evaluator import evaluate
from src.fsm_navigator.verifier import verify_problem, solve_bfs

app = typer.Typer()


def _problem_summary(p: Problem) -> str:
    n_corrupt = sum(1 for t in p.transitions if t.corrupts)
    n_clears = sum(1 for t in p.transitions if t.clears_flags)
    parts = [
        f"{len(p.states)} states",
        f"{len(p.transitions)} transitions",
        f"{len(p.flags)} flags",
    ]
    if n_corrupt:
        parts.append(f"{n_corrupt} corrupt")
    if n_clears:
        parts.append(f"{n_clears} clears")
    return ", ".join(parts)


@app.command()
def gen(
    num_problems: int = 10,
    max_states: int = 5,
    max_transitions: int = 8,
    max_flags: int = 3,
    max_clears: int = 2,
    num_corrupts: int = 1,
    min_steps: int = 1,
    max_steps: int = 0,
    output_dir: str = "data/problems.jsonl",
):
    """Generate FSM navigation problems.

    Use --min-steps / --max-steps to filter by BFS optimal path length.
    --max-steps 0 means no upper limit.
    """
    Path(output_dir).parent.mkdir(parents=True, exist_ok=True)
    accepted = 0
    attempts = 0
    total_steps = 0
    with open(output_dir, "w") as f:
        while accepted < num_problems:
            attempts += 1
            p = generate_problem(max_states, max_transitions, max_flags, max_clears, num_corrupts)
            solution = solve_bfs(p)
            if solution is None:
                continue
            steps = len(solution)
            if steps < min_steps:
                continue
            if max_steps > 0 and steps > max_steps:
                continue
            f.write(p.model_dump_json() + "\n")
            accepted += 1
            total_steps += steps
            mean = total_steps / accepted
            typer.echo(f"  [{accepted}/{num_problems}] {p.start_state} → {p.goal_state}  ({_problem_summary(p)}, optimal {steps} steps, mean {mean:.1f})")
    typer.echo(f"Wrote {num_problems} problems to {output_dir}  ({attempts} generated, mean optimal {total_steps/num_problems:.1f} steps)")


@app.command()
def eval(
    problems: str = "data/problems.jsonl",
    n: int = 20,
):
    """Evaluate LLM on FSM navigation problems."""
    with open(problems) as f:
        lines = f.readlines()

    total_pass = 0
    total_trials = 0

    for idx, line in enumerate(lines):
        p = Problem.model_validate_json(line)
        optimal = solve_bfs(p)
        optimal_steps = len(optimal) if optimal is not None else None
        optimal_str = f"optimal {optimal_steps} steps" if optimal_steps is not None else "unsolvable"
        typer.echo(f"\nProblem {idx+1}/{len(lines)}: {p.start_state} → {p.goal_state}  ({_problem_summary(p)}, {optimal_str})")
        rate = evaluate(p, n, optimal_steps=optimal_steps)
        total_pass += int(rate * n)
        total_trials += n

    if len(lines) > 1:
        typer.echo(f"\nOverall: {total_pass}/{total_trials} ({total_pass/total_trials:.0%})")


@app.command()
def check(
    problems: str = "data/problems.jsonl",
):
    """Verify generated problems are solvable using BFS."""
    ok_count = 0
    with open(problems) as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        p = Problem.model_validate_json(line)
        solution = solve_bfs(p)
        if solution is not None:
            typer.echo(f"  Problem {i+1}: ✓  optimal {len(solution)} steps")
            ok_count += 1
        else:
            typer.echo(f"  Problem {i+1}: ✗  unsolvable")

    typer.echo(f"{ok_count}/{len(lines)} valid")


if __name__ == "__main__":
    app()
