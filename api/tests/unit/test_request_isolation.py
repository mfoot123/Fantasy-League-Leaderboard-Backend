import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

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


def response(payload):
    return SimpleNamespace(ok=True, status_code=200, json=lambda: payload)


def test_concurrent_season_and_week_requests_are_isolated(monkeypatch):
    """Parallel calculations must not reset or add to each other's standings."""
    users = [
        {"display_name": "Alpha", "user_id": "u1", "metadata": {"team_name": "A"}},
        {"display_name": "Beta", "user_id": "u2", "metadata": {"team_name": "B"}},
    ]
    rosters = [{"owner_id": "u1", "roster_id": 1}, {"owner_id": "u2", "roster_id": 2}]
    matchups = {
        1: [{"roster_id": 1, "points": 100}, {"roster_id": 2, "points": 10}],
        2: [{"roster_id": 1, "points": 20}, {"roster_id": 2, "points": 120}],
    }
    first_matchups = threading.Barrier(2)
    matchup_calls = 0
    call_lock = threading.Lock()

    def fake_get(url, timeout=10):
        nonlocal matchup_calls
        if url.endswith("/users"):
            return response(users)
        if url.endswith("/rosters"):
            return response(rosters)

        week = int(url.rsplit("/", 1)[1])
        with call_lock:
            matchup_calls += 1
            should_wait = matchup_calls <= 2
        if should_wait:
            first_matchups.wait(timeout=3)
        return response(matchups[week])

    # A poisoned legacy cache confirms that calculations only use local state.
    App.users_dict["stale"] = User("Stale", "stale", "Old", App.LEAGUE_ID)
    App.roster_id_lookup_table[999] = "stale"
    monkeypatch.setattr(App.http, "get", fake_get)
    monkeypatch.setattr(App, "get_effective_season_data", lambda: (2025, 2))
    monkeypatch.setattr(App, "get_total_weeks", lambda _year: 18)

    with ThreadPoolExecutor(max_workers=2) as executor:
        season_future = executor.submit(App.get_users_wins, 2025)
        week_future = executor.submit(App.get_current_week_wins, 2025)
        season = season_future.result(timeout=5)
        week, rankings = week_future.result(timeout=5)

    assert season == {
        "Alpha": {
            "wins": 1,
            "losses": 1,
            "bracket": None,
            "is_eliminated": False,
            "eliminated_week": None,
        },
        "Beta": {
            "wins": 1,
            "losses": 1,
            "bracket": None,
            "is_eliminated": False,
            "eliminated_week": None,
        },
    }
    assert week == 2
    assert rankings == {
        "Alpha": {"wins": 0, "losses": 1},
        "Beta": {"wins": 1, "losses": 0},
    }
    assert set(App.users_dict) == {"stale"}
    assert App.roster_id_lookup_table == {999: "stale"}
