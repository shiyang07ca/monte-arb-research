from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .adapters import (
    PublicJsonClient,
    SourceRequestError,
    SourceShapeError,
    fetch_hyperliquid_book,
    fetch_hyperliquid_catalog,
    fetch_lighter_book,
    fetch_lighter_catalog,
)
from .market import (
    CatalogMarket,
    MarketIdentity,
    RequestError,
    scan_markets,
)
from .economic import build_day13_report, load_day13_specifications


def _parse_venue(value: str) -> tuple[str, str]:
    if value == "lighter":
        return "lighter", "default"
    if value.startswith("hyperliquid:") and value.count(":") == 1:
        namespace = value.split(":", 1)[1]
        if namespace:
            return "hyperliquid", namespace
    raise argparse.ArgumentTypeError(
        "venue must be 'lighter' or 'hyperliquid:<namespace>'"
    )


def _catalog_by_identity(
    catalogs: Iterable[CatalogMarket],
) -> dict[MarketIdentity, CatalogMarket]:
    result = {}
    for market in catalogs:
        if market.identity in result:
            # Keep duplicate entries in scan_markets; fetching an ambiguous book is forbidden.
            continue
        result[market.identity] = market
    return result


def _raw_capture_path(raw_dir: Path, name: str, sha256: str) -> Path:
    return raw_dir / f"{name}-{sha256}.json"


def _save_raw_captures(client: PublicJsonClient, raw_dir: Path) -> list[str]:
    paths = []
    for capture in client.captures:
        path = _raw_capture_path(raw_dir, capture.name, capture.sha256)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != capture.raw:
                raise SourceShapeError(f"raw capture hash collision at {path}")
        else:
            path.write_bytes(capture.raw)
        paths.append(path.as_posix())
    return paths


def _capture_manifest(client: PublicJsonClient, raw_paths: list[str]) -> dict:
    if len(client.captures) != len(raw_paths):
        raise SourceShapeError("capture/raw path length mismatch")
    return {
        "schema": "day12-universe-v1",
        "read_only": True,
        "captures": [
            {
                "name": capture.name,
                "method": capture.method,
                "endpoint": capture.endpoint,
                "request": capture.request,
                "received_at": capture.received_at,
                "http_status": capture.http_status,
                "sha256": capture.sha256,
                "bytes": len(capture.raw),
                "raw_file": raw_file,
            }
            for capture, raw_file in zip(client.captures, raw_paths)
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def run_scan(args: argparse.Namespace) -> int:
    client = PublicJsonClient(timeout=args.timeout)
    catalogs: list[CatalogMarket] = []

    for venue, namespace in args.venue:
        if venue == "lighter":
            catalogs.extend(fetch_lighter_catalog(client))
        else:
            catalogs.extend(fetch_hyperliquid_catalog(client, namespace))

    requested: list[MarketIdentity] = []
    parse_errors: list[RequestError] = []
    for selector in args.inspect_book:
        try:
            requested.append(MarketIdentity.from_selector(selector))
        except ValueError:
            parse_errors.append(RequestError(selector, "INVALID_SELECTOR"))

    known_counts: dict[MarketIdentity, int] = {}
    for market in catalogs:
        known_counts[market.identity] = known_counts.get(market.identity, 0) + 1
    known = _catalog_by_identity(catalogs)
    books = {}
    for identity in requested:
        market = known.get(identity)
        if market is None or known_counts.get(identity, 0) != 1:
            continue
        if market.catalog_status != "active":
            continue
        if identity.venue == "lighter":
            books[identity] = fetch_lighter_book(client, market, limit=args.book_limit)
        elif identity.venue == "hyperliquid":
            books[identity] = fetch_hyperliquid_book(client, market)

    observed_at = client.captures[-1].received_at if client.captures else None
    report = scan_markets(
        catalogs,
        books,
        requested=requested,
        observed_at=observed_at,
    ).with_request_errors(parse_errors)

    raw_paths = _save_raw_captures(client, args.raw_dir)
    _write_json(args.output, report.to_dict())
    _write_json(args.manifest, _capture_manifest(client, raw_paths))

    counts: dict[str, int] = {}
    for market in report.markets:
        counts[market.scan_status] = counts.get(market.scan_status, 0) + 1
    summary = {
        "output": str(args.output),
        "manifest": str(args.manifest),
        "market_count": len(report.markets),
        "scan_status_counts": counts,
        "request_errors": [error.to_dict() for error in report.request_errors],
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 2 if report.request_errors else 0


def run_map_economics(args: argparse.Namespace) -> int:
    payload = json.loads(args.specifications.read_text())
    specifications = load_day13_specifications(payload)
    report = build_day13_report(specifications)
    _write_json(args.output, report)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "market_count": len(report["markets"]),
                "pair_assessments": report["pair_assessments"],
                "price_state": report["price_state_boundary"]["status"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m monte_arb.cli",
        description="Read-only cross-venue market research commands.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser(
        "scan", help="fetch current catalogs and inspect explicitly selected books"
    )
    scan.add_argument(
        "--venue",
        action="append",
        type=_parse_venue,
        required=True,
        help="lighter or hyperliquid:<namespace>",
    )
    scan.add_argument(
        "--inspect-book",
        action="append",
        default=[],
        help="venue/product_type/namespace/symbol/local_id",
    )
    scan.add_argument(
        "--book-limit", type=int, default=20, choices=range(1, 251), metavar="1..250"
    )
    scan.add_argument(
        "--output", type=Path, default=Path("research/runs/day12-scan.json")
    )
    scan.add_argument(
        "--manifest",
        type=Path,
        default=Path("research/manifests/day12-universe.json"),
    )
    scan.add_argument("--raw-dir", type=Path, default=Path("research/raw/day12"))
    scan.add_argument("--timeout", type=float, default=20.0)
    scan.set_defaults(handler=run_scan)

    economics = subparsers.add_parser(
        "map-economics",
        help="assess sourced economic definitions without calculating spreads",
    )
    economics.add_argument(
        "--specifications",
        type=Path,
        default=Path("tests/fixtures/day13/economic-specifications.json"),
    )
    economics.add_argument(
        "--output",
        type=Path,
        default=Path("research/runs/day13-economic-map.json"),
    )
    economics.set_defaults(handler=run_map_economics)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (
        SourceRequestError,
        SourceShapeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"command failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
