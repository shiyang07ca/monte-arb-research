from __future__ import annotations

import json
import unittest
from pathlib import Path

from monte_arb.economic import (
    EconomicSpecification,
    ObservationState,
    assess_pair,
    classify_price_state,
    load_day13_specifications,
)
from monte_arb.market import MarketIdentity

FIXTURE = Path(__file__).parent / "fixtures" / "day13" / "economic-specifications.json"


class Day13EconomicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.specifications = load_day13_specifications(json.loads(FIXTURE.read_text()))
        self.by_symbol = {spec.identity.symbol: spec for spec in self.specifications}

    def test_wti_and_brent_are_not_paired_by_generic_oil_label(self) -> None:
        result = assess_pair(self.by_symbol["WTI"], self.by_symbol["xyz:BRENTOIL"])

        self.assertEqual(result.status, "not_comparable")
        self.assertIn("BENCHMARK_MISMATCH", result.reason_codes)

    def test_current_wti_pair_remains_unknown_when_contract_year_is_not_explicit(
        self,
    ) -> None:
        result = assess_pair(self.by_symbol["WTI"], self.by_symbol["xyz:CL"])

        self.assertEqual(result.status, "unknown")
        self.assertIn("CONTRACT_YEAR_UNKNOWN", result.reason_codes)
        self.assertNotIn("UNIT_MISMATCH", result.reason_codes)

    def test_same_unit_does_not_override_different_benchmark(self) -> None:
        left = EconomicSpecification(
            MarketIdentity("a", "perp", "default", "OIL-A", "1"),
            asset_class="commodity",
            benchmark="WTI_LIGHT_SWEET_CRUDE",
            unit="barrel",
            quote_currency="USD",
            settlement_currency="USDC",
            contract_month_code="U",
            contract_year="2026",
            external_session="23x5",
            pricing_rule="futures_roll",
            evidence=("source-a",),
        )
        right = EconomicSpecification(
            MarketIdentity("b", "perp", "default", "OIL-B", "2"),
            asset_class="commodity",
            benchmark="BRENT_CRUDE",
            unit="barrel",
            quote_currency="USD",
            settlement_currency="USDC",
            contract_month_code="U",
            contract_year="2026",
            external_session="23x5",
            pricing_rule="futures_roll",
            evidence=("source-b",),
        )

        result = assess_pair(left, right)
        self.assertEqual(result.status, "not_comparable")
        self.assertIn("BENCHMARK_MISMATCH", result.reason_codes)

    def test_price_state_requires_source_evidence_not_wall_clock_guess(self) -> None:
        state = classify_price_state(
            ObservationState(
                external_market_open=False,
                external_price_available=None,
                oracle_fresh=None,
                in_roll_transition=False,
            )
        )

        self.assertEqual(state.status, "unknown")
        self.assertEqual(state.reason_codes, ("PRICE_SOURCE_EVIDENCE_MISSING",))

    def test_price_states_distinguish_external_internal_and_roll(self) -> None:
        external = classify_price_state(ObservationState(True, True, True, False))
        internal = classify_price_state(ObservationState(False, False, False, False))
        roll = classify_price_state(ObservationState(True, True, True, True))

        self.assertEqual(external.status, "external")
        self.assertEqual(internal.status, "internal")
        self.assertEqual(roll.status, "roll_transition")

    def test_pair_is_comparable_only_after_all_required_fields_are_known(self) -> None:
        left = self.by_symbol["WTI"]
        right = self.by_symbol["xyz:CL"]
        right_with_year = EconomicSpecification(
            identity=right.identity,
            asset_class=right.asset_class,
            benchmark=right.benchmark,
            unit=right.unit,
            quote_currency=right.quote_currency,
            settlement_currency=right.settlement_currency,
            contract_month_code=right.contract_month_code,
            contract_year="2026",
            external_session=right.external_session,
            pricing_rule=right.pricing_rule,
            evidence=right.evidence,
        )

        result = assess_pair(left, right_with_year)

        self.assertEqual(result.status, "comparable_definition")
        self.assertEqual(result.reason_codes, ())


if __name__ == "__main__":
    unittest.main()
