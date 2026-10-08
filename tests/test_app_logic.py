import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.analytics import game_trend, split_summary, strongest_split, teammate_candidates
from src.court_visuals import build_court
from src.data_loader import FILES, REQUIRED_COLUMNS, DataLoadError, load_datasets
from src.tactics import tactical_options


def season_row(player_id, first, team, gravity, perimeter, off_perimeter, interior, off_interior, frames=200):
    return {
        "playerId": player_id, "First_Name": first, "Last_name": "Player", "Team_ID": team,
        "Team_Abbreviation": "TST", "Gravity": gravity, "GravityScoreAvg": gravity + 0.2,
        "GP": 10, "MPG": 30, "PPG": 15, "RPG": 5, "APG": 4,
        "onballperimeter_Gravity": perimeter, "offBallPerimeter_Gravity": off_perimeter,
        "onBallInterior_Gravity": interior, "offBallInterior_Gravity": off_interior,
        "onballperimeter_Frames": frames, "offBallPerimeter_Frames": frames,
        "onBallInterior_Frames": frames, "offBallInterior_Frames": frames,
    }


class AnalyticsTests(unittest.TestCase):
    def test_split_reliability_and_strongest_uses_only_reliable_samples(self):
        player = pd.Series(season_row("1", "Star", "A", 8, 2, 9, 4, 10, frames=200))
        player["offBallInterior_Frames"] = 25
        summary = split_summary(player, min_frames=100)
        self.assertEqual(strongest_split(summary), "Off-ball perimeter")
        self.assertFalse(summary.loc[summary["Situation"] == "Off-ball interior", "Reliable sample"].iloc[0])

    def test_teammates_are_selected_by_team_id_not_name(self):
        season = pd.DataFrame([
            season_row("1", "Star", "A", 8, 2, 9, 4, 10),
            season_row("2", "Teammate", "A", 3, 1, 5, 1, 4),
            season_row("3", "Other", "B", 12, 8, 9, 8, 10),
        ])
        teammates = teammate_candidates(season.iloc[0], season)
        self.assertEqual(teammates["playerId"].tolist(), ["2"])

    def test_game_trend_filters_frames_and_does_not_use_date(self):
        games = pd.DataFrame([
            {"playerId": "1", "Game_ID": "002", "teamId": "A", "frames": 700, "averageGravity": 4.0},
            {"playerId": "1", "Game_ID": "001", "teamId": "A", "frames": 450, "averageGravity": 99.0},
            {"playerId": "1", "Game_ID": "003", "teamId": "A", "frames": 800, "averageGravity": 6.0},
        ])
        trend = game_trend("1", games, min_frames=500)
        self.assertEqual(trend["Game_ID"].tolist(), ["002", "003"])
        self.assertEqual(trend["Game_Sequence"].tolist(), [1, 2])
        self.assertNotIn("Date", trend.columns)


class TacticsTests(unittest.TestCase):
    def test_scenario_clock_and_objective_change_explanations(self):
        double = tactical_options("Star", -2, 12, "Star double-teamed", "Need 3 points", "Wing")
        paint = tactical_options("Star", 1, 4, "Paint crowded", "Need 2 points", "Wing")
        self.assertIn("Wing", double[0]["why"])
        self.assertIn("12 seconds", double[0]["why"])
        self.assertIn("three points", double[0]["why"])
        self.assertIn("ahead by 1", paint[0]["why"].lower())
        self.assertIn("4 seconds", paint[0]["why"])
        self.assertNotEqual(double[0]["title"], paint[0]["title"])
        self.assertNotIn("probability", " ".join(option["why"] for option in double).lower())

    def test_objective_clock_and_score_change_option_framing(self):
        late_three = tactical_options("Star", -2, 4, "Star double-teamed", "Need 3 points", "Wing")
        early_two = tactical_options("Star", 1, 18, "Star double-teamed", "Need 2 points", "Wing")
        self.assertIn("quick", late_three[0]["title"].lower())
        self.assertIn("perimeter-oriented", late_three[0]["why"].lower())
        self.assertIn("two points", early_two[0]["why"].lower())
        self.assertIn("ahead by 1", early_two[0]["why"].lower())
        self.assertIn("trails by 2", late_three[0]["why"].lower())
        lead_late = tactical_options("Star", 1, 4, "Star double-teamed", "Need 2 points", "Wing")
        trail_late = tactical_options("Star", -1, 4, "Star double-teamed", "Need 2 points", "Wing")
        self.assertIn("keep", lead_late[0]["title"].lower())
        self.assertIn("off-ball", trail_late[0]["title"].lower())


class CourtTests(unittest.TestCase):
    def test_court_uses_player_names_and_hypothetical_route(self):
        figure = build_court(0, "Star double-teamed", ["Star Name #7", "Wing Name #3"], "Star Name", "Wing Name #3")
        offense = next(trace for trace in figure.data if trace.name == "Hypothetical offense")
        self.assertIn("Star Name", " ".join(offense.text))
        self.assertTrue(any(annotation.showarrow for annotation in figure.layout.annotations))


class DataLoaderTests(unittest.TestCase):
    def test_uploads_load_without_optional_replay_or_split_frame_columns(self):
        source_frames = {}
        for key, filename in FILES.items():
            columns = REQUIRED_COLUMNS[key]
            values = {column: ["1"] for column in columns}
            if key == "season":
                values["First_Name"] = ["Test"]
                values["Last_name"] = ["Player"]
                values["Gravity"] = ["not-a-number"]
                values["Team_Abbreviation"] = ["TST"]
            elif key == "games":
                values["Game_ID"] = ["001"]
                values["averageGravity"] = ["4.5"]
            elif key == "players":
                values["Full_Name"] = ["Test Player"]
                values["Team_Abbreviation"] = ["TST"]
            elif key == "teams":
                values["Team_Abbreviation"] = ["TST"]
                values["Team_Full_Name"] = ["Test Team"]
            source_frames[filename] = pd.DataFrame(values).to_csv(index=False).encode()

        loaded = load_datasets(uploaded_files=source_frames)
        self.assertEqual(set(loaded), set(FILES))
        self.assertTrue(pd.isna(loaded["season"].iloc[0]["Gravity"]))
        self.assertEqual(loaded["games"].iloc[0]["averageGravity"], 4.5)
        self.assertNotIn("wnba_gravity_sample.csv", FILES.values())

    def test_missing_event_csvs_are_reported(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(DataLoadError, "Missing required data files"):
                load_datasets(Path(directory))


if __name__ == "__main__":
    unittest.main()