from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics import (
    GAME_SPLITS,
    SPLITS,
    game_teammate_candidates,
    game_trend,
    qualified_players,
    split_summary,
    strongest_split,
    teammate_candidates,
)
from src.court_visuals import build_court
from src.data_loader import DATA_DIR, FILES, DataLoadError, load_datasets
from src.tactics import tactical_options


@st.cache_data(show_spinner=False)
def load_cached(data_dir: str, signature: tuple[tuple[str, int, int], ...]) -> dict[str, pd.DataFrame]:
    return load_datasets(Path(data_dir))


def app_css() -> None:
    st.markdown("""
    <style>
    :root {
      --gb-ink: #0b0b0f;
      --gb-panel: #141419;
      --gb-panel-raised: #1b1b22;
      --gb-border: #303037;
      --gb-muted: #aaaab2;
      --gb-orange: #ff5c18;
      --gb-orange-soft: #ff9a69;
      --gb-teal: #55d5c6;
      --gb-white: #f7f6f4;
    }
    html, body, [class*="css"] { font-family: "Avenir Next", "Segoe UI", sans-serif; }
    .stApp {
      color: var(--gb-white);
      background: radial-gradient(ellipse at 82% -10%, #302018 0%, #171419 31%, #0b0b0f 72%);
    }
    [data-testid="stSidebar"] {
      background: #101014;
      border-right: 1px solid #29282d;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }
    h1, h2, h3, .gb-wordmark, .gb-kpi-value {
      font-family: "Avenir Next Condensed", "Arial Narrow", Impact, sans-serif !important;
      letter-spacing: 0 !important;
      font-stretch: condensed;
    }
    h1 { font-size: 2.65rem !important; line-height: 1 !important; }
    h2 { font-size: 1.85rem !important; }
    h3 { font-size: 1.32rem !important; }
    p, label, li { color: #e5e3e1; }
    .gb-brand { display:flex; align-items:center; gap:10px; margin: 0 0 1rem; }
    .gb-mark {
      display:grid; place-items:center; width:38px; height:38px; flex:0 0 38px;
      color:#0b0b0f; background:var(--gb-orange); border-radius:8px;
      font:800 1.1rem "Avenir Next Condensed", "Arial Narrow", sans-serif;
      box-shadow:0 6px 20px #ff5c1838;
    }
    .gb-wordmark { color:#fff; font-size:1.08rem; font-weight:800; line-height:1.05; }
    .gb-wordmark span { color:var(--gb-orange); }
    .gb-kicker { color:var(--gb-orange); font-size:.72rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
    .gb-hero {
      position:relative; overflow:hidden; padding:1.5rem 1.65rem 1.4rem;
      background:linear-gradient(105deg,#1b1718 0%,#141419 58%,#171519 100%);
      border:1px solid #363238; border-left:4px solid var(--gb-orange); border-radius:12px;
      margin:.25rem 0 1rem;
    }
    .gb-hero:after {
      content:"GB"; position:absolute; right:2%; top:-30%; color:#ffffff08;
      font:900 11rem/1 "Avenir Next Condensed", "Arial Narrow", sans-serif;
      transform:skew(-9deg); pointer-events:none;
    }
    .gb-hero h1 { font-size:clamp(2.15rem, 4vw, 3.6rem) !important; margin:.4rem 0 .55rem !important; max-width:820px; }
    .gb-hero h1 span { color:var(--gb-orange); }
    .gb-hero p { color:#cfccd0; margin:0; max-width:760px; font-size:1rem; }
    .gb-card {
      background:linear-gradient(145deg,#1b1b21,#141419); border:1px solid var(--gb-border);
      border-radius:10px; padding:15px 16px; min-height:105px;
      transition:transform .16s ease,border-color .16s ease,background .16s ease;
    }
    .gb-card:hover { transform:translateY(-2px); border-color:#7d432e; background:#1e1b1d; }
    .gb-kpi-label { color:var(--gb-muted); font-size:.72rem; font-weight:700; letter-spacing:.09em; text-transform:uppercase; }
    .gb-kpi-value { color:#fff; font-size:2rem; font-weight:800; line-height:1.1; margin:.25rem 0; }
    .gb-kpi-note { color:#a9a7ad; font-size:.72rem; }
    .gb-insight {
      border:1px solid #43332c; border-left:3px solid var(--gb-orange); border-radius:8px;
      background:#1c1716; padding:13px 15px; margin:.55rem 0 1rem; color:#eee9e6;
    }
    .gb-tag { display:inline-block; border:1px solid #4e805f; border-radius:4px; padding:3px 7px; color:#a7edc4; background:#14231a; font-size:.66rem; font-weight:800; letter-spacing:.08em; }
    .gb-illustration { display:inline-block; border:1px solid #985031; border-radius:4px; padding:3px 7px; color:#ffb28d; background:#2a1a14; font-size:.66rem; font-weight:800; letter-spacing:.08em; }
    .gb-muted { color:var(--gb-muted); font-size:.82rem; }
    .gb-rule { height:1px; background:#302f36; margin:1rem 0; }
    div[data-testid="stTabs"] { margin-top:.8rem; }
    div[data-testid="stTabs"] button { color:#c2c0c5; font-weight:750; }
    div[data-testid="stTabs"] button[aria-selected="true"] { color:#fff; border-bottom-color:var(--gb-orange) !important; }
    div[data-testid="stTabs"] button:hover { color:var(--gb-orange-soft); }
    div[data-testid="stMetric"] { background:#17171d; border:1px solid #33323a; border-radius:8px; padding:10px 12px; }
    div[data-testid="stAlert"] { border-radius:8px; }
    .stSelectbox label, .stSlider label, .stRadio label { color:#d5d2d0 !important; }
    @media(max-width:760px) {
      .gb-hero { padding:1.15rem 1.1rem; }
      .gb-hero:after { font-size:7rem; right:-2%; top:4%; }
      h1 { font-size:2rem !important; }
      .gb-card { min-height:90px; padding:12px; }
    }
    </style>
    """, unsafe_allow_html=True)


def display_number(value: object, digits: int = 1) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value:.{digits}f}"


def metric_card(label: str, value: str, note: str) -> None:
    st.markdown(
        f'<div class="gb-card"><div class="gb-kpi-label">{label}</div>'
        f'<div class="gb-kpi-value">{value}</div><div class="gb-kpi-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def base_figure(figure: go.Figure, y_title: str = "Gravity score") -> go.Figure:
    figure.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#dedbdd", "family": "Avenir Next, sans-serif", "size": 12},
        margin={"l": 12, "r": 12, "t": 32, "b": 34},
        xaxis_title="", yaxis_title=y_title,
        legend_title_text="", hoverlabel={"bgcolor": "#17171d", "font_color": "#fff"},
    )
    figure.update_xaxes(showgrid=False, linecolor="#444149", zeroline=False)
    figure.update_yaxes(gridcolor="#302f36", zerolinecolor="#77737a")
    return figure


def split_figure(player: pd.Series, min_frames: int) -> tuple[pd.DataFrame, go.Figure]:
    summary = split_summary(player, min_frames)
    summary["Sample"] = summary["Reliable sample"].map({True: "Threshold met", False: "Low / missing sample"})
    summary["Frames label"] = summary["Frames"].map(lambda value: "N/A" if pd.isna(value) else f"{int(value):,}")
    figure = px.bar(
        summary, x="Situation", y="Gravity", color="Sample",
        color_discrete_map={"Threshold met": "#ff5c18", "Low / missing sample": "#777078"},
        custom_data=["Frames label"],
    )
    figure.add_hline(y=0, line_color="#77737a", line_width=1)
    figure.update_traces(hovertemplate="%{x}<br>Gravity: %{y:.1f}<br>Frames: %{customdata[0]}<extra></extra>")
    base_figure(figure)
    figure.update_layout(barmode="group", margin={"l": 12, "r": 12, "t": 14, "b": 38}, xaxis_tickangle=-12)
    return summary, figure


def strongest_candidate(player: pd.Series, season: pd.DataFrame, min_frames: int) -> tuple[pd.Series | None, str | None, float | None, int | None]:
    teammates = teammate_candidates(player, season, min_frames)
    choices = []
    for _, row in teammates.iterrows():
        for label, value_column, frames_column in (
            ("Off-ball perimeter", "offBallPerimeter_Gravity", "offBallPerimeter_Frames"),
            ("Off-ball interior", "offBallInterior_Gravity", "offBallInterior_Frames"),
        ):
            value, frames = row.get(value_column), row.get(frames_column)
            if pd.notna(value) and pd.notna(frames) and frames >= min_frames and value > 0:
                choices.append((row, label, float(value), int(frames)))
    if not choices:
        return None, None, None, None
    choices.sort(key=lambda item: (item[2], item[3]), reverse=True)
    return choices[0]


def render_war_room(data: dict[str, pd.DataFrame] | None, error: str | None, player: pd.Series | None, team_name: str, opponent_name: str, min_frames: int) -> None:
    st.markdown(
        '<section class="gb-hero"><div class="gb-kicker">WNBA COACHING INTELLIGENCE / 2026</div>'
        '<h1>THE GAME HAS GRAVITY.<br><span>NOW YOU CAN SEE IT.</span></h1>'
        '<p>Explore defensive attention, uncover hidden offensive threats, and build smarter basketball strategies.</p></section>',
        unsafe_allow_html=True,
    )
    if data is None or player is None:
        st.warning("Real scouting data is not available. Add the four event CSVs to `data/` to enable player insights.")
        st.caption(error or "No season player is selected.")
        return

    name = player["Display_Name"]
    st.markdown(f'<span class="gb-tag">REAL DATA</span> &nbsp; <span class="gb-muted">{team_name} scouting context / scenario opponent: {opponent_name}</span>', unsafe_allow_html=True)
    st.markdown('<div class="gb-rule"></div>', unsafe_allow_html=True)
    metrics = st.columns(4)
    with metrics[0]:
        metric_card("Primary player", name, f"{player.get('Team_Abbreviation', 'N/A')} / selected in War Room")
    with metrics[1]:
        metric_card("Season Gravity", display_number(player.get("Gravity")), "Equal-weighted game average")
    with metrics[2]:
        metric_card("Scoring", display_number(player.get("PPG")), "Points per game")
    with metrics[3]:
        metric_card("Creation", display_number(player.get("APG")), "Assists per game")

    summary, chart = split_figure(player, min_frames)
    left, right = st.columns([1.35, 1])
    with left:
        st.subheader("Featured scouting signal")
        st.plotly_chart(chart, width="stretch", config={"displayModeBar": False}, key="war_room_splits")
    with right:
        best = strongest_split(summary)
        if best:
            split = summary.loc[summary["Situation"] == best].iloc[0]
            st.markdown(f'<div class="gb-insight"><b>{name}</b> records the strongest reliable pull in <b>{best}</b>: {split["Gravity"]:+.1f} Gravity across {int(split["Frames"]):,} frames.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="gb-insight">No situation split clears the current frame threshold. Treat the profile as incomplete rather than ranking sparse samples.</div>', unsafe_allow_html=True)
        candidate, candidate_split, value, frames = strongest_candidate(player, data["season"], min_frames)
        if candidate is not None:
            st.markdown(f'<div class="gb-insight"><b>Teammate to evaluate:</b> {candidate["Display_Name"]} shows {value:+.1f} off-ball Gravity in {candidate_split} across {frames:,} frames. This is an attention signal, not proof of an open shot.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="gb-insight">No teammate off-ball split currently has both positive Gravity and enough frames for a closer-look flag.</div>', unsafe_allow_html=True)

    st.caption(f"Gravity is historical defensive attention relative to expectation. Situation reliability threshold: {min_frames} frames, an analyst-selected setting. Source: `wnba_gravity_season_leaderboards.csv`.")


def render_scout(data: dict[str, pd.DataFrame] | None, player: pd.Series | None, min_frames: int) -> None:
    st.markdown('<div class="gb-kicker">01 / PLAYER PROFILE</div>', unsafe_allow_html=True)
    st.header("Scout the Threat")
    if data is None or player is None:
        st.info("Load the four event CSVs and select a qualified player in the War Room sidebar.")
        return
    st.subheader(f'{player["Display_Name"]}  /  {player["Team_Abbreviation"]}')
    st.markdown('<span class="gb-tag">REAL DATA</span>', unsafe_allow_html=True)
    metric_cols = st.columns(5)
    for column, (label, value, note) in zip(metric_cols, (
        ("Season Gravity", player.get("Gravity"), "Equal-weighted games"),
        ("Frame-weighted", player.get("GravityScoreAvg"), "GravityScoreAvg"),
        ("PPG", player.get("PPG"), "Points per game"),
        ("APG", player.get("APG"), "Assists per game"),
        ("GP / MPG", f'{display_number(player.get("GP"), 0)} / {display_number(player.get("MPG"))}', "Games / minutes per game"),
    )):
        with column:
            metric_card(label, value if isinstance(value, str) else display_number(value), note)

    summary, figure = split_figure(player, min_frames)
    left, right = st.columns([1.35, 1])
    with left:
        st.subheader("Attention by situation")
        st.plotly_chart(figure, width="stretch", config={"displayModeBar": False}, key="scout_splits")
    with right:
        onball = summary.loc[summary["Situation"].str.startswith("On-ball") & summary["Reliable sample"]]
        offball = summary.loc[summary["Situation"].str.startswith("Off-ball") & summary["Reliable sample"]]
        if not onball.empty and not offball.empty:
            on_mean, off_mean = onball["Gravity"].mean(), offball["Gravity"].mean()
            st.markdown(f'<div class="gb-insight"><b>On-ball average:</b> {on_mean:+.1f}<br><b>Off-ball average:</b> {off_mean:+.1f}<br><span class="gb-muted">Only splits meeting {min_frames} frames are included.</span></div>', unsafe_allow_html=True)
        best = strongest_split(summary)
        if best:
            row = summary.loc[summary["Situation"] == best].iloc[0]
            takeaway = f"Bring {best.lower()} into the scouting conversation: {row['Gravity']:+.1f} Gravity over {int(row['Frames']):,} frames."
        else:
            takeaway = "No situation-specific takeaway clears the selected sample threshold."
        st.markdown(f'<div class="gb-insight"><b>Coaching takeaway</b><br>{takeaway}</div>', unsafe_allow_html=True)
        st.dataframe(summary[["Situation", "Gravity", "Frames", "Reliable sample"]], hide_index=True, width="stretch")
    st.caption("Season split source: `wnba_gravity_season_leaderboards.csv`. Positive Gravity means more attention than expected; it does not identify open shooters or passing lanes.")


def render_hidden_hero(data: dict[str, pd.DataFrame] | None, player: pd.Series | None, min_frames: int) -> None:
    st.markdown('<div class="gb-kicker">02 / TEAMMATE DISCOVERY</div>', unsafe_allow_html=True)
    st.header("Hidden Hero")
    st.markdown('<p class="gb-muted">Find teammates who may draw attention away from the ball handler. Gravity is not shooting efficiency.</p>', unsafe_allow_html=True)
    if data is None or player is None:
        st.info("Select a qualified player in the War Room sidebar to compare real teammates.")
        return
    candidates = teammate_candidates(player, data["season"], min_frames)
    if candidates.empty:
        fallback = game_teammate_candidates(str(player["playerId"]), data["games"], data["players"], min_split_frames=min_frames)
        if fallback.empty:
            st.info("No qualified season teammates or reliable historical game-level teammate sample is available.")
            return
        st.markdown('<span class="gb-illustration">LIMITED HISTORICAL SAMPLE</span>', unsafe_allow_html=True)
        st.caption("Teammates are inferred from shared Game_ID and game-level teamId, not current team lookup. The sample may be limited.")
        st.dataframe(fallback, hide_index=True, width="stretch")
        return
    rows = []
    for _, teammate in candidates.iterrows():
        row = {"Teammate": teammate["Display_Name"], "PPG": teammate.get("PPG"), "APG": teammate.get("APG"), "GP": teammate.get("GP")}
        qualified_positive = False
        for label, value_column, frames_column in (
            ("Off-ball perimeter", "offBallPerimeter_Gravity", "offBallPerimeter_Frames"),
            ("Off-ball interior", "offBallInterior_Gravity", "offBallInterior_Frames"),
        ):
            value, frames = teammate.get(value_column), teammate.get(frames_column)
            reliable = pd.notna(value) and pd.notna(frames) and frames >= min_frames
            row[label] = value
            row[f"{label} frames"] = frames
            row[f"{label} sample"] = "Threshold met" if reliable else "Low / missing"
            qualified_positive |= bool(reliable and value > 0)
        row["Read"] = "Potential attention creator" if qualified_positive else "No reliable positive off-ball split"
        rows.append(row)
    table = pd.DataFrame(rows)
    table["Peak off-ball Gravity"] = table[["Off-ball perimeter", "Off-ball interior"]].max(axis=1, skipna=True)
    table = table.sort_values("Peak off-ball Gravity", ascending=False, na_position="last")
    st.markdown(f'<span class="gb-tag">REAL DATA</span> &nbsp; <span class="gb-muted">Teammates joined by Team_ID / sample threshold {min_frames}</span>', unsafe_allow_html=True)
    st.dataframe(table.drop(columns="Peak off-ball Gravity"), hide_index=True, width="stretch", column_config={
        "PPG": st.column_config.NumberColumn(format="%.1f"),
        "APG": st.column_config.NumberColumn(format="%.1f"),
        "Off-ball perimeter": st.column_config.NumberColumn(format="%+.1f"),
        "Off-ball interior": st.column_config.NumberColumn(format="%+.1f"),
    })
    chart_names = [player["Display_Name"]] + table["Teammate"].head(3).tolist()
    comparison = []
    for name in chart_names:
        rows_for_player = pd.DataFrame([player]) if name == player["Display_Name"] else candidates.loc[candidates["Display_Name"] == name]
        if rows_for_player.empty:
            continue
        series = rows_for_player.iloc[0]
        for label, (value_column, frame_column) in SPLITS.items():
            comparison.append({"Player": name, "Situation": label, "Gravity": series.get(value_column), "Frames": series.get(frame_column)})
    chart_data = pd.DataFrame(comparison).dropna(subset=["Gravity"])
    if not chart_data.empty:
        figure = px.bar(chart_data, x="Situation", y="Gravity", color="Player", barmode="group", hover_data=["Frames"], color_discrete_sequence=["#ff5c18", "#55d5c6", "#d5d0cb", "#d9a25b"])
        figure.add_hline(y=0, line_color="#77737a", line_width=1)
        base_figure(figure)
        st.plotly_chart(figure, width="stretch", config={"displayModeBar": False}, key="hidden_hero_comparison")
    st.caption("A positive off-ball split is a reason to investigate defensive attention, not evidence of an open shot. Source: `wnba_gravity_season_leaderboards.csv`.")


def render_clutch(data: dict[str, pd.DataFrame] | None, player: pd.Series | None, opponent_name: str, min_frames: int) -> None:
    st.markdown('<div class="gb-kicker">03 / TACTICAL SANDBOX</div>', unsafe_allow_html=True)
    st.header("Clutch Lab")
    st.markdown('<p class="gb-muted">Coach through a hypothetical possession with real historical attention context.</p>', unsafe_allow_html=True)
    st.markdown('<span class="gb-illustration">TACTICAL ILLUSTRATION</span>', unsafe_allow_html=True)
    if data is None or player is None:
        st.info("Clutch Lab needs a selected player and the four event CSVs for real historical context.")
        return

    teammates = teammate_candidates(player, data["season"], min_frames)
    candidate, candidate_split, candidate_value, candidate_frames = strongest_candidate(player, data["season"], min_frames)
    candidate_name = candidate["Display_Name"] if candidate is not None else None
    star_name = player["Display_Name"]
    st.markdown(f'**{star_name}** / {player["Team_Abbreviation"]} offense  &nbsp; vs scenario context: **{opponent_name}**', unsafe_allow_html=True)
    st.caption("Opponent is a scenario selection only; this dataset does not contain a scheduled matchup. Court positions and defenders are generic and hypothetical.")

    controls = st.columns([1, 1, 1.25, 1.15])
    with controls[0]:
        score = st.slider("Score difference", -3, 3, -2, help="Your team's score minus the opponent's.", key="clutch_score")
    with controls[1]:
        seconds = st.slider("Seconds remaining", 2, 24, 12, key="clutch_seconds")
    with controls[2]:
        scenario = st.selectbox("Defensive scenario", ["Star double-teamed", "Paint crowded", "Normal coverage"], key="clutch_scenario")
    with controls[3]:
        objective = st.radio("Objective", ["Need 2 points", "Need 3 points"], key="clutch_objective")

    options = tactical_options(star_name, score, seconds, scenario, objective, candidate_name)
    option_label = st.radio("Coach's next move", [option["title"] for option in options], key="clutch_option", horizontal=True)
    option_index = next(index for index, option in enumerate(options) if option["title"] == option_label)
    selected_rows = [player]
    if candidate is not None:
        selected_rows.append(candidate)
    for _, teammate in teammates.iterrows():
        if len(selected_rows) == 5:
            break
        if str(teammate["playerId"]) != str(player["playerId"]) and (candidate is None or str(teammate["playerId"]) != str(candidate["playerId"])):
            selected_rows.append(teammate)
    offense_names = []
    for row in selected_rows:
        jersey = row.get("Jersey_Num")
        number = f" #{int(jersey)}" if pd.notna(jersey) else ""
        offense_names.append(f"{row['Display_Name']}{number}")
    while len(offense_names) < 5:
        offense_names.append(f"Lineup slot {len(offense_names) + 1}")
    left, right = st.columns([1.25, 1])
    with left:
        st.plotly_chart(build_court(option_index, scenario, offense_names, star_name, candidate_name), width="stretch", config={"displayModeBar": False}, key="clutch_court")
        st.caption("Lineup labels use qualified season players; placement, arrows, and all defenders are hypothetical. No tracking coordinates are provided.")
    with right:
        selected = options[option_index]
        st.markdown('<div class="gb-kicker">COACH\'S NEXT MOVE</div>', unsafe_allow_html=True)
        st.subheader(selected["title"])
        st.write(selected["why"])
        if candidate is not None:
            st.markdown(f'<div class="gb-insight"><b>Historical evidence:</b> {candidate_name} has {candidate_value:+.1f} off-ball Gravity in {candidate_split} across {candidate_frames:,} frames. Candidate to evaluate, not a proven open shooter.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="gb-insight">No teammate off-ball split clears the selected reliability threshold with positive Gravity.</div>', unsafe_allow_html=True)
        st.warning("These are transparent coaching options, not a validated prediction. Gravity cannot establish an open pass, shot success, exact defender location, or points scored.")


def render_trends(data: dict[str, pd.DataFrame] | None, player: pd.Series | None) -> None:
    st.markdown('<div class="gb-kicker">04 / HISTORICAL PERFORMANCE</div>', unsafe_allow_html=True)
    st.header("Game Trends")
    if data is None or player is None:
        st.info("Select a qualified player in the War Room sidebar to inspect game-level history.")
        return
    threshold = st.slider("Minimum player frames per game", 0, 3000, 500, 100, key="trend_frame_threshold")
    trend = game_trend(str(player["playerId"]), data["games"], threshold)
    st.caption(f'{player["Display_Name"]}: {len(trend)} games meet the {threshold:,}-frame minimum. Game_ID orders the sequence and is not a date.')
    if trend.empty:
        st.info("No rows meet this sample threshold.")
        return
    team_names = data["teams"].set_index("Team_ID")["Team_Abbreviation"].to_dict()
    trend["Inferred opponent"] = trend["Inferred_Opponent_Team_ID"].map(team_names).fillna("Matchup unavailable")
    figure = px.line(trend, x="Game_Sequence", y="averageGravity", markers=True, custom_data=["Game_ID", "frames", "Inferred opponent"], color_discrete_sequence=["#ff5c18"])
    figure.add_hline(y=0, line_color="#77737a", line_width=1)
    figure.update_traces(hovertemplate="Game sequence %{x}<br>Game_ID %{customdata[0]}<br>Average Gravity %{y:.1f}<br>Frames %{customdata[1]:,.0f}<br>Opponent %{customdata[2]}<extra></extra>")
    base_figure(figure, "Average Gravity")
    figure.update_layout(xaxis_title="Game sequence / Game_ID")
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False}, key="game_trend")
    with st.expander("Situation-level history"):
        label = st.selectbox("Situation split", list(GAME_SPLITS), key="trend_split_choice")
        value_column, frame_column = GAME_SPLITS[label]
        minimum = st.number_input("Minimum split frames", min_value=0, value=100, step=25, key="trend_split_threshold")
        if frame_column not in trend:
            st.info("This game file has no split frame counts; reliability cannot be assessed.")
        else:
            eligible = trend.loc[(trend[frame_column] >= minimum) & trend[value_column].notna()]
            if eligible.empty:
                st.info("No situation observations meet the selected frame threshold.")
            else:
                chart = px.line(eligible, x="Game_Sequence", y=value_column, markers=True, custom_data=["Game_ID", frame_column], color_discrete_sequence=["#55d5c6"])
                chart.update_traces(hovertemplate="Sequence %{x}<br>Game_ID %{customdata[0]}<br>Gravity %{y:.1f}<br>Split frames %{customdata[1]:,.0f}<extra></extra>")
                base_figure(chart, "Situation Gravity")
                chart.update_layout(xaxis_title="Game sequence / Game_ID")
                st.plotly_chart(chart, width="stretch", config={"displayModeBar": False}, key="game_trend_situation")


def render_methodology(data: dict[str, pd.DataFrame] | None, min_frames: int) -> None:
    st.markdown('<div class="gb-kicker">05 / TRANSPARENT METHOD</div>', unsafe_allow_html=True)
    st.header("Methodology & limits")
    left, right = st.columns(2)
    with left:
        st.subheader("What Gravity means")
        st.write("Gravity measures actual defensive attention relative to expected attention. Zero is baseline; a positive value indicates more attention than expected. It is not simply defender count, shot difficulty, or shooting efficiency.")
        st.markdown("**Season `Gravity`** is equal-weighted across games. **`GravityScoreAvg`** is frame-weighted. They are different measurements.")
        st.markdown(f"Situation split minimum: **{min_frames} frames**. This is analyst-selected, not an official event standard. Game trend minimum defaults to 500 player frames.")
        st.markdown("**Sources:** `wnba_gravity_season_leaderboards.csv` for player profiles; `wnba_gravity_by_game.csv` for game history; player/team lookups for labels. Joins use player and team IDs.")
    with right:
        st.subheader("What the data does not contain")
        st.markdown("- Shot outcomes, shot probabilities, defensive coordinates, play-by-play score, or exact clock time.\n- Game dates. Game_ID is only used to order game sequence.\n- Proof that a player is open or a passing lane exists.\n- Actual lineup or defensive positions for the Clutch Lab.")
        st.markdown("**Perimeter:** outside near the three-point area. **Interior:** near the hoop. **Off-ball:** without possession. **Double-team:** two defenders focus on one player.")
        st.markdown('<span class="gb-illustration">TACTICAL ILLUSTRATION</span> All Clutch Lab placement and movement marks are hypothetical.', unsafe_allow_html=True)
    if data is not None:
        st.caption(f'Loaded {len(data["season"]):,} leaderboard rows, {len(data["games"]):,} player-game rows, and {len(data["teams"]):,} teams.')


def file_signature() -> tuple[tuple[str, int, int], ...]:
    signature = []
    for filename in FILES.values():
        path = DATA_DIR / filename
        signature.append((filename, path.stat().st_mtime_ns, path.stat().st_size) if path.is_file() else (filename, 0, 0))
    return tuple(signature)


def main() -> None:
    app_css()
    st.sidebar.markdown('<div class="gb-brand"><div class="gb-mark">GB</div><div class="gb-wordmark">GRAVITY<br><span>BREAKER</span></div></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="gb-kicker">COACH\'S WAR ROOM / 2026</div>', unsafe_allow_html=True)
    min_frames = st.sidebar.slider("Situation sample minimum", 0, 1000, 100, 25, help="Analyst-selected reliability threshold; not an official standard.", key="global_min_frames")

    data = None
    error = None
    try:
        data = load_cached(str(DATA_DIR), file_signature())
    except DataLoadError as exc:
        error = str(exc)
    except Exception as exc:
        error = f"Could not read the event CSVs: {exc}"

    player = None
    team_name = "No team selected"
    opponent_name = "No opponent selected"
    if data is not None:
        players = qualified_players(data["season"])
        team_table = data["teams"].drop_duplicates("Team_Abbreviation").set_index("Team_Abbreviation")
        teams = sorted(players["Team_Abbreviation"].dropna().unique().tolist())
        if teams:
            counts = players.groupby("Team_Abbreviation").size()
            default_team = "LAS" if "LAS" in teams else str(counts.idxmax())
            if st.session_state.get("offensive_team") not in teams:
                st.session_state["offensive_team"] = default_team
            selected_team = st.sidebar.selectbox("Offensive team", teams, key="offensive_team")
            team_players = players.loc[players["Team_Abbreviation"] == selected_team].sort_values("Display_Name")
            if not team_players.empty:
                ids = team_players["playerId"].astype(str).tolist()
                preferred = next((str(pid) for pid, name in zip(team_players["playerId"], team_players["Display_Name"]) if name in {"A'ja Wilson", "A’ja Wilson"}), None)
                if preferred is None:
                    preferred = str(team_players.sort_values("Gravity", ascending=False).iloc[0]["playerId"])
                if st.session_state.get("primary_player") not in ids:
                    st.session_state["primary_player"] = preferred
                selected_id = st.sidebar.selectbox(
                    "Primary player", ids, key="primary_player",
                    format_func=lambda value: team_players.loc[team_players["playerId"].astype(str) == str(value), "Display_Name"].iloc[0],
                )
                player = team_players.loc[team_players["playerId"].astype(str) == str(selected_id)].iloc[0]
            opponent_options = sorted([team for team in data["teams"]["Team_Abbreviation"].dropna().unique().tolist() if team != selected_team])
            if opponent_options:
                default_opponent = "NYL" if "NYL" in opponent_options else opponent_options[0]
                if st.session_state.get("scenario_opponent") not in opponent_options:
                    st.session_state["scenario_opponent"] = default_opponent
                opponent = st.sidebar.selectbox("Scenario opponent", opponent_options, key="scenario_opponent")
                opponent_name = str(team_table.loc[opponent, "Team_Full_Name"])
            if selected_team in team_table.index:
                team_name = str(team_table.loc[selected_team, "Team_Full_Name"])

    st.sidebar.markdown('<div class="gb-rule"></div>', unsafe_allow_html=True)
    st.sidebar.caption("Gravity is historical defensive attention, not a prediction of shots or outcomes.")
    if data is None:
        st.sidebar.error(error or "Required event data unavailable.")

    tabs = st.tabs(["War Room", "Scout the Threat", "Hidden Hero", "Clutch Lab", "Game Trends", "Methodology"])
    with tabs[0]:
        render_war_room(data, error, player, team_name, opponent_name, min_frames)
    with tabs[1]:
        render_scout(data, player, min_frames)
    with tabs[2]:
        render_hidden_hero(data, player, min_frames)
    with tabs[3]:
        render_clutch(data, player, opponent_name, min_frames)
    with tabs[4]:
        render_trends(data, player)
    with tabs[5]:
        render_methodology(data, min_frames)


if __name__ == "__main__":
    main()