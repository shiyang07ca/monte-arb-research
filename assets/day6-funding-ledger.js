(() => {
  "use strict";

  const root = document.querySelector("[data-day6-funding-app]");
  if (!root) return;

  const markets = {
    WTI: {
      label: "WTI",
      marketId: 145,
      rate: 0.0004,
      apiValue: 0.00032286,
      apiDirection: "long",
      index: 74.670,
      quantity: 0.134,
      quantityLabel: "0.134（Day 3 的 $10 纸上数量）",
    },
    BRENTOIL: {
      label: "BRENTOIL",
      marketId: 159,
      rate: 0.0004,
      apiValue: 0.00033548,
      apiDirection: "long",
      index: 79.04,
      quantity: 0.1266,
      quantityLabel: "0.1266（Day 3 的 $10 纸上数量）",
    },
  };

  const $ = (selector) => root.querySelector(selector);
  const money = (value) => `${value >= 0 ? "+" : "−"}$${Math.abs(value).toFixed(8)}`;

  const payerReceiver = (rate, sign) => {
    if (rate === 0) return "资金费为 0";
    const pays = (rate > 0 && sign === 1) || (rate < 0 && sign === -1);
    return pays ? "付款方" : "收款方";
  };

  const renderMarket = () => {
    const market = markets[$("[data-role=market]").value];
    $("[data-role=market-output]").innerHTML = `
      <div class="grid">
        <div class="card"><strong>真实 raw rate</strong><code>${market.rate}</code><span class="small">2026-08-03T00:00:00Z 示例行</span></div>
        <div class="card"><strong>API value</strong><code>${market.apiValue}</code><span class="small">单位和现金流映射仍 unknown</span></div>
        <div class="card"><strong>API direction</strong><code>${market.apiDirection}</code><span class="small">保留观察，不代替仓位方向</span></div>
      </div>
      <div class="callout amber"><strong>${market.label}（market_id=${market.marketId}）</strong><p>历史 funding 时点的 index、账户持仓和实际账本没有在当前公开快照中同时出现，所以真实现金流状态仍是 <code>unknown</code>。</p></div>`;
  };

  const renderLedger = () => {
    const market = markets[$("[data-role=ledger-market]").value];
    const sign = $("[data-role=position]").value === "long" ? 1 : -1;
    const rate = Number($("[data-role=rate]").value);
    const quantity = market.quantity;
    const cashFlow = -(sign * quantity * market.index * rate);
    const status = rate === market.rate ? "使用本地 raw rate；但 index 仍是未对齐的示例输入" : "教学输入：不是历史成交或账户账本";
    $("[data-role=ledger-output]").innerHTML = `
      <div class="grid">
        <div class="card"><strong>仓位符号</strong><code>${sign > 0 ? "+1 long" : "−1 short"}</code></div>
        <div class="card"><strong>纸上基础数量</strong><code>${quantity}</code><span class="small">${market.quantityLabel}</span></div>
        <div class="card"><strong>纸上现金流</strong><code>${money(cashFlow)}</code><span class="small">${payerReceiver(rate, sign)}</span></div>
      </div>
      <div class="callout ${cashFlow < 0 ? "red" : "green"}"><strong>${cashFlow < 0 ? "这一行是付款" : cashFlow > 0 ? "这一行是收款" : "这一行没有资金费现金流"}</strong><p>公式：<code>−position_sign × quantity × multiplier × index × funding_rate</code>。${status}。</p></div>`;
  };

  const checkQuiz = () => {
    const expected = {
      "q-positive": "long-pays",
      "q-negative": "short-pays",
      "q-value": "unknown",
      "q-proof": "ledger",
      "q-price": "index",
    };
    const checks = Object.entries(expected).map(([role, value]) => {
      const node = $(`[data-quiz-role=${role}]`);
      const ok = node.value === value;
      node.classList.toggle("answer-correct", ok);
      node.classList.toggle("answer-wrong", !ok);
      return ok;
    });
    const score = checks.filter(Boolean).length;
    const message = score === 5
      ? "通过：你已经能从 funding rate、仓位方向和 index 组成一条纸上现金流。"
      : "先记住三步：看 rate 正负 → 看仓位 sign → 用 index 计算；API value 先保持 unknown。";
    $("[data-role=quiz-feedback]").innerHTML = `<div class="callout ${score >= 4 ? "green" : "amber"}"><strong>得分：${score}/5</strong><p>${message}</p><p>正确映射：正 funding→多头付款；负 funding→空头付款；value 单位或映射未知→unknown；可验证依据→账户 funding ledger；公式价格→index。</p></div>`;
  };

  $("[data-role=market]").addEventListener("change", renderMarket);
  $("[data-role=ledger-market]").addEventListener("change", renderLedger);
  $("[data-role=position]").addEventListener("change", renderLedger);
  $("[data-role=rate]").addEventListener("input", renderLedger);
  $("[data-role=quiz-submit]").addEventListener("click", checkQuiz);
  renderMarket();
  renderLedger();
})();
