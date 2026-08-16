import os
import sys
import types

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import App  # noqa: E402


def make_resp(payload):
    return types.SimpleNamespace(
        status_code=200,
        json=lambda: payload,
    )


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"season": "2026", "season_type": "regular", "week": 5}, (2026, 5)),
        ({"season": "2026", "season_type": "off", "week": 1}, (2025, 18)),
        ({"season": "2026", "season_type": "pre", "week": 0}, (2025, 18)),
        ({"season": "2026", "season_type": "regular", "week": 0}, (2025, 18)),
        ({}, (2025, 18)),
    ],
)
def test_get_effective_season_data(monkeypatch, payload, expected):
    def fake_get(url, timeout=10):
        return make_resp(payload)

    monkeypatch.setattr(App.http, "get", fake_get)
    assert App.get_effective_season_data() == expected


def test_get_effective_season_data_on_exception(monkeypatch):
    def fake_get(url, timeout=10):
        raise ValueError("network fail")

    monkeypatch.setattr(App.http, "get", fake_get)
    assert App.get_effective_season_data() == (2025, 18)
