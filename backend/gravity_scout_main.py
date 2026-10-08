"""Gravity Scout API: run with `uvicorn main:app --reload` from backend/.

Set WNBA_DATA_DIR to the directory containing the recommendation_features.csv.
Swagger docs: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from recommendation_model import GravityRecommender

app = FastAPI(title="Gravity Scout API", version="1.0.0", description="Explainable WNBA Gravity role-fit recommendations")

# In production, set CORS_ORIGINS to a comma-separated list of frontend URLs.
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=["*"])


def data_dir() -> Path:
    configured = os.getenv("WNBA_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    here = Path(__file__).resolve().parent
    # CSVs may reside in backend/ or the repository root.
    for directory in (here, here.parent):
        if (directory / "recommendation_features.csv").is_file():
            return directory
    return here.parent


@lru_cache(maxsize=1)
def _load_engine() -> GravityRecommender:
    return GravityRecommender(data_dir())


def get_engine() -> GravityRecommender:
    # This override lets tests inject a fixture without modifying real data.
    return getattr(app.state, "test_engine", None) or _load_engine()


def engine_or_503() -> GravityRecommender:
    try:
        return get_engine()
    except (FileNotFoundError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail=f"WNBA data unavailable or invalid: {exc}") from exc


@app.get("/health")
def health():
    return {"status": "ok", "service": "gravity-scout"}


@app.get("/teams")
def teams():
    engine = engine_or_503()
    rows = engine.teams.sort_values("Team_Full_Name")
    return [{"team_id": int(r.Team_ID), "abbreviation": str(r.Team_Abbreviation),
             "name": str(r.Team_Full_Name)} for r in rows.itertuples(index=False)]


@app.get("/teams/{team}/players")
def players(team: str):
    engine = engine_or_503()
    try:
        team_id = engine._resolve_team(team)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    roster = engine.profiles[engine.profiles.teamId.eq(team_id)].sort_values("games", ascending=False)
    return {"team_id": team_id, "players": [
        {"player_id": int(r.playerId), "name": engine._name(int(r.playerId)),
         "games": int(r.games), "frames": int(r.frames)}
        for r in roster.itertuples(index=False)
    ]}


@app.get("/recommendations")
def recommendations(
    team: str = Query(..., description="Team abbreviation (MIN) or numeric team ID"),
    unavailable: str = Query(..., description="Player name or numeric player ID"),
    top_n: int = Query(3, ge=1, le=20),
):
    engine = engine_or_503()
    try:
        return engine.recommend(team=team, unavailable=unavailable, top_n=top_n)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
