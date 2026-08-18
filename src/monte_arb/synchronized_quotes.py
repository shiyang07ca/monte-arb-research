from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Optional, Sequence, Tuple

from .market import MarketIdentity


@dataclass(frozen=True)
class QuoteObservation:
    identity: MarketIdentity
    request_started_ns: int
    response_received_ns: int
    source_time_ms: Optional[int]
    best_bid: str
    best_ask: str
    bid_size: str
    ask_size: str
    raw_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "request_started_ns": self.request_started_ns,
            "response_received_ns": self.response_received_ns,
            "source_time_ms": self.source_time_ms,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "raw_sha256": self.raw_sha256,
        }


@dataclass(frozen=True)
class SynchronizedSnapshot:
    attempt_id: str
    observations: Tuple[QuoteObservation, ...]
    capture_span_ms: float

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "capture_span_ms": self.capture_span_ms,
            "observations": [item.to_dict() for item in self.observations],
        }


@dataclass(frozen=True)
class PairSampleDecision:
    status: str
    reason_codes: Tuple[str, ...]
    receive_skew_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "receive_skew_ms": self.receive_skew_ms,
        }


@dataclass(frozen=True)
class SnapshotAttempt:
    attempt_id: str
    started_at: datetime
    observations: Tuple[QuoteObservation, ...]
    errors: Tuple[Tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "started_at": self.started_at.isoformat(),
            "observations": [item.to_dict() for item in self.observations],
            "errors": [
                {"selector": selector, "reason_code": reason_code}
                for selector, reason_code in self.errors
            ],
        }


def _positive_decimal(value: Any, field: str) -> str:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} is not numeric") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise ValueError(f"{field} must be positive")
    return str(value)


def _validate_observation(observation: QuoteObservation) -> None:
    bid = Decimal(_positive_decimal(observation.best_bid, "best_bid"))
    ask = Decimal(_positive_decimal(observation.best_ask, "best_ask"))
    _positive_decimal(observation.bid_size, "bid_size")
    _positive_decimal(observation.ask_size, "ask_size")
    if bid >= ask:
        raise ValueError(f"{observation.identity.selector}: crossed or locked book")
    if observation.request_started_ns > observation.response_received_ns:
        raise ValueError("request start is after response receive")
    if len(observation.raw_sha256) != 64:
        raise ValueError("raw_sha256 must be a SHA-256 hex digest")


def parse_lighter_book(
    identity: MarketIdentity,
    payload: Any,
    *,
    request_started_ns: int,
    response_received_ns: int,
    raw_sha256: str,
) -> QuoteObservation:
    if identity.venue != "lighter":
        raise ValueError("Lighter parser requires a Lighter identity")
    if not isinstance(payload, Mapping) or payload.get("code") != 200:
        raise ValueError("invalid Lighter order book response")
    bids = payload.get("bids")
    asks = payload.get("asks")
    if not isinstance(bids, list) or not bids or not isinstance(asks, list) or not asks:
        raise ValueError("Lighter order book must have two sides")
    bid = bids[0]
    ask = asks[0]
    if not isinstance(bid, Mapping) or not isinstance(ask, Mapping):
        raise ValueError("Lighter top level must be objects")
    observation = QuoteObservation(
        identity=identity,
        request_started_ns=request_started_ns,
        response_received_ns=response_received_ns,
        source_time_ms=None,
        best_bid=_positive_decimal(bid.get("price"), "bid.price"),
        best_ask=_positive_decimal(ask.get("price"), "ask.price"),
        bid_size=_positive_decimal(
            bid.get("remaining_base_amount"), "bid.remaining_base_amount"
        ),
        ask_size=_positive_decimal(
            ask.get("remaining_base_amount"), "ask.remaining_base_amount"
        ),
        raw_sha256=raw_sha256,
    )
    _validate_observation(observation)
    return observation


def parse_hyperliquid_book(
    identity: MarketIdentity,
    payload: Any,
    *,
    request_started_ns: int,
    response_received_ns: int,
    raw_sha256: str,
) -> QuoteObservation:
    if identity.venue != "hyperliquid":
        raise ValueError("Hyperliquid parser requires a Hyperliquid identity")
    if not isinstance(payload, Mapping) or payload.get("coin") != identity.symbol:
        raise ValueError("Hyperliquid response identity mismatch")
    levels = payload.get("levels")
    if not isinstance(levels, list) or len(levels) != 2:
        raise ValueError("Hyperliquid order book must have two sides")
    bids, asks = levels
    if not isinstance(bids, list) or not bids or not isinstance(asks, list) or not asks:
        raise ValueError("Hyperliquid order book must have two sides")
    bid = bids[0]
    ask = asks[0]
    if not isinstance(bid, Mapping) or not isinstance(ask, Mapping):
        raise ValueError("Hyperliquid top level must be objects")
    source_time = payload.get("time")
    if not isinstance(source_time, int):
        raise ValueError("Hyperliquid l2Book source time missing")
    observation = QuoteObservation(
        identity=identity,
        request_started_ns=request_started_ns,
        response_received_ns=response_received_ns,
        source_time_ms=source_time,
        best_bid=_positive_decimal(bid.get("px"), "bid.px"),
        best_ask=_positive_decimal(ask.get("px"), "ask.px"),
        bid_size=_positive_decimal(bid.get("sz"), "bid.sz"),
        ask_size=_positive_decimal(ask.get("sz"), "ask.sz"),
        raw_sha256=raw_sha256,
    )
    _validate_observation(observation)
    return observation


def build_snapshot(
    attempt_id: str, observations: Sequence[QuoteObservation]
) -> SynchronizedSnapshot:
    if not attempt_id or not observations:
        raise ValueError("snapshot requires an attempt id and observations")
    for observation in observations:
        _validate_observation(observation)
    if len({item.identity for item in observations}) != len(observations):
        raise ValueError("snapshot contains duplicate identities")
    capture_span_ms = (
        max(item.response_received_ns for item in observations)
        - min(item.request_started_ns for item in observations)
    ) / 1_000_000
    return SynchronizedSnapshot(attempt_id, tuple(observations), capture_span_ms)


def classify_pair_sample(
    left: QuoteObservation,
    right: QuoteObservation,
    *,
    economic_status: str,
    oracle_state_left: str,
    oracle_state_right: str,
    contract_weight_state: str,
    max_receive_skew_ms: float,
) -> PairSampleDecision:
    _validate_observation(left)
    _validate_observation(right)
    receive_skew_ms = (
        abs(left.response_received_ns - right.response_received_ns) / 1_000_000
    )
    reasons = []

    if economic_status != "same":
        reasons.append(
            "ECONOMIC_MAPPING_UNKNOWN"
            if economic_status == "unknown"
            else "ECONOMIC_MAPPING_DIFFERENT"
        )
    if oracle_state_left == "unknown" or oracle_state_right == "unknown":
        reasons.append("ORACLE_STATE_UNKNOWN")
    elif oracle_state_left != oracle_state_right:
        reasons.append("ORACLE_STATE_MISMATCH")
    if contract_weight_state == "unknown":
        reasons.append("CONTRACT_WEIGHT_UNKNOWN")
    elif contract_weight_state != "matched":
        reasons.append("CONTRACT_WEIGHT_MISMATCH")
    if receive_skew_ms > max_receive_skew_ms:
        reasons.append("RECEIVE_SKEW_EXCEEDED")
    if left.source_time_ms is None or right.source_time_ms is None:
        reasons.append("SOURCE_TIME_NOT_COMPARABLE")

    # Missing source-time comparability is retained as evidence but does not by itself
    # reject an otherwise bounded local-receive snapshot. One-sided source timestamps
    # cannot be subtracted from local monotonic clocks.
    blocking = [reason for reason in reasons if reason != "SOURCE_TIME_NOT_COMPARABLE"]
    return PairSampleDecision(
        "exclude" if blocking else "eligible",
        tuple(sorted(set(reasons))),
        receive_skew_ms,
    )
