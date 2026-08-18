from __future__ import annotations

import unittest
from datetime import datetime, timezone

from monte_arb.synchronized_quotes import (
    QuoteObservation,
    SnapshotAttempt,
    build_snapshot,
    classify_pair_sample,
    parse_hyperliquid_book,
    parse_lighter_book,
)
from monte_arb.market import MarketIdentity

WTI = MarketIdentity("lighter", "perp", "default", "WTI", "145")
CL = MarketIdentity("hyperliquid", "perp", "xyz", "xyz:CL", "110029")


def quote(
    identity: MarketIdentity,
    *,
    bid: str = "84.01",
    ask: str = "84.02",
    request_started_ns: int = 1_000_000_000,
    response_received_ns: int = 1_100_000_000,
    source_time_ms: int | None = None,
) -> QuoteObservation:
    return QuoteObservation(
        identity=identity,
        request_started_ns=request_started_ns,
        response_received_ns=response_received_ns,
        source_time_ms=source_time_ms,
        best_bid=bid,
        best_ask=ask,
        bid_size="2",
        ask_size="3",
        raw_sha256="a" * 64,
    )


class Day14SynchronizedQuoteTests(unittest.TestCase):
    def test_lighter_book_has_no_source_timestamp_and_keeps_local_identity(
        self,
    ) -> None:
        observation = parse_lighter_book(
            WTI,
            {
                "code": 200,
                "bids": [{"price": "84.015", "remaining_base_amount": "14.791"}],
                "asks": [{"price": "84.024", "remaining_base_amount": "18.635"}],
            },
            request_started_ns=10,
            response_received_ns=20,
            raw_sha256="b" * 64,
        )

        self.assertEqual(observation.identity, WTI)
        self.assertIsNone(observation.source_time_ms)
        self.assertEqual(observation.best_bid, "84.015")
        self.assertEqual(observation.best_ask, "84.024")

    def test_hyperliquid_book_retains_exchange_source_timestamp(self) -> None:
        observation = parse_hyperliquid_book(
            CL,
            {
                "coin": "xyz:CL",
                "time": 1_787_016_930_824,
                "levels": [
                    [{"px": "84.019", "sz": "3.57", "n": 1}],
                    [{"px": "84.020", "sz": "0.239", "n": 1}],
                ],
            },
            request_started_ns=10,
            response_received_ns=20,
            raw_sha256="c" * 64,
        )

        self.assertEqual(observation.source_time_ms, 1_787_016_930_824)
        self.assertEqual(observation.best_bid, "84.019")
        self.assertEqual(observation.best_ask, "84.020")

    def test_snapshot_spans_first_request_start_to_last_response_receive(self) -> None:
        snapshot = build_snapshot(
            "attempt-1",
            (
                quote(WTI, request_started_ns=1_000, response_received_ns=1_400),
                quote(CL, request_started_ns=1_100, response_received_ns=1_800),
            ),
        )

        self.assertEqual(snapshot.capture_span_ms, 0.0008)
        self.assertEqual(snapshot.observation_count, 2)

    def test_crossed_or_invalid_books_stop_before_pair_assessment(self) -> None:
        with self.assertRaises(ValueError):
            build_snapshot(
                "attempt-crossed",
                (quote(WTI, bid="84.03", ask="84.02"), quote(CL)),
            )

    def test_pair_is_excluded_when_economic_mapping_is_unknown(self) -> None:
        result = classify_pair_sample(
            quote(WTI),
            quote(CL),
            economic_status="unknown",
            oracle_state_left="external",
            oracle_state_right="external",
            contract_weight_state="matched",
            max_receive_skew_ms=1_000,
        )

        self.assertEqual(result.status, "exclude")
        self.assertIn("ECONOMIC_MAPPING_UNKNOWN", result.reason_codes)

    def test_pair_is_excluded_when_oracle_state_differs(self) -> None:
        result = classify_pair_sample(
            quote(WTI),
            quote(CL),
            economic_status="same",
            oracle_state_left="internal",
            oracle_state_right="external",
            contract_weight_state="matched",
            max_receive_skew_ms=1_000,
        )

        self.assertEqual(result.status, "exclude")
        self.assertIn("ORACLE_STATE_MISMATCH", result.reason_codes)

    def test_pair_is_excluded_when_contract_weights_are_unknown(self) -> None:
        result = classify_pair_sample(
            quote(WTI),
            quote(CL),
            economic_status="same",
            oracle_state_left="external",
            oracle_state_right="external",
            contract_weight_state="unknown",
            max_receive_skew_ms=1_000,
        )

        self.assertEqual(result.status, "exclude")
        self.assertIn("CONTRACT_WEIGHT_UNKNOWN", result.reason_codes)

    def test_receive_skew_uses_local_receive_clock_when_one_source_time_is_missing(
        self,
    ) -> None:
        left = quote(WTI, response_received_ns=1_000_000_000, source_time_ms=None)
        right = quote(
            CL,
            response_received_ns=1_250_000_000,
            source_time_ms=1_787_016_930_824,
        )
        result = classify_pair_sample(
            left,
            right,
            economic_status="same",
            oracle_state_left="external",
            oracle_state_right="external",
            contract_weight_state="matched",
            max_receive_skew_ms=100,
        )

        self.assertEqual(result.status, "exclude")
        self.assertIn("RECEIVE_SKEW_EXCEEDED", result.reason_codes)
        self.assertIn("SOURCE_TIME_NOT_COMPARABLE", result.reason_codes)

    def test_all_evidence_can_make_a_sample_eligible_without_calculating_profit(
        self,
    ) -> None:
        left = quote(WTI, response_received_ns=1_000_000_000)
        right = quote(CL, response_received_ns=1_050_000_000)
        result = classify_pair_sample(
            left,
            right,
            economic_status="same",
            oracle_state_left="external",
            oracle_state_right="external",
            contract_weight_state="matched",
            max_receive_skew_ms=100,
        )

        self.assertEqual(result.status, "eligible")
        self.assertEqual(result.reason_codes, ("SOURCE_TIME_NOT_COMPARABLE",))
        self.assertEqual(result.receive_skew_ms, 50.0)

    def test_attempt_reports_request_failure_without_dropping_other_observations(
        self,
    ) -> None:
        attempt = SnapshotAttempt(
            attempt_id="attempt-1",
            started_at=datetime(2026, 8, 18, tzinfo=timezone.utc),
            observations=(quote(WTI),),
            errors=((CL.selector, "REQUEST_FAILED"),),
        )

        payload = attempt.to_dict()
        self.assertEqual(len(payload["observations"]), 1)
        self.assertEqual(payload["errors"][0]["selector"], CL.selector)


if __name__ == "__main__":
    unittest.main()
