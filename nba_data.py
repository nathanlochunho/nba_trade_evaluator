import pandas as pd
from nba_api.stats.endpoints import commonallplayers, playercareerstats
from nba_api.stats.static import players

CURRENT_SEASON = "2026-27"
_PLAYER_CACHE = {}


def get_season_players(season: str = CURRENT_SEASON):
    if season in _PLAYER_CACHE:
        return _PLAYER_CACHE[season]

    try:
        endpoint = commonallplayers.CommonAllPlayers(
            is_only_current_season=1,
            league_id="00",
            season=season,
            timeout=15,
        )
        df = endpoint.get_data_frames()[0]
        roster = []
        for _, row in df.iterrows():
            display_name = str(row.get("DISPLAY_FIRST_LAST") or "").strip()
            if not display_name:
                continue
            parts = display_name.split(" ", 1)
            roster.append({
                "id": int(row["PERSON_ID"]),
                "full_name": display_name,
                "first_name": parts[0],
                "last_name": parts[1] if len(parts) > 1 else "",
                "is_active": True,
            })
        if roster:
            _PLAYER_CACHE[season] = roster
            return roster
    except Exception as e:
        print(f"Live roster fetch failed for {season} ({e}), using static fallback.")

    fallback = players.get_active_players()
    _PLAYER_CACHE[season] = fallback
    return fallback


def search_player_by_name(query: str, max_results: int = 10, season: str = CURRENT_SEASON):
    if not query:
        return []

    clean_query = query.strip().lower()
    active_players = get_season_players(season)

    priority_matches = []
    secondary_matches = []

    for p in active_players:
        full_name = p["full_name"].lower()
        first_name = p["first_name"].lower()
        last_name = p["last_name"].lower()

        if clean_query in full_name:
            if first_name.startswith(clean_query) or last_name.startswith(clean_query):
                priority_matches.append(p)
            else:
                secondary_matches.append(p)

    return (priority_matches + secondary_matches)[:max_results]


def get_player_9cat_stats(player_id: int, season: str = CURRENT_SEASON) -> dict:
    try:
        career = playercareerstats.PlayerCareerStats(player_id=player_id, timeout=15)
        df = career.season_totals_regular_season.get_data_frame()

        if df.empty:
            return None

        season_df = df[df["SEASON_ID"] == season]
        if season_df.empty:
            return None

        # Prefer combined season row ('TOT') if traded mid-season; otherwise sum rows
        tot_df = season_df[season_df["TEAM_ABBREVIATION"] == "TOT"]
        if not tot_df.empty:
            row = tot_df.iloc[0]
            gp = float(row["GP"])
            pts = float(row["PTS"])
            reb = float(row["REB"])
            ast = float(row["AST"])
            stl = float(row["STL"])
            blk = float(row["BLK"])
            fg3m = float(row["FG3M"])
            tov = float(row["TOV"])
            fgm = float(row["FGM"]) if "FGM" in row and pd.notna(row["FGM"]) else None
            fga = float(row["FGA"]) if "FGA" in row and pd.notna(row["FGA"]) else None
            ftm = float(row["FTM"]) if "FTM" in row and pd.notna(row["FTM"]) else None
            fta = float(row["FTA"]) if "FTA" in row and pd.notna(row["FTA"]) else None
            fg_pct = (fgm / fga * 100) if (fgm is not None and fga) else float(row["FG_PCT"]) * 100
            ft_pct = (ftm / fta * 100) if (ftm is not None and fta) else float(row["FT_PCT"]) * 100
        else:
            gp = float(season_df["GP"].sum())
            pts = float(season_df["PTS"].sum())
            reb = float(season_df["REB"].sum())
            ast = float(season_df["AST"].sum())
            stl = float(season_df["STL"].sum())
            blk = float(season_df["BLK"].sum())
            fg3m = float(season_df["FG3M"].sum())
            tov = float(season_df["TOV"].sum())
            fga = float(season_df["FGA"].sum()) if "FGA" in season_df else 0.0
            fta = float(season_df["FTA"].sum()) if "FTA" in season_df else 0.0
            fg_pct = (float(season_df["FGM"].sum()) / fga * 100) if fga > 0 else float(season_df["FG_PCT"].mean()) * 100
            ft_pct = (float(season_df["FTM"].sum()) / fta * 100) if fta > 0 else float(season_df["FT_PCT"].mean()) * 100

        if gp <= 0:
            return None

        return {
            "player_id": player_id,
            "season": season,
            "gp": int(gp),
            "pts": round(pts / gp, 1),
            "reb": round(reb / gp, 1),
            "ast": round(ast / gp, 1),
            "stl": round(stl / gp, 1),
            "blk": round(blk / gp, 1),
            "fg3m": round(fg3m / gp, 1),
            "fg_pct": round(fg_pct, 1),
            "ft_pct": round(ft_pct, 1),
            "tov": round(tov / gp, 1),
        }
    except Exception as e:
        print(f"Error fetching stats for player {player_id}: {e}")
        return None