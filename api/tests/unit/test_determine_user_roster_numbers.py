import os
import sys
import types

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import App 
from User import User


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


def test_assigns_roster_ids_and_lookup(monkeypatch):
    seed_users()
    payload = [
        {"owner_id": "u1", "roster_id": 11},
        {"owner_id": "u2", "roster_id": 22},
        {"owner_id": "u3", "roster_id": 33},  # unknown user -> ignored
    ]

    monkeypatch.setattr(App.http, "get", lambda url, timeout=10: make_resp(200, payload))

    App.determine_user_roster_numbers()

    assert App.users_dict["u1"].roster_id == 11
    assert App.users_dict["u2"].roster_id == 22
    assert App.roster_id_lookup_table == {11: "u1", 22: "u2"}


def test_non_200_response_leaves_state_unchanged(monkeypatch):
    seed_users()
    App.users_dict["u1"].roster_id = None

    monkeypatch.setattr(App.http, "get", lambda url, timeout=10: make_resp(500, []))

    App.determine_user_roster_numbers()

    assert App.users_dict["u1"].roster_id is None
    assert App.roster_id_lookup_table == {}
