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


def test_populates_users_and_properties():
    data = [
        {"display_name": "Alice", "user_id": "u1", "metadata": {"team_name": "Alpha"}},
        {"display_name": "Bob", "user_id": "u2", "metadata": {"team_name": "Beta"}},
    ]

    App.create_user_dictionary(data)

    assert set(App.users_dict.keys()) == {"u1", "u2"}
    alice = App.users_dict["u1"]
    bob = App.users_dict["u2"]

    assert isinstance(alice, User)
    assert alice.display_name == "Alice"
    assert alice.team_name == "Alpha"
    assert alice.roster_id is None

    assert isinstance(bob, User)
    assert bob.team_name == "Beta"

    assert App.roster_id_lookup_table == {}


def test_clears_previous_state_before_populating():
    App.users_dict["stale"] = "old"
    App.roster_id_lookup_table["99"] = "stale"

    App.create_user_dictionary(
        [{"display_name": "Charlie", "user_id": "c1", "metadata": {"team_name": "Cats"}}]
    )

    assert "stale" not in App.users_dict
    assert App.roster_id_lookup_table == {}
    assert list(App.users_dict.keys()) == ["c1"]


def test_missing_metadata_team_name_gracefully_none():
    App.create_user_dictionary([{"display_name": "Dana", "user_id": "d1"}])

    dana = App.users_dict["d1"]
    assert dana.team_name is None
