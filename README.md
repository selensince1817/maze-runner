# Maze Runner – Optimal & Safe Software Traversal

## Overview

A scalable synthetic task family for evaluating LLM agents on structured navigation with prerequisites and safety constraints.

The core idea is to model "software use" as a **finite-state interface** with:

- **States** are screens or application views
- **Transitions** are actions available from a given screen
- **Flags** are latent configuration state (e.g. `email_verified`, `2fa_enabled`) that must be set before certain transitions are allowed
- **Clears** – some transitions reset flags, requiring the agent to redo setup (soft-destructive)
- **Corrupts** – some transitions cause immediate, irreversible failure and must be avoided entirely (hard-destructive)

The agent receives the full graph and must output an ordered action sequence that reaches the goal state while satisfying all flag prerequisites and avoiding corrupting actions.

This isolates three specific failure modes in a verifiable, scalable way:


| Failure mode          | How it's tested                                               |
| --------------------- | ------------------------------------------------------------- |
| Prerequisite ordering | Transitions with `requires_flags`                             |
| Soft consequences     | Noise transitions with `clears_flags` that undo earlier setup |
| Irreversible actions  | Plausible-looking transitions marked `corrupts = true`        |


**Performance range:** Evaluated on `google/gemini-3-flash-preview` via OpenRouter, pass rate ranges from **78% down to 14%** – within the 10–90% target band on most settings and importantly non-trivial / non-impossible overall. The model handles simple prerequisite chains reliably but degrades sharply as flag depth, noise, and destructive action density increase.

**Why it's a good training target**: benchmark targets a specific functional slice of LLM agent competence: goal-directed traversal (near-optimal action sequencing in a structured graph) and non-destructiveness (avoiding irreversible actions). These are partially separable from general language ability or UI-comprehension. The abstraction is deliberately schema-first so new software profiles can be authored by varying structural parameters and tailoring generation style rather than building a UI simulator/trainer for LLMs. 

The environment yields three training-relevant signals:

- **Accuracy:** Did the agent reach the goal without violating constraints?
- **Efficiency:** How close is the path to BFS-optimal?
- **Safety:** Did it avoid corrupting actions and unnecessary flag resets?

These map naturally to dense reward shaping: distance-to-goal provides continuous signal, flag violations give intermediate penalties for step-PRM, and corruption gives a sharp penalty. This is the reward structure needed to train more optimal and safer LLM agents for agentic software-use.

**Note:** state/action names are intentionally generic to measure navigation and planning, not memorization of UI-specific semantics.

---

## Synthetic data generation

Each problem is generated in three stages:

**1. Create solvable golden path**
A chain of `N` shuffled states is created with a guaranteed path from `start_state` to `goal_state`. For each flag in the flag universe, a random early transition on this path sets it, and a random later transition requires it – ensuring the backbone path is always solvable.

**2. Add noise transitions**
Additional random transitions are added between arbitrary states. These increase the search space and create misleading paths. Soft-destructive (`clears_flags`) and hard-destructive (`corrupts`) properties are assigned exclusively to noise transitions, so the backbone path remains safe.

**3. Validate via BFS and filter for difficulty**
After generation, BFS is run over the full product state space `(current_screen, active_flags)` to confirm solvability and compute the optimal path length. Problems outside a specified step range are discarded and regenerated. This decouples generation from difficulty control.

Problems are stored as JSONL, one JSON object per line.

**What a problem looks like as a training example:**
Each problem is an `(input, label)` pair. The **input** is a system prompt describing the rules plus a user message containing the start state, goal state, available flags, and the full transition graph. The **golden label** is the BFS-optimal action sequence. The verifier provides a binary pass/fail signal plus a structured failure reason (missing flag, corrupting action, wrong terminal state).

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

The project maps to the spec deliverables as follows:

| Spec deliverable | This project                              |
| ---------------- | ----------------------------------------- |
| `generate.py`    | `src/fsm_navigator/generator.py` + `cli gen` command   |
| `verify.py`      | `src/fsm_navigator/verifier.py` (BFS solver + solution checker) |
| `evaluate.py`    | `src/fsm_navigator/evaluator.py` + `cli eval` command  |
| `problems.jsonl` | `data/problems.jsonl`, `data/gmail.jsonl`, `data/linear.jsonl`, `data/aws_console.jsonl` |

All entry points are exposed through a single CLI: `python -m src.fsm_navigator.cli`.

---

## Usage

**Generate problems**

```bash
uv run python -m src.fsm_navigator.cli gen \
  --num-problems 20 \
  --max-states 8 \
  --max-transitions 12 \
  --max-flags 3 \
  --max-clears 2 \
  --num-corrupts 1 \
  --min-steps 3 \
  --max-steps 8 \
  --output-dir data/problems.jsonl
```

**Evaluate a model**

```bash
uv run python -m src.fsm_navigator.cli eval --problems data/problems.jsonl --n 5
```

Output per problem includes pass rate, average steps on passing vs failing trials, and overhead vs BFS optimal.

**Verify problems are solvable (optional)**

```bash
uv run python -m src.fsm_navigator.cli check --problems data/problems.jsonl
```

---

## Difficulty profiles

Profiles are parameter presets that structurally approximate real software workflows – not pixel-level simulations, but rough emulations of screen count, branching, prerequisite depth, and destructive action density.


| Profile     | States | Transitions | Flags | Clears | Corrupts | Difficulty |
| ----------- | ------ | ----------- | ----- | ------ | -------- | ---------- |
| Gmail       | 8      | 14          | 1     | 1      | 1        | Easy       |
| Linear      | 14     | 19          | 3     | 1      | 0        | Medium     |
| AWS Console | 22     | 32          | 8     | 5      | 2        | Hard       |


**Generate each profile:**

```bash
# Gmail: easy
uv run python -m src.fsm_navigator.cli gen \
  --num-problems 10 --max-states 8 --max-transitions 14 \
  --max-flags 1 --max-clears 1 --num-corrupts 1 \
  --output-dir data/gmail.jsonl

# Linear - medium
uv run python -m src.fsm_navigator.cli gen \
  --num-problems 10 --max-states 14 --max-transitions 19 \
  --max-flags 3 --max-clears 1 --num-corrupts 0 \
  --output-dir data/linear.jsonl

# AWS Console - hard
uv run python -m src.fsm_navigator.cli gen \
  --num-problems 10 --max-states 22 --max-transitions 32 \
  --max-flags 8 --max-clears 5 --num-corrupts 2 \
  --output-dir data/aws_console.jsonl
```

---

## Results

Evaluated on `google/gemini-3-flash-preview` via OpenRouter, 20 trials per problem:

| Profile     | Pass Rate | Avg Optimal Path | Step Overhead |
| ----------- | --------- | ---------------- | ------------- |
| Gmail       | 78%       | 2.2 steps        | +1.45 steps   |
| Linear      | 66%       | 4.9 steps        | +3.63 steps   |
| AWS Console | 14%       | 7.6 steps        | +11.9 steps   |

The model handles shallow prerequisite chains (Gmail) reasonably well but degrades sharply as flag depth and destructive action density increase (AWS Console). This confirms the task sits firmly in the 10–90% target range and scales with structural complexity.

![results](Code_Generated_Image.png)
