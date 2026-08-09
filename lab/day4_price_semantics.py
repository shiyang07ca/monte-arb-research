"""Small, auditable Day 4 price-semantics exercises.

This module deliberately separates valuation prices from executable prices.
It never connects to an account or submits an order.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "lab" / "data" / "day4_price_semantics_snapshot.json"


def ema_step(previous: float, impact: float, delta_minutes: float, tau_minutes: float) -> float:
    """One time-weighted EMA step from the Lighter RWA docs."""
    if tau_minutes <= 0 or delta_minutes < 0:
        raise ValueError("tau_minutes must be positive and delta_minutes non-negative")
    alpha = 1.0 - math.exp(-delta_minutes / tau_minutes)
    return alpha * impact + (1.0 - alpha) * previous


def unrealized_pnl(entry: float, mark: float, signed_position: float) -> float:
    """Mark-based perpetual unrealized PnL; long is positive position."""
    return (mark - entry) * signed_position


def executable_close_pnl(entry: float, bid: float, ask: float, quantity: float, side: str) -> float:
    """Paper close PnL before fees/funding/depth: long exits at bid, short covers at ask."""
    if quantity < 0 or side not in {"long", "short"}:
        raise ValueError("quantity must be non-negative and side must be long or short")
    if side == "long":
        return (bid - entry) * quantity
    return (entry - ask) * quantity


def load_snapshot(path: Path = SNAPSHOT) -> dict[str, Any]:
    return json.loads(path.read_text())


def main() -> None:
    data = load_snapshot()
    print("Day 4 price semantics snapshot")
    print("unknown fields:", ", ".join(data["unknown_in_current_snapshot"]))
    for symbol, market in data["markets"].items():
        print(
            f"{symbol}: mark={market['mark_price']} index={market['index_price']} "
            f"last_trade={market['last_trade_price']} "
            f"mark-index={market['mark_minus_index']}"
        )
    print("EMA index example:", ema_step(75.0, 76.0, 1.0, 30.0))
    print("EMA mark example:", ema_step(75.0, 76.0, 1.0, 2.0))
    print("long mark PnL:", unrealized_pnl(75.0, 75.03, 1.0))
    print("long bid-close PnL:", executable_close_pnl(75.0, 74.90, 75.10, 1.0, "long"))


if __name__ == "__main__":
    main()
