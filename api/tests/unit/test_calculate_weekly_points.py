import os
import sys
import types

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import App  # noqa: E402
from User import User  # noqa: E402


def make_resp(status=200, payload=None):
    return types.SimpleNamespace(
        status_code=status,
        json=lambda: payload or [],
    )


@pytest.fixture(autouse=True)
def reset_globals():
    App.users_dict.clear()
    App.roster_id_lookup_table.clear()
    yield
    App.users_dict.clear()
    App.roster_id_lookup_table.clear()


def seed_users():
    App.users_dict["u1"] = User("Alice", "u1", "Alpha", App.LEAGUE_ID)
    App.users_dict["u2"] = User("Bob", "u2", "Beta", App.LEAGUE_ID)
    App.roster_id_lookup_table[11] = "u1"
    App.roster_id_lookup_table[22] = "u2"


def test_calculate_weekly_points_updates_known_rosters(monkeypatch):
    seed_users()
    payload = [
        {"roster_id": 11, "points": 85.5},
        {"roster_id": 22, "points": 92.0},
        {"roster_id": 33, "points": 75.0},
    ]

    monkeypatch.setattr(App.http, "get", lambda url, timeout=10: make_resp(200, payload))

    App.calculate_weekly_points(App.users_dict, 3)

    assert App.users_dict["u1"].points_per_week[3] == 85.5
    assert App.users_dict["u2"].points_per_week[3] == 92.0
    assert 3 not in App.users_dict.get("u3", User("", "u3", "", App.LEAGUE_ID)).points_per_week


def test_calculate_weekly_points_missing_points_defaults_zero(monkeypatch):
    seed_users()
    payload = [{"roster_id": 11}]
    monkeypatch.setattr(App.http, "get", lambda url, timeout=10: make_resp(200, payload))

    App.calculate_weekly_points(App.users_dict, 5)

    assert App.users_dict["u1"].points_per_week[5] == 0.0


def test_calculate_weekly_points_non_200_leaves_state(monkeypatch):
    seed_users()
    monkeypatch.setattr(App.http, "get", lambda url, timeout=10: make_resp(500, []))

    App.calculate_weekly_points(App.users_dict, 7)

    assert 7 not in App.users_dict["u1"].points_per_week
    assert 7 not in App.users_dict["u2"].points_per_week
