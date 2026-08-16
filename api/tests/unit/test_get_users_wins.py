import os
import sys
import types

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import App
from User import User


@pytest.fixture(autouse=True)
def reset_globals():
    App.users_dict.clear()
    App.roster_id_lookup_table.clear()
    yield
    App.users_dict.clear()
    App.roster_id_lookup_table.clear()


def make_resp(ok=True):
    return types.SimpleNamespace(
        ok=ok,
        status_code=200 if ok else 500,
        json=lambda: [],
    )


def test_get_users_wins_returns_empty_on_failed_users_fetch(monkeypatch):
    monkeypatch.setattr(App, "get_effective_season_data", lambda: (2025, 5))
    monkeypatch.setattr(App, "get_total_weeks", lambda _year: 18)
    monkeypatch.setattr(App, "determine_user_roster_numbers", lambda *_args: None)
    monkeypatch.setattr(App, "build_user_dictionary", lambda _users: pytest.fail("unexpected user creation"))
    monkeypatch.setattr(App, "set_season_rankings", lambda *_args, **_kwargs: pytest.fail("ranking should not run"))

    monkeypatch.setattr(App.http, "get", lambda url, timeout=10: make_resp(ok=False))

    assert App.get_users_wins(App.DEFAULT_YEAR) == {}
    assert App.users_dict == {}


def test_get_users_wins_regular_season_path(monkeypatch):
    monkeypatch.setattr(App, "get_effective_season_data", lambda: (2025, 3))
    monkeypatch.setattr(App, "get_total_weeks", lambda _year: 18)
    monkeypatch.setattr(App, "determine_user_roster_numbers", lambda *_args: None)
    monkeypatch.setattr(App, "set_winners_and_losers", lambda *_args: pytest.fail("playoff seeding should not run"))
    monkeypatch.setattr(App, "drop_week_extremes_from_brackets", lambda *_args: pytest.fail("playoff drop should not run"))

    call_log = {}

    def fake_build_user_dictionary(_payload):
        return {
            "u1": User("Alpha", "u1", "Team A", App.LEAGUE_ID),
            "u2": User("Beta", "u2", "Team B", App.LEAGUE_ID),
        }

    def fake_set_season_rankings(users_by_id_dict, min_week, max_week, roster_lookup):
        call_log["season_range"] = (min_week, max_week)
        for idx, user in enumerate(users_by_id_dict.values()):
            user.wins = 10 - idx
            user.losses = idx

    monkeypatch.setattr(App, "build_user_dictionary", fake_build_user_dictionary)
    monkeypatch.setattr(App, "set_season_rankings", fake_set_season_rankings)
    monkeypatch.setattr(App.http, "get", lambda url, timeout=10: make_resp(ok=True))

    result = App.get_users_wins(App.DEFAULT_YEAR)

    assert call_log.get("season_range") == (1, 3)
    assert result == {
        "Alpha": {
            "wins": 10,
            "losses": 0,
            "bracket": None,
            "is_eliminated": False,
            "eliminated_week": None,
        },
        "Beta": {
            "wins": 9,
            "losses": 1,
            "bracket": None,
            "is_eliminated": False,
            "eliminated_week": None,
        },
    }


def test_get_users_wins_runs_playoff_path(monkeypatch):
    monkeypatch.setattr(App, "get_effective_season_data", lambda: (2025, 15))
    monkeypatch.setattr(App, "get_total_weeks", lambda _year: 18)
    monkeypatch.setattr(App, "determine_user_roster_numbers", lambda *_args: None)

    range_calls = {}
    calc_weeks = []
    drop_weeks = []
    winners_called = False

    def fake_build_user_dictionary(_payload):
        return {
            "u1": User("WinnerOne", "u1", "Team A", App.LEAGUE_ID),
            "u2": User("WinnerTwo", "u2", "Team B", App.LEAGUE_ID),
            "u3": User("Loser", "u3", "Team C", App.LEAGUE_ID),
        }

    def fake_set_season_rankings(users_by_id_dict, min_week, max_week, roster_lookup):
        range_calls["season_range"] = (min_week, max_week)
        for idx, user in enumerate(users_by_id_dict.values()):
            user.wins = 5 - idx
            user.losses = idx

    def fake_set_winners_and_losers(users_by_id_dict):
        nonlocal winners_called
        winners_called = True
        users_by_id_dict["u1"].bracket = "winners"
        users_by_id_dict["u2"].bracket = "winners"
        users_by_id_dict["u3"].bracket = "losers"

    def fake_calculate_weekly_points(users_by_id_dict, week, roster_lookup):
        calc_weeks.append(week)
        for user in users_by_id_dict.values():
            user.points_per_week[week] = 50.0 if user.user_id == "u3" else 100.0

    def fake_drop_week_extremes_from_brackets(week, users_by_id_dict):
        drop_weeks.append(week)
        if week == 13:
            loser = users_by_id_dict["u3"]
            loser.is_eliminated = True
            loser.eliminated_week = week

    monkeypatch.setattr(App, "build_user_dictionary", fake_build_user_dictionary)
    monkeypatch.setattr(App, "set_season_rankings", fake_set_season_rankings)
    monkeypatch.setattr(App, "set_winners_and_losers", fake_set_winners_and_losers)
    monkeypatch.setattr(App, "calculate_weekly_points", fake_calculate_weekly_points)
    monkeypatch.setattr(App, "drop_week_extremes_from_brackets", fake_drop_week_extremes_from_brackets)
    monkeypatch.setattr(App.http, "get", lambda url, timeout=10: make_resp(ok=True))

    result = App.get_users_wins(App.DEFAULT_YEAR)

    assert range_calls.get("season_range") == (1, 12)
    assert winners_called is True
    assert calc_weeks == [13, 14, 15]
    assert drop_weeks == [13, 14, 15]

    assert result["Loser"]["bracket"] == "losers"
    assert result["Loser"]["is_eliminated"] is True
    assert result["Loser"]["eliminated_week"] == 13
    assert result["WinnerOne"]["bracket"] == "winners"
    assert result["WinnerOne"]["is_eliminated"] is False
    assert result["WinnerTwo"]["wins"] == 4
    assert result["WinnerTwo"]["losses"] == 1
