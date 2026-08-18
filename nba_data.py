import pandas as pd
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats

CURRENT_SEASON = "2026-27"

def search_player_by_name(query: str, max_results: int = 10):
    """
    Searches active NBA players by name query.
    Restricts results to is_active=True and returns up to 10-15 matches.
    Prioritizes matches where query starts first or last name (e.g. 'curry' -> Stephen Curry & Seth Curry).
    """
    if not query:
        return []
    
    clean_query = query.strip().lower()
    
    # Strictly retrieves active players (is_active = True)
    active_players = players.get_active_players()
    
    priority_matches = []
    secondary_matches = []
    
    for p in active_players:
        full_name = p['full_name'].lower()
        first_name = p['first_name'].lower()
        last_name = p['last_name'].lower()
        
        if clean_query in full_name:
            # High priority: Query starts first name OR last name
            if first_name.startswith(clean_query) or last_name.startswith(clean_query):
                priority_matches.append(p)
            else:
                secondary_matches.append(p)
                
    # Combine results and cap at max_results (default 10)
    combined_results = priority_matches + secondary_matches
    return combined_results[:max_results]

def get_player_9cat_stats(player_id: int, season: str = CURRENT_SEASON) -> dict:
    """Fetches 9-Cat per-game stats for a specified season."""
    try:
        career = playercareerstats.PlayerCareerStats(player_id=player_id)
        df = career.season_totals_regular_season.get_data_frame()
        
        if df.empty:
            return None
        
        season_df = df[df['SEASON_ID'] == season]
        
        # If the player did not play in the selected season, return None
        if season_df.empty:
            return None
            
        row = season_df.iloc[0]
        gp = row['GP']
        
        if gp == 0:
            return None

        return {
            "player_id": player_id,
            "season": row['SEASON_ID'],
            "gp": gp,
            "pts": round(row['PTS'] / gp, 1),
            "reb": round(row['REB'] / gp, 1),
            "ast": round(row['AST'] / gp, 1),
            "stl": round(row['STL'] / gp, 1),
            "blk": round(row['BLK'] / gp, 1),
            "fg3m": round(row['FG3M'] / gp, 1),
            "fg_pct": round(row['FG_PCT'] * 100, 1),
            "ft_pct": round(row['FT_PCT'] * 100, 1),
            "tov": round(row['TOV'] / gp, 1),
        }
    except Exception as e:
        print(f"Error fetching stats for player {player_id}: {e}")
        return None