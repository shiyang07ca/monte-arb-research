from __future__ import annotations

import csv
import io
import json
import math
import tempfile
import unittest
import urllib.error
import urllib.request
from decimal import Decimal
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch

from monte_arb.oil_relative_value import (
    OilDataset,
    PricePoint,
    PriceSeries,
    build_oil_projection,
    export_source_csv,
    load_variational_recordings,
)
from monte_arb.workbench_app import WorkbenchApp


def series(key: str, values: list[tuple[int, float, float]]) -> PriceSeries:
    return PriceSeries(
        key=key,
        label=key.title(),
        venue=key,
        price_kind="test_close",
        interval="1h",
        points=tuple(
            PricePoint(
                timestamp_ms=timestamp_ms,
                wti=wti,
                brent=brent,
                wti_volume=None,
                brent_volume=None,
            )
            for timestamp_ms, wti, brent in values
        ),
        status="ok",
        reason=None,
        source_urls=("https://example.test",),
    )


class OilProjectionTests(unittest.TestCase):
    def test_projection_keeps_metrics_distinct_and_freezes_model(self) -> None:
        values = [
            (i * 3_600_000, 70 + i * 0.2, 75 + i * 0.25 + (0.5 if i == 9 else 0))
            for i in range(10)
        ]
        dataset = OilDataset(
            generated_at="2026-08-22T00:00:00Z",
            sources=(series("lighter", values),),
            execution={},
            diagnostics=(),
            raw_manifest={},
        )

        projection = build_oil_projection(dataset, formation_fraction=0.7)
        source = projection["sources"][0]
        latest = source["summary"]

        self.assertEqual(source["sample_count"], 10)
        self.assertAlmostEqual(latest["spread_usd"], values[-1][2] - values[-1][1])
        self.assertAlmostEqual(latest["ratio"], values[-1][2] / values[-1][1])
        self.assertAlmostEqual(
            latest["log_ratio"], math.log(values[-1][2]) - math.log(values[-1][1])
        )
        self.assertEqual(source["model"]["formation_count"], 7)
        self.assertEqual(source["model"]["validation_count"], 3)
        self.assertEqual(len(source["model"]["formation_data_sha256"]), 64)
        self.assertIsNotNone(latest["residual"])
        self.assertNotEqual(latest["spread_usd"], latest["residual"])
        self.assertTrue(source["model"]["frozen"])

    def test_leg_contribution_reports_which_market_moved(self) -> None:
        values = [(i * 3_600_000, 80.0, 85.0 + i * 0.1) for i in range(30)]
        dataset = OilDataset(
            generated_at="2026-08-22T00:00:00Z",
            sources=(series("lighter", values),),
            execution={},
            diagnostics=(),
            raw_manifest={},
        )

        source = build_oil_projection(dataset)["sources"][0]
        contribution = source["leg_contribution"]

        self.assertEqual(contribution["lookback_points"], 24)
        self.assertAlmostEqual(contribution["wti_log_change_bps"], 0.0)
        self.assertGreater(contribution["brent_log_change_bps"], 0)
        self.assertEqual(contribution["dominant_leg"], "brent")

    def test_leg_contribution_uses_elapsed_24_hours_not_row_count(self) -> None:
        points = tuple(
            PricePoint(timestamp_ms=i * 6 * 3_600_000, wti=80.0, brent=85.0 + i)
            for i in range(8)
        )
        dataset = OilDataset(
            generated_at="2026-08-22T00:00:00Z",
            sources=(
                PriceSeries(
                    key="irregular",
                    label="Irregular",
                    venue="test",
                    price_kind="test",
                    interval="observation",
                    points=points,
                    status="ok",
                    reason=None,
                    source_urls=(),
                ),
            ),
            execution={},
            diagnostics=(),
            raw_manifest={},
        )

        contribution = build_oil_projection(dataset)["sources"][0]["leg_contribution"]

        self.assertEqual(contribution["lookback_hours"], 24)
        self.assertEqual(contribution["lookback_points"], 4)
        self.assertEqual(contribution["elapsed_ms"], 24 * 3_600_000)

    def test_model_can_be_reused_without_refitting_new_observations(self) -> None:
        initial = series(
            "lighter",
            [(i * 3_600_000, 70 + i * 0.2, 75 + i * 0.25) for i in range(10)],
        )
        initial_projection = build_oil_projection(
            OilDataset("2026-08-22T00:00:00Z", (initial,), {}, (), {}),
            formation_fraction=0.7,
        )
        frozen = {"lighter": initial_projection["sources"][0]["model"]}
        extended = series(
            "lighter",
            [
                (i * 3_600_000, 70 + i * 0.2, 75 + i * 0.25 + (8 if i >= 10 else 0))
                for i in range(14)
            ],
        )

        projection = build_oil_projection(
            OilDataset("2026-08-23T00:00:00Z", (extended,), {}, (), {}),
            frozen_models=frozen,
        )
        model = projection["sources"][0]["model"]

        self.assertEqual(model["alpha"], frozen["lighter"]["alpha"])
        self.assertEqual(model["beta"], frozen["lighter"]["beta"])
        self.assertEqual(model["formation_end_ms"], frozen["lighter"]["formation_end_ms"])
        self.assertEqual(model["validation_count"], 7)
        self.assertEqual(model["model_origin"], "reused")
        self.assertEqual(
            model["formation_data_sha256"], frozen["lighter"]["formation_data_sha256"]
        )

    def test_model_reuse_survives_rolling_source_after_formation_expires(self) -> None:
        initial = series(
            "lighter",
            [(i * 3_600_000, 70 + i * 0.2, 75 + i * 0.25) for i in range(10)],
        )
        frozen = {
            "lighter": build_oil_projection(
                OilDataset("2026-08-22T00:00:00Z", (initial,), {}, (), {})
            )["sources"][0]["model"]
        }
        rolled = series(
            "lighter",
            [(i * 3_600_000, 70 + i * 0.2, 75 + i * 0.25) for i in range(5, 15)],
        )

        projection = build_oil_projection(
            OilDataset("2026-08-23T00:00:00Z", (rolled,), {}, (), {}),
            frozen_models=frozen,
        )

        self.assertTrue(projection["sources"][0]["model_reused"])
        self.assertEqual(
            projection["sources"][0]["model"]["formation_data_sha256"],
            frozen["lighter"]["formation_data_sha256"],
        )

    def test_changed_formation_data_refuses_frozen_model_reuse(self) -> None:
        initial = series(
            "lighter",
            [(i * 3_600_000, 70 + i * 0.2, 75 + i * 0.25) for i in range(10)],
        )
        initial_projection = build_oil_projection(
            OilDataset("2026-08-22T00:00:00Z", (initial,), {}, (), {})
        )
        frozen = {"lighter": initial_projection["sources"][0]["model"]}
        changed_values = [
            (i * 3_600_000, 70 + i * 0.2, 75 + i * 0.25) for i in range(10)
        ]
        changed_values[2] = (changed_values[2][0], changed_values[2][1], 999.0)
        changed = series("lighter", changed_values)

        projection = build_oil_projection(
            OilDataset("2026-08-23T00:00:00Z", (changed,), {}, (), {}),
            frozen_models=frozen,
        )

        self.assertFalse(projection["sources"][0]["model_reused"])
        self.assertNotEqual(
            projection["sources"][0]["model"]["formation_data_sha256"],
            frozen["lighter"]["formation_data_sha256"],
        )

    def test_regime_shift_is_reported_out_of_sample(self) -> None:
        values = []
        for i in range(40):
            wti = 70 + i * 0.15
            baseline = wti * (1.05 + (0.0005 if i % 2 else -0.0005))
            brent = baseline if i < 28 else wti * 1.12
            values.append((i * 3_600_000, wti, brent))
        dataset = OilDataset(
            generated_at="2026-08-22T00:00:00Z",
            sources=(series("lighter", values),),
            execution={},
            diagnostics=(),
            raw_manifest={},
        )

        projection = build_oil_projection(dataset, formation_fraction=0.7)
        source = projection["sources"][0]
        codes = {item["code"] for item in projection["diagnostics"]}

        self.assertGreater(source["validation"]["median_residual_z"], 2)
        self.assertGreater(source["validation"]["outside_two_sigma_fraction"], 0.5)
        self.assertIn("VALIDATION_DISTRIBUTION_SHIFT", codes)

    def test_daily_weekends_are_not_reported_as_feed_gaps(self) -> None:
        day_ms = 86_400_000
        # Monday through Friday, then the following Monday and Tuesday.
        timestamps = [0, 1, 2, 3, 4, 7, 8]
        dataset = OilDataset(
            generated_at="2026-08-22T00:00:00Z",
            sources=(
                PriceSeries(
                    key="external_daily",
                    label="External Daily",
                    venue="external",
                    price_kind="daily_close",
                    interval="1d",
                    points=tuple(
                        PricePoint(timestamp_ms=i * day_ms, wti=80 + i, brent=85 + i)
                        for i in timestamps
                    ),
                    status="ok",
                    reason=None,
                    source_urls=("https://example.test",),
                ),
            ),
            execution={},
            diagnostics=(),
            raw_manifest={"captures": [{"sha256": "abc", "name": "fixture"}]},
        )

        projection = build_oil_projection(dataset)

        self.assertIsNone(projection["sources"][0]["health"]["gap_count"])
        self.assertEqual(
            projection["sources"][0]["health"]["gap_evaluation"],
            "requires_exchange_calendar",
        )
        self.assertEqual(projection["provenance"]["captures"][0]["sha256"], "abc")

    def test_mechanism_diagnostics_expose_results_and_evidence_gaps(self) -> None:
        values = [
            (i * 3_600_000, 80 + i * 0.01, 85 + i * 0.015)
            for i in range(96)
        ]
        dataset = OilDataset(
            generated_at="2026-08-22T00:00:00Z",
            sources=(series("lighter", values),),
            execution={"limitations": ["HOLDING_FUNDING_UNKNOWN"]},
            diagnostics=(),
            raw_manifest={},
        )

        projection = build_oil_projection(dataset)
        diagnostics = projection["diagnostics"]
        codes = {item["code"] for item in diagnostics}

        self.assertIn("LEG_CONTRIBUTION_24_HOUR", codes)
        self.assertIn("UTC_HOUR_PROFILE", codes)
        self.assertIn("ROLL_EVIDENCE_UNAVAILABLE", codes)
        self.assertIn("FUNDING_EVIDENCE_UNAVAILABLE", codes)
        self.assertIn("DATA_HEALTH_SUMMARY", codes)
        self.assertTrue(
            all("limitations" in item and "next_check" in item for item in diagnostics)
        )

    def test_unavailable_source_is_preserved_without_fake_points(self) -> None:
        unavailable = PriceSeries(
            key="variational_rfq",
            label="Variational RFQ",
            venue="variational",
            price_kind="indicative_rfq_mid",
            interval="observation",
            points=(),
            status="unavailable",
            reason="NO_LOCAL_RECORDINGS",
            source_urls=(),
        )
        dataset = OilDataset(
            generated_at="2026-08-22T00:00:00Z",
            sources=(unavailable,),
            execution={},
            diagnostics=(),
            raw_manifest={},
        )

        source = build_oil_projection(dataset)["sources"][0]

        self.assertEqual(source["status"], "unavailable")
        self.assertEqual(source["reason"], "NO_LOCAL_RECORDINGS")
        self.assertEqual(source["points"], [])
        self.assertIsNone(source["summary"])

    def test_variational_import_reads_only_market_observations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "runtime-test.jsonl"
            events = [
                {
                    "event_type": "market_observation",
                    "recorded_at_utc": "2026-08-22T00:00:01+00:00",
                    "payload": {
                        "observed_at": "2026-08-22T00:00:01+00:00",
                        "quotes": {
                            "BZ": {
                                "bid": "92.00",
                                "ask": "92.04",
                                "index_price": "92.02",
                                "quantity": "0.002",
                                "source_at": "2026-08-22T00:00:00+00:00",
                                "received_at": "2026-08-22T00:00:00.5+00:00",
                            },
                            "CL": {
                                "bid": "86.40",
                                "ask": "86.44",
                                "index_price": "86.42",
                                "quantity": "0.002",
                                "source_at": "2026-08-22T00:00:00+00:00",
                                "received_at": "2026-08-22T00:00:00.5+00:00",
                            },
                        },
                    },
                },
                {
                    "event_type": "account_snapshot",
                    "recorded_at_utc": "2026-08-22T00:00:02+00:00",
                    "payload": {"balance_usdc": "SECRET-NOT-MARKET-DATA"},
                },
            ]
            path.write_text("\n".join(json.dumps(row) for row in events) + "\n")

            imported = load_variational_recordings(root)

        by_key = {item.key: item for item in imported}
        self.assertEqual(set(by_key), {"variational_index", "variational_rfq"})
        self.assertEqual(len(by_key["variational_rfq"].points), 1)
        self.assertAlmostEqual(by_key["variational_rfq"].points[0].brent, 92.02)
        self.assertAlmostEqual(by_key["variational_index"].points[0].wti, 86.42)
        self.assertIsNone(by_key["variational_index"].points[0].roll_window)
        serialized = json.dumps([item.to_dict() for item in imported])
        self.assertNotIn("SECRET-NOT-MARKET-DATA", serialized)
        self.assertNotIn("balance_usdc", serialized)

    def test_variational_import_skips_non_market_payload_before_json_decode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime-filter.jsonl"
            account = json.dumps(
                {
                    "event_type": "account_snapshot",
                    "payload": {"balance_usdc": "SECRET"},
                },
                separators=(",", ":"),
            )
            market = json.dumps(
                {
                    "event_type": "market_observation",
                    "recorded_at_utc": "2026-08-22T00:00:00+00:00",
                    "payload": {
                        "observed_at": "2026-08-22T00:00:00+00:00",
                        "quotes": {
                            "BZ": {"bid": "92", "ask": "92.1"},
                            "CL": {"bid": "86", "ask": "86.1"},
                        },
                    },
                },
                separators=(",", ":"),
            )
            path.write_text(account + "\n" + market + "\n")
            original_loads = json.loads
            decoded: list[str] = []

            def tracking_loads(value, *args, **kwargs):
                decoded.append(value)
                return original_loads(value, *args, **kwargs)

            with patch("monte_arb.oil_relative_value.json.loads", side_effect=tracking_loads):
                imported = load_variational_recordings(Path(tmp))

        self.assertEqual(len(decoded), 1)
        self.assertIn('"event_type":"market_observation"', decoded[0])
        self.assertNotIn("SECRET", decoded[0])
        self.assertEqual(len(imported[1].points), 1)

    def test_frozen_book_round_trip_friction_is_non_negative_for_both_directions(self) -> None:
        from monte_arb.execution_engine import L2Book, L2Level, MarketSpec
        from monte_arb.market import MarketIdentity
        from monte_arb.oil_relative_value import estimate_oil_direction

        def spec(symbol: str) -> MarketSpec:
            return MarketSpec(
                identity=MarketIdentity("test", "perp", "", symbol, symbol),
                venue="test",
                taker_fee_bps=Decimal("0"),
                maker_fee_bps=Decimal("0"),
                size_decimals=2,
                min_base_amount=Decimal("0.01"),
                min_quote_amount=Decimal("1"),
                multiplier=Decimal("1"),
                price_decimals=2,
                max_leverage=None,
                margin_evidence="unknown",
            )

        def book(_symbol: str, bid: str, ask: str) -> L2Book:
            return L2Book(
                bids=(L2Level(Decimal(bid), Decimal("100")),),
                asks=(L2Level(Decimal(ask), Decimal("100")),),
                source_time_ms=1,
            )

        specs = {"WTI": spec("WTI"), "BRENTOIL": spec("BRENTOIL")}
        books = {
            "WTI": book("WTI", "79.95", "80.05"),
            "BRENTOIL": book("BRENTOIL", "84.95", "85.05"),
        }

        for direction in ("long_brent_short_wti", "long_wti_short_brent"):
            result = estimate_oil_direction(
                books, specs, direction=direction, size_usd=Decimal("500")
            )
            self.assertEqual(result["status"], "full_fill")
            self.assertGreater(result["entry_crossing_bps"], 0)
            self.assertGreater(result["round_trip_friction_bps"], 0)
            self.assertEqual(result["entry_fill_pct"], 100.0)
            self.assertEqual(result["entry_residual_qty"], 0.0)
            self.assertEqual(result["exit_fill_pct"], 100.0)
            self.assertEqual(result["residual_open_qty"], 0.0)
            self.assertEqual(result["entry_status"], "full_fill")
            self.assertEqual(result["exit_status"], "full_fill")

    def test_execution_reports_entry_and_exit_fill_separately(self) -> None:
        from monte_arb.execution_engine import L2Book, L2Level, MarketSpec
        from monte_arb.market import MarketIdentity
        from monte_arb.oil_relative_value import estimate_oil_direction

        def spec(symbol: str) -> MarketSpec:
            return MarketSpec(
                identity=MarketIdentity("test", "perp", "", symbol, symbol),
                venue="test",
                taker_fee_bps=Decimal("0"),
                maker_fee_bps=Decimal("0"),
                size_decimals=2,
                min_base_amount=Decimal("0.01"),
                min_quote_amount=Decimal("1"),
                multiplier=Decimal("1"),
                price_decimals=2,
                max_leverage=None,
                margin_evidence="unknown",
            )

        specs = {"WTI": spec("WTI"), "BRENTOIL": spec("BRENTOIL")}
        books = {
            "WTI": L2Book(
                bids=(L2Level(Decimal("79.95"), Decimal("100")),),
                asks=(L2Level(Decimal("80.05"), Decimal("2")),),
            ),
            "BRENTOIL": L2Book(
                bids=(L2Level(Decimal("84.95"), Decimal("100")),),
                asks=(L2Level(Decimal("85.05"), Decimal("100")),),
            ),
        }

        result = estimate_oil_direction(
            books,
            specs,
            direction="long_brent_short_wti",
            size_usd=Decimal("500"),
        )

        self.assertEqual(result["entry_status"], "full_fill")
        self.assertEqual(result["entry_fill_pct"], 100.0)
        self.assertEqual(result["entry_residual_qty"], 0.0)
        self.assertEqual(result["exit_status"], "partial_fill")
        self.assertLess(result["exit_fill_pct"], 100.0)
        self.assertGreater(result["residual_open_qty"], 0)
        self.assertIsNotNone(result["entry_crossing_bps"])
        self.assertIsNone(result["round_trip_friction_bps"])

    def test_unconfigured_variational_source_has_no_fake_path(self) -> None:
        from monte_arb.oil_relative_value import collect_oil_dataset
        from unittest.mock import patch

        empty = PriceSeries(
            key="lighter",
            label="Lighter",
            venue="lighter",
            price_kind="test",
            interval="1h",
            points=(),
            status="unavailable",
            reason="TEST",
            source_urls=(),
        )
        with tempfile.TemporaryDirectory() as tmp, patch(
            "monte_arb.oil_relative_value._collect_lighter",
            return_value=(empty, {"captures": []}, {}, {}),
        ), patch(
            "monte_arb.oil_relative_value._collect_hyperliquid",
            return_value=(empty, {"captures": []}, {}, {}),
        ), patch(
            "monte_arb.oil_relative_value._collect_external_daily",
            return_value=(empty, {"captures": []}),
        ):
            dataset = collect_oil_dataset(raw_directory=Path(tmp), sizes=())

        variational = [
            source for source in dataset.sources if source.venue == "variational"
        ]
        self.assertEqual(len(variational), 2)
        self.assertTrue(all(source.source_urls == () for source in variational))
        self.assertTrue(
            all(source.reason == "NO_LOCAL_RECORDINGS" for source in variational)
        )

    def test_execution_projection_declares_one_to_one_not_beta_hedged(self) -> None:
        from monte_arb.oil_relative_value import build_oil_execution_projection

        projection = build_oil_execution_projection({}, (Decimal("100"),))

        self.assertIn(
            "ONE_TO_ONE_QUANTITY_BASELINE_NOT_BETA_HEDGED",
            projection["limitations"],
        )
        self.assertIn(
            "CONTRACT_WEIGHT_AND_HEDGE_RATIO_UNVERIFIED",
            projection["limitations"],
        )

    def test_csv_export_contains_metrics_not_raw_json(self) -> None:
        dataset = OilDataset(
            generated_at="2026-08-22T00:00:00Z",
            sources=(series("lighter", [(0, 80, 85), (3_600_000, 81, 86)]),),
            execution={},
            diagnostics=(),
            raw_manifest={},
        )
        projection = build_oil_projection(dataset)

        text = export_source_csv(projection, "lighter")
        rows = list(csv.DictReader(io.StringIO(text)))

        self.assertEqual(len(rows), 2)
        self.assertIn("spread_usd", rows[0])
        self.assertIn("log_ratio", rows[0])
        self.assertNotIn("raw", rows[0])


class OilHttpTests(unittest.TestCase):
    def _serve(self) -> tuple[ThreadingHTTPServer, str]:
        dataset = OilDataset(
            generated_at="2026-08-22T00:00:00Z",
            sources=(
                series(
                    "lighter",
                    [
                        (i * 3_600_000, 80 + i * 0.1, 85 + i * 0.12)
                        for i in range(40)
                    ],
                ),
            ),
            execution={
                "sizes_usd": [100, 500, 1000],
                "venues": [],
                "limitations": ["FEE_UNKNOWN"],
            },
            diagnostics=(
                {
                    "code": "CURRENT_RESIDUAL_ELEVATED",
                    "severity": "watch",
                    "title": "当前残差偏高",
                    "evidence": ["fixture"],
                    "counter_evidence": [],
                    "limitations": ["test only"],
                    "next_check": "collect more",
                },
            ),
            raw_manifest={},
        )
        app = WorkbenchApp(oil=build_oil_projection(dataset))
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler())
        Thread(target=server.serve_forever, daemon=True).start()
        return server, f"http://127.0.0.1:{server.server_port}"

    def test_dashboard_and_oil_page_are_product_pages(self) -> None:
        server, base = self._serve()
        try:
            with urllib.request.urlopen(f"{base}/workbench", timeout=10) as response:
                dashboard = response.read().decode()
            with urllib.request.urlopen(f"{base}/workbench/oil", timeout=10) as response:
                oil = response.read().decode()
        finally:
            server.shutdown()
            server.server_close()

        self.assertIn("研究操作台", dashboard)
        self.assertIn("Brent–WTI", dashboard)
        self.assertIn("相对价值", oil)
        self.assertIn("价格源", oil)
        self.assertIn("执行摩擦", oil)
        self.assertNotIn("原始候选 JSON", dashboard)
        self.assertNotIn("<pre>{", dashboard)
        self.assertIn("color-scheme: light", oil)
        self.assertIn("--variational-runtime", oil)
        self.assertIn("Formation UTC", oil)
        self.assertIn("进场成交率", oil)
        self.assertIn("进场残余", oil)
        self.assertIn("退出成交率", oil)
        self.assertIn("退出后未关闭", oil)

    def test_json_and_csv_endpoints_support_secondary_development(self) -> None:
        server, base = self._serve()
        try:
            with urllib.request.urlopen(f"{base}/workbench/api/oil", timeout=10) as response:
                payload = json.loads(response.read())
            with urllib.request.urlopen(
                f"{base}/workbench/api/oil.csv?source=lighter", timeout=10
            ) as response:
                csv_text = response.read().decode()
                content_type = response.headers["Content-Type"]
        finally:
            server.shutdown()
            server.server_close()

        self.assertEqual(payload["schema"], "oil-relative-value-v1")
        self.assertEqual(payload["sources"][0]["key"], "lighter")
        self.assertIn("text/csv", content_type)
        self.assertIn("spread_usd", csv_text)

    def test_http_routes_do_not_expose_execution_or_order_actions(self) -> None:
        server, base = self._serve()
        try:
            for path in (
                "/workbench/api/order",
                "/workbench/api/trade",
                "/workbench/api/oil/execute",
            ):
                request = urllib.request.Request(base + path, data=b"{}", method="POST")
                with self.assertRaises(urllib.error.HTTPError) as context:
                    urllib.request.urlopen(request, timeout=10)
                self.assertEqual(context.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()

    def test_unknown_csv_source_returns_404(self) -> None:
        server, base = self._serve()
        try:
            with self.assertRaises(urllib.error.HTTPError) as context:
                urllib.request.urlopen(
                    f"{base}/workbench/api/oil.csv?source=missing", timeout=10
                )
            self.assertEqual(context.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
