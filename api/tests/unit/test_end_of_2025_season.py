import copy
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from App import app  # noqa: E402


# Expected end-of-season snapshot for 2025-2026
EXPECTED_SEASON = {
    "JaredHartwig": {
        "bracket": "losers",
        "eliminated_week": 15,
        "is_eliminated": True,
        "losses": 68,
        "wins": 40,
    },
    "RyanCrosswhite21": {
        "bracket": "losers",
        "eliminated_week": None,
        "is_eliminated": False,
        "losses": 69,
        "wins": 39,
    },
    "TheSebasDog": {
        "bracket": "losers",
        "eliminated_week": 13,
        "is_eliminated": True,
        "losses": 48,
        "wins": 60,
    },
    "YoBoiiShazam": {
        "bracket": "losers",
        "eliminated_week": 14,
        "is_eliminated": True,
        "losses": 51,
        "wins": 57,
    },
    "aminkhatib": {
        "bracket": "winners",
        "eliminated_week": 14,
        "is_eliminated": True,
        "losses": 38,
        "wins": 70,
    },
    "larsomic": {
        "bracket": "winners",
        "eliminated_week": 15,
        "is_eliminated": True,
        "losses": 46,
        "wins": 62,
    },
    "mfoot456": {
        "bracket": "winners",
        "eliminated_week": 13,
        "is_eliminated": True,
        "losses": 38,
        "wins": 70,
    },
    "ptwangbang": {
        "bracket": "losers",
        "eliminated_week": 17,
        "is_eliminated": True,
        "losses": 80,
        "wins": 28,
    },
    "spencedaddy11": {
        "bracket": "winners",
        "eliminated_week": None,
        "is_eliminated": False,
        "losses": 41,
        "wins": 67,
    },
    "spencergeorge21": {
        "bracket": "losers",
        "eliminated_week": 16,
        "is_eliminated": True,
        "losses": 61,
        "wins": 47,
    },
}


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_users_endpoint_returns_expected_snapshot(monkeypatch, client):
    monkeypatch.setattr("App.get_users_wins", lambda _year: copy.deepcopy(EXPECTED_SEASON))

    resp = client.get("/users")
    assert resp.status_code == 200
    assert resp.get_json() == EXPECTED_SEASON


def test_week_endpoint_includes_wins_and_losses(monkeypatch, client):
    """Ensure weekly endpoint returns wins/losses payload when provided."""

    monkeypatch.setattr(
        "App.get_current_week_wins",
        lambda _year: (18, {
            "Alpha": {"wins": 2, "losses": 1},
            "Beta": {"wins": 4, "losses": 0},
        }),
    )

    resp = client.get("/users?week=current")
    assert resp.status_code == 200
    assert resp.get_json() == {
        "week": 18,
        "rankings": {
            "Alpha": {"wins": 2, "losses": 1},
            "Beta": {"wins": 4, "losses": 0},
        },
    }
