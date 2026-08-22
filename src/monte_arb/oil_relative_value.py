"""Brent–WTI relative-value dataset, diagnostics, and read-only collector.

Public seam:
- ``collect_oil_dataset`` gathers public Lighter/Hyperliquid/Yahoo data and
  optionally imports Variational market observations from monte-fox recordings.
- ``build_oil_projection`` converts source-specific observations into the stable
  research projection consumed by HTTP and CSV clients.

The module never sends orders and never reads Variational account/order events.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import statistics
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .adapters import (
    HYPERLIQUID_INFO_URL,
    LIGHTER_BASE_URL,
    PublicJsonClient,
    fetch_hyperliquid_book,
    fetch_hyperliquid_catalog,
    fetch_lighter_book,
    fetch_lighter_catalog,
)
from .execution_engine import (
    L2Book,
    MarketSpec,
    fetch_lighter_details,
    l2book_from_raw,
    leg_execution,
)
from .market import CatalogMarket

SCHEMA = "oil-relative-value-v1"
DATASET_SCHEMA = "oil-relative-value-dataset-v1"
DEFAULT_SIZES = (Decimal("100"), Decimal("500"), Decimal("1000"))
LIGHTER_MARKETS = {"WTI": 145, "BRENTOIL": 159}
HL_SYMBOLS = {"WTI": "xyz:CL", "BRENTOIL": "xyz:BRENTOIL"}
YAHOO_SYMBOLS = {"WTI": "CL=F", "BRENTOIL": "BZ=F"}


@dataclass(frozen=True)
class PricePoint:
    timestamp_ms: int
    wti: float
    brent: float
    wti_volume: Optional[float] = None
    brent_volume: Optional[float] = None
    roll_window: Optional[bool] = None
    source_skew_ms: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_ms": self.timestamp_ms,
            "timestamp_utc": _iso_ms(self.timestamp_ms),
            "wti": self.wti,
            "brent": self.brent,
            "wti_volume": self.wti_volume,
            "brent_volume": self.brent_volume,
            "roll_window": self.roll_window,
            "source_skew_ms": self.source_skew_ms,
        }


@dataclass(frozen=True)
class PriceSeries:
    key: str
    label: str
    venue: str
    price_kind: str
    interval: str
    points: tuple[PricePoint, ...]
    status: str
    reason: Optional[str]
    source_urls: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "venue": self.venue,
            "price_kind": self.price_kind,
            "interval": self.interval,
            "status": self.status,
            "reason": self.reason,
            "source_urls": list(self.source_urls),
            "points": [point.to_dict() for point in self.points],
        }


@dataclass(frozen=True)
class OilDataset:
    generated_at: str
    sources: tuple[PriceSeries, ...]
    execution: Mapping[str, Any]
    diagnostics: tuple[Mapping[str, Any], ...]
    raw_manifest: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": DATASET_SCHEMA,
            "generated_at": self.generated_at,
            "read_only": True,
            "execution_client_present": False,
            "sources": [source.to_dict() for source in self.sources],
            "execution": dict(self.execution),
            "diagnostics": [dict(item) for item in self.diagnostics],
            "raw_manifest": dict(self.raw_manifest),
        }


@dataclass(frozen=True)
class FrozenModel:
    alpha: float
    beta: float
    center: float
    scale: float
    formation_count: int
    validation_count: int
    formation_start_ms: int
    formation_end_ms: int
    formation_data_sha256: str
    model_origin: str = "fitted"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "log_linear_residual",
            "equation": "ln(brent) = alpha + beta * ln(wti) + residual",
            "alpha": self.alpha,
            "beta": self.beta,
            "center": self.center,
            "scale": self.scale,
            "formation_count": self.formation_count,
            "validation_count": self.validation_count,
            "formation_start_ms": self.formation_start_ms,
            "formation_end_ms": self.formation_end_ms,
            "formation_start_utc": _iso_ms(self.formation_start_ms),
            "formation_end_utc": _iso_ms(self.formation_end_ms),
            "formation_data_sha256": self.formation_data_sha256,
            "model_origin": self.model_origin,
            "frozen": True,
        }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _iso_ms(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, UTC).isoformat().replace(
        "+00:00", "Z"
    )


def _parse_time_ms(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        raw = float(value)
        return int(raw if raw > 10_000_000_000 else raw * 1000)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return int(parsed.timestamp() * 1000)


def _positive_float(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 0 else None


def align_legs(
    wti_rows: Sequence[Mapping[str, Any]],
    brent_rows: Sequence[Mapping[str, Any]],
    *,
    timestamp_field: str,
    price_field: str,
    volume_field: Optional[str] = None,
) -> tuple[PricePoint, ...]:
    """Pair only rows with the exact same timestamp; never fill a missing leg."""

    def rows_by_time(rows: Sequence[Mapping[str, Any]]) -> dict[int, Mapping[str, Any]]:
        result: dict[int, Mapping[str, Any]] = {}
        for row in rows:
            timestamp = _parse_time_ms(row.get(timestamp_field))
            price = _positive_float(row.get(price_field))
            if timestamp is not None and price is not None:
                result[timestamp] = row
        return result

    wti_by_time = rows_by_time(wti_rows)
    brent_by_time = rows_by_time(brent_rows)
    points: list[PricePoint] = []
    for timestamp in sorted(set(wti_by_time) & set(brent_by_time)):
        wti_row = wti_by_time[timestamp]
        brent_row = brent_by_time[timestamp]
        wti = _positive_float(wti_row.get(price_field))
        brent = _positive_float(brent_row.get(price_field))
        if wti is None or brent is None:
            continue
        points.append(
            PricePoint(
                timestamp_ms=timestamp,
                wti=wti,
                brent=brent,
                wti_volume=(
                    _positive_float(wti_row.get(volume_field)) if volume_field else None
                ),
                brent_volume=(
                    _positive_float(brent_row.get(volume_field)) if volume_field else None
                ),
            )
        )
    return tuple(points)


def _formation_data_sha256(points: Sequence[PricePoint]) -> str:
    canonical = [
        {
            "timestamp_ms": point.timestamp_ms,
            "wti": format(point.wti, ".17g"),
            "brent": format(point.brent, ".17g"),
        }
        for point in points
    ]
    payload = json.dumps(
        canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _fit_frozen_model(
    points: Sequence[PricePoint], formation_fraction: float
) -> tuple[Optional[FrozenModel], list[dict[str, Any]]]:
    if not 0 < formation_fraction < 1:
        raise ValueError("formation_fraction must be in (0, 1)")
    if len(points) < 3:
        return None, [_metric_point(point, None) for point in points]
    formation_count = max(2, min(len(points) - 1, int(len(points) * formation_fraction)))
    formation = points[:formation_count]
    x = [math.log(point.wti) for point in formation]
    y = [math.log(point.brent) for point in formation]
    mean_x = statistics.fmean(x)
    mean_y = statistics.fmean(y)
    variance_x = sum((value - mean_x) ** 2 for value in x)
    beta = (
        sum((left - mean_x) * (right - mean_y) for left, right in zip(x, y))
        / variance_x
        if variance_x > 0
        else 0.0
    )
    alpha = mean_y - beta * mean_x
    residuals = [
        math.log(point.brent) - alpha - beta * math.log(point.wti)
        for point in formation
    ]
    center = statistics.median(residuals)
    mad = statistics.median(abs(value - center) for value in residuals)
    scale = 1.4826 * mad
    if not math.isfinite(scale) or scale <= 0:
        population_scale = statistics.pstdev(residuals)
        scale = population_scale if population_scale > 0 else 0.0
    model = FrozenModel(
        alpha=alpha,
        beta=beta,
        center=center,
        scale=scale,
        formation_count=formation_count,
        validation_count=len(points) - formation_count,
        formation_start_ms=formation[0].timestamp_ms,
        formation_end_ms=formation[-1].timestamp_ms,
        formation_data_sha256=_formation_data_sha256(formation),
    )
    metrics = [_metric_point(point, model) for point in points]
    return model, metrics


def _model_from_dict(
    payload: Mapping[str, Any], points: Sequence[PricePoint]
) -> Optional[FrozenModel]:
    try:
        alpha = float(payload["alpha"])
        beta = float(payload["beta"])
        center = float(payload["center"])
        scale = float(payload["scale"])
        formation_start_ms = int(payload["formation_start_ms"])
        formation_end_ms = int(payload["formation_end_ms"])
        formation_count = int(payload["formation_count"])
        formation_data_sha256 = str(payload["formation_data_sha256"])
    except (KeyError, TypeError, ValueError):
        return None
    if not all(math.isfinite(value) for value in (alpha, beta, center, scale)):
        return None
    current_formation = [
        point
        for point in points
        if formation_start_ms <= point.timestamp_ms <= formation_end_ms
    ]
    has_complete_formation = (
        bool(points)
        and points[0].timestamp_ms <= formation_start_ms
        and points[-1].timestamp_ms >= formation_end_ms
        and len(current_formation) == formation_count
    )
    if has_complete_formation and _formation_data_sha256(current_formation) != formation_data_sha256:
        return None
    validation_count = sum(point.timestamp_ms > formation_end_ms for point in points)
    if validation_count <= 0:
        return None
    return FrozenModel(
        alpha=alpha,
        beta=beta,
        center=center,
        scale=scale,
        formation_count=formation_count,
        validation_count=validation_count,
        formation_start_ms=formation_start_ms,
        formation_end_ms=formation_end_ms,
        formation_data_sha256=formation_data_sha256,
        model_origin="reused",
    )


def _metrics_for_model(
    points: Sequence[PricePoint], model: Optional[FrozenModel]
) -> list[dict[str, Any]]:
    return [_metric_point(point, model) for point in points]


def _metric_point(point: PricePoint, model: Optional[FrozenModel]) -> dict[str, Any]:
    log_ratio = math.log(point.brent) - math.log(point.wti)
    residual = None
    residual_z = None
    if model is not None:
        residual = math.log(point.brent) - model.alpha - model.beta * math.log(point.wti)
        residual_z = (
            (residual - model.center) / model.scale if model.scale > 0 else None
        )
    return {
        **point.to_dict(),
        "spread_usd": point.brent - point.wti,
        "ratio": point.brent / point.wti,
        "log_ratio": log_ratio,
        "residual": residual,
        "residual_z": residual_z,
    }


def _leg_contribution(
    points: Sequence[PricePoint], *, lookback_hours: int = 24
) -> Optional[dict[str, Any]]:
    if len(points) < 2:
        return None
    end = points[-1]
    cutoff_ms = end.timestamp_ms - lookback_hours * 3_600_000
    eligible = [point for point in points[:-1] if point.timestamp_ms >= cutoff_ms]
    if eligible:
        start = eligible[0]
    else:
        start = min(points[:-1], key=lambda point: abs(point.timestamp_ms - cutoff_ms))
    lookback_points = points.index(end) - points.index(start)
    elapsed_ms = end.timestamp_ms - start.timestamp_ms
    wti_change = (math.log(end.wti) - math.log(start.wti)) * 10_000
    brent_change = (math.log(end.brent) - math.log(start.brent)) * 10_000
    relative_change = brent_change - wti_change
    if abs(brent_change) > abs(wti_change) * 1.2:
        dominant = "brent"
    elif abs(wti_change) > abs(brent_change) * 1.2:
        dominant = "wti"
    else:
        dominant = "both"
    return {
        "lookback_hours": lookback_hours,
        "lookback_points": lookback_points,
        "elapsed_ms": elapsed_ms,
        "wti_log_change_bps": wti_change,
        "brent_log_change_bps": brent_change,
        "relative_change_bps": relative_change,
        "dominant_leg": dominant,
    }


def _source_health(source: PriceSeries) -> dict[str, Any]:
    timestamps = [point.timestamp_ms for point in source.points]
    expected_step = None
    gap_count: Optional[int] = 0
    max_gap_ms = None
    gap_evaluation = "fixed_interval"
    if len(timestamps) > 1:
        diffs = [later - earlier for earlier, later in zip(timestamps, timestamps[1:])]
        expected_step = int(statistics.median(diffs))
        max_gap_ms = max(diffs)
        if source.interval == "1d":
            # Daily exchange sessions require an explicit holiday/roll calendar.
            # Weekend and holiday closures must not be labelled feed failures.
            gap_count = None
            gap_evaluation = "requires_exchange_calendar"
        else:
            gap_count = sum(diff > expected_step * 1.5 for diff in diffs)
    return {
        "status": source.status,
        "reason": source.reason,
        "sample_count": len(timestamps),
        "first_at": _iso_ms(timestamps[0]) if timestamps else None,
        "last_at": _iso_ms(timestamps[-1]) if timestamps else None,
        "expected_step_ms": expected_step,
        "gap_count": gap_count,
        "gap_evaluation": gap_evaluation,
        "max_gap_ms": max_gap_ms,
    }


def _validation_evidence(
    model: Optional[FrozenModel], points: Sequence[Mapping[str, Any]]
) -> Optional[dict[str, Any]]:
    """Summarize the chronological validation slice without refitting it."""
    if model is None or model.validation_count <= 0:
        return None
    validation = [
        point
        for point in points
        if isinstance(point.get("timestamp_ms"), (int, float))
        and float(point["timestamp_ms"]) > model.formation_end_ms
    ]
    z_values = [
        float(point["residual_z"])
        for point in validation
        if isinstance(point.get("residual_z"), (int, float))
        and math.isfinite(float(point["residual_z"]))
    ]
    residuals = [
        float(point["residual"])
        for point in validation
        if isinstance(point.get("residual"), (int, float))
        and math.isfinite(float(point["residual"]))
    ]
    if not z_values:
        return None
    return {
        "sample_count": len(z_values),
        "median_residual": statistics.median(residuals) if residuals else None,
        "median_residual_z": statistics.median(z_values),
        "mean_abs_residual_z": statistics.fmean(abs(value) for value in z_values),
        "outside_two_sigma_fraction": sum(abs(value) >= 2 for value in z_values)
        / len(z_values),
        "purpose": "out_of_sample_descriptive_check",
    }


def build_oil_projection(
    dataset: OilDataset,
    *,
    formation_fraction: float = 0.7,
    frozen_models: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    sources = []
    source_by_key: dict[str, dict[str, Any]] = {}
    for source in dataset.sources:
        model = None
        points: list[dict[str, Any]]
        frozen_payload = frozen_models.get(source.key) if frozen_models else None
        if isinstance(frozen_payload, Mapping):
            model = _model_from_dict(frozen_payload, source.points)
        if model is not None:
            points = _metrics_for_model(source.points, model)
        else:
            model, points = _fit_frozen_model(source.points, formation_fraction)
        summary = points[-1] if points else None
        item = {
            "key": source.key,
            "label": source.label,
            "venue": source.venue,
            "price_kind": source.price_kind,
            "interval": source.interval,
            "status": source.status,
            "reason": source.reason,
            "source_urls": list(source.source_urls),
            "sample_count": len(source.points),
            "health": _source_health(source),
            "summary": summary,
            "model": model.to_dict() if model else None,
            "model_reused": model.model_origin == "reused" if model else False,
            "validation": _validation_evidence(model, points),
            "leg_contribution": _leg_contribution(source.points),
            "points": points,
        }
        sources.append(item)
        source_by_key[source.key] = item

    diagnostics = [dict(item) for item in dataset.diagnostics]
    diagnostics.extend(_automatic_diagnostics(source_by_key, dataset.execution))
    dashboard_source = next(
        (source for source in sources if source["key"] == "lighter" and source["summary"]),
        next((source for source in sources if source["summary"]), None),
    )
    return {
        "schema": SCHEMA,
        "generated_at": dataset.generated_at,
        "read_only": True,
        "execution_client_present": False,
        "dashboard": {
            "primary_module": "oil_relative_value",
            "primary_source": dashboard_source["key"] if dashboard_source else None,
            "summary": dashboard_source["summary"] if dashboard_source else None,
            "source_count": len(sources),
            "healthy_source_count": sum(source["status"] == "ok" for source in sources),
        },
        "sources": sources,
        "execution": dict(dataset.execution),
        "diagnostics": diagnostics,
        "provenance": dict(dataset.raw_manifest),
        "boundaries": [
            "Brent and WTI are different benchmarks; their spread is not risk-free arbitrage PnL.",
            "Each price source keeps its own meaning. Candle close, index, RFQ and L2 are not interchangeable.",
            "The frozen model is descriptive. Mean reversion and future profitability require replay evidence.",
            "Frozen-book execution is a friction baseline, not a future exit forecast.",
        ],
        "downloads": {
            "json": "/workbench/api/oil",
            "csv_template": "/workbench/api/oil.csv?source={source_key}",
        },
    }


def _hour_profile_evidence(source: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    points = source.get("points")
    if not isinstance(points, list) or len(points) < 48 or source.get("interval") == "1d":
        return None
    by_hour: dict[int, list[float]] = {}
    for point in points:
        if not isinstance(point, Mapping):
            continue
        timestamp = point.get("timestamp_ms")
        residual_z = point.get("residual_z")
        if not isinstance(timestamp, (int, float)) or not isinstance(
            residual_z, (int, float)
        ):
            continue
        hour = datetime.fromtimestamp(float(timestamp) / 1000, UTC).hour
        by_hour.setdefault(hour, []).append(float(residual_z))
    eligible = {
        hour: values for hour, values in by_hour.items() if len(values) >= 2
    }
    if not eligible:
        return None
    medians = {hour: statistics.median(values) for hour, values in eligible.items()}
    highest_hour = max(medians, key=lambda hour: abs(medians[hour]))
    return {
        "hour_count": len(eligible),
        "most_distinct_utc_hour": highest_hour,
        "median_residual_z": medians[highest_hour],
        "sample_count": len(eligible[highest_hour]),
    }


def _automatic_diagnostics(
    sources: Mapping[str, Mapping[str, Any]], execution: Mapping[str, Any]
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    roll_evidence_present = False
    for key, source in sources.items():
        points = source.get("points")
        if isinstance(points, list) and any(
            isinstance(point, Mapping) and point.get("roll_window") is True
            for point in points
        ):
            roll_evidence_present = True
        summary = source.get("summary")
        if not isinstance(summary, Mapping):
            continue
        residual_z = summary.get("residual_z")
        if isinstance(residual_z, (int, float)) and math.isfinite(float(residual_z)):
            diagnostics.append(
                {
                    "code": "CURRENT_RESIDUAL_POSITION",
                    "severity": "watch" if abs(float(residual_z)) >= 2 else "info",
                    "title": f"{source['label']} 当前参考残差",
                    "evidence": [f"frozen residual z={float(residual_z):+.2f}"],
                    "counter_evidence": [
                        "a residual extreme can be structural around session, roll, or source changes"
                    ],
                    "limitations": ["descriptive model; no causal or profitability claim"],
                    "next_check": "compare the same window across venues and executable quotes",
                }
            )
        validation = source.get("validation")
        if isinstance(validation, Mapping):
            median_z = validation.get("median_residual_z")
            outside = validation.get("outside_two_sigma_fraction")
            if (
                isinstance(median_z, (int, float))
                and isinstance(outside, (int, float))
                and (abs(float(median_z)) >= 2 or float(outside) >= 0.5)
            ):
                diagnostics.append(
                    {
                        "code": "VALIDATION_DISTRIBUTION_SHIFT",
                        "severity": "watch",
                        "title": f"{source['label']} 验证窗口偏离形成分布",
                        "evidence": [
                            f"validation median z={float(median_z):+.2f}",
                            f"outside |z|>=2 fraction={float(outside):.1%}",
                        ],
                        "counter_evidence": [
                            "a shifted residual can be a new regime rather than temporary mispricing"
                        ],
                        "limitations": [
                            "chronological holdout is descriptive, not a trading backtest"
                        ],
                        "next_check": "segment by session/roll and replay convergence without refitting",
                    }
                )
        contribution = source.get("leg_contribution")
        if isinstance(contribution, Mapping):
            diagnostics.append(
                {
                    "code": "LEG_CONTRIBUTION_24_HOUR",
                    "severity": "info",
                    "title": f"{source['label']} 最近变化由哪条腿推动",
                    "evidence": [
                        f"dominant leg={contribution.get('dominant_leg')}",
                        f"WTI={float(contribution.get('wti_log_change_bps', 0)):+.1f} bps; "
                        f"Brent={float(contribution.get('brent_log_change_bps', 0)):+.1f} bps",
                    ],
                    "counter_evidence": [
                        "leg contribution describes movement, not causal news or flow"
                    ],
                    "limitations": [
                        f"lookback spans {contribution.get('elapsed_ms', 0) / 3_600_000:.1f} hours "
                        f"across {contribution.get('lookback_points')} synchronized intervals"
                    ],
                    "next_check": "compare volume, funding, and session state around the move",
                }
            )
        hour_profile = _hour_profile_evidence(source)
        if hour_profile is not None:
            diagnostics.append(
                {
                    "code": "UTC_HOUR_PROFILE",
                    "severity": "info",
                    "title": f"{source['label']} UTC 时段分布",
                    "evidence": [
                        f"most distinct hour={hour_profile['most_distinct_utc_hour']:02d}:00 UTC",
                        f"median residual z={hour_profile['median_residual_z']:+.2f} "
                        f"over n={hour_profile['sample_count']}",
                    ],
                    "counter_evidence": [
                        "UTC hour is only a session proxy and does not identify underlying market state"
                    ],
                    "limitations": [
                        "holiday, DST, and venue-specific sessions are not yet mapped"
                    ],
                    "next_check": "join an explicit exchange session and holiday calendar",
                }
            )
    lighter = sources.get("lighter", {}).get("summary")
    hyperliquid = sources.get("hyperliquid", {}).get("summary")
    if isinstance(lighter, Mapping) and isinstance(hyperliquid, Mapping):
        left = lighter.get("log_ratio")
        right = hyperliquid.get("log_ratio")
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            delta_bps = (float(left) - float(right)) * 10_000
            diagnostics.append(
                {
                    "code": "VENUE_LOG_RATIO_DIVERGENCE",
                    "severity": "watch" if abs(delta_bps) >= 10 else "info",
                    "title": "Lighter 与 Hyperliquid 的 CL/BZ 关系",
                    "evidence": [f"latest log-ratio difference={delta_bps:+.2f} bps"],
                    "counter_evidence": [
                        "latest candles may have different market microstructure and close semantics"
                    ],
                    "limitations": ["not executable unless current books/RFQs are checked"],
                    "next_check": "compare source timestamps and target-size entry intervals",
                }
            )
    limitations = execution.get("limitations") if isinstance(execution, Mapping) else None
    if not roll_evidence_present:
        diagnostics.append(
            {
                "code": "ROLL_EVIDENCE_UNAVAILABLE",
                "severity": "blocked",
                "title": "展期机制证据尚未接入",
                "evidence": ["no synchronized point carries a verified roll-window label"],
                "counter_evidence": [],
                "limitations": [
                    "continuous futures and venue perps can use different contract/roll semantics"
                ],
                "next_check": "join verified CL/BZ contract months, weights, and roll calendar",
            }
        )
    if isinstance(limitations, Sequence) and "HOLDING_FUNDING_UNKNOWN" in limitations:
        diagnostics.append(
            {
                "code": "FUNDING_EVIDENCE_UNAVAILABLE",
                "severity": "blocked",
                "title": "持有期 Funding 证据尚未接入",
                "evidence": ["execution limitations include HOLDING_FUNDING_UNKNOWN"],
                "counter_evidence": [],
                "limitations": ["current residual and book friction exclude holding cash flows"],
                "next_check": "collect venue-native funding intervals and realized historical cash flow",
            }
        )
    health_evidence = []
    for source in sources.values():
        health = source.get("health")
        if not isinstance(health, Mapping):
            continue
        health_evidence.append(
            f"{source.get('key')}: status={health.get('status')}, "
            f"samples={health.get('sample_count')}, gaps={health.get('gap_count')}"
        )
    diagnostics.append(
        {
            "code": "DATA_HEALTH_SUMMARY",
            "severity": "info",
            "title": "价格源覆盖与缺口",
            "evidence": health_evidence,
            "counter_evidence": [
                "HTTP success and sample count do not prove economic identity or freshness"
            ],
            "limitations": [
                "daily gap evaluation requires an exchange calendar"
            ],
            "next_check": "add calendar-aware freshness and last-good-dataset retention",
        }
    )
    if limitations:
        diagnostics.append(
            {
                "code": "EXECUTION_EVIDENCE_INCOMPLETE",
                "severity": "blocked",
                "title": "执行现金结果仍不完整",
                "evidence": [str(item) for item in limitations],
                "counter_evidence": [],
                "limitations": ["unknown inputs are never treated as zero"],
                "next_check": "verify account fees, holding funding, and future exit state",
            }
        )
    return diagnostics


def export_source_csv(projection: Mapping[str, Any], source_key: str) -> str:
    sources = projection.get("sources")
    if not isinstance(sources, list):
        raise KeyError(source_key)
    source = next(
        (item for item in sources if isinstance(item, Mapping) and item.get("key") == source_key),
        None,
    )
    if source is None:
        raise KeyError(source_key)
    points = source.get("points")
    if not isinstance(points, list):
        points = []
    fields = [
        "timestamp_ms",
        "timestamp_utc",
        "wti",
        "brent",
        "spread_usd",
        "ratio",
        "log_ratio",
        "residual",
        "residual_z",
        "wti_volume",
        "brent_volume",
        "roll_window",
        "source_skew_ms",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for point in points:
        writer.writerow({field: point.get(field) for field in fields})
    return output.getvalue()


def load_variational_recordings(runtime_directory: Path) -> tuple[PriceSeries, ...]:
    rfq_points: list[PricePoint] = []
    index_points: list[PricePoint] = []
    for path in sorted(runtime_directory.glob("runtime-*.jsonl")):
        try:
            stream = path.open("r", encoding="utf-8")
        except OSError:
            continue
        with stream:
            for line in stream:
                if not re.search(r'"event_type"\s*:\s*"market_observation"', line):
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, Mapping) or event.get("event_type") != "market_observation":
                    continue
                payload = event.get("payload")
                if not isinstance(payload, Mapping):
                    continue
                quotes = payload.get("quotes")
                if not isinstance(quotes, Mapping):
                    continue
                bz = quotes.get("BZ")
                cl = quotes.get("CL")
                if not isinstance(bz, Mapping) or not isinstance(cl, Mapping):
                    continue
                observed_ms = _parse_time_ms(
                    payload.get("observed_at", event.get("recorded_at_utc"))
                )
                if observed_ms is None:
                    continue
                bz_bid = _positive_float(bz.get("bid"))
                bz_ask = _positive_float(bz.get("ask"))
                cl_bid = _positive_float(cl.get("bid"))
                cl_ask = _positive_float(cl.get("ask"))
                bz_source = _parse_time_ms(bz.get("source_at"))
                cl_source = _parse_time_ms(cl.get("source_at"))
                source_skew = (
                    float(abs(bz_source - cl_source))
                    if bz_source is not None and cl_source is not None
                    else None
                )
                roll_value = payload.get("roll_window")
                roll_window = roll_value if isinstance(roll_value, bool) else None
                if all(value is not None for value in (bz_bid, bz_ask, cl_bid, cl_ask)):
                    assert bz_bid is not None and bz_ask is not None
                    assert cl_bid is not None and cl_ask is not None
                    if bz_bid <= bz_ask and cl_bid <= cl_ask:
                        rfq_points.append(
                            PricePoint(
                                timestamp_ms=observed_ms,
                                wti=(cl_bid + cl_ask) / 2,
                                brent=(bz_bid + bz_ask) / 2,
                                roll_window=roll_window,
                                source_skew_ms=source_skew,
                            )
                        )
                bz_index = _positive_float(bz.get("index_price"))
                cl_index = _positive_float(cl.get("index_price"))
                if bz_index is not None and cl_index is not None:
                    index_points.append(
                        PricePoint(
                            timestamp_ms=observed_ms,
                            wti=cl_index,
                            brent=bz_index,
                            roll_window=roll_window,
                            source_skew_ms=source_skew,
                        )
                    )

    def unique(points: Sequence[PricePoint]) -> tuple[PricePoint, ...]:
        by_time = {point.timestamp_ms: point for point in points}
        return tuple(by_time[key] for key in sorted(by_time))

    source_path = str(runtime_directory)
    if not rfq_points and not index_points:
        reason = "NO_LOCAL_RECORDINGS"
    else:
        reason = None
    return (
        PriceSeries(
            key="variational_index",
            label="Variational 指数",
            venue="variational",
            price_kind="economic_reference_index",
            interval="observation",
            points=unique(index_points),
            status="ok" if index_points else "unavailable",
            reason=reason or (None if index_points else "INDEX_PRICE_MISSING"),
            source_urls=(source_path,),
        ),
        PriceSeries(
            key="variational_rfq",
            label="Variational 指示性 RFQ",
            venue="variational",
            price_kind="indicative_rfq_mid",
            interval="observation",
            points=unique(rfq_points),
            status="ok" if rfq_points else "unavailable",
            reason=reason or (None if rfq_points else "RFQ_MISSING"),
            source_urls=(source_path,),
        ),
    )


def _capture_public_json(
    *,
    method: str,
    url: str,
    payload: Optional[Mapping[str, Any]] = None,
    timeout: float = 30.0,
) -> tuple[Any, bytes, int]:
    body = (
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if payload is not None
        else None
    )
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "monte-arb-oil-research/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        status = int(response.status)
    return json.loads(raw), raw, status


def _write_raw(
    raw_directory: Path,
    name: str,
    raw: bytes,
    *,
    method: str,
    url: str,
    status: int,
) -> dict[str, Any]:
    raw_directory.mkdir(parents=True, exist_ok=True)
    path = raw_directory / f"{name}.json"
    path.write_bytes(raw)
    return {
        "name": name,
        "method": method,
        "url": url,
        "http_status": status,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "path": str(path),
    }


def _collect_lighter(
    raw_directory: Path, timeout: float
) -> tuple[PriceSeries, Mapping[str, Any], dict[str, L2Book], dict[str, MarketSpec]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    manifest = []
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    for symbol, market_id in LIGHTER_MARKETS.items():
        params = {
            "market_id": market_id,
            "resolution": "1h",
            "start_timestamp": 1,
            "end_timestamp": now_ms,
            "count_back": 500,
            "set_timestamp_to_end": False,
        }
        url = f"{LIGHTER_BASE_URL}/candles?{urllib.parse.urlencode(params)}"
        payload, raw, status = _capture_public_json(
            method="GET", url=url, timeout=timeout
        )
        if not isinstance(payload, Mapping) or payload.get("code") != 200:
            raise ValueError(f"Lighter candles invalid for {symbol}")
        candles = payload.get("c")
        if not isinstance(candles, list):
            raise ValueError(f"Lighter candles missing for {symbol}")
        rows[symbol] = [dict(item) for item in candles if isinstance(item, Mapping)]
        manifest.append(
            _write_raw(
                raw_directory,
                f"lighter-{symbol.lower()}-candles-1h",
                raw,
                method="GET",
                url=url,
                status=status,
            )
        )

    points = align_legs(
        rows["WTI"],
        rows["BRENTOIL"],
        timestamp_field="t",
        price_field="c",
        volume_field="V",
    )

    client = PublicJsonClient(timeout=timeout)
    catalog = fetch_lighter_catalog(client)
    by_symbol = {market.identity.symbol: market for market in catalog}
    details = fetch_lighter_details(client, list(LIGHTER_MARKETS.values()))
    books: dict[str, L2Book] = {}
    specs: dict[str, MarketSpec] = {}
    for symbol, market_id in LIGHTER_MARKETS.items():
        market = by_symbol.get(symbol)
        if market is None:
            raise ValueError(f"Lighter catalog missing {symbol}")
        raw_book = fetch_lighter_book(client, market, limit=20)
        books[symbol] = l2book_from_raw(market.identity, raw_book)
        specs[symbol] = details[market_id]
    for capture in client.captures:
        manifest.append(
            _write_raw(
                raw_directory,
                capture.name,
                capture.raw,
                method=capture.method,
                url=capture.endpoint,
                status=capture.http_status,
            )
        )
    source = PriceSeries(
        key="lighter",
        label="Lighter 1h K 线",
        venue="lighter",
        price_kind="perp_candle_close",
        interval="1h",
        points=points,
        status="ok" if points else "unavailable",
        reason=None if points else "NO_SYNCHRONIZED_CANDLES",
        source_urls=(f"{LIGHTER_BASE_URL}/candles",),
    )
    return source, {"captures": manifest}, books, specs


def _optional_decimal(value: Any) -> Optional[Decimal]:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except Exception:
        return None
    return parsed if parsed.is_finite() else None


def _hl_spec(market: CatalogMarket) -> MarketSpec:
    size_decimals = market.context.get("szDecimals")
    if not isinstance(size_decimals, int):
        raise ValueError(f"Hyperliquid size precision missing for {market.identity.symbol}")
    max_leverage = _optional_decimal(market.context.get("maxLeverage"))
    return MarketSpec(
        identity=market.identity,
        venue="hyperliquid",
        taker_fee_bps=None,
        maker_fee_bps=None,
        size_decimals=size_decimals,
        min_base_amount=Decimal(0),
        min_quote_amount=Decimal(10),
        multiplier=Decimal(1),
        price_decimals=3,
        max_leverage=max_leverage,
        margin_evidence=(
            "public_market_max_leverage" if max_leverage is not None else "unknown"
        ),
    )


def _collect_hyperliquid(
    raw_directory: Path, timeout: float
) -> tuple[PriceSeries, Mapping[str, Any], dict[str, L2Book], dict[str, MarketSpec]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    manifest = []
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    start_ms = now_ms - 30 * 24 * 60 * 60 * 1000
    for symbol, coin in HL_SYMBOLS.items():
        request_payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": "1h",
                "startTime": start_ms,
                "endTime": now_ms,
            },
        }
        payload, raw, status = _capture_public_json(
            method="POST",
            url=HYPERLIQUID_INFO_URL,
            payload=request_payload,
            timeout=timeout,
        )
        if not isinstance(payload, list):
            raise ValueError(f"Hyperliquid candles invalid for {coin}")
        rows[symbol] = [dict(item) for item in payload if isinstance(item, Mapping)]
        manifest.append(
            _write_raw(
                raw_directory,
                f"hyperliquid-{symbol.lower()}-candles-1h",
                raw,
                method="POST",
                url=HYPERLIQUID_INFO_URL,
                status=status,
            )
        )
    points = align_legs(
        rows["WTI"],
        rows["BRENTOIL"],
        timestamp_field="t",
        price_field="c",
        volume_field="v",
    )
    client = PublicJsonClient(timeout=timeout)
    catalog = fetch_hyperliquid_catalog(client, "xyz")
    by_symbol = {market.identity.symbol: market for market in catalog}
    books: dict[str, L2Book] = {}
    specs: dict[str, MarketSpec] = {}
    for symbol, coin in HL_SYMBOLS.items():
        market = by_symbol.get(coin)
        if market is None:
            raise ValueError(f"Hyperliquid catalog missing {coin}")
        raw_book = fetch_hyperliquid_book(client, market)
        books[symbol] = l2book_from_raw(market.identity, raw_book)
        specs[symbol] = _hl_spec(market)
    for capture in client.captures:
        manifest.append(
            _write_raw(
                raw_directory,
                capture.name,
                capture.raw,
                method=capture.method,
                url=capture.endpoint,
                status=capture.http_status,
            )
        )
    source = PriceSeries(
        key="hyperliquid",
        label="Hyperliquid xyz 1h K 线",
        venue="hyperliquid",
        price_kind="hip3_perp_candle_close",
        interval="1h",
        points=points,
        status="ok" if points else "unavailable",
        reason=None if points else "NO_SYNCHRONIZED_CANDLES",
        source_urls=(HYPERLIQUID_INFO_URL,),
    )
    return source, {"captures": manifest}, books, specs


def _collect_external_daily(raw_directory: Path, timeout: float) -> tuple[PriceSeries, Mapping[str, Any]]:
    period1 = 1_185_753_600
    period2 = int(datetime.now(UTC).timestamp()) + 86_400
    rows: dict[str, list[dict[str, Any]]] = {}
    manifest = []
    for symbol, yahoo_symbol in YAHOO_SYMBOLS.items():
        encoded = urllib.parse.quote(yahoo_symbol, safe="")
        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "history",
        }
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?"
            f"{urllib.parse.urlencode(params)}"
        )
        payload, raw, status = _capture_public_json(method="GET", url=url, timeout=timeout)
        chart = payload.get("chart") if isinstance(payload, Mapping) else None
        result = chart.get("result") if isinstance(chart, Mapping) else None
        item = result[0] if isinstance(result, list) and result else None
        timestamps = item.get("timestamp") if isinstance(item, Mapping) else None
        indicators = item.get("indicators") if isinstance(item, Mapping) else None
        quotes = indicators.get("quote") if isinstance(indicators, Mapping) else None
        quote = quotes[0] if isinstance(quotes, list) and quotes else None
        closes = quote.get("close") if isinstance(quote, Mapping) else None
        volumes = quote.get("volume") if isinstance(quote, Mapping) else None
        if not isinstance(timestamps, list) or not isinstance(closes, list):
            raise ValueError(f"Yahoo chart invalid for {yahoo_symbol}")
        rows[symbol] = [
            {
                "t": timestamp,
                "c": close,
                "v": volumes[index] if isinstance(volumes, list) and index < len(volumes) else None,
            }
            for index, (timestamp, close) in enumerate(zip(timestamps, closes))
            if close is not None
        ]
        manifest.append(
            _write_raw(
                raw_directory,
                f"yahoo-{symbol.lower()}-daily",
                raw,
                method="GET",
                url=url,
                status=status,
            )
        )
    points = align_legs(
        rows["WTI"],
        rows["BRENTOIL"],
        timestamp_field="t",
        price_field="c",
        volume_field="v",
    )
    source = PriceSeries(
        key="external_daily",
        label="外部连续期货日线",
        venue="yahoo_chart",
        price_kind="continuous_futures_daily_close",
        interval="1d",
        points=points,
        status="ok" if points else "unavailable",
        reason=None if points else "NO_SYNCHRONIZED_DAILY_ROWS",
        source_urls=(
            "https://query1.finance.yahoo.com/v8/finance/chart/CL%3DF",
            "https://query1.finance.yahoo.com/v8/finance/chart/BZ%3DF",
        ),
    )
    return source, {"captures": manifest}


def _blocked_oil_direction(
    direction: str, size_usd: Decimal, reason: str
) -> dict[str, Any]:
    return {
        "direction": direction,
        "size_usd": float(size_usd),
        "status": "blocked",
        "entry_status": "blocked",
        "exit_status": "not_evaluated",
        "entry_fill_pct": 0.0,
        "exit_fill_pct": 0.0,
        "entry_unfilled_qty": 0.0,
        "exit_unfilled_qty": 0.0,
        "entry_residual_qty": 0.0,
        "residual_open_qty": 0.0,
        "residual_open_quantities": {},
        "quantity": 0.0,
        "entry_log_ratio": None,
        "entry_crossing_bps": None,
        "round_trip_friction_bps": None,
        "fees_known": False,
        "reason_codes": [reason],
        "legs": {},
    }


def estimate_oil_direction(
    books: Mapping[str, L2Book],
    specs: Mapping[str, MarketSpec],
    *,
    direction: str,
    size_usd: Decimal,
) -> dict[str, Any]:
    if direction == "long_brent_short_wti":
        buy_symbol, sell_symbol = "BRENTOIL", "WTI"
    elif direction == "long_wti_short_brent":
        buy_symbol, sell_symbol = "WTI", "BRENTOIL"
    else:
        raise ValueError("unknown oil direction")
    buy_spec, sell_spec = specs[buy_symbol], specs[sell_symbol]
    buy_book, sell_book = books[buy_symbol], books[sell_symbol]
    buy_top, sell_top = buy_book.best_ask, sell_book.best_bid
    if buy_top is None or sell_top is None:
        return _blocked_oil_direction(direction, size_usd, "NO_TOP_OF_BOOK")
    common_step = _decimal_lcm(buy_spec.quantity_step, sell_spec.quantity_step)
    max_quantity = min(size_usd / buy_top, size_usd / sell_top)
    quantity = (max_quantity / common_step).to_integral_value(rounding=ROUND_DOWN) * common_step
    if quantity <= 0:
        return _blocked_oil_direction(direction, size_usd, "NO_COMMON_QUANTITY")
    buy = leg_execution(buy_spec, buy_book, side="buy", target_qty=quantity)
    sell = leg_execution(sell_spec, sell_book, side="sell", target_qty=quantity)
    # The frozen-book exit closes only quantities that actually entered.  It
    # must not invent a full-size close after a partial entry.
    exit_buy = leg_execution(
        sell_spec,
        sell_book,
        side="buy",
        target_qty=sell.filled_qty,
    )
    exit_sell = leg_execution(
        buy_spec,
        buy_book,
        side="sell",
        target_qty=buy.filled_qty,
    )
    entry_full = all(
        leg.orderable and leg.unfilled_qty == 0 for leg in (buy, sell)
    )
    entry_residual_qty = abs(buy.filled_qty - sell.filled_qty)
    exit_full = all(
        leg.orderable and leg.unfilled_qty == 0 for leg in (exit_buy, exit_sell)
    )

    def phase_fill(legs: Sequence[Any]) -> tuple[float, Decimal]:
        fractions = [
            (leg.filled_qty / leg.target_qty) if leg.target_qty > 0 else Decimal(0)
            for leg in legs
        ]
        return (
            float(min(fractions, default=Decimal(0)) * Decimal(100)),
            max((leg.unfilled_qty for leg in legs), default=Decimal(0)),
        )

    entry_fill_pct, entry_unfilled_qty = phase_fill((buy, sell))
    exit_fill_pct, exit_unfilled_qty = phase_fill((exit_buy, exit_sell))
    residual_open_quantities = {
        buy_symbol: float(exit_sell.unfilled_qty),
        sell_symbol: float(exit_buy.unfilled_qty),
    }
    residual_open_qty = max(exit_buy.unfilled_qty, exit_sell.unfilled_qty)
    round_trip_complete = entry_full and exit_full
    entry_log_ratio = None
    round_trip_friction_bps = None
    entry_crossing_bps = None
    if entry_full and buy.vwap is not None and sell.vwap is not None:
        assert buy.vwap and sell.vwap
        if direction == "long_brent_short_wti":
            entry_log_ratio = math.log(float(buy.vwap)) - math.log(float(sell.vwap))
        else:
            entry_log_ratio = math.log(float(sell.vwap)) - math.log(float(buy.vwap))
        mid_buy = (buy_book.best_bid + buy_book.best_ask) / 2  # type: ignore[operator]
        mid_sell = (sell_book.best_bid + sell_book.best_ask) / 2  # type: ignore[operator]
        entry_crossing_bps = float(
            (buy.vwap / mid_buy - Decimal(1) + Decimal(1) - sell.vwap / mid_sell)
            * Decimal(10_000)
        )
    if round_trip_complete and exit_buy.vwap is not None and exit_sell.vwap is not None:
        assert buy.vwap and sell.vwap and exit_buy.vwap and exit_sell.vwap
        entry_cost = quantity * buy.vwap - quantity * sell.vwap
        exit_value = quantity * exit_sell.vwap - quantity * exit_buy.vwap
        reference = quantity * (buy_top + sell_top) / 2
        round_trip_friction_bps = float((entry_cost - exit_value) / reference * Decimal(10_000))
    fees_known = all(leg.fee_cost_usd is not None for leg in (buy, sell, exit_buy, exit_sell))
    reason_codes = []
    if not entry_full:
        reason_codes.append("ENTRY_DEPTH_INSUFFICIENT")
    if not exit_full:
        reason_codes.append("EXIT_DEPTH_INSUFFICIENT")
    if not fees_known:
        reason_codes.append("FEE_UNKNOWN")
    return {
        "direction": direction,
        "size_usd": float(size_usd),
        "status": "full_fill" if round_trip_complete else "partial_or_blocked",
        "entry_status": "full_fill" if entry_full else "partial_fill",
        "exit_status": "full_fill" if exit_full else "partial_fill",
        "entry_fill_pct": entry_fill_pct,
        "exit_fill_pct": exit_fill_pct,
        "entry_unfilled_qty": float(entry_unfilled_qty),
        "entry_residual_qty": float(entry_residual_qty),
        "exit_unfilled_qty": float(exit_unfilled_qty),
        "residual_open_qty": float(residual_open_qty),
        "residual_open_quantities": residual_open_quantities,
        "quantity": float(quantity),
        "entry_log_ratio": entry_log_ratio,
        "entry_crossing_bps": entry_crossing_bps,
        "round_trip_friction_bps": round_trip_friction_bps,
        "fees_known": fees_known,
        "reason_codes": reason_codes,
        "legs": {
            "entry_buy": buy.to_dict(),
            "entry_sell": sell.to_dict(),
            "exit_buy": exit_buy.to_dict(),
            "exit_sell": exit_sell.to_dict(),
        },
    }


def _decimal_lcm(left: Decimal, right: Decimal) -> Decimal:
    left_exponent = left.as_tuple().exponent
    right_exponent = right.as_tuple().exponent
    if not isinstance(left_exponent, int) or not isinstance(right_exponent, int):
        raise ValueError("quantity steps must be finite Decimals")
    exponent = max(-left_exponent, -right_exponent, 0)
    scale = Decimal(10) ** exponent
    left_int = int(left * scale)
    right_int = int(right * scale)
    gcd = math.gcd(left_int, right_int)
    return Decimal(abs(left_int * right_int) // gcd) / scale


def build_oil_execution_projection(
    venue_inputs: Mapping[str, tuple[Mapping[str, L2Book], Mapping[str, MarketSpec]]],
    sizes: Sequence[Decimal],
) -> dict[str, Any]:
    venues = []
    for venue, (books, specs) in venue_inputs.items():
        rows = []
        for size in sizes:
            for direction in ("long_brent_short_wti", "long_wti_short_brent"):
                rows.append(
                    estimate_oil_direction(
                        books,
                        specs,
                        direction=direction,
                        size_usd=size,
                    )
                )
        venues.append(
            {
                "venue": venue,
                "basis": "l2_book",
                "book_source_times_ms": {
                    symbol: book.source_time_ms for symbol, book in books.items()
                },
                "rows": rows,
            }
        )
    limitations = [
        "ONE_TO_ONE_QUANTITY_BASELINE_NOT_BETA_HEDGED",
        "CONTRACT_WEIGHT_AND_HEDGE_RATIO_UNVERIFIED",
        "SAME_FROZEN_BOOK_EXIT_BASELINE",
        "FUTURE_EXIT_STATE_UNKNOWN",
        "HOLDING_FUNDING_UNKNOWN",
    ]
    if any(
        "FEE_UNKNOWN" in row["reason_codes"]
        for venue in venues
        for row in venue["rows"]
    ):
        limitations.append("ACCOUNT_FEE_UNKNOWN")
    return {
        "sizes_usd": [float(size) for size in sizes],
        "venues": venues,
        "limitations": limitations,
    }


def collect_oil_dataset(
    *,
    raw_directory: Path,
    variational_runtime_directory: Optional[Path] = None,
    timeout: float = 30.0,
    sizes: Sequence[Decimal] = DEFAULT_SIZES,
) -> OilDataset:
    sources: list[PriceSeries] = []
    raw_manifest: dict[str, Any] = {"schema": "oil-raw-manifest-v1", "captures": []}
    errors = []
    venue_inputs: dict[
        str, tuple[Mapping[str, L2Book], Mapping[str, MarketSpec]]
    ] = {}

    for collector_name, collector in (
        ("lighter", _collect_lighter),
        ("hyperliquid", _collect_hyperliquid),
    ):
        try:
            source, manifest, books, specs = collector(raw_directory, timeout)
            sources.append(source)
            venue_inputs[collector_name] = (books, specs)
            raw_manifest["captures"].extend(manifest.get("captures", []))
        except Exception as exc:  # preserve other sources and report the failure
            sources.append(
                PriceSeries(
                    key=collector_name,
                    label=collector_name.title(),
                    venue=collector_name,
                    price_kind="unknown",
                    interval="1h",
                    points=(),
                    status="unavailable",
                    reason=f"COLLECTION_FAILED:{type(exc).__name__}",
                    source_urls=(),
                )
            )
            errors.append({"source": collector_name, "error": type(exc).__name__})

    try:
        source, manifest = _collect_external_daily(raw_directory, timeout)
        sources.append(source)
        raw_manifest["captures"].extend(manifest.get("captures", []))
    except Exception as exc:
        sources.append(
            PriceSeries(
                key="external_daily",
                label="外部连续期货日线",
                venue="yahoo_chart",
                price_kind="continuous_futures_daily_close",
                interval="1d",
                points=(),
                status="unavailable",
                reason=f"COLLECTION_FAILED:{type(exc).__name__}",
                source_urls=(),
            )
        )
        errors.append({"source": "external_daily", "error": type(exc).__name__})

    if variational_runtime_directory is not None:
        sources.extend(load_variational_recordings(variational_runtime_directory))
    else:
        sources.extend(
            (
                PriceSeries(
                    key="variational_index",
                    label="Variational 指数",
                    venue="variational",
                    price_kind="economic_reference_index",
                    interval="observation",
                    points=(),
                    status="unavailable",
                    reason="NO_LOCAL_RECORDINGS",
                    source_urls=(),
                ),
                PriceSeries(
                    key="variational_rfq",
                    label="Variational 指示性 RFQ",
                    venue="variational",
                    price_kind="indicative_rfq_mid",
                    interval="observation",
                    points=(),
                    status="unavailable",
                    reason="NO_LOCAL_RECORDINGS",
                    source_urls=(),
                ),
            )
        )

    execution = build_oil_execution_projection(venue_inputs, sizes)
    diagnostics: list[Mapping[str, Any]] = []
    if errors:
        diagnostics.append(
            {
                "code": "SOURCE_COLLECTION_ERROR",
                "severity": "blocked",
                "title": "部分价格源采集失败",
                "evidence": [f"{item['source']}: {item['error']}" for item in errors],
                "counter_evidence": [],
                "limitations": ["other successful sources remain usable independently"],
                "next_check": "retry the failed source without replacing the last good dataset",
            }
        )
    raw_manifest["generated_at"] = _utc_now()
    return OilDataset(
        generated_at=_utc_now(),
        sources=tuple(sources),
        execution=execution,
        diagnostics=tuple(diagnostics),
        raw_manifest=raw_manifest,
    )


def write_projection_atomic(path: Path, projection: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(projection, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def load_existing_frozen_models(path: Path) -> dict[str, Mapping[str, Any]]:
    """Load only model parameters from an existing projection for stable reuse."""
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    sources = payload.get("sources")
    if not isinstance(sources, list):
        return result
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        key = source.get("key")
        model = source.get("model")
        if isinstance(key, str) and isinstance(model, Mapping):
            result[key] = model
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m monte_arb.oil_relative_value",
        description="Collect and build the read-only Brent-WTI research projection.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/runs/oil-relative-value.json"),
    )
    parser.add_argument(
        "--raw-directory",
        type=Path,
        default=None,
        help="raw capture directory (default research/raw/oil/<UTC capture id>)",
    )
    parser.add_argument("--variational-runtime", type=Path, default=None)
    parser.add_argument(
        "--refit-models",
        action="store_true",
        help="fit new formation windows instead of reusing models from --output",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--sizes", default="100,500,1000")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        sizes = tuple(Decimal(value.strip()) for value in args.sizes.split(","))
    except Exception as exc:
        raise SystemExit(f"invalid --sizes: {exc}") from exc
    capture_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    raw_directory = args.raw_directory or Path("research/raw/oil") / capture_id
    dataset = collect_oil_dataset(
        raw_directory=raw_directory,
        variational_runtime_directory=args.variational_runtime,
        timeout=args.timeout,
        sizes=sizes,
    )
    frozen_models = {} if args.refit_models else load_existing_frozen_models(args.output)
    projection = build_oil_projection(dataset, frozen_models=frozen_models)
    write_projection_atomic(args.output, projection)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "raw_directory": str(raw_directory),
                "source_status": {
                    source["key"]: source["status"] for source in projection["sources"]
                },
                "samples": {
                    source["key"]: source["sample_count"]
                    for source in projection["sources"]
                },
                "execution_venues": len(projection["execution"].get("venues", [])),
                "models_reused": sorted(
                    source["key"] for source in projection["sources"] if source["model_reused"]
                ),
                "diagnostics": len(projection["diagnostics"]),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if any(source["status"] == "ok" for source in projection["sources"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
