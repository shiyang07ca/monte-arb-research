from __future__ import annotations

import asyncio
import json
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

try:
    import websockets
except ImportError:  # pragma: no cover - optional outside browser-QA environments
    websockets = None

from monte_arb.oil_relative_value import OilDataset, PricePoint, PriceSeries, build_oil_projection
from monte_arb.workbench_app import WorkbenchApp


def _chrome_path() -> str | None:
    candidates = (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    )
    return next((str(path) for path in candidates if path and Path(path).exists()), None)


def _series(key: str, offset: float) -> PriceSeries:
    return PriceSeries(
        key=key,
        label=key.title(),
        venue=key,
        price_kind="perp_candle_close",
        interval="1h",
        points=tuple(
            PricePoint(
                timestamp_ms=index * 3_600_000,
                wti=80 + index * 0.03 + offset,
                brent=85 + index * 0.04 + offset,
            )
            for index in range(80)
        ),
        status="ok",
        reason=None,
        source_urls=("https://example.test",),
    )


def _execution_row(direction: str, size: int) -> dict[str, Any]:
    return {
        "direction": direction,
        "size_usd": float(size),
        "status": "full_fill",
        "entry_status": "full_fill",
        "exit_status": "full_fill",
        "entry_fill_pct": 100.0,
        "exit_fill_pct": 100.0,
        "entry_unfilled_qty": 0.0,
        "entry_residual_qty": 0.0,
        "exit_unfilled_qty": 0.0,
        "residual_open_qty": 0.0,
        "residual_open_quantities": {"WTI": 0.0, "BRENTOIL": 0.0},
        "quantity": 1.25,
        "entry_log_ratio": 0.06,
        "entry_crossing_bps": 1.2,
        "round_trip_friction_bps": 3.4,
        "fees_known": True,
        "reason_codes": [],
        "legs": {},
    }


class _Cdp:
    def __init__(self, websocket_url: str) -> None:
        self.websocket_url = websocket_url
        self.next_id = 0
        self.events: list[dict[str, Any]] = []

    async def _call(
        self,
        websocket: Any,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.next_id += 1
        request_id = self.next_id
        await websocket.send(
            json.dumps({"id": request_id, "method": method, "params": params or {}})
        )
        while True:
            message = json.loads(await asyncio.wait_for(websocket.recv(), timeout=10))
            if message.get("id") == request_id:
                if "error" in message:
                    raise AssertionError(f"CDP {method} failed: {message['error']}")
                return message.get("result", {})
            self.events.append(message)

    async def _evaluate(self, websocket: Any, expression: str) -> Any:
        result = await self._call(
            websocket,
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        if result.get("exceptionDetails"):
            raise AssertionError(f"browser expression failed: {result['exceptionDetails']}")
        return result["result"].get("value")

    async def run(self, base_url: str) -> dict[str, Any]:
        assert websockets is not None
        async with websockets.connect(self.websocket_url, max_size=10_000_000) as websocket:
            await self._call(websocket, "Runtime.enable")
            await self._call(websocket, "Page.enable")
            await self._call(
                websocket,
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
window.__qaErrors = [];
window.addEventListener('error', event => window.__qaErrors.push(String(event.error || event.message)));
window.addEventListener('unhandledrejection', event => window.__qaErrors.push(String(event.reason)));
const originalConsoleError = console.error;
console.error = (...args) => { window.__qaErrors.push(args.map(String).join(' ')); originalConsoleError(...args); };
"""
                },
            )
            await self._call(
                websocket,
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": 1280,
                    "height": 900,
                    "deviceScaleFactor": 1,
                    "mobile": False,
                },
            )
            await self._call(
                websocket, "Page.navigate", {"url": f"{base_url}/workbench"}
            )
            await self._evaluate(
                websocket,
                """new Promise((resolve, reject) => {
const deadline = Date.now() + 5000;
(function wait() {
  if (document.querySelector('a[href="/workbench/oil"]')) return resolve(true);
  if (Date.now() > deadline) return reject(new Error('dashboard did not render'));
  setTimeout(wait, 40);
})();
})""",
            )
            dashboard = await self._evaluate(
                websocket,
                "({title:document.title,text:document.body.innerText,scroll:[document.documentElement.clientWidth,document.documentElement.scrollWidth]})",
            )
            await self._evaluate(
                websocket, "document.querySelector('a[href=\"/workbench/oil\"]').click(); true"
            )
            await self._evaluate(
                websocket,
                """new Promise((resolve, reject) => {
const deadline = Date.now() + 7000;
(function wait() {
  const content = document.querySelector('#content');
  if (location.pathname === '/workbench/oil' && content && getComputedStyle(content).display !== 'none') return resolve(true);
  if (Date.now() > deadline) return reject(new Error('oil page did not boot'));
  setTimeout(wait, 50);
})();
})""",
            )
            initial = await self._evaluate(
                websocket,
                """({
  sourceOptions: document.querySelector('#source').options.length,
  chartPaths: [...document.querySelectorAll('#chart path.chart-path')].map(path => (path.getAttribute('d') || '').length),
  diagnostics: document.querySelectorAll('#diagnostics article').length,
  executionRows: document.querySelectorAll('#execution-body tr').length,
  healthRows: document.querySelectorAll('#health tr').length,
  modelText: document.querySelector('#model').innerText,
  executionText: document.querySelector('#execution-body').innerText
})""",
            )
            interacted = await self._evaluate(
                websocket,
                """(() => {
const source = document.querySelector('#source');
source.value = 'hyperliquid';
source.dispatchEvent(new Event('change', {bubbles:true}));
document.querySelector('#ranges [data-value="7d"]').click();
document.querySelector('#metrics [data-value="ratio"]').click();
document.querySelector('#directions [data-value="long_wti_short_brent"]').click();
document.querySelector('#sizes [data-value="100"]').click();
return {
  source: source.value,
  range: document.querySelector('#ranges button.on').dataset.value,
  metric: document.querySelector('#metrics button.on').dataset.value,
  direction: document.querySelector('#directions button.on').dataset.value,
  size: document.querySelector('#sizes button.on').dataset.value,
  chartPaths: [...document.querySelectorAll('#chart path.chart-path')].map(path => (path.getAttribute('d') || '').length)
};
})()""",
            )
            await self._call(
                websocket,
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": 390,
                    "height": 844,
                    "deviceScaleFactor": 1,
                    "mobile": False,
                },
            )
            narrow = await self._evaluate(
                websocket,
                """new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve({
  innerWidth,
  documentWidth:[document.documentElement.clientWidth, document.documentElement.scrollWidth],
  bodyWidth:[document.body.clientWidth, document.body.scrollWidth],
  navWidth:[document.querySelector('.nav').clientWidth, document.querySelector('.nav').scrollWidth],
  tableWidths:[...document.querySelectorAll('.table-wrap')].map(item => [item.clientWidth, item.scrollWidth])
}))))""",
            )
            errors = await self._evaluate(websocket, "window.__qaErrors")
            runtime_exceptions = [
                event
                for event in self.events
                if event.get("method") == "Runtime.exceptionThrown"
            ]
            return {
                "dashboard": dashboard,
                "initial": initial,
                "interacted": interacted,
                "narrow": narrow,
                "errors": errors,
                "runtime_exceptions": runtime_exceptions,
            }


@unittest.skipUnless(_chrome_path() and websockets is not None, "Chrome and websockets required")
class OilBrowserTests(unittest.TestCase):
    def test_dashboard_to_oil_workflow_and_narrow_layout(self) -> None:
        rows = [
            _execution_row(direction, size)
            for direction in ("long_brent_short_wti", "long_wti_short_brent")
            for size in (100, 500)
        ]
        dataset = OilDataset(
            generated_at="2026-08-22T00:00:00Z",
            sources=(_series("lighter", 0), _series("hyperliquid", 0.15)),
            execution={
                "sizes_usd": [100, 500],
                "venues": [{"venue": "lighter", "basis": "l2_book", "rows": rows}],
                "limitations": ["HOLDING_FUNDING_UNKNOWN"],
            },
            diagnostics=(
                {
                    "code": "FIXTURE_DIAGNOSTIC",
                    "severity": "info",
                    "title": "浏览器验收诊断",
                    "evidence": ["fixture"],
                    "counter_evidence": [],
                    "limitations": ["browser fixture"],
                    "next_check": "none",
                },
            ),
            raw_manifest={"schema": "oil-raw-manifest-v1", "captures": []},
        )
        app = WorkbenchApp(oil=build_oil_projection(dataset))
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler())
        Thread(target=server.serve_forever, daemon=True).start()
        base_url = f"http://127.0.0.1:{server.server_port}"

        debug_socket = socket.socket()
        debug_socket.bind(("127.0.0.1", 0))
        debug_port = debug_socket.getsockname()[1]
        debug_socket.close()
        chrome_profile = tempfile.TemporaryDirectory()
        chrome = subprocess.Popen(
            [
                str(_chrome_path()),
                "--headless=new",
                "--disable-gpu",
                "--disable-extensions",
                "--no-first-run",
                "--no-default-browser-check",
                f"--remote-debugging-port={debug_port}",
                f"--user-data-dir={chrome_profile.name}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            pages: list[dict[str, Any]] = []
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{debug_port}/json/list", timeout=1
                    ) as response:
                        pages = json.load(response)
                    if any(page.get("type") == "page" for page in pages):
                        break
                except OSError:
                    time.sleep(0.1)
            page = next(page for page in pages if page.get("type") == "page")
            result = asyncio.run(_Cdp(page["webSocketDebuggerUrl"]).run(base_url))
        finally:
            chrome.terminate()
            try:
                chrome.wait(timeout=5)
            except subprocess.TimeoutExpired:
                chrome.kill()
            chrome_profile.cleanup()
            server.shutdown()
            server.server_close()

        self.assertIn("研究操作台", result["dashboard"]["text"])
        self.assertEqual(result["dashboard"]["scroll"][0], result["dashboard"]["scroll"][1])
        self.assertEqual(result["initial"]["sourceOptions"], 2)
        self.assertTrue(all(length > 0 for length in result["initial"]["chartPaths"]))
        self.assertGreaterEqual(result["initial"]["diagnostics"], 1)
        self.assertEqual(result["initial"]["executionRows"], 1)
        self.assertEqual(result["initial"]["healthRows"], 2)
        self.assertIn("Formation UTC", result["initial"]["modelText"])
        self.assertIn("本次形成期拟合", result["initial"]["modelText"])
        self.assertIn("100.0%", result["initial"]["executionText"])
        self.assertEqual(
            result["interacted"],
            {
                "source": "hyperliquid",
                "range": "7d",
                "metric": "ratio",
                "direction": "long_wti_short_brent",
                "size": "100",
                "chartPaths": result["interacted"]["chartPaths"],
            },
        )
        self.assertTrue(all(length > 0 for length in result["interacted"]["chartPaths"]))
        self.assertEqual(result["narrow"]["innerWidth"], 390)
        self.assertEqual(result["narrow"]["documentWidth"], [390, 390])
        self.assertEqual(result["narrow"]["bodyWidth"], [390, 390])
        self.assertGreater(result["narrow"]["navWidth"][1], result["narrow"]["navWidth"][0])
        self.assertTrue(
            any(scroll > client for client, scroll in result["narrow"]["tableWidths"])
        )
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["runtime_exceptions"], [])


if __name__ == "__main__":
    unittest.main()
