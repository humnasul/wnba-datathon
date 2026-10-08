from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[1] / "data"

FILES = {
    "season": "wnba_gravity_season_leaderboards.csv",
    "games": "wnba_gravity_by_game.csv",
    "players": "wnba_player_lookup.csv",
    "teams": "wnba_team_lookup.csv",
}

REQUIRED_COLUMNS = {
    "season": {
        "playerId", "First_Name", "Last_name", "Team_ID", "Team_Abbreviation",
        "Gravity", "GravityScoreAvg", "GP", "MPG", "PPG", "RPG", "APG",
        "onballperimeter_Gravity", "offBallPerimeter_Gravity",
        "onBallInterior_Gravity", "offBallInterior_Gravity",
    },
    "games": {
        "Game_ID", "teamId", "playerId", "frames", "averageGravity",
        "onBallPerimeter_averageGravity", "offBallPerimeter_averageGravity",
        "onBallInterior_averageGravity", "offBallInterior_averageGravity",
    },
    "players": {"playerId", "Full_Name", "Team_ID", "Team_Abbreviation"},
    "teams": {"Team_ID", "Team_Abbreviation", "Team_Full_Name"},
}

OPTIONAL_COLUMNS = {
    "season": {
        "onballperimeter_Frames": ("onballperimeter_Frames", "onballperimeter_frames"),
        "offBallPerimeter_Frames": ("offBallPerimeter_Frames", "offBallPerimeter_frames"),
        "onBallInterior_Frames": ("onBallInterior_Frames", "onBallInterior_frames"),
        "offBallInterior_Frames": ("offBallInterior_Frames", "offBallInterior_frames"),
    },
    "games": {
        "onBallPerimeter_Frames": ("onBallPerimeter_Frames", "onBallPerimeter_frames"),
        "offBallPerimeter_Frames": ("offBallPerimeter_Frames", "offBallPerimeter_frames"),
        "onBallInterior_Frames": ("onBallInterior_Frames", "onBallInterior_frames"),
        "offBallInterior_Frames": ("offBallInterior_Frames", "offBallInterior_frames"),
    },
}

NUMERIC_COLUMNS = {
    "season": (
        "Gravity", "GravityScoreAvg", "GP", "MPG", "PPG", "RPG", "APG",
        "onballperimeter_Gravity", "offBallPerimeter_Gravity",
        "onBallInterior_Gravity", "offBallInterior_Gravity",
        "onballperimeter_Frames", "offBallPerimeter_Frames",
        "onBallInterior_Frames", "offBallInterior_Frames",
    ),
    "games": (
        "frames", "averageGravity", "onBallPerimeter_averageGravity",
        "offBallPerimeter_averageGravity", "onBallInterior_averageGravity",
        "offBallInterior_averageGravity", "onBallPerimeter_Frames",
        "offBallPerimeter_Frames", "onBallInterior_Frames", "offBallInterior_Frames",
    ),
}


class DataLoadError(ValueError):
    """Raised when required event data is missing or does not match its schema."""


def _normalize_id(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def _read_csv(source: Path | bytes | BinaryIO) -> pd.DataFrame:
    if isinstance(source, Path):
        return pd.read_csv(source)
    if isinstance(source, bytes):
        return pd.read_csv(BytesIO(source))
    return pd.read_csv(source)


def load_datasets(
    data_dir: Path = DATA_DIR,
    uploaded_files: dict[str, bytes] | None = None,
) -> dict[str, pd.DataFrame]:
    """Load and validate the four required CSVs without altering source files."""
    uploaded_files = uploaded_files or {}
    frames: dict[str, pd.DataFrame] = {}
    missing: list[str] = []

    for key, filename in FILES.items():
        if filename in uploaded_files:
            source: Path | bytes = uploaded_files[filename]
        else:
            source = data_dir / filename
            if not source.is_file():
                missing.append(filename)
                continue

        frame = _read_csv(source)
        column_lookup = {column.lower(): column for column in frame.columns}
        for canonical, alternatives in OPTIONAL_COLUMNS.get(key, {}).items():
            if canonical not in frame.columns:
                match = next((column_lookup.get(name.lower()) for name in alternatives if name.lower() in column_lookup), None)
                if match:
                    frame = frame.rename(columns={match: canonical})

        absent = sorted(REQUIRED_COLUMNS[key] - set(frame.columns))
        if absent:
            raise DataLoadError(f"{filename} is missing required columns: {', '.join(absent)}")

        for column in NUMERIC_COLUMNS.get(key, ()):
            if column in frame.columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")

        for column in ("playerId", "Team_ID", "teamId", "Game_ID"):
            if column in frame.columns:
                frame[column] = frame[column].map(_normalize_id).astype("string")
        frames[key] = frame

    if missing:
        raise DataLoadError(f"Missing required data files: {', '.join(missing)}")

    return frames