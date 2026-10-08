from __future__ import annotations

import math

import plotly.graph_objects as go


COURT = "#17171d"
LINES = "#b95b36"
OFFENSE = "#ff5c18"
DEFENSE = "#66D9CB"
STAR = "#fff5ef"


def _arc(cx: float, cy: float, radius: float, start: float, end: float, points: int = 80) -> tuple[list[float], list[float]]:
    angles = [start + (end - start) * index / (points - 1) for index in range(points)]
    return ([cx + radius * math.cos(angle) for angle in angles],
            [cy + radius * math.sin(angle) for angle in angles])


def build_court(
    option_index: int = 0,
    scenario: str = "Normal coverage",
    offensive_names: list[str] | None = None,
    star_name: str | None = None,
    candidate_name: str | None = None,
) -> go.Figure:
    """Draw a hypothetical half-court setup; no tracking positions are implied."""
    figure = go.Figure()

    def line(x: list[float], y: list[float], width: int = 2) -> None:
        figure.add_trace(go.Scatter(x=x, y=y, mode="lines", line={"color": LINES, "width": width}, hoverinfo="skip", showlegend=False))

    line([0, 50, 50, 0, 0], [0, 0, 47, 47, 0])
    line([17, 17, 33, 33], [0, 19, 19, 0])
    x, y = _arc(25, 19, 6, 0, math.pi * 2)
    line(x, y)
    x, y = _arc(25, 5.25, 22.15, 0.25, math.pi - 0.25)
    line(x, y)
    x, y = _arc(25, 5.25, 4, 0, math.pi)
    line(x, y)
    x, y = _arc(25, 5.25, 0.75, 0, math.pi * 2, 30)
    line(x, y)
    line([22, 28], [4.3, 4.3], 3)

    offense_sets = [
        [(25, 31), (8, 22), (42, 22), (12, 8), (38, 8)],
        [(25, 34), (9, 24), (41, 28), (12, 9), (37, 13)],
        [(25, 29), (10, 19), (40, 22), (15, 8), (35, 11)],
    ]
    defense_sets = {
        "Star double-teamed": [(22, 30), (28, 30), (16, 18), (34, 18)],
        "Paint crowded": [(21, 13), (29, 13), (18, 9), (32, 9)],
        "Normal coverage": [(18, 25), (32, 23), (19, 11), (31, 10)],
    }
    offense = offense_sets[option_index % len(offense_sets)]
    names = offensive_names or ["Star", "Offense 2", "Offense 3", "Offense 4", "Offense 5"]
    names = (names + [f"Lineup slot {index}" for index in range(len(names) + 1, 6)])[:5]
    labels = [f"O{index + 1}<br>{name}" for index, name in enumerate(names)]
    labels[0] = f"STAR<br>{star_name or names[0]}"
    figure.add_trace(go.Scatter(
        x=[point[0] for point in offense], y=[point[1] for point in offense],
        mode="markers+text", text=labels,
        textposition="top center", textfont={"color": "#f7f6f4", "size": 10},
        marker={"size": [21, 15, 15, 15, 15], "color": [STAR, OFFENSE, OFFENSE, OFFENSE, OFFENSE], "line": {"color": "#fff5ef", "width": 1}},
        name="Hypothetical offense", hovertemplate="Hypothetical position: %{text}<extra></extra>",
    ))
    defense = defense_sets.get(scenario, defense_sets["Normal coverage"])
    figure.add_trace(go.Scatter(
        x=[point[0] for point in defense], y=[point[1] for point in defense],
        mode="markers+text", text=["D1", "D2", "D3", "D4"], textposition="middle center",
        textfont={"color": "#0b2825", "size": 8},
        marker={"size": 19, "color": DEFENSE, "line": {"color": "#d8fff8", "width": 1}},
        name="Hypothetical defense", hovertemplate="Generic hypothetical defender; not observed<extra></extra>",
    ))

    star_position = offense[0]
    target_index = next(
        (index for index, name in enumerate(names) if candidate_name and (name == candidate_name or name.startswith(f"{candidate_name} #"))),
        1,
    )
    if option_index % 3 == 0:
        start, target = star_position, offense[target_index]
    elif option_index % 3 == 1:
        start, target = offense[min(2, len(offense) - 1)], (25, 25)
    else:
        start, target = star_position, (25, 17)
    figure.add_annotation(
        x=target[0], y=target[1], ax=start[0], ay=start[1],
        xref="x", yref="y", axref="x", ayref="y", showarrow=True,
        arrowhead=3, arrowsize=1.25, arrowwidth=3, arrowcolor=OFFENSE,
        text="illustrative route", font={"color": "#ffd5c3", "size": 9},
    )
    figure.update_layout(
        height=540, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=COURT,
        margin={"l": 12, "r": 12, "t": 12, "b": 12},
        xaxis={"range": [-1, 51], "visible": False, "constrain": "domain"},
        yaxis={"range": [-1, 48], "visible": False, "scaleanchor": "x", "scaleratio": 1},
        showlegend=False, dragmode=False,
    )
    return figure