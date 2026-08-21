from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from monte_arb.market_event_collector import (
    JsonlGzWriter,
    parse_hl_ctx,
    parse_hl_l2,
    parse_hl_trades,
    parse_lighter_book,
)
from monte_arb.market import MarketIdentity

WTI = MarketIdentity("lighter", "perp", "default", "WTI", "145")
CL = MarketIdentity("hyperliquid", "perp", "xyz", "xyz:CL", "110029")


class TestHyperliquidParsers(unittest.TestCase):
    def test_l2_with_sides_field(self) -> None:
        message = {
            "channel": "l2Book",
            "data": {
                "coin": "xyz:CL",
                "time": 1787000000000,
                "levels": [
                    [{"px": "84.01", "sz": "2.5", "n": 1}],
                    [{"px": "84.03", "sz": "3.1", "n": 2}],
                ],
                "sides": ["bids", "asks"],
            },
        }
        book = parse_hl_l2(message["data"])
        self.assertEqual(book["ts_ms"], 1787000000000)
        self.assertEqual(book["bids"][0], ["84.01", "2.5"])
        self.assertEqual(book["asks"][0], ["84.03", "3.1"])

    def test_l2_legacy_order_without_sides(self) -> None:
        message = {
            "channel": "l2Book",
            "data": {
                "coin": "xyz:CL",
                "time": 1787000000001,
                "levels": [
                    [{"px": "84.00", "sz": "1.0", "n": 1}],
                    [{"px": "84.02", "sz": "1.0", "n": 1}],
                ],
            },
        }
        book = parse_hl_l2(message["data"])
        self.assertEqual(book["bids"][0][0], "84.00")
        self.assertEqual(book["asks"][0][0], "84.02")

    def test_l2_malformed_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_hl_l2({"coin": "xyz:CL", "levels": [{"px": "1"}]})
        with self.assertRaises(ValueError):
            parse_hl_l2(
                {
                    "coin": "xyz:CL",
                    "levels": [[{"n": 1}], [{"n": 1}]],
                }
            )

    def test_trades(self) -> None:
        message = {
            "channel": "trades",
            "data": [
                {
                    "coin": "xyz:CL",
                    "side": "B",
                    "px": "84.02",
                    "sz": "0.5",
                    "time": 1787000000500,
                    "tid": 991,
                    "users": ["a"],
                }
            ],
        }
        trades = parse_hl_trades(message)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["side"], "B")
        self.assertEqual(trades[0]["px"], "84.02")

    def test_trades_malformed_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_hl_trades({"data": [{"px": "1"}]})

    def test_ctx(self) -> None:
        message = {
            "channel": "activeAssetCtx",
            "data": {
                "coin": "xyz:CL",
                "time": 1787000001000,
                "ctx": {
                    "markPx": "84.02",
                    "oraclePx": "84.00",
                    "funding": "0.000012",
                    "openInterest": "12345.6",
                    "dayNtlVlm": "98765.4",
                },
            },
        }
        ctx = parse_hl_ctx(message)
        self.assertEqual(ctx["mark_px"], "84.02")
        self.assertEqual(ctx["funding"], "0.000012")
        self.assertEqual(ctx["ts_ms"], 1787000001000)

    def test_ctx_missing_ctx_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_hl_ctx({"data": {"coin": "xyz:CL"}})


class TestLighterParser(unittest.TestCase):
    def test_snapshot_message_with_object_rows(self) -> None:
        message = {
            "type": "subscribed/order_book",
            "channel": "order_book/145",
            "order_book": {
                "bids": [{"price": "84.00", "remaining_base_amount": "4.0"}],
                "asks": [{"price": "84.05", "remaining_base_amount": "2.0"}],
            },
        }
        book = parse_lighter_book(message)
        self.assertEqual(book["bids"][0], ["84.00", "4.0"])
        self.assertEqual(book["asks"][0], ["84.05", "2.0"])
        self.assertIsNone(book["ts_ms"])

    def test_update_message_with_list_rows(self) -> None:
        message = {
            "type": "update/order_book",
            "channel": "order_book/159",
            "order_book": {"bids": [["83.90", "1.0"]], "asks": [["83.95", "1.5"]]},
        }
        book = parse_lighter_book(message)
        self.assertEqual(book["bids"][0], ["83.90", "1.0"])

    def test_live_shape_colon_channel_price_size_rows(self) -> None:
        # Shape verified against the live stream on 2026-08-20.
        message = {
            "type": "update/order_book",
            "channel": "order_book:145",
            "timestamp": 1787185000000,
            "order_book": {
                "code": 0,
                "nonce": 1001,
                "offset": 42,
                "bids": [{"price": "84.471", "size": "0.893"}],
                "asks": [{"price": "84.481", "size": "14.205"}],
            },
        }
        book = parse_lighter_book(message)
        self.assertEqual(book["bids"][0], ["84.471", "0.893"])
        self.assertEqual(book["ts_ms"], 1787185000000)
        self.assertEqual(book["nonce"], 1001)
        self.assertEqual(book["offset"], 42)

    def test_missing_order_book_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_lighter_book({"type": "update/order_book", "channel": "order_book/145"})


class TestJsonlGzWriter(unittest.TestCase):
    def test_append_only_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl.gz"
            first = JsonlGzWriter(path)
            first.write({"session": "s1", "n": 1})
            first.close()
            second = JsonlGzWriter(path)
            second.write({"session": "s2", "n": 2})
            second.close()
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                lines = [json.loads(line) for line in stream if line.strip()]
            self.assertEqual([item["session"] for item in lines], ["s1", "s2"])
            self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
