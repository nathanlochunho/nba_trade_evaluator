# evaluator.py

def calculate_9cat_value(stats: dict) -> float:
    """
    Calculates total 9-cat value score for a single player.
    Weights can be customized depending on league settings.
    """
    if not stats:
        return 0.0

    # Custom weights for 9-Cat
    pts_w = 1.0
    reb_w = 1.2
    ast_w = 1.5
    stl_w = 3.0
    blk_w = 3.0
    fg3m_w = 2.0
    fg_pct_w = 0.5   # Scaled for % (Baseline 45%)
    ft_pct_w = 0.5   # Scaled for % (Baseline 75%)
    tov_w = -2.0     # Negative impact

    score = (
        stats.get('pts', 0) * pts_w +
        stats.get('reb', 0) * reb_w +
        stats.get('ast', 0) * ast_w +
        stats.get('stl', 0) * stl_w +
        stats.get('blk', 0) * blk_w +
        stats.get('fg3m', 0) * fg3m_w +
        (stats.get('fg_pct', 0) - 45.0) * fg_pct_w +
        (stats.get('ft_pct', 0) - 75.0) * ft_pct_w +  # FT% compared vs 75% league average baseline
        stats.get('tov', 0) * tov_w
    )
    return round(score, 1)


def evaluate_trade(team_a_assets: list[dict], team_b_assets: list[dict]):
    """Calculates total value scores for both sides and determines trade delta."""
    
    score_a = sum(calculate_9cat_value(p) for p in team_a_assets[:10])
    score_b = sum(calculate_9cat_value(p) for p in team_b_assets[:10])
    
    diff = round(score_b - score_a, 1)
    
    if abs(diff) <= 3.0:
        status = "Fair / Even Trade"
        color = "green"
    elif diff > 3.0:
        status = f"Team B with higher value: (+{diff} Value)"
        color = "blue"
    else:
        status = f"Team A with higher value: (+{abs(diff)} Value)"
        color = "orange"

    return {
        "team_a_score": round(score_a, 1),
        "team_b_score": round(score_b, 1),
        "difference": diff,
        "status": status,
        "status_color": color
    }