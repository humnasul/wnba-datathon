
"""
WNBA Gravity Data Aggregation Pipeline
=======================================
Merges all 5 CSV datasets into a single clean, model-ready CSV
for a recommendation system that suggests the best player to deploy
when a player is surrounded (high defensive pressure / high gravity)
or when the game is getting more intense.

Input files (place in same directory):
  1. wnba_player_lookup.csv
  2. wnba_team_lookup.csv
  3. wnba_gravity_season_leaderboards.csv
  4. wnba_gravity_by_game.csv
  5. wnba_gravity_sample.csv

Output:
  → recommendation_features.csv
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────
# 1. LOAD ALL 5 DATASETS
# ──────────────────────────────────────────────
print("Loading datasets...")
players = pd.read_csv("wnba_player_lookup.csv")
teams = pd.read_csv("wnba_team_lookup.csv")
leaderboard = pd.read_csv("wnba_gravity_season_leaderboards.csv")
by_game = pd.read_csv("wnba_gravity_by_game.csv")
sample = pd.read_csv("wnba_gravity_sample.csv")

print(f"  Players:      {players.shape}")
print(f"  Teams:        {teams.shape}")
print(f"  Leaderboard:  {leaderboard.shape}")
print(f"  By Game:      {by_game.shape}")
print(f"  Sample:       {sample.shape}")

# ──────────────────────────────────────────────
# 2. CLEAN: GRAVITY BY GAME (primary table)
# ──────────────────────────────────────────────
print("\nCleaning game-level data...")

# 2a. Drop rows with null teamId (19 rows from broken game 1022600183)
null_team_count = by_game["teamId"].isna().sum()
by_game = by_game.dropna(subset=["teamId"])
print(f"  Dropped {null_team_count} rows with null teamId")

# 2b. Replace fake 0.0 gravity with NaN where frames = 0
#     (Problem 2: zero frames → gravity recorded as 0.0 instead of null)
situation_pairs = [
    ("onBallPerimeter_Frames", "onBallPerimeter_averageGravity"),
    ("offBallPerimeter_Frames", "offBallPerimeter_averageGravity"),
    ("onBallInterior_Frames", "onBallInterior_averageGravity"),
    ("offBallInterior_Frames", "offBallInterior_averageGravity"),
]
for frame_col, grav_col in situation_pairs:
    mask = by_game[frame_col] == 0
    by_game.loc[mask, grav_col] = np.nan
    print(f"  Set {mask.sum()} fake 0.0 → NaN in {grav_col}")

# 2c. Filter out low-frame records (< 100 frames ≈ 4 seconds — too noisy)
MIN_FRAMES = 100
low_frame_count = (by_game["frames"] < MIN_FRAMES).sum()
by_game = by_game[by_game["frames"] >= MIN_FRAMES]
print(f"  Dropped {low_frame_count} rows with < {MIN_FRAMES} total frames")

# 2d. Winsorize extreme gravity values at 1st/99th percentile
for col in ["averageGravity"] + [p[1] for p in situation_pairs]:
    if by_game[col].notna().sum() > 0:
        p01 = by_game[col].quantile(0.01)
        p99 = by_game[col].quantile(0.99)
        clipped = ((by_game[col] < p01) | (by_game[col] > p99)).sum()
        by_game[col] = by_game[col].clip(lower=p01, upper=p99)
        if clipped > 0:
            print(f"  Winsorized {clipped} values in {col} to [{p01:.2f}, {p99:.2f}]")

# ──────────────────────────────────────────────
# 3. CLEAN: PLAYER LOOKUP
# ──────────────────────────────────────────────
print("\nCleaning player lookup...")

# 3a. Fill missing draft info with -1 (undrafted players)
for col in ["Draft_Year", "Draft_Round", "Draft_Number"]:
    players[col] = players[col].fillna(-1).astype(int)

# 3b. Create is_drafted flag
players["is_drafted"] = (players["Draft_Year"] != -1).astype(int)

# 3c. Fill blank School/Country
players["School"] = players["School"].fillna("Unknown").replace("", "Unknown")
players["Country"] = players["Country"].fillna("Unknown").replace("", "Unknown")

# 3d. Fill missing Rookie_Year with median
players["Rookie_Year"] = players["Rookie_Year"].fillna(players["Rookie_Year"].median())

# 3e. Calculate experience (years since rookie year)
players["experience_years"] = 2026 - players["Rookie_Year"]

print(f"  54 undrafted players flagged, blanks filled, experience calculated")

# ──────────────────────────────────────────────
# 4. AGGREGATE GAME-LEVEL → PLAYER-LEVEL FEATURES
# ──────────────────────────────────────────────
print("\nAggregating game-level data to player-level features...")

# 4a. Core gravity aggregations per player
player_game_agg = by_game.groupby("playerId").agg(
    # Game counts
    total_games=("Game_ID", "nunique"),
    total_frames=("frames", "sum"),
    avg_frames_per_game=("frames", "mean"),

    # Overall gravity stats
    gravity_mean=("averageGravity", "mean"),
    gravity_median=("averageGravity", "median"),
    gravity_std=("averageGravity", "std"),
    gravity_min=("averageGravity", "min"),
    gravity_max=("averageGravity", "max"),
    gravity_p25=("averageGravity", lambda x: x.quantile(0.25)),
    gravity_p75=("averageGravity", lambda x: x.quantile(0.75)),

    # Situational gravity means (NaN-safe — ignores games where player wasn't in that situation)
    onBallPerimeter_gravity_mean=("onBallPerimeter_averageGravity", "mean"),
    offBallPerimeter_gravity_mean=("offBallPerimeter_averageGravity", "mean"),
    onBallInterior_gravity_mean=("onBallInterior_averageGravity", "mean"),
    offBallInterior_gravity_mean=("offBallInterior_averageGravity", "mean"),

    # Situational gravity std (consistency in each zone)
    onBallPerimeter_gravity_std=("onBallPerimeter_averageGravity", "std"),
    offBallPerimeter_gravity_std=("offBallPerimeter_averageGravity", "std"),
    onBallInterior_gravity_std=("onBallInterior_averageGravity", "std"),
    offBallInterior_gravity_std=("offBallInterior_averageGravity", "std"),

    # Situational frame totals (time spent in each zone)
    onBallPerimeter_total_frames=("onBallPerimeter_Frames", "sum"),
    offBallPerimeter_total_frames=("offBallPerimeter_Frames", "sum"),
    onBallInterior_total_frames=("onBallInterior_Frames", "sum"),
    offBallInterior_total_frames=("offBallInterior_Frames", "sum"),
).reset_index()

# 4b. Derived features for "surrounded / intense game" scenarios
# Gravity range = how much a player's gravity swings game-to-game
player_game_agg["gravity_range"] = player_game_agg["gravity_max"] - player_game_agg["gravity_min"]

# Gravity IQR = more robust measure of variability
player_game_agg["gravity_iqr"] = player_game_agg["gravity_p75"] - player_game_agg["gravity_p25"]

# Consistency score = inverse of std dev (higher = more predictable)
player_game_agg["gravity_consistency"] = 1 / (player_game_agg["gravity_std"] + 0.01)

# Pct of time in each zone (how the player distributes across situations)
total_situation_frames = (
    player_game_agg["onBallPerimeter_total_frames"]
    + player_game_agg["offBallPerimeter_total_frames"]
    + player_game_agg["onBallInterior_total_frames"]
    + player_game_agg["offBallInterior_total_frames"]
)
player_game_agg["pct_onBallPerimeter"] = player_game_agg["onBallPerimeter_total_frames"] / total_situation_frames
player_game_agg["pct_offBallPerimeter"] = player_game_agg["offBallPerimeter_total_frames"] / total_situation_frames
player_game_agg["pct_onBallInterior"] = player_game_agg["onBallInterior_total_frames"] / total_situation_frames
player_game_agg["pct_offBallInterior"] = player_game_agg["offBallInterior_total_frames"] / total_situation_frames

# "Pressure performance" — gravity in high-frame games vs low-frame games
# (proxy for how a player performs in intense / high-minute games)
for pid, group in by_game.groupby("playerId"):
    median_frames = group["frames"].median()
    high_intensity = group[group["frames"] >= median_frames]["averageGravity"].mean()
    low_intensity = group[group["frames"] < median_frames]["averageGravity"].mean()
    player_game_agg.loc[player_game_agg["playerId"] == pid, "gravity_high_intensity_games"] = high_intensity
    player_game_agg.loc[player_game_agg["playerId"] == pid, "gravity_low_intensity_games"] = low_intensity

player_game_agg["intensity_gravity_delta"] = (
    player_game_agg["gravity_high_intensity_games"] - player_game_agg["gravity_low_intensity_games"]
)

# Rolling trend: gravity in last 5 games vs first 5 games (improving or declining?)
for pid, group in by_game.sort_values("Game_ID").groupby("playerId"):
    games_sorted = group.sort_values("Game_ID")
    n = len(games_sorted)
    if n >= 10:
        first5 = games_sorted.head(5)["averageGravity"].mean()
        last5 = games_sorted.tail(5)["averageGravity"].mean()
    elif n >= 4:
        half = n // 2
        first5 = games_sorted.head(half)["averageGravity"].mean()
        last5 = games_sorted.tail(half)["averageGravity"].mean()
    else:
        first5 = games_sorted["averageGravity"].mean()
        last5 = first5
    player_game_agg.loc[player_game_agg["playerId"] == pid, "gravity_early_season"] = first5
    player_game_agg.loc[player_game_agg["playerId"] == pid, "gravity_late_season"] = last5

player_game_agg["gravity_trend"] = (
    player_game_agg["gravity_late_season"] - player_game_agg["gravity_early_season"]
)

print(f"  Aggregated {len(player_game_agg)} players with {player_game_agg.shape[1]} features")

# ──────────────────────────────────────────────
# 5. AGGREGATE FRAME-LEVEL SAMPLE DATA
# ──────────────────────────────────────────────
print("\nAggregating frame-level sample data...")

# From the sample game, extract per-player micro-level features
sample_agg = sample.groupby("playerId").agg(
    sample_frames=("frameId", "count"),
    sample_gravity_mean=("playerGravity", "mean"),
    sample_gravity_std=("playerGravity", "std"),
    sample_gravity_max=("playerGravity", "max"),
    sample_gravity_min=("playerGravity", "min"),
    sample_pct_ball_handler=("ballHandler", "mean"),  # % of frames as ball handler
    sample_pct_has_gravity=("hasGravity", "mean"),     # % of frames with gravity data
).reset_index()

# Gravity spike frequency: how often does gravity exceed +10 (high pressure moments)
gravity_spikes = sample.groupby("playerId").apply(
    lambda x: (x["playerGravity"] > 10).mean() if len(x) > 0 else 0
).reset_index(name="sample_gravity_spike_pct")

sample_agg = sample_agg.merge(gravity_spikes, on="playerId", how="left")

print(f"  Aggregated {len(sample_agg)} players from sample game")

# ──────────────────────────────────────────────
# 6. JOIN EVERYTHING TOGETHER
# ──────────────────────────────────────────────
print("\nJoining all datasets...")

# Start with game-level aggregations (broadest player coverage)
master = player_game_agg.copy()

# Join player bio/lookup info
master = master.merge(
    players[["playerId", "Full_Name", "Country", "School", "Draft_Year",
             "Draft_Round", "Draft_Number", "Rookie_Year", "Team_ID",
             "Team_Abbreviation", "All_Teams_2026", "Games_In_Data",
             "In_Leaderboard", "In_Sample_Game", "is_drafted", "experience_years"]],
    on="playerId",
    how="left"
)

# Join team info
master = master.merge(
    teams[["Team_ID", "Team_City", "Team_Name", "Team_Full_Name"]],
    on="Team_ID",
    how="left"
)

# Join season leaderboard stats (only 69 players have these)
leaderboard_cols = ["playerId", "GravityScoreAvg", "GP", "MPG", "PPG", "RPG", "APG",
                    "Gravity", "Frames"]
# Rename to avoid collisions
leaderboard_join = leaderboard[leaderboard_cols].rename(columns={
    "GravityScoreAvg": "season_GravityScoreAvg",
    "Gravity": "season_Gravity",
    "Frames": "season_Frames",
    "GP": "season_GP",
    "MPG": "season_MPG",
    "PPG": "season_PPG",
    "RPG": "season_RPG",
    "APG": "season_APG",
})
master = master.merge(leaderboard_join, on="playerId", how="left")

# Join sample game features (only players in the sample game)
master = master.merge(sample_agg, on="playerId", how="left")

print(f"  Final joined table: {master.shape}")

# ──────────────────────────────────────────────
# 7. ENGINEER RECOMMENDATION-SPECIFIC FEATURES
# ──────────────────────────────────────────────
print("\nEngineering recommendation-specific features...")

# 7a. "Surrounded" score: how well does a player perform when drawing heavy attention?
#     High gravity = player is being surrounded by defenders
#     We want players who THRIVE under pressure (high gravity + high PPG)
master["pressure_efficiency"] = master["gravity_mean"] * master["season_PPG"].fillna(0)

# 7b. Interior vs Perimeter preference (for matchup-based recommendations)
master["interior_preference"] = (
    master["pct_onBallInterior"].fillna(0) + master["pct_offBallInterior"].fillna(0)
)
master["perimeter_preference"] = (
    master["pct_onBallPerimeter"].fillna(0) + master["pct_offBallPerimeter"].fillna(0)
)

# 7c. Versatility score: how evenly distributed across all 4 zones
zone_pcts = master[["pct_onBallPerimeter", "pct_offBallPerimeter",
                     "pct_onBallInterior", "pct_offBallInterior"]].fillna(0)
# Shannon entropy as versatility measure (higher = more versatile)
zone_pcts_safe = zone_pcts.replace(0, 1e-10)
master["zone_versatility"] = -(zone_pcts_safe * np.log2(zone_pcts_safe)).sum(axis=1)

# 7d. Clutch factor: gravity trend (improving late season = clutch)
master["is_trending_up"] = (master["gravity_trend"] > 0).astype(int)

# 7e. Reliability score: combines consistency + games played
games_norm = master["total_games"] / master["total_games"].max()
consistency_norm = master["gravity_consistency"] / master["gravity_consistency"].max()
master["reliability_score"] = (games_norm + consistency_norm) / 2

# 7f. Composite recommendation score for "surrounded" scenarios
#     Weights: gravity (40%), PPG efficiency (25%), consistency (20%), trend (15%)
gravity_z = (master["gravity_mean"] - master["gravity_mean"].mean()) / master["gravity_mean"].std()
ppg_z = (master["season_PPG"].fillna(0) - master["season_PPG"].fillna(0).mean()) / master["season_PPG"].fillna(0).std()
consistency_z = (master["gravity_consistency"] - master["gravity_consistency"].mean()) / master["gravity_consistency"].std()
trend_z = (master["gravity_trend"].fillna(0) - master["gravity_trend"].fillna(0).mean()) / master["gravity_trend"].fillna(0).std()

master["surrounded_recommendation_score"] = (
    0.40 * gravity_z +
    0.25 * ppg_z +
    0.20 * consistency_z +
    0.15 * trend_z
)

# ──────────────────────────────────────────────
# 8. FINAL CLEANUP & OUTPUT
# ──────────────────────────────────────────────
print("\nFinal cleanup...")

# Round numeric columns
numeric_cols = master.select_dtypes(include=[np.number]).columns
master[numeric_cols] = master[numeric_cols].round(4)

# Sort by recommendation score descending
master = master.sort_values("surrounded_recommendation_score", ascending=False)

# Reorder columns: identifiers first, then features, then scores
id_cols = ["playerId", "Full_Name", "Team_Abbreviation", "Team_Full_Name",
           "Country", "experience_years", "is_drafted"]
game_cols = ["total_games", "total_frames", "avg_frames_per_game"]
gravity_cols = ["gravity_mean", "gravity_median", "gravity_std", "gravity_min",
                "gravity_max", "gravity_range", "gravity_iqr", "gravity_consistency"]
situation_cols = ["onBallPerimeter_gravity_mean", "offBallPerimeter_gravity_mean",
                  "onBallInterior_gravity_mean", "offBallInterior_gravity_mean",
                  "onBallPerimeter_gravity_std", "offBallPerimeter_gravity_std",
                  "onBallInterior_gravity_std", "offBallInterior_gravity_std"]
zone_cols = ["pct_onBallPerimeter", "pct_offBallPerimeter",
             "pct_onBallInterior", "pct_offBallInterior"]
trend_cols = ["gravity_early_season", "gravity_late_season", "gravity_trend",
              "gravity_high_intensity_games", "gravity_low_intensity_games",
              "intensity_gravity_delta", "is_trending_up"]
season_cols = ["season_GravityScoreAvg", "season_Gravity", "season_GP",
               "season_MPG", "season_PPG", "season_RPG", "season_APG"]
sample_cols = ["sample_frames", "sample_gravity_mean", "sample_gravity_std",
               "sample_gravity_max", "sample_gravity_min",
               "sample_pct_ball_handler", "sample_pct_has_gravity",
               "sample_gravity_spike_pct"]
score_cols = ["pressure_efficiency", "interior_preference", "perimeter_preference",
              "zone_versatility", "reliability_score",
              "surrounded_recommendation_score"]

# Build final column order (only include columns that exist)
all_ordered = id_cols + game_cols + gravity_cols + situation_cols + zone_cols + \
              trend_cols + season_cols + sample_cols + score_cols
final_cols = [c for c in all_ordered if c in master.columns]
# Add any remaining columns not in the ordered list
remaining = [c for c in master.columns if c not in final_cols]
final_cols += remaining

master = master[final_cols]

# Output
output_path = "recommendation_features.csv"
master.to_csv(output_path, index=False)

print(f"\n{'='*60}")
print(f"OUTPUT: {output_path}")
print(f"  Rows:    {master.shape[0]} players")
print(f"  Columns: {master.shape[1]} features")
print(f"{'='*60}")

# Print top 10 recommended players for "surrounded" scenarios
print(f"\nTop 10 Players for 'Surrounded / High Pressure' Scenarios:")
print(f"{'─'*60}")
top10 = master.head(10)[["Full_Name", "Team_Abbreviation", "gravity_mean",
                          "season_PPG", "gravity_consistency",
                          "surrounded_recommendation_score"]]
print(top10.to_string(index=False))

# Print column inventory
print(f"\n\nFull Column Inventory ({master.shape[1]} columns):")
print(f"{'─'*60}")
for i, col in enumerate(master.columns, 1):
    dtype = master[col].dtype
    nulls = master[col].isna().sum()
    print(f"  {i:3d}. {col:<45s} {str(dtype):<10s} ({nulls} nulls)")

