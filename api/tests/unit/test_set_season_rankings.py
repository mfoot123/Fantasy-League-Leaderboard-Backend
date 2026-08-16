import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import App  # noqa: E402
from User import User  # noqa: E402


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
    App.users_dict["u3"] = User("Cara", "u3", "Gamma", App.LEAGUE_ID)
    return App.users_dict


def test_set_season_rankings_accumulates_wins_and_losses(monkeypatch):
    users = seed_users()

    # Pre-fill weekly points so we don't hit HTTP; patch calculate_weekly_points to no-op
    users["u1"].points_per_week = {1: 100.0, 2: 50.0}
    users["u2"].points_per_week = {1: 90.0, 2: 120.0}
    users["u3"].points_per_week = {1: 80.0, 2: 70.0}

    monkeypatch.setattr(App, "calculate_weekly_points", lambda *_args, **_kwargs: None)

    App.set_season_rankings(users, 1, 2)

    assert users["u1"].wins == 2   # idx 2 (wk1) + idx 0 (wk2)
    assert users["u2"].wins == 3   # idx 1 + idx 2
    assert users["u3"].wins == 1   # idx 0 + idx 1

    assert users["u1"].losses == 2  # (2-2)+(2-0)
    assert users["u2"].losses == 1  # (2-1)+(2-2)
    assert users["u3"].losses == 3  # (2-0)+(2-1)


def test_set_season_rankings_handles_missing_points(monkeypatch):
    users = seed_users()

    # Only one user has points; others default to 0.0
    users["u1"].points_per_week = {1: 5.0}
    users["u2"].points_per_week = {}
    users["u3"].points_per_week = {}

    monkeypatch.setattr(App, "calculate_weekly_points", lambda *_args, **_kwargs: None)

    App.set_season_rankings(users, 1, 1)

    # Sorted ascending by points -> u2/u3 (0.0) first, u1 last
    assert users["u1"].wins == 2  # index 2
    assert users["u2"].wins == 0
    assert users["u3"].wins == 1

    assert users["u1"].losses == 0
    assert users["u2"].losses == 2
    assert users["u3"].losses == 1
