"""Day14 workbench v0 tests: candidate snapshot and HTTP surface."""

from __future__ import annotations

import json
import unittest
from http.server import ThreadingHTTPServer
from threading import Thread
from typing import Any, Mapping

from monte_arb.market import CatalogMarket, MarketIdentity
from monte_arb.candidate_workbench import (
    BookQuote,
    SnapshotItem,
    build_candidate_snapshot,
)
from monte_arb.workbench_app import WorkbenchApp

WTI = MarketIdentity("lighter", "perp", "default", "WTI", "145")
CL = MarketIdentity("hyperliquid", "perp", "xyz", "xyz:CL", "110029")
BRENT = MarketIdentity("lighter", "perp", "default", "BRENTOIL", "159")
XYZ_BRENT = MarketIdentity("hyperliquid", "perp", "xyz", "xyz:BRENTOIL", "110049")


def catalog(*markets: MarketIdentity) -> tuple[CatalogMarket, ...]:
    return tuple(CatalogMarket(identity, "active", {}) for identity in markets)


def lighter_book(
    bid: str, ask: str, bid_size: str = "10", ask_size: str = "10"
) -> Mapping[str, Any]:
    return {
        "code": 200,
        "bids": [{"price": bid, "remaining_base_amount": bid_size}],
        "asks": [{"price": ask, "remaining_base_amount": ask_size}],
    }


def hl_book(
    coin: str,
    bid: str,
    ask: str,
    bid_size: str = "10",
    ask_size: str = "10",
    time_ms: int = 1_787_000_000_000,
) -> Mapping[str, Any]:
    return {
        "coin": coin,
        "time": time_ms,
        "levels": [
            [{"px": bid, "sz": bid_size, "n": 1}],
            [{"px": ask, "sz": ask_size, "n": 1}],
        ],
    }


def item(
    identity: MarketIdentity,
    *,
    bid: str = "100.0",
    ask: str = "100.1",
    source_time_ms: int | None = None,
    book_status: str = "two_sided",
) -> SnapshotItem:
    return SnapshotItem(
        identity=identity,
        catalog_status="active",
        book_status=book_status,
        quote=BookQuote(
            identity=identity,
            best_bid=bid,
            best_ask=ask,
            bid_size="10",
            ask_size="10",
            source_time_ms=source_time_ms,
        )
        if book_status == "two_sided"
        else None,
        funding=None,
        source_time_ms=source_time_ms,
    )


class CandidateSnapshotTests(unittest.TestCase):
    def test_pair_discovery_uses_exact_symbols_and_namespace_prefix(self) -> None:
        snapshot = build_candidate_snapshot(
            catalog(WTI, BRENT),
            catalog(CL, XYZ_BRENT),
            {
                BRENT: lighter_book("100", "100.1"),
                XYZ_BRENT: hl_book("xyz:BRENTOIL", "100.05", "100.15"),
            },
        )
        self.assertEqual(
            {candidate.pair_name for candidate in snapshot.candidates},
            {"BRENTOIL__xyz:BRENTOIL"},
        )

    def test_pair_discovery_does_not_map_wti_to_xyz_cl(self) -> None:
        # xyz:CL's base symbol is CL; Lighter's market is WTI. Exact-symbol
        # mapping must NOT pair them, no matter how similar they look.
        snapshot = build_candidate_snapshot(
            catalog(WTI),
            catalog(CL),
            {
                WTI: lighter_book("100", "100.1"),
                CL: hl_book("xyz:CL", "100.05", "100.15"),
            },
        )
        self.assertEqual(len(snapshot.candidates), 0)

    def test_cross_venue_spread_uses_bid_of_one_side_ask_of_other(self) -> None:
        snapshot = build_candidate_snapshot(
            catalog(BRENT),
            catalog(XYZ_BRENT),
            {
                BRENT: lighter_book("100", "100.1"),
                XYZ_BRENT: hl_book("xyz:BRENTOIL", "100.2", "100.3"),
            },
        )
        candidate = snapshot.candidates[0]
        # Buy BRENTOIL ask 100.1, sell xyz:BRENTOIL bid 100.2 -> 9.99 bps positive.
        self.assertAlmostEqual(candidate.executable_spread_bps, 9.9900, places=2)
        self.assertEqual(candidate.direction, "bid_right_ask_left")

    def test_crossed_direction_is_negative_spread(self) -> None:
        snapshot = build_candidate_snapshot(
            catalog(BRENT),
            catalog(XYZ_BRENT),
            {
                BRENT: lighter_book("100", "100.1"),
                XYZ_BRENT: hl_book("xyz:BRENTOIL", "99.9", "100.4"),
            },
        )
        candidate = snapshot.candidates[0]
        # Both directions are negative: buy left ask 100.1 / sell right bid 99.9 = -19.98 bps,
        # buy right ask 100.4 / sell left bid 100.0 = -39.84 bps. max() keeps the least bad.
        self.assertLess(candidate.executable_spread_bps, 0)
        self.assertEqual(candidate.direction, "bid_right_ask_left")

    def test_lighter_quote_has_no_source_time_and_is_flagged(self) -> None:
        snapshot = build_candidate_snapshot(
            catalog(BRENT),
            catalog(XYZ_BRENT),
            {
                BRENT: lighter_book("100", "100.1"),
                XYZ_BRENT: hl_book("xyz:BRENTOIL", "100.05", "100.15"),
            },
        )
        candidate = snapshot.candidates[0]
        self.assertIn("SOURCE_TIME_NOT_COMPARABLE", candidate.data_quality_issues)

    def test_missing_book_stops_candidate_advancement(self) -> None:
        snapshot = build_candidate_snapshot(
            catalog(BRENT),
            catalog(XYZ_BRENT),
            {BRENT: lighter_book("100", "100.1")},
        )
        self.assertEqual(len(snapshot.candidates), 0)

    def test_ranks_are_transparent_component_values(self) -> None:
        snapshot = build_candidate_snapshot(
            catalog(BRENT),
            catalog(XYZ_BRENT),
            {
                BRENT: lighter_book("100", "100.1"),
                XYZ_BRENT: hl_book("xyz:BRENTOIL", "100.05", "100.15"),
            },
        )
        candidate = snapshot.candidates[0]
        self.assertIn("CROSS_VENUE_EXECUTABLE_SPREAD", candidate.reasons)
        self.assertGreaterEqual(candidate.trade_rank, 0)
        self.assertGreaterEqual(candidate.research_rank, 0)

    def test_snapshot_declares_read_only_and_no_execution_client(self) -> None:
        snapshot = build_candidate_snapshot(catalog(BRENT), catalog(XYZ_BRENT), {})
        self.assertTrue(snapshot.read_only)
        self.assertFalse(snapshot.execution_client_present)
        self.assertIn(
            "No fees, funding cash, slippage, or spread PnL is calculated.",
            snapshot.boundaries,
        )

    def test_snapshot_json_round_trip_preserves_candidates(self) -> None:
        snapshot = build_candidate_snapshot(
            catalog(BRENT),
            catalog(XYZ_BRENT),
            {
                BRENT: lighter_book("100", "100.1"),
                XYZ_BRENT: hl_book("xyz:BRENTOIL", "100.05", "100.15"),
            },
        )
        payload = json.loads(json.dumps(snapshot.to_dict(), ensure_ascii=False))
        self.assertEqual(payload["schema"], snapshot.schema)
        self.assertEqual(len(payload["candidates"]), 1)
        self.assertEqual(
            payload["candidates"][0]["pair_name"], "BRENTOIL__xyz:BRENTOIL"
        )


class WorkbenchHttpTests(unittest.TestCase):
    def _serve(self) -> tuple[ThreadingHTTPServer, str]:
        snapshot = build_candidate_snapshot(
            catalog(BRENT),
            catalog(XYZ_BRENT),
            {
                BRENT: lighter_book("100", "100.1"),
                XYZ_BRENT: hl_book("xyz:BRENTOIL", "100.05", "100.15"),
            },
        )
        app = WorkbenchApp(snapshot)
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler())
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, f"http://127.0.0.1:{server.server_port}"

    def test_candidate_page_uses_light_color_scheme(self) -> None:
        from monte_arb.workbench_views import render_candidate_html

        snapshot = build_candidate_snapshot(catalog(BRENT), catalog(XYZ_BRENT), {})
        html = render_candidate_html(snapshot)
        self.assertIn("color-scheme: light", html)
        self.assertNotIn("color-scheme: dark", html)

    def test_html_and_json_endpoints_serve(self) -> None:
        import urllib.request

        server, base = self._serve()
        try:
            with urllib.request.urlopen(f"{base}/workbench", timeout=10) as response:
                html = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertIn("研究工作台", html)
            self.assertIn("BRENTOIL__xyz:BRENTOIL", html)
            with urllib.request.urlopen(
                f"{base}/workbench/api/candidates", timeout=10
            ) as response:
                payload = json.loads(response.read())
            self.assertEqual(payload["schema"], "day14-candidate-snapshot-v1")
            self.assertEqual(len(payload["candidates"]), 1)
        finally:
            server.shutdown()
            server.server_close()

    def test_unknown_route_returns_404(self) -> None:
        import urllib.error
        import urllib.request

        server, base = self._serve()
        try:
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(f"{base}/nope", timeout=10)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
