import random

from src.fsm_navigator.types import Problem, Transition


def generate_problem(
    max_states: int,
    max_transitions: int,  # TODO(rv): misnomer — doesn't cap total transitions; total = (max_states-1) + int(this * 0.7)
    max_flags: int,
    max_clears: int,  # TODO(rv): silently under-delivers — set.add deduplicates, so effective clears < max_clears
    num_corrupts: int,  # TODO(rv): silently under-delivers when num_corrupts > len(noise_transitions)
) -> Problem:
    # TODO(rv): add guard — max_states < 2 causes IndexError (0) or degenerate problem (1)
    states = [f"state_{i}" for i in range(max_states)]
    random.shuffle(states)

    start_state = states[0]
    goal_state = states[-1]

    # Golden route
    transitions = []
    for i in range(len(states) - 1):
        transitions.append(
            Transition(
                from_state=states[i],
                action=f"action_{i}",
                to_state=states[i + 1],
            )
        )

    # extra transitions (noise)
    max_extra_transitions = int(max_transitions * 0.7) # TODO: Define it in config.py, calibrate it.
    for i in range(max_extra_transitions):
        from_state_rand, to_state_rand = random.sample(states, k=2) # Doesn't return duplicates
        transitions.append(
            Transition(
                from_state=from_state_rand,
                action=f"action_{i + len(states) - 1}",
                to_state=to_state_rand,
            )
        )

    golden_count = len(states) - 1
    noise_transitions = transitions[golden_count:]

    # TODO(rv): sets_flags and requires_flags are exclusive to golden transitions — fingerprints the golden path.
    # Flags are decorative: walking golden in order auto-satisfies all requires. No planning challenge.
    # v2: scatter sets_flags onto noise too; place requires on non-golden edges to force real flag reasoning.
    flags = {f"flag_{i}" for i in range(max_flags)}
    for flag in flags:
        if golden_count == 0: # TODO: Move the guard up to the top of the loop (raise ValueError if max_states < 2).
            continue
        set_idx = random.randint(0, golden_count - 1) # TODO: Major: allow mapping from golden path to noise transitions sets!
        transitions[set_idx].sets_flags.add(flag)
        if golden_count >= 2 and set_idx < golden_count - 1:
            require_idx = random.randint(set_idx + 1, golden_count - 1)
            transitions[require_idx].requires_flags.add(flag)

    # TODO(rv): noise transitions never have requires_flags, so clean noise shortcuts are zero-risk.
    # No transition is simultaneously dangerous and necessary — risk/reward tradeoff doesn't exist.
    if noise_transitions and flags:
        for _ in range(max_clears):
            t = random.choice(noise_transitions)
            t.clears_flags.add(random.choice(list(flags)))

    # hard destructive: mark num_corrupts noise transitions as corrupts
    if noise_transitions:
        corrupt_candidates = noise_transitions.copy()
        random.shuffle(corrupt_candidates) # TODO: Redundant
        for t in corrupt_candidates[:num_corrupts]:
            t.corrupts = True

    return Problem(
        states=set(states),
        flags=flags,
        transitions=transitions,
        start_state=start_state,
        goal_state=goal_state,
    )
