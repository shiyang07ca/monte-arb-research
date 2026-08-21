"""Day14 oracle consistency tests."""

from __future__ import annotations

import unittest

from monte_arb.oracle_consistency import detect_funding_source_mismatch

TOKENLIST = {
    "tokens": [
        {"symbol": "BOT", "name": "RoboStrategy", "asset_type": "RWA"},
        {"symbol": "BTC", "name": "Bitcoin", "asset_type": "CRYPTO"},
        {"symbol": "AAPL", "name": "Apple", "asset_type": "RWA"},
        {"symbol": "WTI", "name": "Oil - US Crude", "asset_type": "RWA"},
    ]
}


def funding_row(exchange: str, symbol: str, rate: float = 1e-4) -> dict:
    return {"market_id": 1, "exchange": exchange, "symbol": symbol, "rate": rate}


class OracleConsistencyTests(unittest.TestCase):
    def test_stock_with_crypto_funding_source_is_flagged(self) -> None:
        issues = detect_funding_source_mismatch(
            TOKENLIST,
            [funding_row("binance", "BOT"), funding_row("lighter", "BOT")],
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0][0], "BOT")
        self.assertEqual(issues[0][1], "RWA")
        self.assertEqual(issues[0][2], "binance")
        self.assertTrue(issues[0][4].startswith("CONFIRMED"))

    def test_apple_with_crypto_funding_source_is_verify_not_confirmed(self) -> None:
        # AAPL exists on Binance as tokenized stock (AAPLBUSDT), so the
        # funding source is intentional; flag VERIFY, not CONFIRMED.
        issues = detect_funding_source_mismatch(
            TOKENLIST,
            [funding_row("binance", "AAPL")],
        )
        self.assertEqual(len(issues), 1)
        self.assertTrue(issues[0][4].startswith("VERIFY"))

    def test_crypto_asset_with_crypto_funding_source_is_clean(self) -> None:
        issues = detect_funding_source_mismatch(
            TOKENLIST,
            [funding_row("binance", "BTC"), funding_row("bybit", "BTC")],
        )
        self.assertEqual(issues, ())

    def test_lighter_own_source_is_never_flagged(self) -> None:
        issues = detect_funding_source_mismatch(
            TOKENLIST,
            [funding_row("lighter", "BOT"), funding_row("lighter", "WTI")],
        )
        self.assertEqual(issues, ())

    def test_unknown_symbol_with_crypto_source_is_not_flagged(self) -> None:
        # No tokenlist entry -> cannot claim mismatch (absence of evidence).
        issues = detect_funding_source_mismatch(
            TOKENLIST,
            [funding_row("binance", "ZZZZ")],
        )
        self.assertEqual(issues, ())

    def test_dedupes_repeated_sources(self) -> None:
        issues = detect_funding_source_mismatch(
            TOKENLIST,
            [
                funding_row("binance", "BOT"),
                funding_row("binance", "BOT"),
                funding_row("bybit", "BOT"),
            ],
        )
        self.assertEqual(len(issues), 2)
        self.assertEqual({i[2] for i in issues}, {"binance", "bybit"})

    def test_wrapped_dict_shape_like_lighter_funding_rates_endpoint(self) -> None:
        # The real endpoint returns {"code": 200, "funding_rates": [...]}.
        # Callers must unwrap the list; the detector must never receive the
        # wrapping dict itself.
        wrapped = {"code": 200, "funding_rates": [funding_row("binance", "BOT")]}
        issues = detect_funding_source_mismatch(TOKENLIST, wrapped["funding_rates"])
        self.assertEqual(len(issues), 1)


if __name__ == "__main__":
    unittest.main()
