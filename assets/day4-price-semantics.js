(() => {
  "use strict";

  const root = document.querySelector("[data-day4-price-app]");
  if (!root) return;

  const markets = {
    WTI: {
      label: "WTI",
      marketId: 145,
      mark: 74.692,
      index: 74.670,
      lastTrade: 74.677,
    },
    BRENTOIL: {
      label: "BRENTOIL",
      marketId: 159,
      mark: 79.03,
      index: 79.04,
      lastTrade: 79.01,
    },
  };

  const scenarios = {
    immediateBuy: {
      answer: "ask",
      title: "立即买入",
      reason: "立即买入要主动吃卖方流动性，保守估计使用 ask；还需要足够 ask 深度，不能只看一个价格。",
    },
    immediateSell: {
      answer: "bid",
      title: "立即卖出",
      reason: "立即卖出要主动吃买方流动性，保守估计使用 bid；还需要足够 bid 深度，不能只看一个价格。",
    },
    liquidation: {
      answer: "mark",
      title: "保证金/未实现 PnL",
      reason: "mark 用于公平价格、未实现 PnL 和清算相关语义；它不是你可以直接成交的价格。",
    },
    historicalWindow: {
      answer: "candleClose",
      title: "固定时间窗口历史描述",
      reason: "固定时间窗口用 candle_close 描述该窗口；它是聚合观察值，不等于当下 ask 或 bid。",
    },
    externalReference: {
      answer: "oracle",
      title: "外部价格源观察",
      reason: "oracle_price 是外部价格源输入/观察，不是交易所盘口成交价；当前本地快照没有直接提供它。",
    },
  };

  const $ = (selector) => root.querySelector(selector);
  const number = (value, digits = 6) => Number.isFinite(value)
    ? value.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: digits })
    : "unknown";

  const renderSnapshot = () => {
    const market = markets[$("[data-role=snapshot-market]").value];
    const markGap = market.mark - market.index;
    const tradeGap = market.lastTrade - market.index;
    $("[data-role=snapshot-output]").innerHTML = `
      <div class="grid">
        <div class="card"><strong>mark − index</strong><code>${number(markGap, 6)}</code><span class="small">描述性快照差异，不是可成交 PnL</span></div>
        <div class="card"><strong>last trade − index</strong><code>${number(tradeGap, 6)}</code><span class="small">最近成交快照与 index 的差异</span></div>
        <div class="card"><strong>缺失字段</strong><code>oracle / bid / ask / mid</code><span class="small">应保持 unknown，不能自行插值</span></div>
      </div>
      <div class="callout amber"><strong>${market.label}（market_id=${market.marketId}）</strong><p>mark=${market.mark}，index=${market.index}，last_trade=${market.lastTrade}。这些数值来自一次只读市场详情快照，不能证明历史连续过程或未来成交。</p></div>`;
  };

  const renderEma = () => {
    const previous = Number.parseFloat($("[data-role=ema-previous]").value);
    const impact = Number.parseFloat($("[data-role=ema-impact]").value);
    const delta = Number.parseFloat($("[data-role=ema-delta]").value);
    const tau = Number.parseFloat($("[data-role=ema-tau]").value);
    if (![previous, impact, delta, tau].every(Number.isFinite) || tau <= 0 || delta < 0) {
      $("[data-role=ema-output]").innerHTML = `<div class="callout red">请输入有效的正数参数。</div>`;
      return;
    }
    const alpha = 1 - Math.exp(-delta / tau);
    const next = alpha * impact + (1 - alpha) * previous;
    $("[data-role=ema-output]").innerHTML = `
      <div class="grid">
        <div class="card"><strong>alpha</strong><code>${number(alpha, 8)}</code><span class="small">1 − exp(−Δt / τ)</span></div>
        <div class="card"><strong>下一步 EMA</strong><code>${number(next, 8)}</code><span class="small">比 impact 更平滑</span></div>
      </div>
      <div class="callout blue"><p><code>EMA_next = alpha × impact + (1 − alpha) × EMA_previous</code>。τ 越小，价格对新的 impact 越敏感；τ 越大，反应越慢。</p></div>`;
  };

  const renderExecutionPnl = () => {
    const direction = $("[data-role=position-direction]").value;
    const entry = Number.parseFloat($("[data-role=position-entry]").value);
    const mark = Number.parseFloat($("[data-role=position-mark]").value);
    const bid = Number.parseFloat($("[data-role=position-bid]").value);
    const ask = Number.parseFloat($("[data-role=position-ask]").value);
    const quantity = Number.parseFloat($("[data-role=position-quantity]").value);
    if (![entry, mark, bid, ask, quantity].every(Number.isFinite) || quantity < 0) {
      $("[data-role=position-output]").innerHTML = `<div class="callout red">请输入有效的价格和数量。</div>`;
      return;
    }
    const signed = direction === "long" ? quantity : -quantity;
    const unrealized = (mark - entry) * signed;
    const executable = direction === "long" ? (bid - entry) * quantity : (entry - ask) * quantity;
    const difference = executable - unrealized;
    const closePrice = direction === "long" ? bid : ask;
    $("[data-role=position-output]").innerHTML = `
      <table><thead><tr><th>结果</th><th>数值</th><th>价格语义</th></tr></thead>
      <tbody>
        <tr><td>按 mark 的未实现 PnL</td><td><code>$${number(unrealized, 6)}</code></td><td>估值/风险语义</td></tr>
        <tr><td>立即平仓的纸上 PnL</td><td><code>$${number(executable, 6)}</code></td><td>${direction === "long" ? "卖出用 bid" : "买回用 ask"}</td></tr>
        <tr><td>两者差异</td><td><code>$${number(difference, 6)}</code></td><td>不含手续费、funding、深度和延迟</td></tr>
      </tbody></table>
      <div class="callout ${Math.abs(difference) < 1e-9 ? "green" : "amber"}"><strong>平仓参考价：${closePrice}</strong><p>如果只用 mark 看结果，可能把“估值上的 PnL”误认为“现在可实现的现金 PnL”。</p></div>`;
  };

  const checkQuiz = () => {
    const answer = (role) => $(`[data-quiz-role=${role}]`);
    const checks = [
      ["q-buy", "ask"],
      ["q-sell", "bid"],
      ["q-margin", "mark"],
      ["q-missing", "unknown"],
      ["q-stale", "ema"],
    ].map(([role, expected]) => {
      const node = answer(role);
      const ok = node.value === expected;
      node.classList.toggle("answer-correct", ok);
      node.classList.toggle("answer-wrong", !ok);
      return ok;
    });
    const score = checks.filter(Boolean).length;
    const feedback = score === 5
      ? "通过：你已经能把价格字段和研究问题匹配起来。"
      : "先不要背答案，逐题问自己：这个价格是估值、外部基准、历史观察，还是现在真的能成交？";
    $("[data-role=quiz-feedback]").innerHTML = `<div class="callout ${score >= 4 ? "green" : "amber"}"><strong>得分：${score}/5</strong><p>${feedback}</p><p>正确映射：立即买入→ask；立即卖出→bid；保证金/未实现 PnL→mark；字段不存在→unknown；oracle stale 后内部平滑价格→EMA。</p></div>`;
  };

  $("[data-role=snapshot-market]").addEventListener("change", renderSnapshot);
  ["ema-previous", "ema-impact", "ema-delta", "ema-tau"].forEach((role) => $("[data-role=" + role + "]").addEventListener("input", renderEma));
  ["position-direction", "position-entry", "position-mark", "position-bid", "position-ask", "position-quantity"].forEach((role) => $("[data-role=" + role + "]").addEventListener("input", renderExecutionPnl));
  $("[data-role=quiz-submit]").addEventListener("click", checkQuiz);
  renderSnapshot();
  renderEma();
  renderExecutionPnl();
})();
