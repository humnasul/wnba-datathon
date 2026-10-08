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


st.set_page_config(
    page_title="Gravity Breaker | Coach's War Room",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root { --ink:#101115; --panel:#191a20; --muted:#aaa9b3; --violet:#a98bff; --orange:#ff934f; --mint:#66d9cb; }
html, body, [class*="css"] { font-family:'DM Sans','Avenir Next',sans-serif; }
.stApp { background: radial-gradient(ellipse at 88% 0%, #272131 0%, #15151a 35%, #101115 74%); color:#f5f3f8; }
[data-testid="stSidebar"] { background:#15161b; border-right:1px solid #2a2931; }
h1,h2,h3 { font-family:'Barlow Condensed','Avenir Next Condensed',sans-serif !important; letter-spacing:0 !important; }
h1 { font-size:3rem !important; line-height:1.02 !important; margin-bottom:.1rem !important; }
h2 { font-size:1.8rem !important; }
.eyebrow { color:var(--orange); font-size:.75rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }
.subhead { color:#b9b6c2; font-size:1rem; margin:0 0 1rem; }
.real-label,.illustration-label { display:inline-block; border-radius:2px; padding:4px 8px; font-size:.69rem; font-weight:700; letter-spacing:.08em; }
.real-label { color:#9df0df; border:1px solid #3c897e; background:#15302c; }
.illustration-label { color:#ffd1ae; border:1px solid #a75d35; background:#39271f; }
.metric { background:linear-gradient(135deg,#202127,#191a20); border:1px solid #34333c; border-top:2px solid var(--violet); padding:14px 16px; min-height:94px; }
.metric-label { color:#aaa9b3; font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; }
.metric-value { color:#fff; font:700 1.9rem 'Barlow Condensed','Avenir Next Condensed',sans-serif; margin-top:3px; }
.metric-note { color:#aaa9b3; font-size:.73rem; }
.insight { border-left:3px solid var(--orange); background:#201d20; padding:12px 15px; margin:.5rem 0 1rem; color:#ece8ec; }
.data-note { color:#aaa9b3; font-size:.82rem; }
.section-rule { height:1px; background:#33323a; margin:1rem 0 1.4rem; }
div[data-testid="stTabs"] button { font-weight:700; }
div[data-testid="stMetric"] { background:#1b1c22; border:1px solid #35343d; padding:10px 12px; }
div[data-testid="stAlert"] { border-radius:2px; }
@media(max-width:760px) { h1 {font-size:2.3rem !important;} }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def cached_load(data_dir: str, uploads: tuple[tuple[str, bytes], ...]) -> dict[str, pd.DataFrame]:
    return load_datasets(Path(data_dir), dict(uploads))


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f'<div class="metric"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def gravity_figure(summary: pd.DataFrame, title: str = "Gravity by situation") -> go.Figure:
    chart = summary.copy()
    chart["Sample status"] = chart["Reliable sample"].map({True: "At/above analyst threshold", False: "Low or missing sample"})
    figure = px.bar(
        chart, x="Situation", y="Gravity", color="Sample status",
        color_discrete_map={"At/above analyst threshold": "#a98bff", "Low or missing sample": "#766a86"},
        custom_data=["Frames", "Sample status"],
    )
    figure.add_hline(y=0, line_color="#82808a", line_width=1)
    figure.update_traces(hovertemplate="%{x}<br>Gravity: %{y:.1f}<br>Frames: %{customdata[0]}<extra></extra>")
    figure.update_layout(
        title={"text": title, "font": {"size": 18, "color": "#f5f3f8"}},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#d7d3df", "family": "DM Sans"},
        margin={"l": 12, "r": 12, "t": 52, "b": 35},
        yaxis_title="Gravity score", xaxis_title="", legend_title="Split sample",
    )
    return figure


def missing_data_panel(error: str) -> None:
    st.markdown('<span class="real-label">REAL DATA REQUIRED</span>', unsafe_allow_html=True)
    st.warning("The scouting views are waiting for the event CSVs. No player or season numbers are being substituted.")
    st.caption(error)
    st.markdown("Add the four files to `data/` or upload them in the sidebar. The Clutch Lab remains available as a clearly hypothetical tactics exercise.")


def render_scout(data: dict[str, pd.DataFrame] | None, error: str | None, min_split_frames: int) -> None:
    st.markdown('<span class="eyebrow">01 / SCOUT THE THREAT</span>', unsafe_allow_html=True)
    st.header("Scout the Threat")
    st.markdown('<p class="subhead">Who bends the defense, and in which situations?</p>', unsafe_allow_html=True)
    if data is None:
        missing_data_panel(error or "Required data is unavailable.")
        return

    players = qualified_players(data["season"])
    teams = data["teams"].sort_values("Team_Abbreviation")
    team_options = teams["Team_Abbreviation"].dropna().tolist()
    preferred_team = "LAS" if "LAS" in team_options else team_options[0]
    selected_team = st.selectbox("Team", team_options, index=team_options.index(preferred_team), key="scout_team")
    team_players = players.loc[players["Team_Abbreviation"] == selected_team].sort_values("Display_Name")
    if team_players.empty:
        st.info("No qualified leaderboard players are available for this team.")
        return
    preferred_player = next((name for name in team_players["Display_Name"] if name in {"A'ja Wilson", "A’ja Wilson"}), team_players.iloc[0]["Display_Name"])
    selected_name = st.selectbox("Player", team_players["Display_Name"].tolist(), index=team_players["Display_Name"].tolist().index(preferred_player), key="scout_player")
    player = team_players.loc[team_players["Display_Name"] == selected_name].iloc[0]

    st.markdown('<span class="real-label">REAL DATA</span>', unsafe_allow_html=True)
    st.subheader(f"{selected_name}  ·  {selected_team}")
    cards = st.columns(5)
    values = [("Season Gravity", player.get("Gravity"), "Equal-weighted game average"),
              ("PPG", player.get("PPG"), "Points per game"),
              ("APG", player.get("APG"), "Assists per game"),
              ("GP", player.get("GP"), "Games played"),
              ("MPG", player.get("MPG"), "Minutes per game")]
    for column, (label, value, note) in zip(cards, values):
        rendered = "N/A" if pd.isna(value) else f"{value:.1f}" if label != "GP" else f"{int(value)}"
        with column:
            metric_card(label, rendered, note)

    summary = split_summary(player, min_split_frames)
    left, right = st.columns([1.45, 1])
    with left:
        st.plotly_chart(gravity_figure(summary), use_container_width=True, config={"displayModeBar": False})
    with right:
        strongest = strongest_split(summary)
        if strongest:
            strongest_row = summary.loc[summary["Situation"] == strongest].iloc[0]
            st.markdown(f'<div class="insight"><b>Strongest reliable pull:</b> {strongest}, at {strongest_row["Gravity"]:+.1f} Gravity across {int(strongest_row["Frames"]):,} frames.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="insight">No situation split meets the current frame threshold. Treat the displayed values as sparse or unavailable.</div>', unsafe_allow_html=True)
        st.markdown("**How to read it**")
        st.write("Positive Gravity means more defensive attention than expected. Off-ball measures attention when the player does not have the ball; it does not establish that a teammate had an open shot.")
        st.caption(f"Situation reliability threshold: {min_split_frames} frames (analyst-chosen, not an official standard). Source: `wnba_gravity_season_leaderboards.csv`.")

    league = players["Gravity"].dropna()
    if not league.empty:
        league_median = league.median()
        st.caption(f"Qualified cohort context: {len(league)} players; median season Gravity {league_median:+.1f}. This is a descriptive cohort comparison, not an official league ranking.")


def render_hidden_hero(data: dict[str, pd.DataFrame] | None, error: str | None, min_split_frames: int) -> None:
    st.markdown('<span class="eyebrow">02 / HIDDEN HERO</span>', unsafe_allow_html=True)
    st.header("Find the off-ball attention")
    st.markdown('<p class="subhead">Look for potential attention creators beyond the headline scorer.</p>', unsafe_allow_html=True)
    if data is None:
        missing_data_panel(error or "Required data is unavailable.")
        return

    players = qualified_players(data["season"])
    teams = data["teams"]["Team_Abbreviation"].dropna().sort_values().tolist()
    team_default = "LAS" if "LAS" in teams else teams[0]
    selected_team = st.selectbox("Team", teams, index=teams.index(team_default), key="hero_team")
    team_players = players.loc[players["Team_Abbreviation"] == selected_team].sort_values("Display_Name")
    if team_players.empty:
        st.info("No qualified season players are available for this team.")
        return
    selected_name = st.selectbox("Anchor player", team_players["Display_Name"].tolist(), key="hero_player")
    star = team_players.loc[team_players["Display_Name"] == selected_name].iloc[0]
    candidates = teammate_candidates(star, data["season"], min_split_frames)

    if candidates.empty:
        fallback = game_teammate_candidates(str(star["playerId"]), data["games"], data["players"])
        if fallback.empty:
            st.info("No qualified season teammate comparison or reliable game-level teammate sample is available for this selection.")
            return
        st.markdown('<span class="illustration-label">LIMITED GAME SAMPLE</span>', unsafe_allow_html=True)
        st.caption("These teammates are inferred from shared historical Game_ID and teamId rows. Current team lookup is not used to assign past teammates.")
        st.dataframe(fallback, hide_index=True, use_container_width=True)
        return

    offball = [("offBallPerimeter_Gravity", "offBallPerimeter_Frames", "Off-ball perimeter"),
               ("offBallInterior_Gravity", "offBallInterior_Frames", "Off-ball interior")]
    table_rows = []
    eligible = []
    for _, teammate in candidates.iterrows():
        row = {"Teammate": teammate["Display_Name"], "PPG": teammate.get("PPG"), "APG": teammate.get("APG"), "GP": teammate.get("GP")}
        reliable_positive = False
        for value_column, frames_column, label in offball:
            value, frames = teammate.get(value_column), teammate.get(frames_column)
            row[label] = value
            row[f"{label} frames"] = frames
            enough = pd.notna(value) and pd.notna(frames) and frames >= min_split_frames
            row[f"{label} sample"] = "Reliable" if enough else "Low / missing"
            reliable_positive |= bool(enough and value > 0)
        row["Signal"] = "Potential off-ball attention creator" if reliable_positive else "Insufficient positive evidence"
        if reliable_positive:
            eligible.append(teammate["Display_Name"])
        table_rows.append(row)
    table = pd.DataFrame(table_rows)
    st.markdown('<span class="real-label">REAL DATA</span>', unsafe_allow_html=True)
    st.dataframe(table, hide_index=True, use_container_width=True, column_config={
        "PPG": st.column_config.NumberColumn(format="%.1f"),
        "APG": st.column_config.NumberColumn(format="%.1f"),
        "Off-ball perimeter": st.column_config.NumberColumn(format="%+.1f"),
        "Off-ball interior": st.column_config.NumberColumn(format="%+.1f"),
    })
    if eligible:
        st.markdown(f'<div class="insight"><b>Worth a closer look:</b> {", ".join(eligible)} show a positive off-ball split with at least {min_split_frames} frames. This is a potential attention signal, not evidence of open shots or shooting efficiency.</div>', unsafe_allow_html=True)
    else:
        st.info("No teammate split currently clears the sample threshold with positive Gravity. Sparse values are not ranked as certain.")

    chart_names = [selected_name] + candidates["Display_Name"].tolist()
    comparison_names = st.multiselect("Compare players", chart_names, default=chart_names[:min(3, len(chart_names))], key="hero_compare")
    comparison_rows = []
    for name in comparison_names:
        row = team_players.loc[team_players["Display_Name"] == name]
        if row.empty:
            row = candidates.loc[candidates["Display_Name"] == name]
        if row.empty:
            continue
        for label, (value_column, frame_column) in SPLITS.items():
            comparison_rows.append({"Player": name, "Situation": label, "Gravity": row.iloc[0].get(value_column), "Frames": row.iloc[0].get(frame_column)})
    if comparison_rows:
        comparison = pd.DataFrame(comparison_rows).dropna(subset=["Gravity"])
        figure = px.bar(comparison, x="Situation", y="Gravity", color="Player", barmode="group", hover_data=["Frames"], color_discrete_sequence=["#a98bff", "#ff934f", "#66d9cb", "#e6d65c"])
        figure.add_hline(y=0, line_color="#82808a", line_width=1)
        figure.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#d7d3df", margin={"t":20,"b":20}, yaxis_title="Gravity", xaxis_title="")
        st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
    st.caption("Source: `wnba_gravity_season_leaderboards.csv`; teammate membership comes from the season leaderboard Team_ID. Gravity is not shooting efficiency.")


def render_clutch(data: dict[str, pd.DataFrame] | None, min_split_frames: int) -> None:
    st.markdown('<span class="eyebrow">03 / CLUTCH LAB</span>', unsafe_allow_html=True)
    st.header("Pressure is a conversation, not a prediction")
    st.markdown('<p class="subhead">Explore conditional choices with historical evidence and an illustrative court.</p>', unsafe_allow_html=True)
    st.markdown('<span class="illustration-label">TACTICAL ILLUSTRATION</span>', unsafe_allow_html=True)

    if data is not None:
        player_frame = qualified_players(data["season"])
        star_names = player_frame["Display_Name"].tolist()
        default_star = "A'ja Wilson" if "A'ja Wilson" in star_names else star_names[0]
        star_name = st.selectbox("Star player", star_names, index=star_names.index(default_star), key="clutch_player")
        star = player_frame.loc[player_frame["Display_Name"] == star_name].iloc[0]
        teammates = teammate_candidates(star, data["season"], min_split_frames)
        reliable = teammates.loc[
            ((teammates["offBallPerimeter_Gravity"] > 0) & teammates["offBallPerimeter_Gravity_reliable"])
            | ((teammates["offBallInterior_Gravity"] > 0) & teammates["offBallInterior_Gravity_reliable"])
        ]
        candidate_name = reliable.iloc[0]["Display_Name"] if not reliable.empty else None
        star_evidence = f"Historical season Gravity {star['Gravity']:+.1f}; sourced from the qualified leaderboard."
    else:
        star_name = st.text_input("Scenario star", value="Star player", key="clutch_generic_star")
        candidate_name = None
        star_evidence = "No player data loaded. The scenario below uses no player-specific statistics."
        st.caption("The court and tactics are available now; adding the CSVs enables player-specific historical context.")

    controls = st.columns([1, 1, 1.35, 1.2])
    with controls[0]:
        score = st.slider("Score difference", min_value=-3, max_value=3, value=-2, help="Your team's score minus the opponent's.")
    with controls[1]:
        seconds = st.slider("Time remaining (sec)", min_value=2, max_value=24, value=12)
    with controls[2]:
        scenario = st.selectbox("Defensive scenario", ["Star double-teamed", "Paint crowded", "Normal coverage"])
    with controls[3]:
        objective = st.radio("Objective", ["Need 2 points", "Need 3 points"], horizontal=False)

    options = tactical_options(star_name, score, seconds, scenario, objective, candidate_name)
    option_label = st.radio("Possible responses", [option["title"] for option in options], horizontal=False, label_visibility="collapsed")
    selected_option_index = next(index for index, option in enumerate(options) if option["title"] == option_label)
    left, right = st.columns([1.18, 1])
    with left:
        st.plotly_chart(build_court(selected_option_index, scenario), use_container_width=True, config={"displayModeBar": False})
        st.caption("Orange / violet = hypothetical offense. Mint = generic hypothetical defenders. No positions, routes, score, or play are observed.")
    with right:
        chosen = options[selected_option_index]
        st.subheader(chosen["title"])
        st.write(chosen["why"])
        with st.expander("Why this option? Historical evidence and limits", expanded=True):
            st.write(star_evidence)
            if data is not None:
                star_row = player_frame.loc[player_frame["Display_Name"] == star_name].iloc[0]
                split = split_summary(star_row, min_split_frames)
                best = strongest_split(split)
                if best:
                    best_row = split.loc[split["Situation"] == best].iloc[0]
                    st.write(f"Strongest reliable historical situation: {best} ({best_row['Gravity']:+.1f}, {int(best_row['Frames']):,} frames).")
            st.warning("Gravity describes historical defensive attention relative to expectation. It does not identify an open player, passing lane, successful shot, exact defender count, or winning probability. These are options for a coach to evaluate, not a best-play prediction.")


def render_game_trend(data: dict[str, pd.DataFrame] | None, error: str | None) -> None:
    st.markdown('<span class="eyebrow">04 / GAME TRENDS</span>', unsafe_allow_html=True)
    st.header("Game-by-game Gravity")
    st.markdown('<p class="subhead">A sequence of games, never a date axis.</p>', unsafe_allow_html=True)
    if data is None:
        missing_data_panel(error or "Required data is unavailable.")
        return
    players = qualified_players(data["season"])
    selected_name = st.selectbox("Player", players["Display_Name"].tolist(), key="trend_player")
    player = players.loc[players["Display_Name"] == selected_name].iloc[0]
    threshold = st.slider("Minimum game frames", min_value=0, max_value=3000, value=500, step=100, key="trend_frames")
    trend = game_trend(str(player["playerId"]), data["games"], threshold)
    st.caption(f"{len(trend)} qualifying games at frames >= {threshold:,}. Game_ID is used only to order game sequence; no date or opponent name is provided.")
    if trend.empty:
        st.info("No games meet this frame threshold.")
        return
    figure = px.line(trend, x="Game_Sequence", y="averageGravity", markers=True, custom_data=["Game_ID", "frames"], color_discrete_sequence=["#ff934f"])
    figure.add_hline(y=0, line_color="#82808a", line_width=1)
    figure.update_traces(hovertemplate="Game sequence %{x}<br>Game_ID %{customdata[0]}<br>Gravity %{y:.1f}<br>Frames %{customdata[1]:,.0f}<extra></extra>")
    figure.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#d7d3df", xaxis_title="Game sequence / Game_ID", yaxis_title="Average Gravity", margin={"t":20,"b":20})
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
    with st.expander("Situation splits by game"):
        split_name = st.selectbox("Situation", list(GAME_SPLITS), key="trend_split")
        value_column, frames_column = GAME_SPLITS[split_name]
        if frames_column not in trend.columns:
            st.info("Situation-level frame counts are not present in this file; reliability cannot be assessed.")
        else:
            split_minimum = st.number_input("Minimum situation frames", min_value=0, value=100, step=25, key="trend_split_min")
            eligible = trend.loc[trend[frames_column] >= split_minimum].dropna(subset=[value_column])
            if eligible.empty:
                st.info("No situation values meet the selected sample threshold.")
            else:
                chart = px.line(eligible, x="Game_Sequence", y=value_column, markers=True, custom_data=["Game_ID", frames_column], color_discrete_sequence=["#a98bff"])
                chart.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#d7d3df", xaxis_title="Game sequence / Game_ID", yaxis_title="Situation Gravity")
                st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})


def render_methodology(min_split_frames: int, data: dict[str, pd.DataFrame] | None) -> None:
    st.markdown('<span class="eyebrow">05 / HOW IT WORKS</span>', unsafe_allow_html=True)
    st.header("A transparent scouting lens")
    st.markdown("**Gravity** measures actual defensive attention relative to expected attention. Zero is baseline; positive values indicate more attention than expected. It is not simply defender count, shot difficulty, or shot quality.")
    left, right = st.columns(2)
    with left:
        st.subheader("Sources and calculations")
        st.markdown("- Season profile and box-score averages: `wnba_gravity_season_leaderboards.csv`\n- Trends and historical teammate fallback: `wnba_gravity_by_game.csv`\n- Display names and team names: `wnba_player_lookup.csv`, `wnba_team_lookup.csv`\n- Player and team records join on IDs, not names. Game teammate membership uses the game's `teamId`.")
        st.markdown("**Season averages:** `Gravity` is equal-weighted across games. `GravityScoreAvg` is frame-weighted. They are distinct measures and are not interchangeable.")
        st.markdown(f"**Situation reliability:** splits below {min_split_frames} frames are flagged as low sample. This threshold is analyst-chosen, not an event standard. Game trends default to at least 500 player frames per game.")
    with right:
        st.subheader("What this does not know")
        st.markdown("- No shot outcomes, shot probabilities, defensive coordinates, play-by-play score, or exact game clock are present.\n- Game_ID is not a date. A matchup may be inferred only when exactly two team IDs appear in a game.\n- Gravity alone cannot establish an open shooter or passing lane.\n- The Clutch Lab court, defenders, and tactical choices are hypothetical, not tracking data or model predictions.")
        st.subheader("Quick glossary")
        st.markdown("**Perimeter:** outside near the three-point area. **Interior:** near the hoop. **Off-ball:** without possession. **Double-team:** two defenders focus on one player.")
    if data is not None:
        st.caption(f"Loaded {len(data['season']):,} qualified leaderboard rows, {len(data['games']):,} player-game rows, and {len(data['teams']):,} teams.")


def main() -> None:
    st.sidebar.markdown('<div class="eyebrow">WNBA · SCOUTING INTELLIGENCE</div>', unsafe_allow_html=True)
    st.sidebar.title("GRAVITY BREAKER")
    st.sidebar.caption("COACH'S WAR ROOM  /  2026")
    st.sidebar.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.sidebar.markdown("**Gravity, in 10 seconds**")
    st.sidebar.caption("Higher positive Gravity means the defense reacts to a player more than expected, even without the ball.")
    st.sidebar.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.sidebar.markdown("**Data source**")
    uploaded = {}
    for key, filename in FILES.items():
        file = st.sidebar.file_uploader(filename, type="csv", key=f"upload_{key}", label_visibility="collapsed")
        if file is not None:
            uploaded[filename] = file.getvalue()
    st.sidebar.caption("Upload all four CSVs, or place them in `data/`. The optional tracking sample is not required.")
    min_split_frames = st.sidebar.slider("Situation split minimum frames", min_value=0, max_value=1000, value=100, step=25, help="Analyst-chosen sample threshold, not an official standard.")

    data = None
    error = None
    try:
        data = cached_load(str(DATA_DIR), tuple(sorted(uploaded.items())))
    except DataLoadError as exc:
        error = str(exc)
    except Exception as exc:
        error = f"Could not read the supplied data: {exc}"

    st.markdown('<span class="eyebrow">WNBA · COACHING INTELLIGENCE</span>', unsafe_allow_html=True)
    st.title("Gravity Breaker")
    st.markdown('<p class="subhead">The box score shows who scored. Gravity shows who bends the defense.</p>', unsafe_allow_html=True)
    st.markdown("**The question:** when a star draws extra defensive attention, which teammates and tactical responses deserve a closer look?")

    tabs = st.tabs(["Scout the Threat", "Hidden Hero", "Clutch Lab", "Game Trends", "How It Works"])
    with tabs[0]:
        render_scout(data, error, min_split_frames)
    with tabs[1]:
        render_hidden_hero(data, error, min_split_frames)
    with tabs[2]:
        render_clutch(data, min_split_frames)
    with tabs[3]:
        render_game_trend(data, error)
    with tabs[4]:
        render_methodology(min_split_frames, data)


if __name__ == "__main__":
    from src.dashboard import main as dashboard_main

    dashboard_main()