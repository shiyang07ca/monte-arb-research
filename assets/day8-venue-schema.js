(() => {
  "use strict";

  const root = document.querySelector("[data-day8-venue-app]");
  if (!root) return;

  const $ = (selector) => root.querySelector(selector);

  const venues = {
    lighter: {
      name: "Lighter WTI",
      market: "market_id=145",
      rows: [
        { side: "bid", price: 82.008, size: 109.744, note: "订单级 remaining_base_amount" },
        { side: "bid", price: 82.007, size: 0.635, note: "初始 3.158，已部分成交" },
        { side: "ask", price: 82.014, size: 0.635, note: "订单级 remaining_base_amount" },
        { side: "ask", price: 82.015, size: 109.776, note: "订单级 remaining_base_amount" },
      ],
      timestamp: "无公共快照时间",
      precision: "price 3 / size 3",
      ref: "lab/data/day8_raw/lighter_wti_book_ok.json",
    },
    binance: {
      name: "Binance BTCUSDT",
      market: "BTCUSDT",
      rows: [
        { side: "bid", price: 64026.4, size: 14.774, note: "聚合档" },
        { side: "bid", price: 64026.3, size: 0.038, note: "聚合档" },
        { side: "ask", price: 64026.5, size: 4.679, note: "聚合档" },
        { side: "ask", price: 64026.6, size: 0.007, note: "聚合档" },
      ],
      timestamp: "E 消息输出时间（ms）",
      precision: "price 2 / qty 3",
      ref: "lab/data/day8_raw/binance_book.json",
    },
    hyperliquid: {
      name: "Hyperliquid BTC",
      market: "BTC",
      rows: [
        { side: "bid", price: 64033.0, size: 22.36121, note: "聚合档，n=48" },
        { side: "bid", price: 64032.0, size: 2.97895, note: "聚合档，n=10" },
        { side: "ask", price: 64034.0, size: 4.80057, note: "聚合档，n=10" },
        { side: "ask", price: 64037.0, size: 1.42083, note: "聚合档，n=3" },
      ],
      timestamp: "time（ms）",
      precision: "szDecimals=5",
      ref: "lab/data/day8_raw/hyperliquid_l2book.json",
    },
  };

  const fmt = (value) => (value === "" ? "—" : value);

  function renderVenue() {
    const key = $("[data-role=venue]").value;
    const venue = venues[key];
    const rows = venue.rows.map((row) => {
      const orderLevel = row.note.startsWith("订单级");
      const badge = orderLevel
        ? '<span class="badge paper">订单级</span>'
        : '<span class="badge pass">聚合档</span>';
      return `<tr><td>${row.side}</td><td><code>${row.price}</code></td><td><code>${row.size}</code></td><td>${badge}<span class="small"> ${row.note}</span></td></tr>`;
    }).join("");
    $("[data-role=venue-output]").innerHTML = `
      <div class="grid">
        <div class="card"><strong>${venue.name}</strong><code>${venue.market}</code></div>
        <div class="card"><strong>时间语义</strong><code>${venue.timestamp}</code></div>
        <div class="card"><strong>精度</strong><code>${venue.precision}</code></div>
      </div>
      <table>
        <thead><tr><th>side</th><th>price</th><th>size</th><th>语义</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="small">证据文件：<code>${venue.ref}</code></p>
      <div class="callout ${key === "lighter" ? "amber" : "green"}">
        <strong>${key === "lighter" ? "注意" : "一致"}</strong>
        <p>${key === "lighter"
          ? "Lighter 的档位是订单级视图：一个价格档可能只显示剩余数量，并且订单可以被部分成交。Binance/Hyperliquid 返回的是聚合档。"
          : "该场所返回聚合档：每个价格档汇总了该价位的所有订单数量。"}</p>
      </div>`;
  }

  const quiz = {
    "q-level": "order-level",
    "q-ts": "missing",
    "q-limit": "400",
    "q-precision": "decimals",
    "q-funding": "unit",
  };

  function checkQuiz() {
    const checks = Object.entries(quiz).map(([role, value]) => {
      const node = $(`[data-quiz-role="${role}"]`);
      const ok = node.value === value;
      node.classList.toggle("answer-correct", ok);
      node.classList.toggle("answer-wrong", !ok);
      return ok;
    });
    const score = checks.filter(Boolean).length;
    const message = score === 5
      ? "通过：你能把三个场所的盘口放进同一张表，同时保留语义差异。"
      : "再记一次：档位语义（订单级 vs 聚合）、时间戳（缺失 vs E vs time）、limit 规则、精度字段和 funding 时间单位都不能混为一谈。";
    $("[data-role=quiz-feedback]").innerHTML = `<div class="callout ${score >= 4 ? "green" : "amber"}"><strong>得分：${score}/5</strong><p>${message}</p><p>正确映射：Lighter→订单级；Lighter 盘口无公共时间戳→missing；Lighter orderBookOrders 只传 market_id→400；精度→各自字段不同；funding 时间→秒 vs 毫秒。</p></div>`;
  }

  $("[data-role=venue]").addEventListener("change", renderVenue);
  $("[data-role=quiz-submit]").addEventListener("click", checkQuiz);
  renderVenue();
})();
