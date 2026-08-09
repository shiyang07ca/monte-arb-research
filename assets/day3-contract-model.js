(() => {
  "use strict";

  const root = document.querySelector("[data-day3-contract-app]");
  if (!root) return;

  const markets = {
    WTI: {
      label: "WTI",
      marketId: 145,
      price: 74.692,
      minBase: 0.1,
      minQuote: 10,
      sizeDecimals: 3,
      priceDecimals: 3,
      multiplier: 1,
      quoteMultiplier: 1,
      defaultInitialMarginFraction: 500,
      maintenanceMarginFraction: 300,
    },
    BRENTOIL: {
      label: "BRENTOIL",
      marketId: 159,
      price: 79.03,
      minBase: 0.08,
      minQuote: 10,
      sizeDecimals: 4,
      priceDecimals: 2,
      multiplier: 1,
      quoteMultiplier: 1,
      defaultInitialMarginFraction: 666,
      maintenanceMarginFraction: 300,
    },
  };

  const $ = (selector) => root.querySelector(selector);
  const marketSelect = $("[data-role=market]");
  const targetInput = $("[data-role=target]");
  const calculatorOutput = $("[data-role=calculator-output]");
  const equalQuantityOutput = $("[data-role=equal-quantity-output]");
  const quizButton = $("[data-role=quiz-submit]");
  const quizFeedback = $("[data-role=quiz-feedback]");

  const number = (value, digits = 6) => {
    if (!Number.isFinite(value)) return "—";
    return value.toLocaleString("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: digits,
    });
  };

  const quantityText = (value, decimals) => value.toFixed(decimals);

  const calculate = (market, target) => {
    const step = 10 ** -market.sizeDecimals;
    const unconstrained = target / (market.price * market.multiplier * market.quoteMultiplier);
    const minUnits = Math.ceil((market.minBase / step) - 1e-9);
    const targetUnits = Math.ceil((unconstrained / step) - 1e-9);
    const units = Math.max(minUnits, targetUnits);
    const quantity = units * step;
    const notional = quantity * market.price * market.multiplier * market.quoteMultiplier;
    return {
      step,
      unconstrained,
      quantity,
      notional,
      meetsMinBase: quantity + 1e-12 >= market.minBase,
      meetsMinQuote: notional + 1e-12 >= market.minQuote,
    };
  };

  const renderCalculator = () => {
    const market = markets[marketSelect.value];
    const target = Math.max(Number.parseFloat(targetInput.value) || 0, 0);
    const result = calculate(market, target);
    const legal = result.meetsMinBase && result.meetsMinQuote && target > 0;
    calculatorOutput.innerHTML = `
      <div class="grid">
        <div class="card"><strong>理论数量</strong><code>${number(result.unconstrained, 8)}</code><span class="small">目标金额 ÷ 价格 ÷ 乘数</span></div>
        <div class="card"><strong>向上取整后数量</strong><code>${quantityText(result.quantity, market.sizeDecimals)}</code><span class="small">步长 ${quantityText(result.step, market.sizeDecimals)}</span></div>
        <div class="card"><strong>实际纸上报价金额</strong><code>$${number(result.notional, 8)}</code><span class="small">不是历史成交结果</span></div>
      </div>
      <div class="callout ${legal ? "green" : "red"}">
        <strong>${legal ? "纸上约束通过" : "请先输入正的目标金额"}</strong>
        <ul>
          <li>基础数量：${quantityText(result.quantity, market.sizeDecimals)} ≥ ${market.minBase.toFixed(market.sizeDecimals)} ${result.meetsMinBase ? "✓" : "✗"}</li>
          <li>报价金额：$${number(result.notional, 8)} ≥ $${number(market.minQuote, 2)} ${result.meetsMinQuote ? "✓" : "✗"}</li>
          <li>市场：${market.label}（market_id=${market.marketId}，${market.marketType || "perp"}）</li>
        </ul>
        <span class="badge paper">PAPER FEASIBILITY ONLY</span>
      </div>`;
  };

  const renderEqualQuantity = () => {
    const quantity = Number.parseFloat($("[data-role=equal-quantity]").value) || 0;
    const wti = quantity * markets.WTI.price;
    const brent = quantity * markets.BRENTOIL.price;
    equalQuantityOutput.innerHTML = `
      <table>
        <thead><tr><th>腿</th><th>基础数量</th><th>纸上报价金额</th></tr></thead>
        <tbody>
          <tr><td>WTI</td><td><code>${number(quantity, 6)}</code></td><td><code>$${number(wti, 6)}</code></td></tr>
          <tr><td>BRENTOIL</td><td><code>${number(quantity, 6)}</code></td><td><code>$${number(brent, 6)}</code></td></tr>
        </tbody>
      </table>
      <div class="callout amber">
        相同基础数量不代表相同报价金额。这里的差异来自两个市场价格不同；这也还没有回答经济上的对冲比率应该是多少。
      </div>`;
  };

  const closeEnough = (actual, expected, tolerance = 0.00001) => Math.abs(actual - expected) <= tolerance;

  const checkQuiz = () => {
    const checks = [];
    const answer = (role) => $("[data-quiz-role=" + role + "]");
    const q50Wti = Number.parseFloat(answer("q50-wti").value);
    const q50Brent = Number.parseFloat(answer("q50-brent").value);
    checks.push({ node: answer("q50-wti"), ok: closeEnough(q50Wti, 0.67, 0.0005) });
    checks.push({ node: answer("q50-brent"), ok: closeEnough(q50Brent, 0.6327, 0.00005) });
    checks.push({ node: answer("equal-notional").value, ok: answer("equal-notional").value === "no" });
    checks.push({ node: answer("margin-claim").value, ok: answer("margin-claim").value === "cannot" });

    checks.forEach(({ node, ok }) => {
      const element = node instanceof HTMLElement ? node : answer(node);
      if (element) element.classList.toggle("answer-correct", ok);
      if (element) element.classList.toggle("answer-wrong", !ok);
    });

    const score = checks.filter((item) => item.ok).length;
    const messages = [
      score >= 3 ? "通过：你已经抓住了 Day 3 的数量模型。" : "先不要背答案，重新检查价格、步长和最小名义金额。",
      "$50 的纸上数量：WTI = 0.670，BRENTOIL = 0.6327。",
      "相同数量 0.650 时，WTI 约 $48.5498，BRENTOIL 约 $51.3695。",
      "公共快照的保证金字段不能单独证明账户实际保证金、组合保证金或清算路径。",
    ];
    quizFeedback.innerHTML = `<div class="callout ${score >= 3 ? "green" : "amber"}"><strong>得分：${score}/4</strong><p>${messages.join(" ")}</p></div>`;
  };

  marketSelect.addEventListener("change", renderCalculator);
  targetInput.addEventListener("input", renderCalculator);
  $("[data-role=equal-quantity]").addEventListener("input", renderEqualQuantity);
  quizButton.addEventListener("click", checkQuiz);

  renderCalculator();
  renderEqualQuantity();
})();
