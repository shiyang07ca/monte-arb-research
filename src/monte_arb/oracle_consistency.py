"""Day14 oracle consistency check.

Compares Lighter's token metadata (tokenlist) with the funding-rate
reference sources (funding-rates). Two severities:

- CONFIRMED: the funding source on a crypto exchange tracks a DIFFERENT
  underlying than Lighter's tokenlist entry (verified mismatch).
- VERIFY: crypto-exchange funding source for a non-crypto asset. Most stock
  symbols exist on Binance/Bybit as tokenized stocks (e.g. AAPLBUSDT tracks
  Apple), so a crypto exchange source is usually intentional and correct;
  confirm before relying on it.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence, Tuple

CRYPTO_EXCHANGES = {"binance", "bybit", "okx", "gateio", "kucoin", "mexc"}

# Verified mismatches: funding reference source on a crypto exchange tracks a
# different underlying than Lighter's tokenlist entry.
# BOT: Binance/Bybit BOT is a crypto token (~$9.62, BOTUSDT does not exist);
# Lighter BOT is RoboStrategy stock (~$28.44). Verified 2026-08-19 via
# Binance exchangeInfo/ticker + CoinGecko prices.
CONFIRMED_MISMATCHES = {"BOT"}

AssetIssue = Tuple[
    str, str, str, str, str
]  # (symbol, asset_type, exchange, ref_symbol, note)


def asset_type_from_tokenlist(tokenlist: Mapping[str, Any]) -> Mapping[str, str]:
    rows = tokenlist.get("tokens", []) if isinstance(tokenlist, Mapping) else []
    return {
        row.get("symbol"): row.get("asset_type", "")
        for row in rows
        if row.get("symbol")
    }


def detect_funding_source_mismatch(
    tokenlist: Mapping[str, Any],
    funding_rates: Sequence[Mapping[str, Any]],
) -> Tuple[AssetIssue, ...]:
    asset_types = asset_type_from_tokenlist(tokenlist)
    issues: list[AssetIssue] = []
    for row in funding_rates:
        exchange = str(row.get("exchange", "")).lower()
        symbol = row.get("symbol", "")
        if exchange == "lighter" or exchange not in CRYPTO_EXCHANGES:
            continue
        asset_type = asset_types.get(symbol, "")
        if asset_type not in ("STOCK", "RWA"):
            continue
        if symbol in CONFIRMED_MISMATCHES:
            issues.append(
                (
                    symbol,
                    asset_type,
                    exchange,
                    str(row.get("symbol", "")),
                    "CONFIRMED: funding source tracks a different underlying "
                    "(crypto token) than tokenlist (stock/RWA)",
                )
            )
        else:
            issues.append(
                (
                    symbol,
                    asset_type,
                    exchange,
                    str(row.get("symbol", "")),
                    "VERIFY: crypto exchange funding source for non-crypto "
                    "asset; usually a tokenized stock on that exchange, "
                    "confirm before use",
                )
            )
    return tuple(sorted(set(issues)))
