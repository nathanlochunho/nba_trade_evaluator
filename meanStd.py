import math
import time
from nba_api.stats.endpoints import LeagueDashPlayerStats

# Update this list each year (e.g., add "2026-27" once enough games are played)
SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]

# Filter out players whose season average minutes per game is under 10.0
MIN_AVG_MINUTES = 10.0

# Optional minimum games played filter (set to 0 to keep all players meeting MIN_AVG_MINUTES)
MIN_GP = 10

# Sample std (ddof=1) or population std (ddof=0)
DDOF = 1


def calc_mean_std(values: list[float], ddof: int = 1) -> tuple[float, float]:
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mean = sum(values) / n
    if n <= ddof:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in values) / (n - ddof)
    return mean, math.sqrt(variance)


def _to_float(val) -> float:
    if val is None or val == "":
        return 0.0
    return float(val)


def fetch_all_seasons(
    seasons: list[str],
    min_avg_minutes: float = 10.0,
    min_gp: int = 0,
    sleep_sec: float = 1.0,
) -> list[dict]:
    records: list[dict] = []

    for idx, season in enumerate(seasons):
        resp = LeagueDashPlayerStats(
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="PerGame",
            timeout=30,
        )
        df = resp.get_data_frames()[0]
        kept_in_season = 0

        for _, row in df.iterrows():
            avg_min = _to_float(row.get("MIN"))
            gp = _to_float(row.get("GP"))

            if avg_min < min_avg_minutes or gp < min_gp:
                continue

            records.append({
                "season": season,
                "min": avg_min,
                "gp": gp,
                "fga": _to_float(row.get("FGA")),
                "fta": _to_float(row.get("FTA")),
                "fg_pct": _to_float(row.get("FG_PCT")),  # already 0.0 - 1.0 in nba_api
                "ft_pct": _to_float(row.get("FT_PCT")),  # already 0.0 - 1.0 in nba_api
                "fg3m": _to_float(row.get("FG3M")),
                "reb": _to_float(row.get("REB")),
                "ast": _to_float(row.get("AST")),
                "stl": _to_float(row.get("STL")),
                "blk": _to_float(row.get("BLK")),
                "tov": _to_float(row.get("TOV")),
                "pts": _to_float(row.get("PTS")),
            })
            kept_in_season += 1

        print(
            f"Season {season}: kept {kept_in_season}/{len(df)} players with MIN >= {min_avg_minutes:.1f}",
            flush=True,
        )

        if idx < len(seasons) - 1:
            time.sleep(sleep_sec)

    return records


def main():
    records = fetch_all_seasons(
        SEASONS,
        min_avg_minutes=MIN_AVG_MINUTES,
        min_gp=MIN_GP,
    )

    raw_cats = ["fg_pct", "ft_pct", "fg3m", "reb", "ast", "stl", "blk", "tov", "pts"]
    stats_benchmark = {}

    for cat in raw_cats:
        vals = [r[cat] for r in records if r.get(cat) is not None]
        mean_val, std_val = calc_mean_std(vals, ddof=DDOF)
        stats_benchmark[cat] = {
            "mean": round(mean_val, 6),
            "std": round(std_val, 8),
        }

    bench_fg = stats_benchmark["fg_pct"]["mean"]
    bench_ft = stats_benchmark["ft_pct"]["mean"]

    fg_impacts = [
        r["fga"] * (r["fg_pct"] - bench_fg)
        for r in records
        if r["fga"] > 0
    ]
    ft_impacts = [
        r["fta"] * (r["ft_pct"] - bench_ft)
        for r in records
        if r["fta"] > 0
    ]

    fg_imp_mean, fg_imp_std = calc_mean_std(fg_impacts, ddof=DDOF)
    ft_imp_mean, ft_imp_std = calc_mean_std(ft_impacts, ddof=DDOF)

    impact_benchmark = {
        "fg_impact": {
            "mean": round(fg_imp_mean, 6),
            "std": round(fg_imp_std, 8),
        },
        "ft_impact": {
            "mean": round(ft_imp_mean, 6),
            "std": round(ft_imp_std, 8),
        },
    }

    print("\nSTATS_BENCHMARK = {")
    for cat, vals in stats_benchmark.items():
        print(f'    "{cat}": {{"mean": {vals["mean"]}, "std": {vals["std"]}}},')
    print("}")

    print("\nFG_FT_IMPACT_BENCHMARK = {")
    for cat, vals in impact_benchmark.items():
        print(f'    "{cat}": {{"mean": {vals["mean"]}, "std": {vals["std"]}}},')
    print("}")


if __name__ == "__main__":
    main()
