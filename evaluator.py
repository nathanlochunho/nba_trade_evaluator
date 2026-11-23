import flet as ft

STATS_BENCHMARK = {
    "fg_pct": {"mean": 0.4781, "std": 0.06324369097},
    "ft_pct": {"mean": 0.7842, "std": 0.0819088861},
    "fg3m":   {"mean": 1.55,   "std": 0.88418079},
    "reb":    {"mean": 4.82,   "std": 2.37764375},
    "ast":    {"mean": 3.15,   "std": 1.99827541},
    "stl":    {"mean": 0.88,   "std": 0.33680838},
    "blk":    {"mean": 0.54,   "std": 0.44408994},
    "tov":    {"mean": 1.53,   "std": 0.78074277},
    "pts":    {"mean": 13.58,  "std": 5.97244752},
}


def calculate_player_zscore(player_stats):
    """Calculates 9-cat Z-scores for a single player."""
    z_scores = {}
    for cat, bench in STATS_BENCHMARK.items():
        raw_val = player_stats.get(cat, 0)
        val = 0.0 if raw_val is None else float(raw_val)
        if cat in ["fg_pct", "ft_pct"] and val > 1.0:
            val = val / 100.0

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