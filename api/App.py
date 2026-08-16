import os
from typing import Dict, List, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from User import User

app = Flask(__name__)

cors_origins = os.getenv("CORS_ORIGINS", "*")
parsed_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
CORS(app, resources={r"/*": {"origins": parsed_origins if len(parsed_origins) > 1 or parsed_origins[0] != "*" else "*"}})

http = requests.Session()
http.headers.update(
    {
        "User-Agent": "fantasy-leaderboard/1.0 (+https://github.com/mitchfooter/fantasy-league-leaderboard)",
        "Accept": "application/json",
    }
)

LEAGUE_ID = "1257085186806382592"
PEOPLE_IN_LEAGUE = 10
LOSERS = 6
WINNERS = 4
DEFAULT_YEAR = 2025

# Id, User
users_dict: Dict[str, User] = {}
# roster Id, User Id
roster_id_lookup_table: Dict[str, str] = {}

rankings: List[User] = []

def get_effective_season_data():
    state_url = "https://api.sleeper.app/v1/state/nfl"
    try:
        resp = http.get(state_url, timeout=10).json()
        current_year = int(resp.get("season"))
        season_type = resp.get("season_type") 
        current_week = resp.get("week", 1)

        # If off-season, pre-season, or before week 1, look at last year's end
        if season_type in ["off", "pre"] or current_week < 1:
            return current_year - 1, 18 
        
        return current_year, current_week
    except Exception as e:
        print(f"Error determining season: {e}")
        return 2025, 18
    
def get_total_weeks(year):
    url = f"https://api.sleeper.app/v1/nfl/schedule/{year}"
    try:
        response = http.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return len({game.get("week") for game in data})
    except:
        pass
    return 18

def build_user_dictionary(users) -> Dict[str, User]:
    users_by_id_dict: Dict[str, User] = {}
    for user in users:
        newUser = User(
            display_name=user.get("display_name"),
            user_id=user.get("user_id"),
            team_name=user.get("metadata", {}).get("team_name"),
            league_id=LEAGUE_ID
        )

        users_by_id_dict[newUser.user_id] = newUser

    return users_by_id_dict


def create_user_dictionary(users):
    users_dict.clear()
    users_dict.update(build_user_dictionary(users))
    roster_id_lookup_table.clear()

def determine_user_roster_numbers(users_by_id_dict=None, roster_lookup=None):
    if users_by_id_dict is None:
        users_by_id_dict = users_dict
    if roster_lookup is None:
        roster_lookup = roster_id_lookup_table

    rosters_url = f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters"
    response = http.get(rosters_url, timeout=10)
    
    if response.status_code == 200:
        for roster in response.json():
            user_id = roster["owner_id"]
            if user_id in users_by_id_dict:
                users_by_id_dict[user_id].roster_id = roster["roster_id"]
                roster_lookup[roster["roster_id"]] = user_id

def calculate_weekly_points(users_by_id_dict, week: int, roster_lookup=None):
    if roster_lookup is None:
        roster_lookup = roster_id_lookup_table

    matchups_url = f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/{week}"
    matchups_response = http.get(matchups_url, timeout=10)

    if matchups_response.status_code == 200:
            for matchup in matchups_response.json():
                roster_id = matchup.get("roster_id")
                # Safety check: Only process rosters we know about
                if roster_id in roster_lookup:
                    user_id = roster_lookup[roster_id]
                    # Only update if the user belongs to this request.
                    if user_id in users_by_id_dict:
                        current_user = users_by_id_dict[user_id]
                        current_user.points_per_week[week] = matchup.get("points", 0.0)
    else:
        print(f"Failed to fetch matchups for week {week} (status code {matchups_response.status_code})")
    
def set_season_rankings(users_by_id_dict, min_week, max_week, roster_lookup=None):
    for user in users_by_id_dict.values():
        user.wins = 0
        user.losses = 0

    for week in range(min_week, max_week + 1):
        calculate_weekly_points(users_by_id_dict, week, roster_lookup)

        weekly_rankings = sorted(
            users_by_id_dict.values(),
            key=lambda u: u.points_per_week.get(week, 0.0),
            reverse=False
        )
        for i, user in enumerate(weekly_rankings):
            user.wins += i
            user.losses += (len(weekly_rankings) - 1 - i)

def set_current_week_rankings(users_by_id_dict, year: int, roster_lookup=None) -> Optional[int]:
    for user in users_by_id_dict.values():
        user.wins = 0
        user.losses = 0

    effective_year, week = get_effective_season_data()
    if year < effective_year:
        week = get_total_weeks(year)
    elif year > effective_year:
        return None

    calculate_weekly_points(users_by_id_dict, week, roster_lookup)

    weekly_rankings = sorted(
        users_by_id_dict.values(),
        key=lambda u: u.points_per_week.get(week, 0.0),
        reverse=False
    )

    for i, user in enumerate(weekly_rankings):
        user.wins += i
        user.losses += (len(weekly_rankings) - 1 - i)

    return week

def set_winners_and_losers(users_by_id_dict=None):
    if users_by_id_dict is None:
        users_by_id_dict = users_dict

    ranked_users = sorted(
            users_by_id_dict.values(),
            key=lambda u: (u.wins, sum(u.points_per_week.values())),
            reverse=True
        )
        
    for user in ranked_users[:WINNERS]:
        user.bracket = "winners"
    for user in ranked_users[-LOSERS:]:
        user.bracket = "losers"

def drop_week_extremes_from_brackets(week: int, users_by_id_dict=None):
    if users_by_id_dict is None:
        users_by_id_dict = users_dict

    active_winners = [u for u in users_by_id_dict.values() if u.bracket == "winners" and not u.is_eliminated]
    if len(active_winners) > 1:
        lowest = min(active_winners, key=lambda u: (u.points_per_week.get(week, 0.0), sum(u.points_per_week.values())))
        lowest.is_eliminated = True
        lowest.eliminated_week = week

    active_losers = [u for u in users_by_id_dict.values() if u.bracket == "losers" and not u.is_eliminated]
    if len(active_losers) > 1:
        highest = max(active_losers, key=lambda u: (u.points_per_week.get(week, 0.0), sum(u.points_per_week.values())))
        highest.is_eliminated = True
        highest.eliminated_week = week


def get_request_users():
    """Fetch league data into objects owned by one HTTP request."""
    users_url = f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/users"
    users_response = http.get(users_url, timeout=10)

    if not users_response.ok:
        print("Failed to fetch users")
        return None, None

    request_users = build_user_dictionary(users_response.json())
    request_roster_lookup: Dict[int, str] = {}
    determine_user_roster_numbers(request_users, request_roster_lookup)
    return request_users, request_roster_lookup


def get_users_wins(year: int):
    effective_year, active_week = get_effective_season_data()
    target_year = year
    total_weeks = get_total_weeks(target_year)

    # A past season is complete, while a future season has no weekly results yet.
    if target_year < effective_year:
        active_week = total_weeks
    elif target_year > effective_year:
        active_week = 0

    request_users, request_roster_lookup = get_request_users()
    if request_users is None:
        return {}

    playoff_start_week = total_weeks - LOSERS + 1 
    current_active_week = min(active_week, total_weeks)

    reg_season_end = min(current_active_week, playoff_start_week - 1)
    set_season_rankings(request_users, 1, reg_season_end, request_roster_lookup)

    if current_active_week >= playoff_start_week:
        set_winners_and_losers(request_users)

        for week in range(playoff_start_week, current_active_week + 1):
            calculate_weekly_points(request_users, week, request_roster_lookup)
            drop_week_extremes_from_brackets(week, request_users)

    return {
        user.display_name: {
            "wins": user.wins,
            "losses": user.losses,
            "bracket": user.bracket,
            "is_eliminated": user.is_eliminated,
            "eliminated_week": user.eliminated_week
        } 
        for user in request_users.values()
    }


def get_current_week_wins(year: int):
    request_users, request_roster_lookup = get_request_users()
    if request_users is None:
        return None, {}

    current_week = set_current_week_rankings(request_users, year, request_roster_lookup)
    return current_week, {
        user.display_name: {
            "wins": user.wins,
            "losses": user.losses
        } for user in request_users.values()
    }

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "users_endpoint": "/users?year=2025",
    })

@app.route("/users", methods=["GET"])
def get_users():
    week = request.args.get("week")
    year_arg = request.args.get("year")
    try:
        year = int(year_arg) if year_arg is not None else DEFAULT_YEAR
    except ValueError:
        return jsonify({"error": "year must be a whole number"}), 400

    if week == "current":
        current_week, current_rankings = get_current_week_wins(year)
        return jsonify({
            "week": current_week,
            "rankings": current_rankings,
        })
    
    else:
        users_data = get_users_wins(year)
        return jsonify(users_data)

# Vercel serverless entrypoint compatibility
handler = app

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
