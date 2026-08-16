import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import App
from User import User


@pytest.fixture(autouse=True)
def reset_globals():
    App.users_dict.clear()
    App.roster_id_lookup_table.clear()
    yield
    App.users_dict.clear()
    App.roster_id_lookup_table.clear()


def make_user(uid, bracket, points, eliminated=False):
    user = User(f"User {uid}", uid, f"Team {uid}", App.LEAGUE_ID)
    user.bracket = bracket
    user.points_per_week = points
    user.is_eliminated = eliminated
    return user


def test_drop_week_extremes_eliminates_lowest_winner_and_highest_loser():
    week = 3
    winners_high_total = make_user("u2", "winners", {3: 10, 1: 10})
    winners_low_total = make_user("u1", "winners", {3: 10, 1: 5})
    losers_low_total = make_user("u3", "losers", {3: 5, 1: 20})
    losers_high_total = make_user("u4", "losers", {3: 5, 1: 25})

    # Insert in an order that would pick the first element if tie-breakers were missing
    for u in [winners_high_total, winners_low_total, losers_low_total, losers_high_total]:
        App.users_dict[u.user_id] = u

    App.drop_week_extremes_from_brackets(week)

    assert winners_low_total.is_eliminated is True
    assert winners_low_total.eliminated_week == week
    assert winners_high_total.is_eliminated is False

    assert losers_high_total.is_eliminated is True
    assert losers_high_total.eliminated_week == week
    assert losers_low_total.is_eliminated is False


def test_drop_week_extremes_does_nothing_with_single_active_per_bracket():
    week = 7
    active_winner = make_user("u1", "winners", {week: 15})
    eliminated_winner = make_user("u2", "winners", {week: 10}, eliminated=True)
    active_loser = make_user("u3", "losers", {week: 3})
    eliminated_loser = make_user("u4", "losers", {week: 9}, eliminated=True)

    for u in [active_winner, eliminated_winner, active_loser, eliminated_loser]:
        App.users_dict[u.user_id] = u

    App.drop_week_extremes_from_brackets(week)

    assert active_winner.is_eliminated is False
    assert active_winner.eliminated_week is None
    assert eliminated_winner.is_eliminated is True
    assert eliminated_winner.eliminated_week is None
    assert active_loser.is_eliminated is False
    assert active_loser.eliminated_week is None
