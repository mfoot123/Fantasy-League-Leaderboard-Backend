# Backend/tests/unit/test_get_total_weeks.py
import os
import sys
import types
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import App  # noqa: E402


def make_resp(status=200, payload=None):
    return types.SimpleNamespace(
        status_code=status,
        json=lambda: payload or [],
    )


@pytest.mark.parametrize(
    "status,payload,expected",
    [
        (200, [{"week": 1}, {"week": 1}, {"week": 2}], 2),
        (200, [{"week": w} for w in range(1, 19)], 18),
        (200, [{"week": None}, {}], 1), 
        (404, [], 18), 
    ],
)

def test_get_total_weeks(monkeypatch, status, payload, expected):
    monkeypatch.setattr(App.http, "get", lambda url, timeout=10: make_resp(status, payload))
    assert App.get_total_weeks(2025) == expected


def test_get_total_weeks_on_exception(monkeypatch):
    def boom(url, timeout=10):
        raise ValueError("network fail")

    monkeypatch.setattr(App.http, "get", boom)
    assert App.get_total_weeks(2025) == 18
