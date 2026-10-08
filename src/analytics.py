from __future__ import annotations

import pandas as pd


SPLITS = {
    "On-ball perimeter": ("onballperimeter_Gravity", "onballperimeter_Frames"),
    "Off-ball perimeter": ("offBallPerimeter_Gravity", "offBallPerimeter_Frames"),
    "On-ball interior": ("onBallInterior_Gravity", "onBallInterior_Frames"),
    "Off-ball interior": ("offBallInterior_Gravity", "offBallInterior_Frames"),
}

GAME_SPLITS = {
    "On-ball perimeter": ("onBallPerimeter_averageGravity", "onBallPerimeter_Frames"),
    "Off-ball perimeter": ("offBallPerimeter_averageGravity", "offBallPerimeter_Frames"),
    "On-ball interior": ("onBallInterior_averageGravity", "onBallInterior_Frames"),
    "Off-ball interior": ("offBallInterior_averageGravity", "offBallInterior_Frames"),
}


def player_name(row: pd.Series) -> str:
    first_value = row.get("First_Name", "")
    last_value = row.get("Last_name", "")
    first = "" if pd.isna(first_value) else str(first_value).strip()
    last = "" if pd.isna(last_value) else str(last_value).strip()
    return f"{first} {last}".strip() or str(row.get("playerId", "Unknown player"))


def qualified_players(season: pd.DataFrame) -> pd.DataFrame:
    players = season.loc[season["Gravity"].notna()].copy()
    players["Display_Name"] = players.apply(player_name, axis=1)
    return players


def split_summary(player: pd.Series, min_frames: int = 100) -> pd.DataFrame:
    rows = []
    for label, (value_column, frame_column) in SPLITS.items():
        value = player.get(value_column)
        frames = player.get(frame_column)
        valid_value = pd.notna(value)
        valid_frames = pd.notna(frames)
        rows.append({
            "Situation": label,
            "Gravity": float(value) if valid_value else None,
            "Frames": int(frames) if valid_frames else None,
            "Reliable sample": bool(valid_value and valid_frames and frames >= min_frames),
        })
    return pd.DataFrame(rows)


def strongest_split(summary: pd.DataFrame) -> str | None:
    eligible = summary.loc[summary["Reliable sample"] & summary["Gravity"].notna()]
    if eligible.empty:
        return None
    return str(eligible.loc[eligible["Gravity"].idxmax(), "Situation"])


def teammate_candidates(
    player: pd.Series,
    season: pd.DataFrame,
    min_frames: int = 100,
) -> pd.DataFrame:
    teammates = season.loc[
        (season["Team_ID"] == player["Team_ID"])
        & (season["playerId"] != player["playerId"])
    ].copy()
    if teammates.empty:
        return teammates

    teammates["Display_Name"] = teammates.apply(player_name, axis=1)
    for split_label, (value_column, frame_column) in SPLITS.items():
        if split_label.startswith("Off-ball"):
            reliable_column = f"{value_column}_reliable"
            frames = teammates[frame_column] if frame_column in teammates.columns else pd.Series(pd.NA, index=teammates.index, dtype="Float64")
            teammates[reliable_column] = (
                teammates[value_column].notna()
                & frames.notna()
                & (frames >= min_frames)
            ).fillna(False)
    return teammates.sort_values("Display_Name").reset_index(drop=True)


def game_trend(
    player_id: str,
    games: pd.DataFrame,
    min_frames: int = 500,
) -> pd.DataFrame:
    selected = games.loc[
        (games["playerId"] == player_id) & (games["frames"] >= min_frames)
    ].copy()
    if selected.empty:
        return selected

    team_counts = games.groupby("Game_ID")["teamId"].nunique()
    opponents: dict[str, str] = {}
    for game_id, game_rows in games.groupby("Game_ID"):
        if team_counts.get(game_id) == 2:
            teams = game_rows["teamId"].dropna().unique().tolist()
            selected_team = selected.loc[selected["Game_ID"] == game_id, "teamId"]
            if len(teams) == 2 and not selected_team.empty:
                opponents[game_id] = next((team for team in teams if team != selected_team.iloc[0]), "")

    selected = selected.sort_values("Game_ID").reset_index(drop=True)
    selected["Game_Sequence"] = range(1, len(selected) + 1)
    selected["Inferred_Opponent_Team_ID"] = selected["Game_ID"].map(opponents)
    return selected


def game_teammate_candidates(
    player_id: str,
    games: pd.DataFrame,
    players: pd.DataFrame,
    min_game_frames: int = 500,
    min_split_frames: int = 100,
) -> pd.DataFrame:
    selected = games.loc[(games["playerId"] == player_id) & (games["frames"] >= min_game_frames)]
    if selected.empty:
        return pd.DataFrame()
    joins = selected[["Game_ID", "teamId"]].drop_duplicates().rename(columns={"teamId": "selected_team"})
    candidates = games.merge(joins, on="Game_ID", how="inner")
    candidates = candidates.loc[
        (candidates["teamId"] == candidates["selected_team"])
        & (candidates["playerId"] != player_id)
        & (candidates["frames"] >= min_game_frames)
    ].copy()
    if candidates.empty:
        return candidates

    value_columns = ["offBallPerimeter_averageGravity", "offBallInterior_averageGravity"]
    frame_columns = ["offBallPerimeter_Frames", "offBallInterior_Frames"]
    available_frames = [column for column in frame_columns if column in candidates.columns]
    if available_frames:
        for column in available_frames:
            candidates[column] = pd.to_numeric(candidates[column], errors="coerce")
        candidates = candidates.loc[candidates[available_frames].max(axis=1) >= min_split_frames]
    names = players[["playerId", "Full_Name"]].drop_duplicates("playerId")
    candidates = candidates.merge(names, on="playerId", how="left")
    candidates["Full_Name"] = candidates["Full_Name"].fillna(candidates["playerId"])
    return candidates.groupby(["playerId", "Full_Name"], as_index=False)[value_columns + available_frames].mean(numeric_only=True)