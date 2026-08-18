from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple

from .market import MarketIdentity


@dataclass(frozen=True)
class EconomicSpecification:
    """A sourced economic definition; unknown fields stay None."""

    identity: MarketIdentity
    asset_class: Optional[str]
    benchmark: Optional[str]
    unit: Optional[str]
    quote_currency: Optional[str]
    settlement_currency: Optional[str]
    contract_month_code: Optional[str]
    contract_year: Optional[str]
    contract_reference_status: Optional[str]
    external_session: Optional[str]
    pricing_rule: Optional[str]
    evidence: Tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "asset_class": self.asset_class,
            "benchmark": self.benchmark,
            "unit": self.unit,
            "quote_currency": self.quote_currency,
            "settlement_currency": self.settlement_currency,
            "contract_month_code": self.contract_month_code,
            "contract_year": self.contract_year,
            "contract_reference_status": self.contract_reference_status,
            "external_session": self.external_session,
            "pricing_rule": self.pricing_rule,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class PairAssessment:
    status: str
    reason_codes: Tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "reason_codes": list(self.reason_codes)}


@dataclass(frozen=True)
class ObservationState:
    external_market_open: Optional[bool]
    external_price_available: Optional[bool]
    oracle_fresh: Optional[bool]
    in_roll_transition: Optional[bool]


@dataclass(frozen=True)
class PriceState:
    status: str
    reason_codes: Tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "reason_codes": list(self.reason_codes)}


_REQUIRED_FIELDS = (
    ("asset_class", "ASSET_CLASS_UNKNOWN", "ASSET_CLASS_MISMATCH"),
    ("benchmark", "BENCHMARK_UNKNOWN", "BENCHMARK_MISMATCH"),
    ("unit", "UNIT_UNKNOWN", "UNIT_MISMATCH"),
    ("quote_currency", "QUOTE_CURRENCY_UNKNOWN", "QUOTE_CURRENCY_MISMATCH"),
    (
        "settlement_currency",
        "SETTLEMENT_CURRENCY_UNKNOWN",
        "SETTLEMENT_CURRENCY_MISMATCH",
    ),
    ("contract_month_code", "CONTRACT_MONTH_UNKNOWN", "CONTRACT_MONTH_MISMATCH"),
    ("contract_year", "CONTRACT_YEAR_UNKNOWN", "CONTRACT_YEAR_MISMATCH"),
    (
        "contract_reference_status",
        "CONTRACT_REFERENCE_STATUS_UNKNOWN",
        "CONTRACT_REFERENCE_STATUS_MISMATCH",
    ),
)


def assess_pair(
    left: EconomicSpecification, right: EconomicSpecification
) -> PairAssessment:
    """Fail closed when a required economic field differs or lacks evidence."""
    mismatches = []
    unknowns = []
    for field, unknown_code, mismatch_code in _REQUIRED_FIELDS:
        left_value = getattr(left, field)
        right_value = getattr(right, field)
        if left_value is None or right_value is None:
            unknowns.append(unknown_code)
        elif left_value != right_value:
            mismatches.append(mismatch_code)

    if mismatches:
        return PairAssessment("not_comparable", tuple(sorted(set(mismatches))))
    if unknowns:
        return PairAssessment("unknown", tuple(sorted(set(unknowns))))
    return PairAssessment("comparable_definition", ())


def classify_price_state(observation: ObservationState) -> PriceState:
    """Classify source state from explicit evidence, never from wall clock alone."""
    if observation.in_roll_transition is None:
        return PriceState("unknown", ("ROLL_STATE_UNKNOWN",))
    if observation.in_roll_transition:
        return PriceState("roll_transition", ("ROLL_TRANSITION",))

    source_values = (
        observation.external_market_open,
        observation.external_price_available,
        observation.oracle_fresh,
    )
    if any(value is None for value in source_values):
        return PriceState("unknown", ("PRICE_SOURCE_EVIDENCE_MISSING",))
    if observation.external_price_available and observation.oracle_fresh:
        return PriceState("external", ())
    if not observation.external_price_available and not observation.oracle_fresh:
        return PriceState("internal", ("EXTERNAL_PRICE_UNAVAILABLE",))
    return PriceState("transition", ("PRICE_SOURCE_TRANSITION",))


def _optional_text(row: Mapping[str, Any], key: str) -> Optional[str]:
    value = row.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string or null")
    return value


def load_day13_specifications(payload: Any) -> Tuple[EconomicSpecification, ...]:
    if not isinstance(payload, Mapping):
        raise ValueError("economic specifications must be an object")
    rows = payload.get("records")
    if not isinstance(rows, list):
        raise ValueError("economic specification records must be a list")

    result = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("economic specification record must be an object")
        identity = row.get("identity")
        evidence = row.get("evidence")
        if (
            not isinstance(identity, list)
            or len(identity) != 5
            or not all(isinstance(item, str) and item for item in identity)
        ):
            raise ValueError("identity must contain five non-empty strings")
        if not isinstance(evidence, list) or not all(
            isinstance(item, str) and item for item in evidence
        ):
            raise ValueError("evidence must be a list of source URLs")
        result.append(
            EconomicSpecification(
                identity=MarketIdentity(*identity),
                asset_class=_optional_text(row, "asset_class"),
                benchmark=_optional_text(row, "benchmark"),
                unit=_optional_text(row, "unit"),
                quote_currency=_optional_text(row, "quote_currency"),
                settlement_currency=_optional_text(row, "settlement_currency"),
                contract_month_code=_optional_text(row, "contract_month_code"),
                contract_year=_optional_text(row, "contract_year"),
                contract_reference_status=_optional_text(
                    row, "contract_reference_status"
                ),
                external_session=_optional_text(row, "external_session"),
                pricing_rule=_optional_text(row, "pricing_rule"),
                evidence=tuple(evidence),
            )
        )
    return tuple(result)


def build_day13_report(
    specifications: Sequence[EconomicSpecification],
) -> dict[str, Any]:
    by_symbol = {spec.identity.symbol: spec for spec in specifications}
    pairs = (
        ("WTI", "xyz:CL"),
        ("BRENTOIL", "xyz:BRENTOIL"),
        ("WTI", "xyz:BRENTOIL"),
    )
    return {
        "schema": "day13-economic-map-v1",
        "markets": [spec.to_dict() for spec in specifications],
        "pair_assessments": [
            {
                "left": left,
                "right": right,
                **assess_pair(by_symbol[left], by_symbol[right]).to_dict(),
            }
            for left, right in pairs
        ],
        "price_state_boundary": {
            "status": "unknown",
            "reason_codes": ["OBSERVATION_STATE_NOT_CAPTURED"],
            "explanation": (
                "Static specifications define possible states but do not prove the live "
                "external/internal/roll state at a quote timestamp."
            ),
        },
    }
