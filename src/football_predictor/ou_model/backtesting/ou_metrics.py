"""Evaluation metrics for O/U 2.5 predictions."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

JsonDict = dict[str, Any]


def binary_brier_score(y_true: Sequence[int], p_over: Sequence[float]) -> float:
    """Brier score for binary O/U classification."""
    if not y_true:
        return float("nan")
    return sum((p - y) ** 2 for y, p in zip(y_true, p_over, strict=True)) / len(y_true)


def binary_log_loss(
    y_true: Sequence[int],
    p_over: Sequence[float],
    epsilon: float = 1e-15,
) -> float:
    """Binary cross-entropy loss."""
    if not y_true:
        return float("nan")
    total = 0.0
    for y, p in zip(y_true, p_over, strict=True):
        p_clamped = max(min(float(p), 1 - epsilon), epsilon)
        total -= y * math.log(p_clamped) + (1 - y) * math.log(1 - p_clamped)
    return total / len(y_true)


def roi_simulation(
    y_true: Sequence[int],
    p_over: Sequence[float],
    market_odds_over: Sequence[float | None],
    market_odds_under: Sequence[float | None],
    *,
    edge_threshold: float = 0.03,
    kelly_fraction: float = 0.25,
    bankroll: float = 1000.0,
    max_bet_fraction: float = 0.05,
) -> JsonDict:
    """Simulate O/U betting with quarter-Kelly staking.

    Only bets when |p_model - market_p| >= edge_threshold.
    Returns ROI, drawdown, Sharpe, and per-bet details.
    """
    current_bankroll = bankroll
    peak_bankroll = bankroll
    max_drawdown = 0.0
    total_staked = 0.0
    bet_results: list[float] = []
    total_bets = bets_over = bets_under = wins = 0

    for y, p, odd_over, odd_under in zip(
        y_true, p_over, market_odds_over, market_odds_under, strict=True
    ):
        if odd_over is None or odd_under is None:
            continue
        odd_over_f = float(odd_over)
        odd_under_f = float(odd_under)
        if odd_over_f <= 1 or odd_under_f <= 1:
            continue

        q_over = 1 / odd_over_f
        q_under = 1 / odd_under_f
        total_q = q_over + q_under
        market_p_over = q_over / total_q

        edge_over = float(p) - market_p_over
        edge_under = market_p_over - float(p)

        if abs(edge_over) < edge_threshold and abs(edge_under) < edge_threshold:
            continue

        if edge_over >= edge_threshold:
            bet_side = "over"
            edge = edge_over
            odd = odd_over_f
            p_model = float(p)
        else:
            bet_side = "under"
            edge = edge_under
            odd = odd_under_f
            p_model = 1 - float(p)

        kelly = (p_model * odd - 1) / (odd - 1)
        stake = min(kelly_fraction * kelly * current_bankroll, max_bet_fraction * current_bankroll)
        stake = max(stake, 0)
        if stake == 0:
            continue

        total_staked += stake
        total_bets += 1
        if bet_side == "over":
            bets_over += 1
            outcome = int(y)
        else:
            bets_under += 1
            outcome = 1 - int(y)

        if outcome:
            profit = stake * (odd - 1)
            wins += 1
        else:
            profit = -stake

        current_bankroll += profit
        bet_results.append(profit / stake if stake > 0 else 0)
        peak_bankroll = max(peak_bankroll, current_bankroll)
        drawdown = (peak_bankroll - current_bankroll) / peak_bankroll
        max_drawdown = max(max_drawdown, drawdown)

    roi = (current_bankroll - bankroll) / max(total_staked, 1e-9)
    if len(bet_results) > 1:
        import statistics
        mean_r = statistics.mean(bet_results)
        std_r = statistics.pstdev(bet_results)
        sharpe = mean_r / std_r if std_r > 0 else 0.0
    else:
        sharpe = 0.0

    return {
        "roi": roi,
        "total_bets": total_bets,
        "bets_over": bets_over,
        "bets_under": bets_under,
        "wins": wins,
        "win_rate": wins / max(total_bets, 1),
        "final_bankroll": current_bankroll,
        "total_staked": total_staked,
        "net_profit": current_bankroll - bankroll,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe,
    }


def closing_line_value(
    p_over_at_prediction: Sequence[float],
    closing_market_p_over: Sequence[float],
) -> float:
    """CLV = mean(p_model - closing_market_p). Positive = model beats closing line."""
    if not p_over_at_prediction:
        return float("nan")
    return sum(
        p - c for p, c in zip(p_over_at_prediction, closing_market_p_over, strict=True)
    ) / len(p_over_at_prediction)


def calibration_bins_binary(
    y_true: Sequence[int],
    p_over: Sequence[float],
    n_bins: int = 10,
) -> list[JsonDict]:
    """Compute reliability diagram data (mean predicted vs actual fraction per bin)."""
    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    for y, p in zip(y_true, p_over, strict=True):
        idx = min(int(float(p) * n_bins), n_bins - 1)
        bins[idx].append((float(p), int(y)))

    results: list[JsonDict] = []
    for i, bin_data in enumerate(bins):
        lower = i / n_bins
        upper = (i + 1) / n_bins
        if not bin_data:
            results.append({"bin_lower": lower, "bin_upper": upper, "count": 0,
                            "mean_predicted": None, "actual_fraction": None})
        else:
            results.append({
                "bin_lower": lower,
                "bin_upper": upper,
                "count": len(bin_data),
                "mean_predicted": sum(p for p, _ in bin_data) / len(bin_data),
                "actual_fraction": sum(y for _, y in bin_data) / len(bin_data),
            })
    return results
