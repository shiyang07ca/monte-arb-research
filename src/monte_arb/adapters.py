from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from .market import CatalogMarket, MarketIdentity

LIGHTER_BASE_URL = "https://mainnet.zklighter.elliot.ai/api/v1"
HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"


class SourceShapeError(ValueError):
    """Raised when an official response cannot be paired without guessing."""


class SourceRequestError(RuntimeError):
    """Raised when a read-only public request fails."""


@dataclass(frozen=True)
class Capture:
    name: str
    method: str
    endpoint: str
    request: Mapping[str, Any]
    received_at: str
    http_status: int
    sha256: str
    raw: bytes


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class PublicJsonClient:
    """Minimal read-only JSON client which retains exact response bytes."""

    def __init__(self, *, timeout: float = 20.0) -> None:
        self.timeout = timeout
        self.captures: list[Capture] = []

    def _request(
        self,
        *,
        name: str,
        method: str,
        endpoint: str,
        request_metadata: Mapping[str, Any],
        body: Optional[bytes] = None,
    ) -> Any:
        headers = {
            "Accept": "application/json",
            "User-Agent": "monte-arb-day12/1.0",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            endpoint, data=body, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                status = int(response.status)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise SourceRequestError(f"{method} {endpoint} failed: {exc}") from exc

        received_at = _utc_now()
        capture = Capture(
            name=name,
            method=method,
            endpoint=endpoint,
            request=dict(request_metadata),
            received_at=received_at,
            http_status=status,
            sha256=hashlib.sha256(raw).hexdigest(),
            raw=raw,
        )
        self.captures.append(capture)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SourceShapeError(f"{name}: response is not JSON") from exc

    def get(
        self, name: str, endpoint: str, params: Optional[Mapping[str, Any]] = None
    ) -> Any:
        query = dict(params or {})
        url = endpoint
        if query:
            url = f"{endpoint}?{urllib.parse.urlencode(query)}"
        return self._request(
            name=name,
            method="GET",
            endpoint=url,
            request_metadata={"params": query},
        )

    def post(self, name: str, endpoint: str, payload: Mapping[str, Any]) -> Any:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return self._request(
            name=name,
            method="POST",
            endpoint=endpoint,
            request_metadata={"json": dict(payload)},
            body=body,
        )


def normalize_lighter_catalog(response: Any) -> tuple[CatalogMarket, ...]:
    if not isinstance(response, Mapping) or response.get("code") != 200:
        raise SourceShapeError("lighter orderBooks: expected code=200 object")
    rows = response.get("order_books")
    if not isinstance(rows, list):
        raise SourceShapeError("lighter orderBooks: order_books must be a list")

    markets = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise SourceShapeError("lighter orderBooks: market must be an object")
        symbol = row.get("symbol")
        market_id = row.get("market_id")
        product_type = row.get("market_type")
        if (
            not isinstance(symbol, str)
            or market_id is None
            or not isinstance(product_type, str)
        ):
            raise SourceShapeError("lighter orderBooks: identity field missing")
        if product_type != "perp":
            continue
        status = row.get("status")
        catalog_status = status if status in {"active", "inactive"} else "unknown"
        markets.append(
            CatalogMarket(
                MarketIdentity(
                    "lighter", product_type, "default", symbol, str(market_id)
                ),
                catalog_status,
                dict(row),
            )
        )
    return tuple(markets)


def find_perp_dex_index(perp_dexs: Any, venue_namespace: str) -> int:
    if not isinstance(perp_dexs, list):
        raise SourceShapeError("hyperliquid perpDexs: expected list")
    for index, dex in enumerate(perp_dexs):
        if isinstance(dex, Mapping) and dex.get("name") == venue_namespace:
            return index
    raise SourceShapeError(
        f"hyperliquid perpDexs: unknown namespace {venue_namespace!r}"
    )


def normalize_hyperliquid_catalog(
    response: Any, *, perp_dex_index: int, venue_namespace: str
) -> tuple[CatalogMarket, ...]:
    if not isinstance(response, list) or len(response) != 2:
        raise SourceShapeError("hyperliquid metaAndAssetCtxs: expected two arrays")
    metadata, contexts = response
    if not isinstance(metadata, Mapping):
        raise SourceShapeError("hyperliquid metadata must be an object")
    universe = metadata.get("universe")
    if not isinstance(universe, list) or not isinstance(contexts, list):
        raise SourceShapeError("hyperliquid universe/contexts must be lists")
    if len(universe) != len(contexts):
        raise SourceShapeError("hyperliquid meta/context length mismatch")

    markets = []
    for index, pair in enumerate(zip(universe, contexts)):
        meta, context = pair
        if not isinstance(meta, Mapping) or not isinstance(context, Mapping):
            raise SourceShapeError("hyperliquid meta/context entry must be an object")
        symbol = meta.get("name")
        if not isinstance(symbol, str):
            raise SourceShapeError("hyperliquid market name missing")
        expected_prefix = f"{venue_namespace}:"
        if not symbol.startswith(expected_prefix):
            raise SourceShapeError(
                f"hyperliquid symbol {symbol!r} lacks namespace {expected_prefix!r}"
            )
        asset_id = 100000 + perp_dex_index * 10000 + index
        markets.append(
            CatalogMarket(
                MarketIdentity(
                    "hyperliquid", "perp", venue_namespace, symbol, str(asset_id)
                ),
                "delisted" if meta.get("isDelisted") is True else "active",
                dict(context),
                index,
            )
        )
    return tuple(markets)


def fetch_lighter_catalog(client: PublicJsonClient) -> tuple[CatalogMarket, ...]:
    response = client.get("lighter-order-books", f"{LIGHTER_BASE_URL}/orderBooks")
    return normalize_lighter_catalog(response)


def fetch_lighter_book(
    client: PublicJsonClient, market: CatalogMarket, *, limit: int = 20
) -> Mapping[str, Any]:
    response = client.get(
        f"lighter-book-{market.identity.local_id}",
        f"{LIGHTER_BASE_URL}/orderBookOrders",
        {"market_id": market.identity.local_id, "limit": limit},
    )
    if not isinstance(response, Mapping):
        raise SourceShapeError("lighter orderBookOrders: expected object")
    if response.get("code") != 200:
        raise SourceShapeError("lighter orderBookOrders: expected code=200")
    return response


def fetch_hyperliquid_catalog(
    client: PublicJsonClient, venue_namespace: str
) -> tuple[CatalogMarket, ...]:
    perp_dexs = client.post(
        "hyperliquid-perp-dexs", HYPERLIQUID_INFO_URL, {"type": "perpDexs"}
    )
    perp_dex_index = find_perp_dex_index(perp_dexs, venue_namespace)
    response = client.post(
        f"hyperliquid-meta-contexts-{venue_namespace}",
        HYPERLIQUID_INFO_URL,
        {"type": "metaAndAssetCtxs", "dex": venue_namespace},
    )
    return normalize_hyperliquid_catalog(
        response,
        perp_dex_index=perp_dex_index,
        venue_namespace=venue_namespace,
    )


def fetch_hyperliquid_book(
    client: PublicJsonClient, market: CatalogMarket
) -> Mapping[str, Any]:
    response = client.post(
        f"hyperliquid-book-{market.identity.symbol.replace(':', '-')}",
        HYPERLIQUID_INFO_URL,
        {"type": "l2Book", "coin": market.identity.symbol},
    )
    if not isinstance(response, Mapping):
        raise SourceShapeError("hyperliquid l2Book: expected object")
    if response.get("coin") != market.identity.symbol:
        raise SourceShapeError(
            "hyperliquid l2Book: response identity differs from request"
        )
    return response
