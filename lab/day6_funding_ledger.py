#!/usr/bin/env python3
"""Day 6: turn funding-rate observations into a paper cash-flow ledger.

This module is intentionally read-only.  It keeps API ``value`` and
``direction`` as observations, but uses the official position/rate/index
formula for the illustrative paper ledger.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any

try:
    from lab.audit_lighter_rwa import order_book_detail, paper_quantity_for_quote
except ModuleNotFoundError:  # Allows execution from the lab directory too.
    from audit_lighter_rwa import order_book_detail, paper_quantity_for_quote

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "lab" / "data" / "lighter_rwa_raw"
PAPER_TIMESTAMP = 1785715200  # 2026-08-03T00:00:00Z, present in both raw files.


def _load_raw(symbol: str) -> dict[str, Any]:
    return json.loads((RAW_DIR / f"{symbol}_fundings_1h.json").read_text())


def _load_funding_row(symbol: str, timestamp: int = PAPER_TIMESTAMP) -> dict[str, Any]:
    rows = _load_raw(symbol)["fundings"]
    for row in rows:
        if row["timestamp"] == timestamp:
            return row
    raise KeyError(f"No funding row for {symbol=} {timestamp=}")


def funding_cash_flow(
    position_sign: int,
    base_quantity: Decimal,
    multiplier: Decimal,
    index_price: Decimal,
    funding_rate: Decimal,
) -> Decimal:
    """Return the account cash flow for one funding round.

    Official sign convention: long position is +1, short position is -1.
    A positive funding rate therefore makes a long pay (negative cash flow).
    """
    if position_sign not in (-1, 1):
        raise ValueError("position_sign must be +1 (long) or -1 (short)")
    return (
        -Decimal(position_sign)
        * base_quantity
        * multiplier
        * index_price
        * funding_rate
    )


def payer_receiver(funding_rate: Decimal, position_sign: int) -> str:
    """Classify the paper payer/receiver direction without using API direction."""
    if funding_rate == 0:
        return "zero"
    pays = (funding_rate > 0 and position_sign == 1) or (
        funding_rate < 0 and position_sign == -1
    )
    return "pay" if pays else "receive"


def _paper_quantity(symbol: str, quote_notional: Decimal = Decimal("10")) -> Decimal:
    result = paper_quantity_for_quote(symbol, float(quote_notional))
    decimals = int(result["size_decimals"])
    quantum = Decimal(1).scaleb(-decimals)
    return Decimal(str(result["base_quantity"])).quantize(quantum, rounding=ROUND_DOWN)


def build_snapshot() -> dict[str, Any]:
    timestamp_iso = datetime.fromtimestamp(PAPER_TIMESTAMP, timezone.utc).isoformat()
    raw: dict[str, Any] = {}
    ledger: list[dict[str, Any]] = []

    for symbol in ("WTI", "BRENTOIL"):
        row = _load_funding_row(symbol)
        detail = order_book_detail(symbol)
        quantity = _paper_quantity(symbol)
        rate = Decimal(row["rate"])
        index_price = Decimal(str(detail["index_price"]))
        multiplier = Decimal(str(detail["multiplier"]))
        raw[symbol] = {
            "market_id": detail["market_id"],
            "timestamp": row["timestamp"],
            "timestamp_utc": timestamp_iso,
            "api_value": row["value"],
            "api_rate": row["rate"],
            "api_direction": row["direction"],
            "api_value_cash_flow_status": "unknown_unit_and_position_mapping",
            "historical_index_at_funding_timestamp": "unknown",
            "historical_position": "unknown",
        }

        for position_name, position_sign in (("long", 1), ("short", -1)):
            cash_flow = funding_cash_flow(
                position_sign,
                quantity,
                multiplier,
                index_price,
                rate,
            )
            ledger.append(
                {
                    "symbol": symbol,
                    "market_id": detail["market_id"],
                    "timestamp_utc": timestamp_iso,
                    "position": position_name,
                    "position_sign": position_sign,
                    "base_quantity": str(quantity),
                    "multiplier": str(multiplier),
                    "funding_rate": str(rate),
                    "index_price": str(index_price),
                    "cash_flow": str(cash_flow),
                    "payer_receiver": payer_receiver(rate, position_sign),
                    "cash_flow_status": "paper_only_not_time_aligned",
                    "index_price_note": (
                        "Current orderBookDetails snapshot used only as an illustrative "
                        "index input; it is not aligned to the funding timestamp."
                    ),
                }
            )

    api_value_delta = Decimal(raw["WTI"]["api_value"]) - Decimal(
        raw["BRENTOIL"]["api_value"]
    )
    return {
        "schema": "day6-funding-ledger-v1",
        "paper_timestamp_utc": timestamp_iso,
        "source_files": {
            "WTI_fundings": "lab/data/lighter_rwa_raw/WTI_fundings_1h.json",
            "BRENTOIL_fundings": "lab/data/lighter_rwa_raw/BRENTOIL_fundings_1h.json",
            "market_details": [
                "lab/data/lighter_rwa_raw/145_orderBookDetails.json",
                "lab/data/lighter_rwa_raw/159_orderBookDetails.json",
            ],
        },
        "raw_funding_observations": raw,
        "paper_ledger": ledger,
        "api_value_difference": {
            "WTI_minus_BRENTOIL": str(api_value_delta),
            "status": "not_a_funding_cash_flow",
            "reason": "API value units, account position, and time-aligned index are not verified.",
        },
        "research_conclusion": (
            "Funding direction is explainable from position sign and funding rate, "
            "but this ledger remains paper_only until time-aligned index data and an "
            "account funding ledger are verified."
        ),
    }


def main() -> None:
    print(json.dumps(build_snapshot(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
