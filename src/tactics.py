from __future__ import annotations


def game_state(score_difference: int) -> str:
    if score_difference > 0:
        return f"Ahead by {score_difference}"
    if score_difference < 0:
        return f"Trailing by {abs(score_difference)}"
    return "Tied"


def tactical_options(
    star_name: str,
    score_difference: int,
    seconds: int,
    scenario: str,
    objective: str,
    candidate_name: str | None = None,
) -> list[dict[str, str]]:
    candidate = candidate_name or "a teammate"
    state = game_state(score_difference)
    clock_prefix = "Quick" if seconds <= 5 else "Read"

    if scenario == "Star double-teamed":
        actions = [
            (f"Release to {candidate}",
             f"If a real second defender commits to {star_name}, a quick release is worth discussing. {candidate} is a candidate to evaluate, not a guaranteed open shooter."),
            ("Off-ball screen",
             f"A teammate can move before {star_name} gives up the ball. The court route is illustrative; no passing lane is observed."),
            (f"Keep {star_name} first",
             "If pressure is not committed, keep the ball handler involved and read the actual coverage rather than forcing a pass."),
        ]
    elif scenario == "Paint crowded":
        actions = [
            (f"Move, evaluate {candidate}",
             f"An off-ball action may change the defensive picture around {star_name}. Gravity makes {candidate} worth evaluating, but does not prove an open shot."),
            (f"Screen: {('perimeter' if objective == 'Need 3 points' else 'rim')} read",
             "This is a hypothetical action concept. Defensive positions and a clear lane are not in the data."),
            ("Reset the spacing",
             f"Move {star_name} away from the hypothetical crowd before making a new read. No measured play is shown."),
        ]
    else:
        actions = [
            (f"First read: {star_name}",
             "React to the coverage actually seen on court; this dashboard does not observe today's defense."),
            ("Off-ball movement",
             f"A screen or cut can change the defensive picture. Consider {candidate} for evaluation only; Gravity is not shooting efficiency."),
            (f"Action if {('help shifts' if objective == 'Need 3 points' else 'paint loads')}",
             f"Keep a teammate available if the defense shifts toward {star_name}. Historical Gravity does not establish an open pass."),
        ]

    if objective == "Need 3 points":
        objective_note = "The objective is three points, so the options foreground perimeter-oriented reads; no attempt or make is predicted."
    else:
        objective_note = "The objective is two points, so the options foreground rim-oriented reads; no attempt or make is predicted."
    if score_difference > 0:
        score_note = f"The team is ahead by {score_difference}; preserve decision quality while meeting the selected objective."
    elif score_difference < 0:
        score_note = f"The team trails by {abs(score_difference)}; the selected objective frames the discussion, not a guaranteed way to catch up."
    else:
        score_note = "The score is tied; the selected objective frames the discussion."
    state_note = f"{score_note} Clock: {seconds} seconds. {objective_note}"

    options = actions if objective == "Need 3 points" else [actions[1], actions[2], actions[0]]
    if seconds <= 5 and score_difference > 0:
        patient = next((option for option in options if any(term in option[0].lower() for term in ("keep", "reset", "first read"))), None)
        if patient:
            options = [patient] + [option for option in options if option is not patient]
    elif seconds <= 5:
        options = [options[0], options[2], options[1]]
    return [
        {
            "title": f"{clock_prefix}: {title}",
            "why": f"{why} {state_note}",
            "risk": "Requires a read of the actual defense. No open player, passing lane, shot quality, or outcome is inferred.",
        }
        for title, why in options
    ]