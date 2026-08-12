(() => {
  "use strict";

  const root = document.querySelector("[data-day9-param-app]");
  if (!root) return;

  const $ = (selector) => root.querySelector(selector);

  // Real diff from lab/data/day9_parameter_diff.json (2026-08-12 capture
  // vs 2026-08-05 snapshot). Contract fields did not change; state did.
  const markets = {
    WTI: {
      name: "WTI",
      market_id: 145,
      state: [
        { field: "mark_price", old: "74.692", now: "82.999" },
        { field: "index_price", old: "74.670", now: "83.065" },
        { field: "daily_quote_token_volume", old: "6,998,416", now: "16,683,935" },
        { field: "daily_trades_count", old: "9,100", now: "19,587" },
        { field: "open_interest", old: "74,515", now: "65,172" },
      ],
      contract: {
        "初始保证金 IMR": "500（约 5 倍杠杆）",
        "维持保证金 MMR": "300",
        "最小基础数量": "0.100",
        "价格/数量小数位": "3 / 3",
        "maker/taker 费率": "0 / 0",
      },
    },
    BRENTOIL: {
      name: "BRENTOIL",
      market_id: 159,
      state: [
        { field: "mark_price", old: "79.03", now: "87.96" },
        { field: "index_price", old: "79.04", now: "88.12" },
        { field: "daily_quote_token_volume", old: "1,383,836", now: "6,292,402" },
        { field: "daily_trades_count", old: "8,188", now: "8,273" },
        { field: "open_interest", old: "12,390", now: "62,874" },
      ],
      contract: {
        "初始保证金 IMR": "666",
        "维持保证金 MMR": "300",
        "最小基础数量": "0.0800",
        "价格/数量小数位": "2 / 4",
        "maker/taker 费率": "0 / 0",
      },
    },
  };

  const fmt = (value) => (value === "" ? "—" : value);

  function renderMarket() {
    const key = $("[data-role=market]").value;
    const m = markets[key];
    const stateRows = m.state.map((row) => {
      const changed = row.old !== row.now;
      return `<tr><td><code>${row.field}</code></td><td>${row.old}</td><td>${row.now}</td><td>${changed ? '<span class="badge amber">变化</span>' : '<span class="badge pass">不变</span>'}</td></tr>`;
    }).join("");
    const contractRows = Object.entries(m.contract).map(([k, v]) =>
      `<tr><td>${k}</td><td colspan="3"><code>${v}</code>（7 天内未变）</td></tr>`
    ).join("");
    $("[data-role=market-output]").innerHTML = `
      <div class="grid">
        <div class="card"><strong>${m.name}</strong><code>market_id=${m.market_id}</code></div>
        <div class="card"><strong>证据</strong><code>lab/data/day9_raw/orderBookDetails_${m.market_id}.json</code></div>
      </div>
      <h3>市场状态（7 天对比，真实变化）</h3>
      <table>
        <thead><tr><th>字段</th><th>2026-08-05</th><th>2026-08-12</th><th>判断</th></tr></thead>
        <tbody>${stateRows}</tbody>
      </table>
      <h3>合约参数（决定能不能下单）</h3>
      <table>
        <thead><tr><th>参数</th><th colspan="3">值</th></tr></thead>
        <tbody>${contractRows}</tbody>
      </table>
      <div class="callout green"><strong>本次核心发现</strong>
        <p>合约参数（杠杆、精度、最小单、费率）7 天内没有变化；市场状态（价格、成交量、持仓量）大幅变化。规则决定「能不能下单」，状态决定「有没有机会」——两者必须分开看。</p>
      </div>`;
  }

  // Field classifier: contract-level vs state-level.
  const classifier = [
    { field: "default_initial_margin_fraction", answer: "contract", why: "初始保证金比例，决定杠杆和能开多少仓位" },
    { field: "mark_price", answer: "state", why: "当前标记价格，每分钟都在变" },
    { field: "min_base_amount", answer: "contract", why: "最小下单数量，交易所规则，稳定不变" },
    { field: "open_interest", answer: "state", why: "当前未平仓合约数量，随交易变化" },
    { field: "taker_fee", answer: "contract", why: "吃单手续费率，属于交易所费率规则" },
    { field: "daily_trades_count", answer: "state", why: "当日成交笔数，属于市场活跃度" },
  ];

  function renderClassifier() {
    const items = classifier.map((item, index) => `
      <div class="card">
        <code>${item.field}</code>
        <select data-classify-role="c${index}">
          <option value="">请选择…</option>
          <option value="contract">合约级（决定能不能下单）</option>
          <option value="state">状态级（决定有没有机会）</option>
        </select>
        <span data-classify-why="w${index}"></span>
      </div>`).join("");
    $("[data-role=classifier]").innerHTML = items;
  }

  function checkClassifier() {
    let correct = 0;
    classifier.forEach((item, index) => {
      const select = $(`[data-classify-role="c${index}"]`);
      const why = $(`[data-classify-why="w${index}"]`);
      const ok = select.value === item.answer;
      select.classList.toggle("answer-correct", ok);
      select.classList.toggle("answer-wrong", !ok);
      why.innerHTML = ok ? `<span class="badge pass">✓ 正确</span> <span class="small">${item.why}</span>` : `<span class="badge amber">✗</span>`;
      if (ok) correct += 1;
    });
    $("[data-role=classifier-feedback]").innerHTML = `<div class="callout ${correct === classifier.length ? "green" : "amber"}"><strong>分类得分：${correct}/${classifier.length}</strong><p>合约级字段是交易所规则（杠杆、精度、最小单、费率），决定能不能下单；状态级字段是市场实时数据（价格、成交量、持仓量），决定有没有机会。</p></div>`;
  }

  const quiz = {
    "q-matrix": "snapshot",
    "q-changed": "state",
    "q-contract": "unchanged",
    "q-brent": "per-trade",
    "q-oi": "need-more",
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
      ? "通过：你分得清「合约规则快照」和「市场状态快照」，并且会用真实数据复核参数。"
      : "再记一次：旧参数矩阵只是 2026-08-05 的快照；合约规则决定能不能下单，市场状态决定有没有机会；两者都要带时间戳重新核验。";
    $("[data-role=quiz-feedback]").innerHTML = `<div class="callout ${score >= 4 ? "green" : "amber"}"><strong>得分：${score}/5</strong><p>${message}</p></div>`;
  }

  $("[data-role=market]").addEventListener("change", renderMarket);
  $("[data-role=classifier-submit]").addEventListener("click", checkClassifier);
  $("[data-role=quiz-submit]").addEventListener("click", checkQuiz);
  renderClassifier();
  renderMarket();
})();
