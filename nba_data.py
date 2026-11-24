from __future__ import annotations

import re
from typing import Any

import requests

CURRENT_SEASON = "2026-27"

SEARCH_URL = (
    "https://site.web.api.espn.com/apis/common/v3/search"
)
BY_ATHLETE_URL = (
    "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/statistics/byathlete"
)
GAMELOG_URL = (
    "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{athlete_id}/gamelog"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
        "Chrome/126.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "application/json",
}

SEASON_TO_ESPN_YEAR = {
    "2024-25": 2025,
    "2025-26": 2026,
    "2026-27": 2027,
}

_PLAYER_CACHE: dict[str, list[dict[str, Any]]] = {}
_SEARCH_CACHE: dict[tuple[str, int], list[dict[str, Any]]] = {}
_STATS_CACHE: dict[tuple[str, int], dict[str, Any] | None] = {}


def season_to_espn_year(season: str) -> int:
    """Maps '2026-27' -> 2027 (ESPN uses the ending year of the NBA season)."""
    clean = (season or CURRENT_SEASON).strip()
    if clean in SEASON_TO_ESPN_YEAR:
        return SEASON_TO_ESPN_YEAR[clean]

    match = re.match(r"^(\d{4})\s*-\s*(\d{2,4})$", clean)
    if match:
        start_year = int(match.group(1))
        end_part = match.group(2)
        if len(end_part) == 2:
            century = (start_year // 100) * 100
            end_year = century + int(end_part)
            if end_year < start_year:
                end_year += 100
            return end_year
        return int(end_part)

    if clean.isdigit():
        return int(clean)

    return 2027


def _parse_float(val: Any) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if s in ("", "-", "--", "N/A", "nan", "NaN"):
        return None
    s = s.rstrip("%")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_made_att(val: Any) -> tuple[float | None, float | None]:
    """Parses ESPN combined fields like '8-15' or '8/15' into (made, attempted)."""
    if val is None:
        return None, None
    s = str(val).strip()
    if "-" in s:
        parts = s.split("-", 1)
    elif "/" in s:
        parts = s.split("/", 1)
    else:
        return None, None
    made = _parse_float(parts[0])
    att = _parse_float(parts[1])
    return made, att


def _extract_athletes_from_byathlete_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    roster: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for entry in payload.get("athletes") or []:
        ath = entry.get("athlete") or entry
        ath_id = str(ath.get("id") or entry.get("id") or "").strip()
        full_name = str(ath.get("displayName") or ath.get("fullName") or "").strip()
        if not ath_id or not full_name or ath_id in seen_ids:
            continue
        seen_ids.add(ath_id)
        parts = full_name.split(" ", 1)
        roster.append({
            "id": ath_id,
            "full_name": full_name,
            "first_name": str(ath.get("firstName") or parts[0]).strip(),
            "last_name": str(
                ath.get("lastName") or (parts[1] if len(parts) > 1 else "")
            ).strip(),
            "is_active": True,
        })
    return roster


def get_season_players(season: str = CURRENT_SEASON, timeout: float = 15.0) -> list[dict[str, Any]]:
    """Fallback directory of players from ESPN byathlete statistics."""
    cache_key = (season or CURRENT_SEASON).strip()
    if cache_key in _PLAYER_CACHE and _PLAYER_CACHE[cache_key]:
        return _PLAYER_CACHE[cache_key]

    roster_by_id: dict[str, dict[str, Any]] = {}
    espn_year = season_to_espn_year(cache_key)

    try:
        for page in range(1, 15):
            resp = requests.get(
                BY_ATHLETE_URL,
                params={"limit": 200, "page": page, "season": espn_year},
                headers=HEADERS,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            extracted = _extract_athletes_from_byathlete_payload(data)
            if not extracted:
                break

            new_added = 0
            for p in extracted:
                if p["id"] not in roster_by_id:
                    roster_by_id[p["id"]] = p
                    new_added += 1

            if new_added == 0:
                break
    except Exception as e:
        print(f"[SEARCH] ESPN byathlete fallback error ({e})", flush=True)

    roster = list(roster_by_id.values())
    if roster:
        _PLAYER_CACHE[cache_key] = roster
    return roster


def search_player_by_name(
    query: str,
    max_results: int = 10,
    season: str = CURRENT_SEASON,
) -> list[dict[str, Any]]:
    clean_query = (query or "").strip()
    if not clean_query:
        return []

    cache_key = (clean_query.lower(), max_results)
    if cache_key in _SEARCH_CACHE:
        cached = _SEARCH_CACHE[cache_key]
        print(
            f"[SEARCH] Query='{clean_query}' (cached) -> "
            f"{[(m['full_name'], m['id']) for m in cached]}",
            flush=True,
        )
        return cached

    print(f"[SEARCH] Query='{clean_query}' | Season='{season}'", flush=True)

    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # 1. Direct ESPN player search API
    try:
        resp = requests.get(
            SEARCH_URL,
            params={
                "query": clean_query,
                "limit": max_results,
                "type": "player",
                "sport": "basketball",
                "league": "nba",
            },
            headers=HEADERS,
            timeout=10.0,
        )
        resp.raise_for_status()
        payload = resp.json()

        items = list(payload.get("items") or [])
        if not items:
            for section in payload.get("results") or []:
                if isinstance(section, dict):
                    items.extend(section.get("contents") or section.get("items") or [])

        for item in items:
            ath_id = str(item.get("id") or "").strip()
            full_name = str(
                item.get("displayName") or item.get("fullName") or item.get("name") or ""
            ).strip()
            if not ath_id or not full_name or ath_id in seen_ids:
                continue

            seen_ids.add(ath_id)
            parts = full_name.split(" ", 1)
            results.append({
                "id": ath_id,
                "full_name": full_name,
                "first_name": str(item.get("firstName") or parts[0]).strip(),
                "last_name": str(
                    item.get("lastName") or (parts[1] if len(parts) > 1 else "")
                ).strip(),
                "is_active": True,
            })
    except Exception as e:
        print(f"[SEARCH] ESPN search endpoint error for '{clean_query}': {e}", flush=True)

    # 2. Fallback to paginated byathlete directory if direct search returned nothing
    if not results:
        q_lower = clean_query.lower()
        for p in get_season_players(season):
            if q_lower in p["full_name"].lower() and p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                results.append(p)

    matches = results[:max_results]
    if matches:
        _SEARCH_CACHE[cache_key] = matches

    print(
        f"[SEARCH] Matches for '{clean_query}': "
        f"{[(m['full_name'], m['id']) for m in matches]}",
        flush=True,
    )
    return matches


def _collect_game_stat_rows(
    node: Any,
    labels: list[str] | None,
    out_rows: list[tuple[list[str], list[Any]]],
) -> None:
    """Recursively collects (labels, stat_values) pairs from ESPN gamelog JSON."""
    if isinstance(node, dict):
        node_labels = node.get("labels")
        current_labels = (
            [str(x).strip().upper() for x in node_labels]
            if isinstance(node_labels, list) and node_labels
            else labels
        )

        stats_list = node.get("stats")
        if isinstance(stats_list, list) and stats_list and not isinstance(stats_list[0], dict):
            if current_labels:
                out_rows.append((current_labels, stats_list))

        events_list = node.get("events")
        if isinstance(events_list, list):
            for ev in events_list:
                if isinstance(ev, dict):
                    ev_stats = ev.get("stats")
                    if isinstance(ev_stats, list) and ev_stats and current_labels:
                        out_rows.append((current_labels, ev_stats))

        for k, v in node.items():
            if k not in ("stats", "events", "labels"):
                _collect_game_stat_rows(v, current_labels, out_rows)

    elif isinstance(node, list):
        for item in node:
            _collect_game_stat_rows(item, labels, out_rows)


def _row_to_stat_dict(labels: list[str], values: list[Any]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for idx, lbl in enumerate(labels):
        if idx < len(values):
            mapping[lbl.upper()] = values[idx]
    return mapping


def get_player_9cat_stats(
    player_id: str | int,
    season: str = CURRENT_SEASON,
    timeout: float = 15.0,
) -> dict[str, Any] | None:
    """Fetches a player's game log for `season` and aggregates 9-category per-game averages."""
    ath_id = str(player_id).strip()
    if not ath_id:
        return None

    espn_year = season_to_espn_year(season)
    cache_key = (ath_id, espn_year)
    if cache_key in _STATS_CACHE:
        return _STATS_CACHE[cache_key]

    try:
        url = GAMELOG_URL.format(athlete_id=ath_id)
        resp = requests.get(
            url,
            params={"season": espn_year},
            headers=HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        payload = resp.json()

        raw_rows: list[tuple[list[str], list[Any]]] = []
        season_types = payload.get("seasonTypes")
        if isinstance(season_types, list) and season_types:
            for st in season_types:
                st_name = str(st.get("displayName") or st.get("name") or "").lower()
                if "preseason" in st_name or "postseason" in st_name:
                    continue
                _collect_game_stat_rows(st, payload.get("labels"), raw_rows)
            if not raw_rows:
                _collect_game_stat_rows(season_types, payload.get("labels"), raw_rows)
        else:
            _collect_game_stat_rows(payload, payload.get("labels"), raw_rows)

        games_counted = 0
        tot_pts = tot_reb = tot_ast = tot_stl = tot_blk = tot_3pm = tot_tov = 0.0
        tot_fgm = tot_fga = tot_ftm = tot_fta = 0.0
        fg_pct_samples: list[float] = []
        ft_pct_samples: list[float] = []

        for labels, vals in raw_rows:
            row = _row_to_stat_dict(labels, vals)

            if "MIN" in row:
                min_raw = str(row.get("MIN") or "").strip().upper()
                if min_raw in ("DNP", "N/A", "--", ""):
                    continue

            pts = _parse_float(row.get("PTS"))
            reb = _parse_float(row.get("REB") or row.get("TRB"))
            ast = _parse_float(row.get("AST"))
            stl = _parse_float(row.get("STL"))
            blk = _parse_float(row.get("BLK"))
            tov = _parse_float(row.get("TO") or row.get("TOV"))

            tpm = _parse_float(row.get("3PM") or row.get("FG3M"))
            if tpm is None:
                tpm, _ = _parse_made_att(row.get("3PT") or row.get("3PM-3PA") or row.get("FG3M-FG3A"))

            fgm, fga = _parse_made_att(row.get("FG") or row.get("FGM-FGA"))
            if fgm is None:
                fgm = _parse_float(row.get("FGM"))
            if fga is None:
                fga = _parse_float(row.get("FGA"))

            ftm, fta = _parse_made_att(row.get("FT") or row.get("FTM-FTA"))
            if ftm is None:
                ftm = _parse_float(row.get("FTM"))
            if fta is None:
                fta = _parse_float(row.get("FTA"))

            if pts is None or reb is None or ast is None:
                continue

            games_counted += 1
            tot_pts += pts
            tot_reb += reb
            tot_ast += ast
            tot_stl += stl or 0.0
            tot_blk += blk or 0.0
            tot_3pm += tpm or 0.0
            tot_tov += tov or 0.0

            if fgm is not None and fga is not None:
                tot_fgm += fgm
                tot_fga += fga
            else:
                fg_pct_val = _parse_float(row.get("FG%"))
                if fg_pct_val is not None:
                    fg_pct_samples.append(fg_pct_val * 100.0 if fg_pct_val <= 1.0 else fg_pct_val)

            if ftm is not None and fta is not None:
                tot_ftm += ftm
                tot_fta += fta
            else:
                ft_pct_val = _parse_float(row.get("FT%"))
                if ft_pct_val is not None:
                    ft_pct_samples.append(ft_pct_val * 100.0 if ft_pct_val <= 1.0 else ft_pct_val)

        if games_counted <= 0:
            _STATS_CACHE[cache_key] = None
            return None

        fg_pct = (
            (tot_fgm / tot_fga) * 100.0
            if tot_fga > 0
            else (sum(fg_pct_samples) / len(fg_pct_samples) if fg_pct_samples else 0.0)
        )
        ft_pct = (
            (tot_ftm / tot_fta) * 100.0
            if tot_fta > 0
            else (sum(ft_pct_samples) / len(ft_pct_samples) if ft_pct_samples else 0.0)
        )

        result = {
            "player_id": ath_id,
            "espn_season_year": espn_year,
            "season": season,
            "gp": games_counted,
            "pts": round(tot_pts / games_counted, 1),
            "reb": round(tot_reb / games_counted, 1),
            "ast": round(tot_ast / games_counted, 1),
            "stl": round(tot_stl / games_counted, 1),
            "blk": round(tot_blk / games_counted, 1),
            "fg3m": round(tot_3pm / games_counted, 1),
            "fg_pct": round(fg_pct, 1),
            "ft_pct": round(ft_pct, 1),
            "tov": round(tot_tov / games_counted, 1),
        }
        _STATS_CACHE[cache_key] = result
        return result

    except Exception as e:
        print(f"[STATS] Error fetching ESPN stats for player {ath_id} (season={season} -> {espn_year}): {e}", flush=True)
        return None
