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

def test_set_winners_and_losers_after_current_week(monkeypatch):
    users = seed_users(count=10)
    week = 4

    for idx, uid in enumerate(list(users.keys())):
        users[uid].points_per_week = {week: idx}

    monkeypatch.setattr(App, "get_effective_season_data", lambda: (2025, week))
    monkeypatch.setattr(App, "calculate_weekly_points", lambda *_args, **_kwargs: None)

    App.set_current_week_rankings(users, App.DEFAULT_YEAR)
    App.set_winners_and_losers()

    winners = [u for u in users.values() if u.bracket == "winners"]
    losers = [u for u in users.values() if u.bracket == "losers"]

    assert len(winners) == App.WINNERS  # top 4
    assert len(losers) == App.LOSERS    # bottom 6

    top_ids = [u.user_id for u in sorted(users.values(), key=lambda u: u.points_per_week[week], reverse=True)[:App.WINNERS]]
    bottom_ids = [u.user_id for u in sorted(users.values(), key=lambda u: u.points_per_week[week])[:App.LOSERS]]

    assert set(u.user_id for u in winners) == set(top_ids)
    assert set(u.user_id for u in losers) == set(bottom_ids)


def test_set_current_week_rankings_with_ten_users(monkeypatch):
    users = seed_users(count=10)
    week = 12

    for idx, uid in enumerate(list(users.keys())):
        users[uid].points_per_week = {week: 100 - idx * 5}

    monkeypatch.setattr(App, "get_effective_season_data", lambda: (2025, week))
    monkeypatch.setattr(App, "calculate_weekly_points", lambda *_args, **_kwargs: None)

    App.set_current_week_rankings(users, App.DEFAULT_YEAR)

    # verify top and bottom only to keep test concise
    assert users["u1"].wins == 9  # best score, but sorted ascending wins are index (worst=0)
    assert users["u10"].wins == 0  # worst score gets index 0
    assert users["u1"].losses == 0
    assert users["u10"].losses == 9
