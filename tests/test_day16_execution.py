"""Day16 execution and capacity tests: frozen-L2 walking, order sizing, pair legs.

Public seam: monte_arb.day16_execution pure functions over frozen L2 books and
market parameters, plus the execution snapshot HTTP surface on the workbench
server. No execution client and no orders.
"""

from __future__ import annotations

import json
import unittest
from decimal import Decimal
from http.server import ThreadingHTTPServer
from threading import Thread
from typing import Any, Mapping

from monte_arb.day16_execution import (
    L2Book,
    L2Level,
    MarketSpec,
    build_execution_snapshot,
    capacity_usd,
    leg_execution,
    order_qty_for_notional,
    pair_execution,
    walk_book,
)
from monte_arb.market import MarketIdentity
from monte_arb.workbench_server import WorkbenchApp


def book(bids: list[tuple[str, str]], asks: list[tuple[str, str]]) -> L2Book:
    return L2Book(
        bids=tuple(L2Level(Decimal(p), Decimal(s)) for p, s in bids),
        asks=tuple(L2Level(Decimal(p), Decimal(s)) for p, s in asks),
        source_time_ms=None,
    )


def lighter_spec(
    *,
    taker_fee: str | None = "0.0000",
    maker_fee: str | None = "0.0000",
    size_decimals: int = 4,
    min_base: str = "0.08",
    min_quote: str = "10.000000",
    multiplier: str = "1.0",
) -> MarketSpec:
    return MarketSpec(
        identity=MarketIdentity("lighter", "perp", "default", "BRENTOIL", "159"),
        venue="lighter",
        taker_fee_bps=(
            Decimal(taker_fee) * Decimal(10_000) if taker_fee is not None else None
        ),
        maker_fee_bps=(
            Decimal(maker_fee) * Decimal(10_000) if maker_fee is not None else None
        ),
        size_decimals=size_decimals,
        min_base_amount=Decimal(min_base),
        min_quote_amount=Decimal(min_quote),
        multiplier=Decimal(multiplier),
        price_decimals=2,
    )


def hl_spec(*, size_decimals: int = 2) -> MarketSpec:
    # Hyperliquid HIP-3 meta does not expose taker/maker fee -> unknown.
    return MarketSpec(
        identity=MarketIdentity("hyperliquid", "perp", "xyz", "xyz:BRENTOIL", "110049"),
        venue="hyperliquid",
        taker_fee_bps=None,
        maker_fee_bps=None,
        size_decimals=size_decimals,
        min_base_amount=Decimal("0"),
        min_quote_amount=Decimal("10"),
        multiplier=Decimal("1"),
        price_decimals=3,
    )


class WalkBookTests(unittest.TestCase):
    def test_full_fill_across_levels_uses_vwap(self) -> None:
        levels = book(
            [],
            [("100", "10"), ("100.5", "15"), ("101", "20")],
        ).asks
        result = walk_book(levels, Decimal("30"), is_bid_side=False)
        self.assertEqual(result.filled_qty, Decimal("30"))
        self.assertEqual(result.unfilled_qty, Decimal("0"))
        expected_vwap = (10 * 100 + 15 * 100.5 + 5 * 101) / 30
        self.assertAlmostEqual(float(result.vwap), expected_vwap, places=9)
        self.assertEqual(result.levels_used, 3)
        self.assertEqual(result.worst_price, Decimal("101"))

    def test_partial_fill_keeps_unfilled(self) -> None:
        levels = book(
            [],
            [("100", "10"), ("100.5", "15"), ("101", "20")],
        ).asks
        result = walk_book(levels, Decimal("50"), is_bid_side=False)
        self.assertEqual(result.filled_qty, Decimal("45"))
        self.assertEqual(result.unfilled_qty, Decimal("5"))
        self.assertEqual(result.worst_price, Decimal("101"))

    def test_sell_side_walks_bids_descending(self) -> None:
        levels = book(
            [("101", "20"), ("100.5", "15"), ("100", "10")],
            [],
        ).bids
        result = walk_book(levels, Decimal("30"), is_bid_side=True)
        expected_vwap = (20 * 101 + 10 * 100.5) / 30
        self.assertAlmostEqual(float(result.vwap), expected_vwap, places=9)
        self.assertEqual(result.worst_price, Decimal("100.5"))

    def test_empty_book_fills_nothing(self) -> None:
        result = walk_book((), Decimal("5"), is_bid_side=False)
        self.assertEqual(result.filled_qty, Decimal("0"))
        self.assertEqual(result.unfilled_qty, Decimal("5"))


class OrderSizingTests(unittest.TestCase):
    def test_floor_to_size_decimals(self) -> None:
        # 25 USD / 91.365 = 0.27362... -> floor to 2 dp = 0.27
        qty = order_qty_for_notional(
            notional_usd=Decimal("25"),
            price=Decimal("91.365"),
            size_decimals=2,
            min_base_amount=Decimal("0.08"),
            min_quote_amount=Decimal("10"),
            multiplier=Decimal("1"),
        )
        self.assertEqual(qty, Decimal("0.27"))
    def test_below_min_base_is_not_orderable(self) -> None:
        qty = order_qty_for_notional(
            notional_usd=Decimal("10"),
            price=Decimal("100"),
            size_decimals=2,
            min_base_amount=Decimal("0.3"),
            min_quote_amount=Decimal("10"),
            multiplier=Decimal("1"),
        )
        self.assertEqual(qty, Decimal("0"))

    def test_below_min_quote_is_not_orderable(self) -> None:
        # 0.10 x 99.99 = 9.999 < 10 min quote
        qty = order_qty_for_notional(
            notional_usd=Decimal("10"),
            price=Decimal("99.99"),
            size_decimals=2,
            min_base_amount=Decimal("0.05"),
            min_quote_amount=Decimal("10"),
            multiplier=Decimal("1"),
        )
        self.assertEqual(qty, Decimal("0"))

    def test_multiplier_scales_quote_value(self) -> None:
        # multiplier 10: 1.0 qty x 100 x 10 = 1000 quote
        qty = order_qty_for_notional(
            notional_usd=Decimal("1000"),
            price=Decimal("100"),
            size_decimals=1,
            min_base_amount=Decimal("0.1"),
            min_quote_amount=Decimal("10"),
            multiplier=Decimal("10"),
        )
        self.assertEqual(qty, Decimal("1.0"))


class LegExecutionTests(unittest.TestCase):
    def test_buy_leg_reports_slippage_vs_top_of_book(self) -> None:
        spec = lighter_spec()
        result = leg_execution(
            spec,
            book([], [("100", "10"), ("101", "10")]),
            side="buy",
            target_notional_usd=Decimal("1000"),
        )
        self.assertTrue(result.orderable)
        # qty = floor(1000/100, 4dp) = 10.0; fills level 1 fully at vwap 100
        self.assertEqual(result.filled_qty, Decimal("10"))
        self.assertEqual(result.unfilled_qty, Decimal("0"))
        self.assertAlmostEqual(float(result.vwap), 100.0, places=9)
        self.assertEqual(result.slippage_bps, 0.0)
        self.assertEqual(result.fee_bps, 0.0)

    def test_buy_leg_slippage_when_walking_deeper(self) -> None:
        spec = lighter_spec()
        result = leg_execution(
            spec,
            book([], [("100", "10"), ("101", "10")]),
            side="buy",
            target_notional_usd=Decimal("1500"),
        )
        # 15 qty: 10 @100 + 5 @101 -> vwap 100.333..., slippage ~33.3 bps vs 100
        self.assertAlmostEqual(float(result.vwap), 100 + 5 / 15, places=9)
        self.assertGreater(result.slippage_bps, 33.0)
        self.assertLess(result.slippage_bps, 34.0)

    def test_unknown_fee_stays_none_not_zero(self) -> None:
        result = leg_execution(
            hl_spec(),
            book([], [("100", "10")]),
            side="buy",
            target_notional_usd=Decimal("100"),
        )
        self.assertIsNone(result.fee_bps)
        self.assertEqual(result.slippage_bps, 0.0)

    def test_leg_without_enough_depth_keeps_unfilled(self) -> None:
        result = leg_execution(
            lighter_spec(),
            book([], [("100", "10")]),
            side="buy",
            target_notional_usd=Decimal("5000"),
        )
        self.assertEqual(result.filled_qty, Decimal("10"))
        self.assertEqual(result.unfilled_qty, Decimal("40"))
        self.assertEqual(result.unfilled_notional_usd, Decimal("4000"))


class PairExecutionTests(unittest.TestCase):
    def test_positive_spread_both_directions(self) -> None:
        left = lighter_spec()  # Lighter BRENTOIL
        right = hl_spec()
        left_book = book([("91.30", "10")], [("91.36", "10")])
        right_book = book([("91.40", "10")], [("91.46", "10")])
        # buy left 91.36 / sell right 91.40 -> +4.4 bps capture before fees
        result = pair_execution(
            left,
            left_book,
            right,
            right_book,
            direction="buy_left_sell_right",
            target_notional_usd=Decimal("100"),
        )
        self.assertTrue(result.buy.orderable and result.sell.orderable)
        self.assertGreater(result.net_spread_bps, 0)
        # buy right 91.46 / sell left 91.30 -> negative
        crossed = pair_execution(
            left,
            left_book,
            right,
            right_book,
            direction="buy_right_sell_left",
            target_notional_usd=Decimal("100"),
        )
        self.assertLess(crossed.net_spread_bps, 0)

    def test_fee_unknown_keeps_total_unknown_part(self) -> None:
        left = lighter_spec()
        right = hl_spec()
        left_book = book([("91.30", "10")], [("91.36", "10")])
        right_book = book([("91.40", "10")], [("91.46", "10")])
        result = pair_execution(
            left,
            left_book,
            right,
            right_book,
            direction="buy_left_sell_right",
            target_notional_usd=Decimal("100"),
        )
        # buy leg is Lighter (fee 0.0 known); sell leg is Hyperliquid (unknown)
        self.assertEqual(result.buy.fee_bps, 0.0)
        self.assertIsNone(result.sell.fee_bps)
        # total cost must stay None instead of silently becoming zero
        self.assertIsNone(result.total_cost_bps)

    def test_unfilled_leg_reduces_fill_fraction(self) -> None:
        left = lighter_spec()
        right = hl_spec()
        left_book = book([("91.30", "10")], [("91.36", "10")])
        right_book = book([("91.40", "10")], [("91.46", "10")])
        result = pair_execution(
            left,
            left_book,
            right,
            right_book,
            direction="buy_left_sell_right",
            target_notional_usd=Decimal("5000"),
        )
        self.assertLess(result.fill_pct, 1.0)
        self.assertGreater(result.fill_pct, 0.0)

    def test_capacity_is_largest_size_with_full_fill(self) -> None:
        left = lighter_spec()
        right = hl_spec()
        left_book = book([("91.30", "10")], [("91.36", "10")])
        right_book = book([("91.40", "10")], [("91.46", "10")])
        # depth 10 qty each side; price ~91.4 -> full fill up to ~914 USD
        cap = capacity_usd(
            left,
            left_book,
            right,
            right_book,
            direction="buy_left_sell_right",
            sizes=(Decimal("100"), Decimal("500"), Decimal("1000"), Decimal("2000")),
        )
        self.assertEqual(cap, Decimal("500"))

    def test_capacity_skips_below_min_sizes(self) -> None:
        left = lighter_spec()  # min_quote 10 -> $10 order floors below min notional
        right = hl_spec()
        left_book = book([("91.30", "10")], [("91.36", "10")])
        right_book = book([("91.40", "10")], [("91.46", "10")])
        # $10 is not orderable (MIN_QUOTE after flooring), but $25+ are and
        # fully fill; the curve must not end at the unorderable first tier.
        cap = capacity_usd(
            left,
            left_book,
            right,
            right_book,
            direction="buy_left_sell_right",
            sizes=(Decimal("10"), Decimal("25"), Decimal("50"), Decimal("100"), Decimal("250")),
        )
        self.assertEqual(cap, Decimal("250"))


class SnapshotTests(unittest.TestCase):
    def test_snapshot_declares_read_only_and_no_execution_client(self) -> None:
        left = lighter_spec()
        right = hl_spec()
        snapshot = build_execution_snapshot(
            [left],
            [right],
            books={
                left.identity: book([("91.30", "10")], [("91.36", "10")]),
                right.identity: book([("91.40", "10")], [("91.46", "10")]),
            },
            sizes_usd=(Decimal("10"), Decimal("25"), Decimal("50")),
        )
        self.assertEqual(snapshot.schema, "day16-execution-snapshot-v1")
        self.assertTrue(snapshot.read_only)
        self.assertFalse(snapshot.execution_client_present)
        self.assertEqual(len(snapshot.pairs), 1)
        pair = snapshot.pairs[0]
        self.assertEqual(pair.pair_name, "BRENTOIL__xyz:BRENTOIL")
        self.assertEqual(len(pair.per_size), 3)
        self.assertIn("BRENTOIL__xyz:BRENTOIL", pair.pair_name)

    def test_snapshot_round_trip_preserves_fees_and_unfilled(self) -> None:
        left = lighter_spec()
        right = hl_spec()
        snapshot = build_execution_snapshot(
            [left],
            [right],
            books={
                left.identity: book([("91.30", "10")], [("91.36", "10")]),
                right.identity: book([("91.40", "10")], [("91.46", "10")]),
            },
            sizes_usd=(Decimal("100"), Decimal("5000")),
        )
        payload = json.loads(json.dumps(snapshot.to_dict(), ensure_ascii=False))
        per_size = payload["pairs"][0]["per_size"]
        small = next(row for row in per_size if row["size_usd"] == 100)
        large = next(row for row in per_size if row["size_usd"] == 5000)
        self.assertIn("buy_left_sell_right", small)
        self.assertIn("buy_right_sell_left", small)
        # buy_left_sell_right sells the Hyperliquid leg -> fee unknown
        self.assertIsNone(large["buy_left_sell_right"]["sell"]["fee_bps"])
        # buy_right_sell_left buys the Hyperliquid leg -> fee unknown
        self.assertIsNone(large["buy_right_sell_left"]["buy"]["fee_bps"])


class LighterDetailsTests(unittest.TestCase):
    def test_normalize_lighter_details_from_repo_fixture(self) -> None:
        import json as _json
        from pathlib import Path

        from monte_arb.day16_execution import normalize_lighter_details

        fixture = Path(
            __file__,
        ).parent.parent / "lab" / "data" / "day9_raw" / "orderBookDetails_145.json"
        rows = _json.loads(fixture.read_text())
        specs = normalize_lighter_details(rows)
        self.assertIn(145, specs)
        spec = specs[145]
        self.assertEqual(spec.identity.symbol, "WTI")
        self.assertEqual(spec.size_decimals, 3)
        self.assertEqual(spec.price_decimals, 3)
        self.assertEqual(spec.min_base_amount, Decimal("0.100"))
        self.assertEqual(spec.taker_fee_bps, Decimal("0"))


class ExecutionHttpTests(unittest.TestCase):
    def _serve(self, scanner=None) -> tuple[ThreadingHTTPServer, str]:
        left = lighter_spec()
        right = hl_spec()
        snapshot = build_execution_snapshot(
            [left],
            [right],
            books={
                left.identity: book([("91.30", "10")], [("91.36", "10")]),
                right.identity: book([("91.40", "10")], [("91.46", "10")]),
            },
            sizes_usd=(Decimal("10"), Decimal("25"), Decimal("50")),
        )
        app = WorkbenchApp(snapshot, scanner=scanner)
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler())
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, f"http://127.0.0.1:{server.server_port}"

    def test_execution_page_and_json_serve(self) -> None:
        import urllib.request

        server, base = self._serve()
        try:
            with urllib.request.urlopen(f"{base}/workbench/execution", timeout=10) as r:
                html = r.read().decode("utf-8")
            self.assertEqual(r.status, 200)
            self.assertIn("可执行性与容量", html)
            self.assertIn("auto_refresh", html)
            with urllib.request.urlopen(
                f"{base}/workbench/api/execution", timeout=10
            ) as r:
                payload = json.loads(r.read())
            self.assertEqual(payload["schema"], "day16-execution-snapshot-v1")
            self.assertEqual(
                payload["pairs"][0]["pair_name"], "BRENTOIL__xyz:BRENTOIL"
            )
        finally:
            server.shutdown()
            server.server_close()

    def test_refresh_endpoint_runs_scanner_and_updates(self) -> None:
        import urllib.request

        calls = {"n": 0}

        def scanner():
            calls["n"] += 1
            left = lighter_spec()
            right = hl_spec()
            return build_execution_snapshot(
                [left],
                [right],
                books={
                    left.identity: book([("91.30", "10")], [("91.36", "10")]),
                    right.identity: book([("91.40", "10")], [("91.46", "10")]),
                },
                sizes_usd=(Decimal("10"),),
                scanned_at=f"2026-08-21T00:0{calls['n']}Z",
            )

        server, base = self._serve(scanner=scanner)
        try:
            request = urllib.request.Request(
                f"{base}/workbench/api/refresh", method="POST"
            )
            with urllib.request.urlopen(request, timeout=10) as r:
                payload = json.loads(r.read())
            self.assertEqual(r.status, 200)
            self.assertEqual(calls["n"], 1)
            self.assertEqual(payload["scanned_at"], "2026-08-21T00:01Z")
            with urllib.request.urlopen(
                f"{base}/workbench/api/execution", timeout=10
            ) as r:
                payload = json.loads(r.read())
            self.assertEqual(payload["scanned_at"], "2026-08-21T00:01Z")
        finally:
            server.shutdown()
            server.server_close()

    def test_old_day14_routes_still_serve(self) -> None:
        import urllib.request

        server, base = self._serve()
        try:
            with urllib.request.urlopen(f"{base}/workbench", timeout=10) as r:
                html = r.read().decode("utf-8")
            self.assertIn("研究工作台", html)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
