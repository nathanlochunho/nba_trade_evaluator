import flet as ft
import logging
import sys

logger = logging.getLogger("trade_evaluator")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)

STATS_BENCHMARK = {
    "fg_pct": {"mean": 0.450222, "std": 0.11818162},
    "ft_pct": {"mean": 0.71036, "std": 0.22320338},
    "fg3m":   {"mean": 0.987618,   "std": 0.87863102},
    "reb":    {"mean": 3.507394,   "std": 2.39051417},
    "ast":    {"mean": 2.031287,   "std": 1.84985086},
    "stl":    {"mean": 0.635682,   "std": 0.41164985},
    "blk":    {"mean": 0.390338,   "std": 0.39436115},
    "tov":    {"mean": 1.062295,   "std": 0.81751033},
    "pts":    {"mean": 8.756958,  "std": 6.585474},
}

# Volume-weighted percentage impact benchmarks:
# impact = attempts * (pct_decimal - benchmark_pct_decimal)
# Update mean/std here if you compute empirical impact distributions from your player pool.
FG_FT_IMPACT_BENCHMARK = {
    "fg_impact": {"mean": 0.090159, "std": 0.5272703},
    "ft_impact": {"mean": 0.116816, "std": 0.28433345},
}


def _normalize_pct_decimal(raw_val) -> float:
    val = 0.0 if raw_val is None else float(raw_val)
    return val / 100.0 if val > 1.0 else val


def calculate_player_zscore(player_stats):
    """Calculates 9-cat Z-scores for a single player using FGA/FTA-weighted FG%/FT% impact."""
    z_scores = {}

    # 1. Volume-weighted FG% impact Z-score
    fg_pct_dec = _normalize_pct_decimal(player_stats.get("fg_pct", 0))
    fga_raw = player_stats.get("fga", 0)
    fga = 0.0 if fga_raw is None else max(0.0, float(fga_raw))
    bench_fg_pct = STATS_BENCHMARK["fg_pct"]["mean"]
    fg_impact = fga * (fg_pct_dec - bench_fg_pct)
    fg_imp_bench = FG_FT_IMPACT_BENCHMARK["fg_impact"]
    z_scores["fg_pct"] = round((fg_impact - fg_imp_bench["mean"]) / fg_imp_bench["std"], 2)

    # 2. Volume-weighted FT% impact Z-score
    ft_pct_dec = _normalize_pct_decimal(player_stats.get("ft_pct", 0))
    fta_raw = player_stats.get("fta", 0)
    fta = 0.0 if fta_raw is None else max(0.0, float(fta_raw))
    bench_ft_pct = STATS_BENCHMARK["ft_pct"]["mean"]
    ft_impact = fta * (ft_pct_dec - bench_ft_pct)
    ft_imp_bench = FG_FT_IMPACT_BENCHMARK["ft_impact"]
    z_scores["ft_pct"] = round((ft_impact - ft_imp_bench["mean"]) / ft_imp_bench["std"], 2)

    # 3. Remaining 7 counting/turnover categories
    for cat in ("fg3m", "reb", "ast", "stl", "blk", "tov", "pts"):
        bench = STATS_BENCHMARK[cat]
        raw_val = player_stats.get(cat, 0)
        val = 0.0 if raw_val is None else float(raw_val)

        z = (val - bench["mean"]) / bench["std"]
        if cat == "tov":
            z = -z

        z_scores[cat] = round(z, 2)

    total_zscore = round(sum(z_scores.values()), 2)
    return total_zscore, z_scores


def evaluate_trade(team_a, team_b):
    """
    Evaluates trade fairness:
    - Equal player counts: fair threshold 1.75
    - Unequal player counts: fair threshold 1.25
    """
    team_a_players = []
    for p in team_a:
        total, cats = calculate_player_zscore(p)
        team_a_players.append({"name": p.get("name", "Unknown"), "total": total, "cats": cats})

    team_b_players = []
    for p in team_b:
        total, cats = calculate_player_zscore(p)
        team_b_players.append({"name": p.get("name", "Unknown"), "total": total, "cats": cats})

    team_a_score = sum(p["total"] for p in team_a_players)
    team_b_score = sum(p["total"] for p in team_b_players)

    diff = round(team_b_score - team_a_score, 2)
    abs_diff = abs(diff)

    threshold = 1.25 if len(team_a) != len(team_b) else 1.75

    if abs_diff <= threshold:
        status = f"Fair Trade (Net Difference: {diff:+.2f})"
        status_color = ft.Colors.GREEN_400
    elif diff > threshold:
        status = f"Unfair trade. Team B with (Net Value: +{diff:.2f})"
        status_color = ft.Colors.RED_400
    else:
        status = f"Unfair trade. Team A with (Net Value: +{abs_diff:.2f})"
        status_color = ft.Colors.RED_400

    team_a_summary = [
        f"{p.get('name', 'Unknown')} ({p.get('season', 'N/A')} | Z: {res_p['total']:+.2f})"
        for p, res_p in zip(team_a, team_a_players)
    ]
    team_b_summary = [
        f"{p.get('name', 'Unknown')} ({p.get('season', 'N/A')} | Z: {res_p['total']:+.2f})"
        for p, res_p in zip(team_b, team_b_players)
    ]

    logger.info(
        "EVALUATION | Team A: [%s] (Total: %+.2f) vs. Team B: [%s] (Total: %+.2f) | Delta (B - A): %+.2f | %s",
        ", ".join(team_a_summary),
        team_a_score,
        ", ".join(team_b_summary),
        team_b_score,
        diff,
        status,
    )

    sys.stdout.flush()

    return {
        "status": status,
        "status_color": status_color,
        "team_a_score": round(team_a_score, 2),
        "team_b_score": round(team_b_score, 2),
        "team_a_players": team_a_players,
        "team_b_players": team_b_players,
        "difference": diff,
        "threshold_used": threshold,
    }
