# GRAVITY BREAKER — COACH'S WAR ROOM
## Software Requirements Specification (SRS)
**Version:** 1.0 | **Date:** October 8, 2026 | **Challenge:** WNBA × AWS × Girls Who Code Mini Data Jam — The Front Office

## 1. Executive summary
Build a polished, fast, interactive, data-driven WNBA coaching intelligence web app. The core question is: **When a star draws extra defensive attention, which teammates and tactical responses deserve a closer look?** The product turns historical player Gravity into scouting evidence, teammate comparisons, and an explicitly *illustrative* clutch-scenario tactical sandbox. It is NOT a real-time predictor of scoring, shot success, defensive assignments, or winning probability.

**One-sentence pitch:** *The box score shows who scored. Gravity Breaker shows who bends the defense — and helps a coach think through the next move.*

## 2. Goals and success criteria
- Meet judging criteria: one clear finding, transparent method, defined coaching audience, and one self-explanatory visualization.
- Make Gravity understandable to a basketball novice in 10 seconds.
- Deliver a working local web app in approximately 60 minutes, prioritizing truthful data and a smooth demo over breadth.
- Provide a standout interactive tactical court, anchored to real season/game metrics and clearly distinguished from illustrative tactics.
- Make the default demo load with no manual data preparation beyond placing supplied CSVs in `data/`.

## 3. Audience and workflow
**Primary user:** WNBA assistant coach / scouting analyst preparing a game plan.
**Secondary user:** A fan or judge who has little basketball knowledge.
**Main workflow:** Select team → select player → understand her Gravity profile → compare eligible teammates → choose a hypothetical crisis → see 2–3 possible tactical responses and supporting historical evidence → explain the insight.

## 4. Available inputs and exact schema
Input files provided by the event:

| File | Grain | Important columns | Role |
|---|---|---|---|
| `wnba_gravity_season_leaderboards.csv` | 69 qualified players, 2026 season | `playerId`, `First_Name`, `Last_name`, `Team_ID`, `Team_Abbreviation`, `Gravity`, `GravityScoreAvg`, `onballperimeter_Gravity`, `offBallPerimeter_Gravity`, `onBallInterior_Gravity`, `offBallInterior_Gravity`, matching `*_Frames`, `GP`, `MPG`, `PPG`, `RPG`, `APG` | Season scouting, player comparisons |
| `wnba_gravity_by_game.csv` | 5,521 player-game rows | `Game_ID`, `teamId`, `playerId`, `frames`, `averageGravity`, `onBallPerimeter_averageGravity`, `offBallPerimeter_averageGravity`, `onBallInterior_averageGravity`, `offBallInterior_averageGravity`, matching `*_Frames` | Game-to-game trend and teammate game comparisons |
| `wnba_player_lookup.csv` | 239 players | `playerId`, `Full_Name`, `Team_ID`, `Team_Abbreviation`, `All_Teams_2026`, `In_Leaderboard`, `In_Sample_Game` | Display names and IDs |
| `wnba_team_lookup.csv` | 15 teams | `Team_ID`, `Team_Abbreviation`, `Team_Full_Name` | Team selection |
| `wnba_court.py` | Python module | `draw_court(ax=None, ...)` | Accurate static court diagram |
| `wnba_gravity_sample.csv` | **NOT UPLOADED; OPTIONAL** | `frameId`, `gameId`, `period`, `gameClockTime`, `shotClockTime`, `ballCentroid`, `playerId`, `playerCentroid`, `ballHandler`, `hasGravity`, `playerGravity` | Optional real tracking replay; only if file becomes available |

Join `playerId` across datasets; `teamId` in game data matches `Team_ID` in lookup; `Game_ID` matches `gameId` in optional sample. Do NOT assume the player lookup's latest team is the player's team for all historic games; use game-level `teamId` when analyzing games or traded players. Preserve the event guide's exact distinction between season `Gravity` (equal-weighted game average) and `GravityScoreAvg` (frame-weighted).

### Metric semantics
Gravity measures **actual defensive attention relative to expected defensive attention**, not simply defender count or shot difficulty. Scores range from -100 to +100. 0 is baseline; positive means more attention than expected. A season average around +8 is elite, whereas +80/+90 refer to high single-moment scores, NOT season-level cutoffs. Four splits: on-ball perimeter, off-ball perimeter, on-ball interior, off-ball interior. Gravity alone does not identify an open shooter or prove a passing lane exists.

### Data constraints
- The uploaded files do NOT contain per-shot outcomes, shot probabilities, defensive player coordinates, play-by-play scores, or exact time left in individual games.
- The uploaded game-level file has no game date or opponent column. A shared `Game_ID` and team IDs can be used to infer the other participating team **only when exactly two teams are present**; label this derived matchup carefully. No date axis unless reliable date data is added.
- The optional sample has only the five OFFENSIVE players per frame, ball position, and Gravity, not all ten player coordinates. Never draw defensive player dots as if they were observed.
- If optional sample is missing, omit/hide real replay rather than fabricate it.

## 5. Functional requirements
### FR-01 — Landing and explanation (P0)
- Title, tagline, clear audience, and one-sentence definition of Gravity.
- A compact explanation: “Higher positive Gravity means the defense reacts to her more than expected, even without the ball.”
- Show clear **REAL DATA** vs **TACTICAL ILLUSTRATION** labels.
- On load, show a default real team/player and a useful insight rather than a blank screen.

### FR-02 — Scout the Threat (P0)
- Team and player dropdowns populated from actual data; only show relevant players with reliable season metrics in the default qualified view.
- Display player name, team, season Gravity, PPG, APG, and GP.
- Four-situation Gravity comparison chart, with labels and sample frame counts, omitting or flagging splits with too few frames.
- Explain whether player's strongest pull occurs on/off ball and perimeter/interior using actual values. Avoid comparing raw averages without sample context.
- Include league/qualified-player comparison if straightforward to compute.

### FR-03 — Hidden Hero teammate explorer (P0)
- Display qualified teammates from the same team with off-ball perimeter/interior Gravity and basic box-score averages.
- Highlight players who have positive or relatively strong off-ball Gravity even if their PPG is modest; label them **potential off-ball attention creators**, NOT “proven open shooters.”
- Allow side-by-side comparison of star and a teammate using radar/bar chart or simple cards.
- Show frames or a reliability indicator for each split; avoid ranking sparse samples as certain.
- If no qualified teammate exists, fall back to game-level teammate data with a clear “limited sample” label or explain why no comparison is available.

### FR-04 — Clutch Lab scenario simulator (P0)
- Interactive inputs: star player, hypothetical score difference (e.g., -3 to +3), remaining time (2–24 sec), defensive scenario (`Star double-teamed`, `Paint crowded`, `Normal coverage`), objective (`Need 2 points`, `Need 3 points`).
- Display an attractive **illustrative** court with five offense markers and a few generic defense markers. Explicitly mark all positions/defenders/routes as hypothetical unless sourced from actual tracking data.
- Provide 2–3 tactical *options* rather than asserting a proven best play. Examples: kick to perimeter, attack the basket, use off-ball screening/movement, retain star as first option.
- Rule-based explanation must depend on selected scenario, clock and objective; historical Gravity/splits may inform *which player deserves attention* but cannot establish a successful shooter or exact open pass.
- Provide “Why this option?” disclosure with historical evidence and limitations.
- Never output made-up probabilities, confidence scores, exact shot success predictions, actual defender counts, or simulated points labeled as real.
- If an option says “pass to X,” label it **candidate to evaluate**, not guaranteed best shooter; no shooting percentage is available.

### FR-05 — Game-by-game Gravity (P1)
- For selected player, plot `averageGravity` across sequential games sorted by `Game_ID` and label x-axis **Game sequence / Game ID**, not date.
- Filter rows with `frames >= 500` by default; allow adjusting minimum and show number of qualifying games.
- Show optional opponent comparison derived from game teams where safe; if inference fails, omit.
- Allow comparing situation-level Gravity per game where sample sizes support it.

### FR-06 — Real movement replay (P2, ONLY if sample file exists)
- Parse `playerCentroid` `[x y]`, `ballCentroid` `[x y z]` strings; normalize orientation where appropriate.
- Draw actual offensive player positions on `wnba_court.py` court and optionally ball location, with Gravity-based marker size/color and a frame slider or animation.
- Select one short segment for responsiveness; optional sample game is Indiana Fever at Minnesota Lynx on Aug. 2, 2026, `gameId=1022600218`.
- Sample has five offensive rows per frame, ~0.08 sec apart. `hasGravity=False` implies missing Gravity, not zero.
- Clearly disclose that defensive player locations and pass success are not provided.
- Hide gracefully if sample is missing; never block core dashboard.

### FR-07 — Methodology and limits (P0)
- Show datasets used, filtering thresholds, exact definitions, and a small data limitations panel.
- Every factual chart should be sourced to a named file/column.
- Explain season-vs-frame averaging and why minimum frame counts matter.
- No “AI prediction” branding without a trained and evaluated predictive model.

## 6. UX and visual design
- Modern sports broadcast-inspired dark theme: charcoal/near-black background, bright purple accent, orange accent, white text, high contrast.
- Main navigation as tabs: `Scout the Threat`, `Hidden Hero`, `Clutch Lab`, optional `Replay`, `How It Works`.
- Large legible metric cards, one standout Gravity comparison, visually accurate court.
- Interactions update instantly; use Streamlit `st.selectbox`, `st.slider`, `st.radio`, Plotly charts, `st.columns`.
- Include concise basketball glossary: perimeter = outside near three-point area; interior = near hoop; off-ball = without ball; double-team = two defenders focus on one player.
- Optimize for laptop projector and demo; avoid clutter, long paragraphs, tiny legends, or unnecessary animations.

## 7. Data processing and business rules
1. Load CSVs with pandas, check required columns, coerce numeric fields safely, and handle nulls.
2. Season leaderboard is the primary qualified cohort. Player IDs, not names, are join keys.
3. For game ranks/trends, default `frames >= 500` (guide recommendation). For situation splits, set a visible minimum (suggest 100 frames, configurable) and label this an analyst-chosen threshold, not official standard.
4. Do not convert Gravity frames to minutes. Use `MPG` for minutes.
5. Don't interpret season +8 using single-frame +80 thresholds.
6. For teammate discovery, compute relative off-ball Gravity rankings only among players with sufficient sample; never treat Gravity as shooting efficiency.
7. A tactical recommendation is a transparent conditional rule based on scenario and available historic metrics, not a trained outcome forecast.
8. Make missing data visible as “N/A” instead of zero; handle no results gracefully.

## 8. Architecture and implementation
**Preferred stack:** Python 3.11+, Streamlit, pandas, numpy, plotly, matplotlib. Use existing `wnba_court.py` directly where practical, or faithfully render its geometry in Plotly if that improves interactivity. No external APIs, authentication, databases, LLM calls, or internet required.

Suggested layout:
```
gravity-breaker/
  app.py
  requirements.txt
  README.md
  data/
    wnba_gravity_season_leaderboards.csv
    wnba_gravity_by_game.csv
    wnba_player_lookup.csv
    wnba_team_lookup.csv
    wnba_gravity_sample.csv      # optional; do not require
  wnba_court.py
  src/
    data_loader.py
    analytics.py
    tactics.py
    court_visuals.py
```
Keep architecture lightweight; a single `app.py` plus a few helpers is acceptable if faster. Use `@st.cache_data` for file loading. Code should run via `pip install -r requirements.txt` and `streamlit run app.py`.

## 9. Acceptance tests / definition of done
- [ ] App launches with only the four uploaded CSVs and `wnba_court.py`; missing optional sample does not crash.
- [ ] Team/player selectors populate real WNBA names and correctly filter data.
- [ ] Gravity season metrics and four splits match underlying CSV values.
- [ ] Hidden Hero shows real teammates with transparent frame counts and caveats.
- [ ] Clutch Lab controls visibly change illustrated court and tactical explanations.
- [ ] Court is recognizable, correct orientation, and legible on projector.
- [ ] No fabricated predictions, shot probabilities, actual defender positions, game clock or scores.
- [ ] Game trend excludes low-frame rows by default and does not claim Game_ID is a date.
- [ ] All charts and insights handle nulls, small samples, and traded players.
- [ ] README includes setup, data file requirements, and 60–90 second demo script.

## 10. Build priority and timebox
**0–10 min:** Verify data files, column names, joins, and sample metrics.  
**10–25 min:** Build Scout the Threat with real metrics and four-situation chart.  
**25–35 min:** Build Hidden Hero teammate comparison.  
**35–50 min:** Build visually impressive Clutch Lab court and scenario controls.  
**50–60 min:** Test end-to-end, polish default demo, create README and pitch.  
**Stretch only:** Game trend, optional frame replay, export/share. If time runs short, cut optional replay first; never sacrifice working core functionality.

## 11. Demo story / judge presentation
1. “A player can change the defense without scoring. That's Gravity.”
2. Select a real star and show her four Gravity contexts with measured values.
3. Identify a real teammate whose off-ball Gravity is noteworthy; explain why that changes scouting questions, not that she is definitely open.
4. Switch to Clutch Lab: “Down two, 12 seconds left, star double-teamed. What are our options?” Change one scenario control and show the tactics update.
5. End with: “We turn invisible defensive attention into visible scouting evidence and a more informed coaching conversation.”

## 12. Instructions for Claude Code (execution contract)
You are the implementation engineer. Read this SRS fully, inspect the local CSVs and `wnba_court.py`, and build the complete working app. **Do not stop at a plan, mockup, or pseudocode.** Implement all P0 requirements, run basic sanity checks, fix errors, and provide exact run commands. If time is limited, finish a polished and honest MVP before P1/P2 features. Do not invent unsupported data or fake model predictions. Do not ask for extra information unless a required file is truly missing; `wnba_gravity_sample.csv` is optional. Preserve the supplied CSV schema exactly. Add short clear comments explaining key calculations and limitations. End with a concise summary of implemented features and any omissions.

## 13. Source of truth
WNBA Mini Data Jam Student Guide and Data Dictionary (Oct. 8, 2026), pages 1–7; the four provided CSVs; provided `wnba_court.py`. If the dataset disagrees with this specification, inspect and report the discrepancy rather than silently inventing replacements.
