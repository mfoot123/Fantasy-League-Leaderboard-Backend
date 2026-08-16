from typing import Dict, Optional


class User:
    def __init__(self, display_name: str, user_id: str, team_name: str, league_id: str):
        self.display_name = display_name
        self.user_id = user_id
        self.team_name = team_name
        self.roster_id: Optional[int] = None
        self.points_per_week: Dict[int, float] = {}
        self.wins: int = 0
        self.losses: int = 0
        self.bracket: Optional[str] = None  # "winners" or "losers"
        self.is_eliminated: bool = False
        self.eliminated_week: Optional[int] = None
