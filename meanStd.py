import math
import time
from nba_api.stats.endpoints import LeagueDashPlayerStats

# Update this list each year (e.g., add "2026-27" once enough games are played)
SEASONS = ["2021-22","2022-23","2023-24", "2024-25", "2025-26"]

# Use sample std (ddof=1) or population std (ddof=0) to match your existing convention
DDOF = 1

# Optional minimum games played filter (set to 0 to include every player in the endpoint)
MIN_GP = 5


def calc_mean_std(values: list[float], ddof: int = 1) -> tuple[float, float]:
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mean = sum(values) / n
    if n <= ddof:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in values) / (n - ddof)
    return mean, math.sqrt(variance)


def fetch_all_seasons(seasons: list[str], min_gp: int = 0, sleep_sec: float = 1.0) -> list[dict]:
    records: list[dict] = []

    for season in seasons:
        resp = LeagueDashPlayerStats(
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="PerGame",
            timeout=30,
        )
        df = resp.get_data_frames()[0]
        print(f"Fetched {len(df)} rows for {season}")

        for _, row in df.iterrows():
            gp = float(row.get("GP") or 0.0)
            if gp < min_gp:
                continue

            records.append({
                "season": season,
                "fga": float(row.get("FGA") or 0.0),
                "fta": float(row.get("FTA") or 0.0),
                "fg_pct": float(row.get("FG_PCT") or 0.0),  # already 0.0 - 1.0 in nba_api
                "ft_pct": float(row.get("FT_PCT") or 0.0),  # already 0.0 - 1.0 in nba_api
                "fg3m": float(row.get("FG3M") or 0.0),
                "reb": float(row.get("REB") or 0.0),
                "ast": float(row.get("AST") or 0.0),
                "stl": float(row.get("STL") or 0.0),
                "blk": float(row.get("BLK") or 0.0),
                "tov": float(row.get("TOV") or 0.0),
                "pts": float(row.get("PTS") or 0.0),
            })

        time.sleep(sleep_sec)

    return records


def main():
    records = fetch_all_seasons(SEASONS, min_gp=MIN_GP)

    # 1. Standard per-game / percentage benchmarks across all players
    raw_cats = ["fg_pct", "ft_pct", "fg3m", "reb", "ast", "stl", "blk", "tov", "pts"]
    stats_benchmark = {}

    for cat in raw_cats:
        vals = [r[cat] for r in records if r.get(cat) is not None]
        mean_val, std_val = calc_mean_std(vals, ddof=DDOF)
        stats_benchmark[cat] = {
            "mean": round(mean_val, 6),
            "std": round(std_val, 8),
        }

    # 2. Volume-weighted FG% and FT% impact benchmarks:
    #    fg_impact = fga * (fg_pct - bench_fg_pct)
    #    ft_impact = fta * (ft_pct - bench_ft_pct)
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
