# Gravity Breaker: Coach's War Room

A local WNBA scouting dashboard for exploring historical Gravity, potential off-ball attention creators, game-to-game trends, and an explicitly hypothetical tactical scenario.

## Run it

Python 3.11 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Data files

Place the four required event CSVs in `data/` using these exact filenames. The app loads them automatically and refreshes its cache when a source file changes:

- `wnba_gravity_season_leaderboards.csv`
- `wnba_gravity_by_game.csv`
- `wnba_player_lookup.csv`
- `wnba_team_lookup.csv`

The optional `wnba_gravity_sample.csv` is not used. The app validates the supplied schema and reports missing files or columns. Without the four CSVs, data-backed views explain that data is unavailable rather than displaying fabricated player statistics. No sample WNBA dataset is bundled.

## What is included

- **War Room:** selected-player dashboard, real-data featured split, and a sampled teammate attention signal.
- **Scout the Threat:** season and frame-weighted Gravity, box-score averages, four situation splits, sample counts, and a coaching takeaway.
- **Hidden Hero:** same-team off-ball split comparison with frame reliability labels; historical game-team fallback when season teammates are unavailable.
- **Clutch Lab:** shared player/team context plus score, time, coverage, and objective controls, with conditional rules and a named but hypothetical court.
- **Game Trends:** game sequence ordered by `Game_ID`, with a configurable minimum-frame filter (500 by default).
- **Methodology:** definitions, sources, analyst-chosen thresholds, and limitations.

## 60–90 second demo

1. Select the offensive team and primary player once in the sidebar. In **War Room**, point out the real-data featured split and its sample count.
2. In **Scout the Threat**, compare on-ball and off-ball contexts and box-score averages.
3. In **Hidden Hero**, compare a teammate's off-ball Gravity and sample counts. Frame it as an attention signal to investigate, not proof of an open shot.
4. In **Clutch Lab**, set a 2-point deficit, 12 seconds, and **Star double-teamed**. Change the scenario, objective, or clock and show how the options and hypothetical court respond.
5. Close with the limits: no shot outcomes, defensive tracking coordinates, or play-by-play are included, so this supports coaching questions rather than predicting a play's result.

## Checks

```bash
python -m unittest discover -s tests -v
```

Game IDs are not dates. Season `Gravity` is equal-weighted across games; `GravityScoreAvg` is frame-weighted. Situation splits below the selected frame threshold are treated as low sample, not zero. Gravity is not shooting efficiency and does not prove an open shooter or passing lane.