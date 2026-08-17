from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from monte_arb.adapters import (
    Capture,
    SourceShapeError,
    normalize_hyperliquid_catalog,
    normalize_lighter_catalog,
)
from monte_arb.cli import _capture_manifest, _save_raw_captures
from monte_arb.market import (
    CatalogMarket,
    MarketIdentity,
    classify_book,
    scan_markets,
)

FIXTURES = Path(__file__).parent / "fixtures" / "day12"


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


class Day12ScanTests(unittest.TestCase):
    def test_raw_capture_is_content_addressed_and_manifest_points_to_it(self) -> None:
        raw = b'{"code":200}'
        sha256 = hashlib.sha256(raw).hexdigest()
        client = type(
            "FakeClient",
            (),
            {
                "captures": [
                    Capture(
                        "sample",
                        "GET",
                        "https://example.test/data",
                        {},
                        "2026-08-17T00:00:00Z",
                        200,
                        sha256,
                        raw,
                    )
                ]
            },
        )()
        with tempfile.TemporaryDirectory() as directory:
            paths = _save_raw_captures(client, Path(directory))
            manifest = _capture_manifest(client, paths)
            raw_path = Path(manifest["captures"][0]["raw_file"])
            self.assertEqual(raw_path.read_bytes(), raw)

    def test_equal_response_bytes_keep_each_capture_name(self) -> None:
        raw = b"{}"
        sha256 = hashlib.sha256(raw).hexdigest()
        captures = [
            Capture(
                name,
                "GET",
                f"https://example.test/{name}",
                {},
                "2026-08-17T00:00:00Z",
                200,
                sha256,
                raw,
            )
            for name in ("first", "second")
        ]
        client = type("FakeClient", (), {"captures": captures})()

        with tempfile.TemporaryDirectory() as directory:
            paths = _save_raw_captures(client, Path(directory))
            manifest = _capture_manifest(client, paths)
            raw_files = [Path(row["raw_file"]).name for row in manifest["captures"]]

        self.assertEqual(raw_files[0], f"first-{sha256}.json")
        self.assertEqual(raw_files[1], f"second-{sha256}.json")
        with self.assertRaises(SourceShapeError):
            _capture_manifest(client, paths[:1])

    def test_lighter_book_keeps_requested_market_identity(self) -> None:
        catalog = normalize_lighter_catalog(load("lighter-order-books.json"))
        wti = next(m for m in catalog if m.identity.symbol == "WTI")

        report = scan_markets(catalog, {wti.identity: load("lighter-wti-book.json")})
        result = next(m for m in report.markets if m.identity == wti.identity)

        self.assertEqual(result.identity.local_id, "145")
        self.assertEqual(result.book_status, "two_sided")
        self.assertEqual(result.scan_status, "ready_for_market_mapping")

    def test_hyperliquid_pairs_meta_and_context_before_filtering(self) -> None:
        catalog = normalize_hyperliquid_catalog(
            load("hyperliquid-meta-contexts.json"),
            perp_dex_index=1,
            venue_namespace="xyz",
        )
        cl = next(m for m in catalog if m.identity.symbol == "xyz:CL")

        self.assertEqual(cl.index_in_meta, 1)
        self.assertEqual(cl.identity.local_id, "110001")
        self.assertEqual(cl.context["midPx"], "81.15")

    def test_hyperliquid_rejects_meta_context_length_mismatch(self) -> None:
        response = load("hyperliquid-meta-contexts.json")
        response[1].pop()

        with self.assertRaises(SourceShapeError):
            normalize_hyperliquid_catalog(
                response,
                perp_dex_index=1,
                venue_namespace="xyz",
            )

    def test_unknown_symbol_is_explicit(self) -> None:
        catalog = normalize_lighter_catalog(load("lighter-order-books.json"))
        unknown = MarketIdentity("lighter", "perp", "default", "DOES_NOT_EXIST", "999")

        report = scan_markets(catalog, {}, requested=(unknown,))

        self.assertEqual(report.request_errors[0].reason_code, "UNKNOWN_SYMBOL")

    def test_market_selector_round_trip_includes_local_id(self) -> None:
        identity = MarketIdentity("hyperliquid", "perp", "xyz", "xyz:CL", "110001")
        self.assertEqual(MarketIdentity.from_selector(identity.selector), identity)

    def test_duplicate_local_id_is_invalid_even_when_symbols_differ(self) -> None:
        first = CatalogMarket(
            MarketIdentity("lighter", "perp", "default", "WTI", "145"),
            "active",
            {},
        )
        second = CatalogMarket(
            MarketIdentity("lighter", "perp", "default", "NOT_WTI", "145"),
            "active",
            {},
        )

        report = scan_markets((first, second), {})

        self.assertTrue(all(m.scan_status == "invalid" for m in report.markets))
        self.assertTrue(
            all(m.reason_codes == ("DUPLICATE_LOCAL_ID",) for m in report.markets)
        )

    def test_duplicate_symbol_is_invalid_even_when_local_ids_differ(self) -> None:
        first = CatalogMarket(
            MarketIdentity("hyperliquid", "perp", "xyz", "xyz:CL", "110001"),
            "active",
            {},
        )
        second = CatalogMarket(
            MarketIdentity("hyperliquid", "perp", "xyz", "xyz:CL", "110002"),
            "active",
            {},
        )

        report = scan_markets((first, second), {})

        self.assertTrue(all(m.scan_status == "invalid" for m in report.markets))
        self.assertTrue(
            all(m.reason_codes == ("DUPLICATE_SYMBOL",) for m in report.markets)
        )

    def test_book_parser_is_venue_specific_and_rejects_malformed_side(self) -> None:
        lighter = MarketIdentity("lighter", "perp", "default", "WTI", "145")
        hyperliquid = MarketIdentity("hyperliquid", "perp", "xyz", "xyz:CL", "110029")

        missing_code = {
            "bids": [{"price": "1", "remaining_base_amount": "1"}],
            "asks": [{"price": "2", "remaining_base_amount": "1"}],
        }
        wrong_shape = {
            "code": 200,
            "bids": [{"price": "1", "remaining_base_amount": "1"}],
            "asks": [{"price": "2", "remaining_base_amount": "1"}],
        }
        malformed_one_side = {
            "code": 200,
            "bids": [{"price": "bad", "remaining_base_amount": "1"}],
            "asks": [],
        }

        self.assertEqual(classify_book(missing_code, lighter)[0], "invalid")
        self.assertEqual(classify_book(wrong_shape, hyperliquid)[0], "invalid")
        self.assertEqual(classify_book(malformed_one_side, lighter)[0], "invalid")

    def test_hyperliquid_returned_coin_mismatch_is_invalid(self) -> None:
        catalog = normalize_hyperliquid_catalog(
            load("hyperliquid-meta-contexts.json"),
            perp_dex_index=1,
            venue_namespace="xyz",
        )
        cl = next(m for m in catalog if m.identity.symbol == "xyz:CL")
        book = load("hyperliquid-cl-book.json")
        book["coin"] = "xyz:BRENTOIL"

        report = scan_markets(catalog, {cl.identity: book})
        result = next(m for m in report.markets if m.identity == cl.identity)

        self.assertEqual(result.scan_status, "invalid")
        self.assertEqual(result.reason_codes, ("IDENTITY_MISMATCH",))

    def test_empty_and_one_sided_books_do_not_advance(self) -> None:
        catalog = normalize_lighter_catalog(load("lighter-order-books.json"))
        wti = next(m for m in catalog if m.identity.symbol == "WTI")
        brent = next(m for m in catalog if m.identity.symbol == "BRENTOIL")

        report = scan_markets(
            catalog,
            {
                wti.identity: {"code": 200, "bids": [], "asks": []},
                brent.identity: {
                    "code": 200,
                    "bids": [{"price": "1", "remaining_base_amount": "1"}],
                    "asks": [],
                },
            },
        )
        by_symbol = {m.identity.symbol: m for m in report.markets}

        self.assertEqual(by_symbol["WTI"].reason_codes, ("BOOK_EMPTY",))
        self.assertEqual(by_symbol["BRENTOIL"].reason_codes, ("BOOK_ONE_SIDED",))

    def test_uninspected_catalog_record_stays_catalog_only(self) -> None:
        catalog = normalize_lighter_catalog(load("lighter-order-books.json"))
        report = scan_markets(catalog, {})
        self.assertTrue(all(m.scan_status == "catalog_only" for m in report.markets))
        self.assertTrue(
            all(m.reason_codes == ("BOOK_NOT_INSPECTED",) for m in report.markets)
        )

    def test_same_frozen_input_has_same_decisions(self) -> None:
        catalog = normalize_lighter_catalog(load("lighter-order-books.json"))
        wti = next(m for m in catalog if m.identity.symbol == "WTI")
        books = {wti.identity: load("lighter-wti-book.json")}

        first = scan_markets(catalog, books).decision_payload()
        second = scan_markets(catalog, books).decision_payload()

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
