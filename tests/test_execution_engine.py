"""Day16 execution and capacity tests: frozen-L2 walking, order sizing, pair legs.

Public seam: monte_arb.execution_engine pure functions over frozen L2 books and
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

from monte_arb.execution_engine import (
    L2Book,
    L2Level,
    MarketSpec,
    build_execution_snapshot,
    capacity_usd,
    common_exposure_for_notional,
    leg_execution,
    normalize_lighter_details,
    order_qty_for_notional,
    pair_execution,
    round_trip_execution,
    walk_book,
)
from monte_arb.market import CatalogMarket, MarketIdentity
from monte_arb.workbench_app import WorkbenchApp


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
            Decimal(taker_fee) * Decimal(100) if taker_fee is not None else None
        ),
        maker_fee_bps=(
            Decimal(maker_fee) * Decimal(100) if maker_fee is not None else None
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
    def test_pair_uses_common_legal_base_quantity(self) -> None:
        # Independent $100 sizing would produce 0.99 on the buy leg and 1.02
        # on the sell leg. The pair must use the largest quantity legal on both
        # venues: 0.99, leaving no base exposure mismatch.
        left = lighter_spec(size_decimals=2, min_base="0.01")
        right = hl_spec(size_decimals=2)
        result = pair_execution(
            left,
            book([("100", "10")], [("101", "10")]),
            right,
            book([("98", "10")], [("99", "10")]),
            direction="buy_left_sell_right",
            target_notional_usd=Decimal("100"),
        )
        self.assertEqual(result.common_base_qty, Decimal("0.99"))
        self.assertEqual(result.buy.target_qty, Decimal("0.99"))
        self.assertEqual(result.sell.target_qty, Decimal("0.99"))
        self.assertEqual(result.residual_base_qty, Decimal("0"))

    def test_common_quantity_respects_different_multipliers(self) -> None:
        # Equal economic exposure means qty * multiplier matches. With a 10x
        # contract on the right, 1 left unit hedges 0.1 right contracts.
        left = lighter_spec(size_decimals=2, min_base="0.01", multiplier="1")
        right = hl_spec(size_decimals=1)
        right = MarketSpec(
            identity=right.identity,
            venue=right.venue,
            taker_fee_bps=right.taker_fee_bps,
            maker_fee_bps=right.maker_fee_bps,
            size_decimals=right.size_decimals,
            min_base_amount=Decimal("0.1"),
            min_quote_amount=right.min_quote_amount,
            multiplier=Decimal("10"),
            price_decimals=right.price_decimals,
        )
        exposure = common_exposure_for_notional(
            left,
            Decimal("100"),
            right,
            Decimal("100"),
            target_notional_usd=Decimal("100"),
        )
        self.assertEqual(exposure.exposure_units, Decimal("1.0"))
        self.assertEqual(exposure.left_qty, Decimal("1.00"))
        self.assertEqual(exposure.right_qty, Decimal("0.1"))

    def test_vwap_spread_is_not_charged_slippage_twice(self) -> None:
        left = lighter_spec(size_decimals=2, min_base="0.01")
        right = hl_spec(size_decimals=2)
        result = pair_execution(
            left,
            # buy 2 qty -> 1 @100, 1 @102 -> VWAP 101
            book([("99", "5")], [("100", "1"), ("102", "5")]),
            right,
            # sell 2 qty -> 1 @104, 1 @102 -> VWAP 103
            book([("104", "1"), ("102", "5")], [("105", "5")]),
            direction="buy_left_sell_right",
            target_notional_usd=Decimal("202"),
        )
        self.assertAlmostEqual(result.executable_spread_bps, 202.1427, places=4)
        # Slippage remains a diagnostic decomposition, not another deduction.
        self.assertAlmostEqual(result.price_pnl_bps, result.executable_spread_bps, places=4)
        self.assertGreater(result.slippage_cost_bps, 0)

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

    def test_known_fees_produce_net_price_pnl_not_execution_cost(self) -> None:
        left = lighter_spec(taker_fee="0.0100")  # 1 bps
        right = hl_spec()
        right = MarketSpec(
            identity=right.identity,
            venue=right.venue,
            taker_fee_bps=Decimal("2"),
            maker_fee_bps=None,
            size_decimals=right.size_decimals,
            min_base_amount=right.min_base_amount,
            min_quote_amount=right.min_quote_amount,
            multiplier=right.multiplier,
            price_decimals=right.price_decimals,
        )
        result = pair_execution(
            left,
            book([("99", "10")], [("100", "10")]),
            right,
            book([("101", "10")], [("102", "10")]),
            direction="buy_left_sell_right",
            target_notional_usd=Decimal("100"),
        )
        self.assertAlmostEqual(result.executable_spread_bps, 99.5025, places=3)
        self.assertEqual(result.price_pnl_usd, Decimal("0.99000"))
        self.assertEqual(result.reference_notional_usd, Decimal("99.495000"))
        self.assertEqual(result.fee_cost_bps, 3.005)
        self.assertEqual(result.fee_cost_usd, Decimal("0.029898000"))
        self.assertEqual(result.net_price_pnl_usd, Decimal("0.960102000"))
        self.assertAlmostEqual(result.net_price_pnl_bps, 96.4975, places=3)

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

    def test_partial_fill_does_not_publish_target_size_pnl(self) -> None:
        left = lighter_spec(size_decimals=2, min_base="0.01")
        right = hl_spec(size_decimals=2)
        result = pair_execution(
            left,
            # Target is 5 units but only 1 can be bought.
            book([("99", "10")], [("100", "1")]),
            right,
            book([("101", "10")], [("102", "10")]),
            direction="buy_left_sell_right",
            target_notional_usd=Decimal("500"),
        )
        self.assertLess(result.fill_pct, 1.0)
        self.assertIn("DEPTH_INSUFFICIENT", result.reason_codes)
        self.assertIn("RESIDUAL_EXPOSURE", result.reason_codes)
        # The two partial VWAPs cover different exposure, so they must not be
        # presented as the requested-size executable spread or PnL.
        self.assertIsNone(result.executable_spread_bps)
        self.assertIsNone(result.price_pnl_bps)
        self.assertIsNone(result.net_price_pnl_bps)

    def test_round_trip_closes_exact_entry_exposure(self) -> None:
        left = lighter_spec(size_decimals=1, min_base="0.1")
        right = hl_spec(size_decimals=1)
        result = round_trip_execution(
            left,
            book([("99", "10")], [("100", "10")]),
            right,
            # Entry sells at 110, but exit buys at 200. Re-sizing exit from the
            # original $100 target would close only 0.5 instead of the 0.9
            # entered. A true round trip must close the exact entry exposure.
            book([("110", "10")], [("200", "10")]),
            direction="buy_left_sell_right",
            target_notional_usd=Decimal("100"),
        )
        self.assertEqual(result.entry.common_exposure_units, Decimal("0.9"))
        self.assertEqual(result.exit.common_exposure_units, Decimal("0.9"))
        self.assertEqual(result.exit.buy.target_qty, Decimal("0.9"))
        self.assertEqual(result.exit.sell.target_qty, Decimal("0.9"))
        self.assertEqual(result.exit.residual_base_qty, Decimal("0"))

    def test_round_trip_uses_four_aggressive_fills(self) -> None:
        left = lighter_spec(size_decimals=2, min_base="0.01")
        right = hl_spec(size_decimals=2)
        result = round_trip_execution(
            left,
            book([("99", "10")], [("100", "10")]),
            right,
            book([("101", "10")], [("102", "10")]),
            direction="buy_left_sell_right",
            target_notional_usd=Decimal("100"),
        )
        self.assertAlmostEqual(result.entry.executable_spread_bps, 99.5025, places=3)
        # Exit reverses both legs on the same frozen books: buy at 102, sell at
        # 99. Four aggressive fills make round-trip price PnL negative.
        self.assertAlmostEqual(result.exit.executable_spread_bps, -298.5075, places=3)
        self.assertEqual(result.round_trip_price_pnl_usd, Decimal("-1.980"))
        self.assertEqual(result.reference_notional_usd, Decimal("99.495000"))
        self.assertAlmostEqual(result.round_trip_price_pnl_bps, -199.0050, places=3)

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
    def test_pair_discovery_excludes_inactive_markets(self) -> None:
        from monte_arb.execution_engine import _discover_pairs

        def market(venue: str, symbol: str, status: str) -> CatalogMarket:
            namespace = "default" if venue == "lighter" else "xyz"
            return CatalogMarket(
                MarketIdentity(venue, "perp", namespace, symbol, symbol),
                status,
                {},
            )

        pairs = _discover_pairs(
            [market("lighter", "LIVE", "active"), market("lighter", "OLD", "inactive")],
            [
                market("hyperliquid", "xyz:LIVE", "active"),
                market("hyperliquid", "xyz:OLD", "active"),
                market("hyperliquid", "xyz:DELISTED", "delisted"),
            ],
        )
        self.assertEqual([row[2] for row in pairs], ["LIVE__xyz:LIVE"])

    def test_atomic_snapshot_publish_preserves_previous_file_on_serialization_error(self) -> None:
        import tempfile
        from pathlib import Path

        from monte_arb.execution_engine import write_snapshot_atomic

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "snapshot.json"
            output.write_text('{"stable": true}\n')
            with self.assertRaises(TypeError):
                write_snapshot_atomic(output, {"bad": object()})
            self.assertEqual(output.read_text(), '{"stable": true}\n')
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])

    def test_incomplete_scan_does_not_replace_previous_output(self) -> None:
        import tempfile
        from pathlib import Path

        from monte_arb.execution_engine import publish_snapshot_if_complete

        output_text = '{"stable": true}\n'
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "snapshot.json"
            output.write_text(output_text)
            snapshot = build_execution_snapshot(
                [], [], {}, sizes_usd=(Decimal("25"),),
                request_errors=(("venue/market", "REQUEST_FAILED"),),
            )
            published = publish_snapshot_if_complete(
                output, snapshot, snapshot.to_dict()
            )
            self.assertFalse(published)
            self.assertEqual(output.read_text(), output_text)

    def test_capacity_reports_truncation_at_largest_tested_size(self) -> None:
        left = lighter_spec()
        right = hl_spec()
        snapshot = build_execution_snapshot(
            [left],
            [right],
            books={
                left.identity: book([("91.30", "100")], [("91.36", "100")]),
                right.identity: book([("91.40", "100")], [("91.46", "100")]),
            },
            sizes_usd=(Decimal("100"), Decimal("500"), Decimal("1000")),
        )
        capacity = snapshot.pairs[0].capacity["buy_left_sell_right"]
        self.assertEqual(capacity.max_full_fill_usd, Decimal("1000"))
        self.assertTrue(capacity.lower_bound_only)

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
        self.assertEqual(snapshot.schema, "day16-execution-snapshot-v2")
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
    def test_hyperliquid_catalog_preserves_sz_decimals_for_execution(self) -> None:
        from monte_arb.adapters import normalize_hyperliquid_catalog

        response = [
            {"universe": [{"name": "xyz:TEST", "szDecimals": 4}]},
            [{"midPx": "100"}],
        ]
        market = normalize_hyperliquid_catalog(
            response, perp_dex_index=1, venue_namespace="xyz"
        )[0]
        self.assertEqual(market.context["szDecimals"], 4)

    def test_lighter_fee_unit_percent_to_bps(self) -> None:
        response = {
            "code": 200,
            "order_book_details": [
                {
                    "symbol": "TEST",
                    "market_id": 1,
                    "taker_fee": "0.0500",
                    "maker_fee": "0.0200",
                    "min_base_amount": "0.1",
                    "min_quote_amount": "10",
                    "multiplier": "1",
                    "supported_size_decimals": 1,
                    "supported_price_decimals": 2,
                }
            ],
        }
        spec = normalize_lighter_details(response)[1]
        self.assertEqual(spec.taker_fee_bps, Decimal("5"))
        self.assertEqual(spec.maker_fee_bps, Decimal("2"))

    def test_normalize_lighter_details_from_repo_fixture(self) -> None:
        import json as _json
        from pathlib import Path

        from monte_arb.execution_engine import normalize_lighter_details

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

    def test_execution_page_uses_light_color_scheme_and_single_flight_refresh(self) -> None:
        from monte_arb.workbench_views import render_execution_html

        html = render_execution_html()
        self.assertIn("color-scheme: light", html)
        self.assertNotIn("color-scheme: dark", html)
        self.assertIn("state.refreshing", html)
        self.assertIn("if (state.refreshing) return", html)
        self.assertIn("finally", html)
        self.assertIn("state.refreshing = false", html)

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
            self.assertEqual(payload["schema"], "day16-execution-snapshot-v2")
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
                refresh_mode="live_scan",
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
            self.assertEqual(payload["refresh_mode"], "live_scan")
            with urllib.request.urlopen(
                f"{base}/workbench/api/execution", timeout=10
            ) as r:
                payload = json.loads(r.read())
            self.assertEqual(payload["scanned_at"], "2026-08-21T00:01Z")
        finally:
            server.shutdown()
            server.server_close()

    def test_compute_endpoint_rejects_non_finite_size(self) -> None:
        import urllib.error
        import urllib.request

        server, base = self._serve()
        try:
            for value in ("NaN", "Infinity", -1, 0, 10_000_001):
                request = urllib.request.Request(
                    f"{base}/workbench/api/execution/compute",
                    data=json.dumps({"size_usd": value}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(request, timeout=10)
                self.assertEqual(ctx.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()

    def test_refresh_failure_keeps_last_good_snapshot_and_returns_error(self) -> None:
        import urllib.error
        import urllib.request

        def scanner():
            raise RuntimeError("upstream unavailable")

        server, base = self._serve(scanner=scanner)
        try:
            with urllib.request.urlopen(
                f"{base}/workbench/api/execution", timeout=10
            ) as response:
                before = json.loads(response.read())
            request = urllib.request.Request(
                f"{base}/workbench/api/refresh", method="POST"
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(request, timeout=10)
            self.assertEqual(ctx.exception.code, 500)
            with urllib.request.urlopen(
                f"{base}/workbench/api/execution", timeout=10
            ) as response:
                after = json.loads(response.read())
            self.assertEqual(after["scanned_at"], before["scanned_at"])
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
