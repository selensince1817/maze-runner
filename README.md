# Maze Runner - Optimal & Safe Software Traversal

A scalable synthetic task family for evaluating LLM agents on structured navigation with prerequisites and safety constraints. The core idea is to model "software use" as a **finite-state interface**:

- **States** - screens or application views
- **Transitions** - actions available from a given screen
- **Flags** - latent configuration state (e.g. `email_verified`, `2fa_enabled`) that must be set before certain transitions are allowed
- **Clears** - some transitions reset flags, requiring the agent to redo setup (soft-destructive)
- **Corrupts** - some transitions cause immediate, irreversible failure (hard-destructive)

**The agent receives the full graph and must output an ordered action sequence that reaches the goal state while satisfying all flag prerequisites and avoiding corrupting actions.**

| Failure mode          | How it's tested                                               |
| --------------------- | ------------------------------------------------------------- |
| Prerequisite ordering | Transitions with `requires_flags`                             |
| Soft consequences     | Noise transitions with `clears_flags` that undo earlier setup |
| Irreversible actions  | Plausible-looking transitions marked `corrupts = true`        |

**Performance:** Evaluated on `google/gemini-3-flash-preview` via OpenRouter, pass rate ranges from **78% down to 14%** — within the 10-90% target band. The model handles simple prerequisite chains reliably but degrades sharply as flag depth, noise, and destructive action density increase.

**Why it's a good training target:** The benchmark isolates goal-directed traversal and non-destructiveness — partially separable from general language ability. The abstraction is schema-first so new software profiles can be authored by varying structural parameters rather than building a UI simulator. The verifier yields three training signals (accuracy, efficiency vs BFS-optimal, safety) that map naturally to dense reward shaping for RLVR or filtered SFT.

*Note: state/action names are intentionally generic to measure navigation and planning, not memorization of UI-specific semantics.*

---

## Synthetic data generation

Each problem is generated in three stages:

1. **Golden path**  A chain of `N` shuffled states with a guaranteed path from start to goal. Flags are set on early transitions and required on later ones, ensuring the backbone is always solvable.
2. **Noise transitions** - Random transitions between arbitrary states that increase the search space. `clears_flags` and `corrupts` are assigned exclusively to noise, so the backbone stays safe.
3. **BFS validation** - BFS over the full product state space `(screen, active_flags)` confirms solvability and computes optimal path length. Problems outside a specified step range are discarded.

Each problem is an `(input, label)` pair. The **input** is a system prompt plus the start/goal states, flags, and transition graph. The **golden label** is the BFS-optimal action sequence. The verifier provides pass/fail plus a structured failure reason (missing flag, corrupting action, wrong terminal state).

---

## Installation

Requires Python 3.12+. Uses [uv](https://github.com/astral-sh/uv) for dependencies.

```bash
uv sync
```

Add your OpenRouter API key to a `.env` file:

```
OPENROUTER_API_KEY=
```

---

## Project structure

| Spec deliverable | This project                                                    |
| ---------------- | --------------------------------------------------------------- |
| `generate.py`    | `src/fsm_navigator/generator.py` + `cli gen` command            |
| `verify.py`      | `src/fsm_navigator/verifier.py` (BFS solver + solution checker) |
| `evaluate.py`    | `src/fsm_navigator/evaluator.py` + `cli eval` command           |
| `problems.jsonl` | `data/problems.jsonl`, `data/gmail.jsonl`, `data/linear.jsonl`, `data/aws_console.jsonl` |

All entry points: `uv run python -m src.fsm_navigator.cli {gen,eval,check}`.

---

## Usage

```bash
# Generate problems
uv run python -m src.fsm_navigator.cli gen \
  --num-problems 20 --max-states 8 --max-transitions 12 \
  --max-flags 3 --max-clears 2 --num-corrupts 1 \
  --min-steps 3 --max-steps 8 --output-dir data/problems.jsonl

# Evaluate a model (n trials per problem)
uv run python -m src.fsm_navigator.cli eval --problems data/problems.jsonl --n 5

# Verify problems are solvable
uv run python -m src.fsm_navigator.cli check --problems data/problems.jsonl
```

---

## Difficulty profiles

Parameter presets that structurally ***approximate*** real software workflows:

| Profile     | States | Transitions | Flags | Clears | Corrupts |
| ----------- | ------ | ----------- | ----- | ------ | -------- |
| Gmail       | 8      | 14          | 1     | 1      | 1        |
| Linear      | 14     | 19          | 3     | 1      | 0        |
| AWS Console | 22     | 32          | 8     | 5      | 2        |

```bash
# Gmail — easy
uv run python -m src.fsm_navigator.cli gen \
  --num-problems 10 --max-states 8 --max-transitions 14 \
  --max-flags 1 --max-clears 1 --num-corrupts 1 \
  --output-dir data/gmail.jsonl

# Linear — medium
uv run python -m src.fsm_navigator.cli gen \
  --num-problems 10 --max-states 14 --max-transitions 19 \
  --max-flags 3 --max-clears 1 --num-corrupts 0 \
  --output-dir data/linear.jsonl

# AWS Console — hard
uv run python -m src.fsm_navigator.cli gen \
  --num-problems 10 --max-states 22 --max-transitions 32 \
  --max-flags 8 --max-clears 5 --num-corrupts 2 \
  --output-dir data/aws_console.jsonl
```

---

## Results

Evaluated on `google/gemini-3-flash-preview`, 20 trials per problem:

| Profile     | Pass Rate | Avg Optimal Path | Step Overhead |
| ----------- | --------- | ---------------- | ------------- |
| Gmail (easy)       | 78%       | 2.2 steps        | +1.45 steps   |
| Linear (medium)      | 66%       | 4.9 steps        | +3.63 steps   |
| AWS Console (hard) | 14%       | 7.6 steps        | +11.9 steps   |

The model handles shallow prerequisite chains (Gmail) well but degrades sharply as flag depth and destructive action density increase (AWS Console) — confirming the task scales with structural complexity and sits in the 1090% target range.

![results](Code_Generated_Image.png)
