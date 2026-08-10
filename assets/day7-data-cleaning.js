(() => {
  "use strict";

  const root = document.querySelector("[data-day7-cleaning-app]");
  if (!root) return;

  const summary = {
    WTI: { candles: 500, fundings: 750, paired: 500, fundingOnly: 250, jumps: 1 },
    BRENTOIL: { candles: 500, fundings: 750, paired: 500, fundingOnly: 250, jumps: 0 },
    outputRows: 1500,
    uniqueTimestamps: 750,
    split: { train: 450, validation: 150, test: 150 },
  };

  const $ = (selector) => root.querySelector(selector);

  function renderSnapshot() {
    const symbol = $("[data-role=market]").value;
    const item = summary[symbol];
    $("[data-role=snapshot-output]").innerHTML = `
      <div class="grid">
        <div class="card"><strong>${symbol} candles</strong><code>${item.candles}</code><span class="small">当前 API 快照上限内</span></div>
        <div class="card"><strong>${symbol} fundings</strong><code>${item.fundings}</code><span class="small">多出 ${item.fundingOnly} 条 candle 之外的 funding 行</span></div>
        <div class="card"><strong>两者同一 timestamp</strong><code>${item.paired}</code><span class="small">可进入 combined pair 审计</span></div>
      </div>
      <div class="callout ${item.jumps ? "amber" : "green"}"><strong>异常跳点：${item.jumps} 行</strong><p>${item.jumps ? "保留原行并加 close_jump_gt_5pct 标记；异常不是自动删除理由。" : "当前市场没有超过 5% 的 close 跳点，但规则仍然保留在脚本中。"}</p></div>`;
  }

  function classify() {
    const candle = $("[data-role=candle]").value === "yes";
    const funding = $("[data-role=funding]").value === "yes";
    const valid = $("[data-role=valid]").value === "yes";
    const duplicate = $("[data-role=duplicate]").value === "yes";
    const jump = $("[data-role=jump]").value === "yes";
    const reasons = [];
    if (!candle) reasons.push("missing_candle");
    if (!funding) reasons.push("missing_funding");
    if (!valid) reasons.push("invalid_numeric_or_non_positive_price");
    if (duplicate) reasons.push("duplicate_timestamp_explicit_review");
    const combined = candle && funding && valid && !duplicate;
    const status = combined ? (jump ? "eligible_with_jump_flag" : "eligible") : "not_eligible_or_partial";
    $("[data-role=classifier-output]").innerHTML = `
      <div class="card"><strong>输出状态</strong><code>${status}</code><p>${reasons.length ? `原因码：<code>${reasons.join(" | ")}</code>` : "没有阻断原因。"}</p><p>${jump ? "跳点只产生质量标记，不改变原始记录，也不自动把它从统计中删除。" : "先看准入字段，再决定这行能否进入对应统计。"}</p></div>`;
  }

  function checkQuiz() {
    const expected = {
      "q-missing": "flag",
      "q-duplicate": "review",
      "q-jump": "keep",
      "q-split": "time",
      "q-raw": "preserve",
    };
    const checks = Object.entries(expected).map(([role, value]) => {
      const node = $(`[data-quiz-role="${role}"]`);
      const ok = node.value === value;
      node.classList.toggle("answer-correct", ok);
      node.classList.toggle("answer-wrong", !ok);
      return ok;
    });
    const score = checks.filter(Boolean).length;
    $("[data-role=quiz-feedback]").innerHTML = `<div class="callout ${score === 5 ? "green" : "amber"}"><strong>得分：${score}/5</strong><p>${score === 5 ? "通过：你已经能把原始数据、质量标记和统计准入分开。" : "再记一遍：保留原始值、标记异常、按时间切分，不用插值或静默删除制造干净结果。"}</p><p>正确原则：缺失→标记；重复→显式复核；跳点→保留并标记；切分→按时间；原始 JSON→不覆盖。</p></div>`;
  }

  $("[data-role=market]").addEventListener("change", renderSnapshot);
  ["candle", "funding", "valid", "duplicate", "jump"].forEach((role) => $("[data-role=${role}]").addEventListener("change", classify));
  $("[data-role=quiz-submit]").addEventListener("click", checkQuiz);
  renderSnapshot();
  classify();
})();
