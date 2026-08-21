"""Generate assets/day16-execution-capacity.js from a real execution scan.

Usage: PYTHONPATH=src python3 -m monte_arb.day16_lesson_data \
    --scan research/runs/day16-execution-scan.json \
    --out assets/day16-execution-capacity.js
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional, Sequence


def build_lesson_data(scan: dict[str, Any]) -> dict[str, Any]:
    """Pick a compact, real subset for the lesson page."""
    wanted = {
        "BRENTOIL__xyz:BRENTOIL",
        "AAPL__xyz:AAPL",
        "META__xyz:META",
        "SPCX__xyz:SPCX",
        "BOT__xyz:BOT",
    }
    pairs = []
    for row in scan["pairs"]:
        if row["pair_name"] not in wanted:
            continue
        per_size = []
        for size_row in row["per_size"]:
            compact: dict[str, Any] = {"size_usd": size_row["size_usd"]}
            for direction in ("buy_left_sell_right", "buy_right_sell_left"):
                d = size_row[direction]
                compact[direction] = {
                    "buy": {
                        "venue": d["buy"]["venue"],
                        "orderable": d["buy"]["orderable"],
                        "orderable_reason": d["buy"]["orderable_reason"],
                        "target_qty": d["buy"]["target_qty"],
                        "filled_qty": d["buy"]["filled_qty"],
                        "unfilled_qty": d["buy"]["unfilled_qty"],
                        "vwap": d["buy"]["vwap"],
                        "slippage_bps": d["buy"]["slippage_bps"],
                        "fee_bps": d["buy"]["fee_bps"],
                        "levels_used": d["buy"]["levels_used"],
                    },
                    "sell": {
                        "venue": d["sell"]["venue"],
                        "orderable": d["sell"]["orderable"],
                        "orderable_reason": d["sell"]["orderable_reason"],
                        "target_qty": d["sell"]["target_qty"],
                        "filled_qty": d["sell"]["filled_qty"],
                        "unfilled_qty": d["sell"]["unfilled_qty"],
                        "vwap": d["sell"]["vwap"],
                        "slippage_bps": d["sell"]["slippage_bps"],
                        "fee_bps": d["sell"]["fee_bps"],
                        "levels_used": d["sell"]["levels_used"],
                    },
                    "capture_bps": d["capture_bps"],
                    "slippage_cost_bps": d["slippage_cost_bps"],
                    "fee_cost_bps": d["fee_cost_bps"],
                    "net_spread_bps": d["net_spread_bps"],
                    "total_cost_bps": d["total_cost_bps"],
                    "fill_pct": d["fill_pct"],
                }
            per_size.append(compact)
        pairs.append(
            {
                "pair_name": row["pair_name"],
                "left_symbol": row["left"]["identity"]["symbol"],
                "right_symbol": row["right"]["identity"]["symbol"],
                "left_venue": row["left"]["venue"],
                "right_venue": row["right"]["venue"],
                "left_fee_bps": row["left"]["taker_fee_bps"],
                "right_fee_bps": row["right"]["taker_fee_bps"],
                "left_size_decimals": row["left"]["size_decimals"],
                "right_size_decimals": row["right"]["size_decimals"],
                "left_min_base": row["left"]["min_base_amount"],
                "left_min_quote": row["left"]["min_quote_amount"],
                "best": {
                    "left_bid": row["left_book"]["bids"][0]["price"]
                    if row["left_book"]["bids"]
                    else None,
                    "left_ask": row["left_book"]["asks"][0]["price"]
                    if row["left_book"]["asks"]
                    else None,
                    "right_bid": row["right_book"]["bids"][0]["price"]
                    if row["right_book"]["bids"]
                    else None,
                    "right_ask": row["right_book"]["asks"][0]["price"]
                    if row["right_book"]["asks"]
                    else None,
                },
                "capacity_usd": row["capacity_usd"],
                "per_size": per_size,
            }
        )
    return {
        "schema": scan["schema"],
        "observed_at": scan["observed_at"],
        "scanned_at": scan["scanned_at"],
        "sizes_usd": scan["sizes_usd"],
        "pairs": pairs,
        "boundaries": scan["boundaries"],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Day16 lesson data JS")
    parser.add_argument("--scan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    scan = json.loads(args.scan.read_text(encoding="utf-8"))
    data = build_lesson_data(scan)
    body = json.dumps(data, ensure_ascii=False, indent=1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        f"/* Generated by monte_arb.day16_lesson_data — do not edit by hand. */\n"
        f"window.DAY16 = {body};\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(args.out), "pairs": len(data["pairs"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
