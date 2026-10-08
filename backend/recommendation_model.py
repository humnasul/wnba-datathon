"""Gravity Scout: explainable *role-fit* recommendations from WNBA Gravity CSVs.

Usage:
  python recommendation_model.py --data-dir . --team MIN --unavailable 'Kayla McBride'
  python recommendation_model.py --data-dir . --team MIN --unavailable 203825 --top 3

Dependencies: pandas, numpy. A fit score is NOT a success probability.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SITUATIONS = {
    "on_ball_perimeter": ("onBallPerimeter_averageGravity", "onBallPerimeter_Frames"),
    "off_ball_perimeter": ("offBallPerimeter_averageGravity", "offBallPerimeter_Frames"),
    "on_ball_interior": ("onBallInterior_averageGravity", "onBallInterior_Frames"),
    "off_ball_interior": ("offBallInterior_averageGravity", "offBallInterior_Frames"),
}


def _finite(value: Any) -> float | None:
    return round(float(value), 3) if pd.notna(value) and np.isfinite(value) else None


def _weighted_average(frame: pd.DataFrame, score: str, weight: str) -> float:
    good = frame[score].notna() & frame[weight].gt(0)
    if not good.any():
        return float("nan")
    return float(np.average(frame.loc[good, score], weights=frame.loc[good, weight]))


class GravityRecommender:
    def __init__(self, data_dir: str | Path = ".", min_games: int = 3,
                 min_frames: int = 1000, min_situation_frames: int = 300):
        base = Path(data_dir)
        games = pd.read_csv(base / "wnba_gravity_by_game.csv")
        players = pd.read_csv(base / "wnba_player_lookup.csv")
        teams = pd.read_csv(base / "wnba_team_lookup.csv")
        if not (games["Game_ID"].notna().all() and games["playerId"].notna().all()):
            raise ValueError("Missing Game_ID or playerId in game data")
        numeric = ["frames", "averageGravity"] + [c for pair in SITUATIONS.values() for c in pair]
        for c in numeric:
            games[c] = pd.to_numeric(games[c], errors="coerce")
        games["playerId"] = games["playerId"].astype(int)
        games["teamId"] = games["teamId"].astype(int)
        games["Game_ID"] = games["Game_ID"].astype(int)
        players["playerId"] = players["playerId"].astype(int)
        teams["Team_ID"] = teams["Team_ID"].astype(int)
        self.games = games
        self.players = players.drop_duplicates("playerId").set_index("playerId")
        self.teams = teams
        self.min_games = min_games
        self.min_frames = min_frames
        self.min_situation_frames = min_situation_frames
        self.profiles = self._profiles()

    def _profiles(self) -> pd.DataFrame:
        records = []
        # Group by team as well as player to avoid mixing stats from trades.
        for (team, player), g in self.games.groupby(["teamId", "playerId"]):
            record = {"teamId": int(team), "playerId": int(player),
                      "games": int(g["Game_ID"].nunique()),
                      "frames": int(g["frames"].fillna(0).sum()),
                      "overall": _weighted_average(g, "averageGravity", "frames")}
            valid = g.loc[g["averageGravity"].notna() & g["frames"].ge(500), "averageGravity"]
            record["game_std"] = float(valid.std(ddof=0)) if len(valid) >= 2 else np.nan
            for name, (score, weight) in SITUATIONS.items():
                record[name] = _weighted_average(g, score, weight)
                record[name + "_frames"] = int(g[weight].fillna(0).sum())
            records.append(record)
        return pd.DataFrame(records)

    def _resolve_team(self, team: str | int) -> int:
        if str(team).isdigit():
            team_id = int(team)
            match = self.teams[self.teams.Team_ID.eq(team_id)]
        else:
            key = str(team).strip().casefold()
            match = self.teams[(self.teams.Team_Abbreviation.str.casefold() == key) |
                               (self.teams.Team_Full_Name.str.casefold() == key)]
        if len(match) != 1:
            raise ValueError(f"Unknown/ambiguous team: {team}")
        return int(match.iloc[0].Team_ID)

    def _resolve_player(self, unavailable: str | int, team_id: int) -> int:
        roster = self.profiles[self.profiles.teamId.eq(team_id)].playerId
        if str(unavailable).isdigit():
            pid = int(unavailable)
            if pid not in roster.values:
                raise ValueError("Unavailable player not found for selected team")
            return pid
        full_names = self.players["Full_Name"].fillna("").str.casefold()
        ids = self.players.index[full_names == str(unavailable).strip().casefold()]
        ids = [int(pid) for pid in ids if pid in roster.values]
        if len(ids) != 1:
            raise ValueError(f"Player not uniquely identified on team: {unavailable}")
        return ids[0]

    def _name(self, pid: int) -> str:
        return str(self.players.loc[pid, "Full_Name"]) if pid in self.players.index else str(pid)

    def _absence_exploration(self, team_id: int, star_id: int, candidate_id: int) -> dict:
        """Descriptive comparison; star missing from records != verified injury/absence."""
        team_games = set(self.games.loc[self.games.teamId.eq(team_id), "Game_ID"])
        star_games = set(self.games.loc[(self.games.teamId.eq(team_id)) &
                                        (self.games.playerId.eq(star_id)), "Game_ID"])
        candidate = self.games[(self.games.teamId.eq(team_id)) &
                               (self.games.playerId.eq(candidate_id)) &
                               self.games.frames.ge(500)]
        with_star = candidate[candidate.Game_ID.isin(star_games)]
        without_star = candidate[candidate.Game_ID.isin(team_games - star_games)]
        a = _weighted_average(with_star, "averageGravity", "frames")
        b = _weighted_average(without_star, "averageGravity", "frames")
        enough = len(with_star) >= 2 and len(without_star) >= 2 and np.isfinite(a) and np.isfinite(b)
        return {"games_with_star": int(len(with_star)),
                "games_star_not_recorded": int(len(without_star)),
                "mean_gravity_with_star": _finite(a) if enough else None,
                "mean_gravity_without_star": _finite(b) if enough else None,
                "difference": _finite(b-a) if enough else None,
                "interpretation": "Descriptive only; not evidence of causality or confirmed absence."}

    def recommend(self, team: str | int, unavailable: str | int, top_n: int = 3) -> dict:
        team_id = self._resolve_team(team)
        star_id = self._resolve_player(unavailable, team_id)
        roster = self.profiles[self.profiles.teamId.eq(team_id)].copy()
        star = roster[roster.playerId.eq(star_id)].iloc[0]
        candidates = roster[(roster.playerId.ne(star_id)) &
                            (roster.games.ge(self.min_games)) &
                            (roster.frames.ge(self.min_frames))].copy()
        if candidates.empty:
            return {"team_id": team_id, "unavailable_player": self._name(star_id),
                    "recommendations": [], "warning": "No candidates satisfy sample-size thresholds."}

        features = list(SITUATIONS)
        # Use league-wide spread to compare the different situations on similar scales.
        league = self.profiles
        spreads = {k: max(float(league[k].std(skipna=True)), 1.0) for k in features}
        counts = np.array([star[k + "_frames"] for k in features], dtype=float)
        importance = counts / counts.sum() if counts.sum() else np.full(4, .25)
        # Don't entirely ignore a less-common offensive situation.
        weights = .75 * importance + .25 * np.full(4, .25)
        results = []
        max_frames = max(float(candidates.frames.max()), 1.0)
        for _, cand in candidates.iterrows():
            available = np.array([
                (pd.notna(star[k]) and pd.notna(cand[k]) and
                 star[k + "_frames"] >= self.min_situation_frames and
                 cand[k + "_frames"] >= self.min_situation_frames)
                for k in features], dtype=bool)
            coverage = float(weights[available].sum())
            if not available.any() or coverage < .50:
                continue  # Insufficient comparable offensive role evidence
            normalized_deltas = np.array([(float(cand[k])-float(star[k])) / spreads[k]
                                          if available[i] else 0.0
                                          for i, k in enumerate(features)])
            distance = float(np.sqrt(np.sum(weights[available] * normalized_deltas[available]**2) / coverage))
            similarity = 100.0 * np.exp(-distance)  # heuristic scale; NOT a probability
            # Conservative penalty for short samples / missing situation coverage.
            evidence = min(1.0, float(cand.games)/15.0) * min(1.0, float(cand.frames)/max_frames)
            fit_score = round(similarity * (.85 + .15*evidence) * coverage, 1)
            comparable = [k for i,k in enumerate(features) if available[i]]
            closest = sorted(comparable, key=lambda k: abs(float(cand[k])-float(star[k]))/spreads[k])[:2]
            strongest = max(comparable, key=lambda k: float(cand[k]))
            results.append({
                "player_id": int(cand.playerId), "player_name": self._name(int(cand.playerId)),
                "fit_score": fit_score, "role_similarity": round(similarity, 1),
                "profile_coverage": round(coverage, 3),
                "games": int(cand.games), "frames": int(cand.frames),
                "average_gravity": _finite(cand.overall),
                "profile": {k: _finite(cand[k]) for k in features},
                "explanation": (f"Closest comparable Gravity situations: {', '.join(closest)}. "
                                f"Strongest measured situation: {strongest}. "
                                "Fit score measures historical role similarity, not predicted points or wins."),
                "with_without_star": self._absence_exploration(team_id, star_id, int(cand.playerId)),
            })
        results.sort(key=lambda x: (-x["fit_score"], -x["games"], x["player_name"]))
        return {"team_id": team_id, "unavailable_player_id": star_id,
                "unavailable_player": self._name(star_id),
                "unavailable_profile": {k: _finite(star[k]) for k in features},
                "recommendations": results[:max(0, top_n)],
                "method": "Frame-weighted team-season Gravity profiles, standardized distance, situation coverage and sample-size adjustment. Fit scores are relative heuristics, not probabilities.",
                "caution": "Players with no game record are not necessarily injured; with/without comparisons are observational."}


def recommend_replacements(team_id: str | int, unavailable_player_id: str | int,
                           data_dir: str | Path = ".", top_n: int = 3) -> dict:
    return GravityRecommender(data_dir).recommend(team_id, unavailable_player_id, top_n)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=".")
    parser.add_argument("--team", required=True)
    parser.add_argument("--unavailable", required=True)
    parser.add_argument("--top", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(recommend_replacements(args.team, args.unavailable,
                                            args.data_dir, args.top), indent=2))
