import os
import sys
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


@pytest.fixture
def client():
    with App.app.test_client() as client:
        yield client


def test_get_users_current_uses_request_local_users(monkeypatch, client):
    """Week=current should build a fresh user set and return its rankings."""

    payload = [
        {"display_name": "Alpha", "user_id": "u1", "metadata": {"team_name": "Team A"}},
        {"display_name": "Beta", "user_id": "u2", "metadata": {"team_name": "Team B"}},
    ]

    call_log = {"http_calls": 0}

    def fake_http_get(url, timeout=10):
        call_log["http_calls"] += 1
        call_log["users_url"] = url
        return SimpleNamespace(json=lambda: payload, status_code=200, ok=True)

    def fake_build_user_dictionary(users):
        call_log["created_with"] = users
        request_users = {}
        for entry in users:
            request_users[entry["user_id"]] = User(
                entry["display_name"],
                entry["user_id"],
                entry["metadata"]["team_name"],
                App.LEAGUE_ID,
            )
        return request_users

    def fake_determine_user_roster_numbers(users_by_id_dict, roster_lookup):
        call_log["rosters_called"] = True
        assert roster_lookup == {}

    def fake_set_current_week_rankings(users_by_id_dict, year, roster_lookup):
        call_log["ranked_ids"] = set(users_by_id_dict.keys())
        call_log["year"] = year
        for idx, user in enumerate(users_by_id_dict.values()):
            user.wins = idx
            user.losses = len(users_by_id_dict) - idx - 1
        return 12

    monkeypatch.setattr(App.http, "get", fake_http_get)
    monkeypatch.setattr(App, "build_user_dictionary", fake_build_user_dictionary)
    monkeypatch.setattr(App, "determine_user_roster_numbers", fake_determine_user_roster_numbers)
    monkeypatch.setattr(App, "set_current_week_rankings", fake_set_current_week_rankings)

    resp = client.get("/users?week=current")

    assert resp.status_code == 200
    assert call_log["http_calls"] == 1
    assert call_log["users_url"].endswith(f"/league/{App.LEAGUE_ID}/users")
    assert call_log["created_with"] == payload
    assert call_log.get("rosters_called") is True
    assert call_log["ranked_ids"] == {"u1", "u2"}
    assert call_log["year"] == App.DEFAULT_YEAR
    assert resp.get_json() == {
        "week": 12,
        "rankings": {
            "Alpha": {"wins": 0, "losses": 1},
            "Beta": {"wins": 1, "losses": 0},
        },
    }


def test_get_users_forwards_requested_year(monkeypatch, client):
    expected = {"Alpha": {"wins": 2, "losses": 1}}
    called_with = []

    def fake_get_users_wins(year):
        called_with.append(year)
        return expected

    monkeypatch.setattr(App, "get_users_wins", fake_get_users_wins)

    response = client.get("/users?year=2026")

    assert response.status_code == 200
    assert response.get_json() == expected
    assert called_with == [2026]


def test_get_users_rejects_non_numeric_year(client):
    response = client.get("/users?year=next")

    assert response.status_code == 400
    assert response.get_json() == {"error": "year must be a whole number"}


def test_root_reports_backend_health(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "users_endpoint": "/users?year=2025",
    }
