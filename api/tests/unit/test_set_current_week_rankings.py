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


def seed_users(count=3):
    names = [
        ("u1", "Alice", "Alpha"),
        ("u2", "Bob", "Beta"),
        ("u3", "Cara", "Gamma"),
        ("u4", "Dan", "Delta"),
        ("u5", "Elle", "Echo"),
        ("u6", "Finn", "Foxtrot"),
        ("u7", "Gus", "Golf"),
        ("u8", "Hana", "Hotel"),
        ("u9", "Ivan", "India"),
        ("u10", "Jade", "Juliet"),
    ]
    for uid, name, team in names[:count]:
        App.users_dict[uid] = User(name, uid, team, App.LEAGUE_ID)
    return App.users_dict


def test_set_current_week_rankings_uses_effective_week(monkeypatch):
    users = seed_users()
    # Pretend effective week is 5
    monkeypatch.setattr(App, "get_effective_season_data", lambda: (2025, 5))
    # Stub weekly points calculator to do nothing so we can prefill
    monkeypatch.setattr(App, "calculate_weekly_points", lambda *_args, **_kwargs: None)

    users["u1"].points_per_week = {5: 10}
    users["u2"].points_per_week = {5: 30}
    users["u3"].points_per_week = {5: 20}

    assert App.set_current_week_rankings(users, App.DEFAULT_YEAR) == 5

    # Sorted ascending → u1 (idx0), u3 (idx1), u2 (idx2)
    assert users["u1"].wins == 0
    assert users["u3"].wins == 1
    assert users["u2"].wins == 2

    assert users["u1"].losses == 2
    assert users["u3"].losses == 1
    assert users["u2"].losses == 0


def test_set_current_week_rankings_missing_points_default_zero(monkeypatch):
    users = seed_users()
    monkeypatch.setattr(App, "get_effective_season_data", lambda: (2025, 9))
    monkeypatch.setattr(App, "calculate_weekly_points", lambda *_args, **_kwargs: None)

    users["u1"].points_per_week = {}          # defaults to 0
    users["u2"].points_per_week = {9: 5.0}
    users["u3"].points_per_week = {9: -1.0}

    assert App.set_current_week_rankings(users, App.DEFAULT_YEAR) == 9

    # Week 9 points: u1=0, u2=5, u3=-1 → order: u3 (idx0), u1 (idx1), u2 (idx2)
    assert users["u3"].wins == 0
    assert users["u1"].wins == 1
    assert users["u2"].wins == 2

    assert users["u3"].losses == 2
    assert users["u1"].losses == 1
    assert users["u2"].losses == 0
