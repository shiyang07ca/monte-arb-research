(() => {
  "use strict";

  const root = document.querySelector("[data-day5-roll-app]");
  if (!root) return;

  const zones = {
    WTI: {
      label: "WTI",
      marketId: 145,
      rollTime: "17:30 ET",
      close: "17:00–18:00 ET",
      utcRoll: "21:30 UTC（2026 年夏令时示例）",
      rollClass: "WTI 的展期窗口",
    },
    BRENTOIL: {
      label: "BRENTOIL",
      marketId: 159,
      rollTime: "19:00 ET",
      close: "18:00–20:00 ET",
      utcRoll: "23:00 UTC（2026 年夏令时示例）",
      rollClass: "BRENTOIL 的展期窗口",
    },
  };

  const stage = (front) => {
    if (front === 100) return "展期前：100% 当前月";
    if (front === 80) return "第 1 天：80% 当前月 / 20% 下月";
    if (front === 60) return "第 2 天：60% 当前月 / 40% 下月";
    if (front === 40) return "第 3 天：40% 当前月 / 60% 下月";
    if (front === 20) return "第 4 天：20% 当前月 / 80% 下月";
    if (front === 0) return "展期后：100% 下月";
    return "未知展期阶段";
  };

  const $ = (selector) => root.querySelector(selector);

  const renderZone = () => {
    const zone = zones[$("[data-role=zone]").value];
    $("[data-role=zone-output]").innerHTML = `
      <div class="grid">
        <div class="card"><strong>每日切换时间</strong><code>${zone.rollTime}</code><span class="small">${zone.utcRoll}</span></div>
        <div class="card"><strong>底层关闭窗口</strong><code>${zone.close}</code><span class="small">关闭不是“Lighter 一定不可交易”的证明</span></div>
        <div class="card"><strong>研究标签</strong><code>${zone.rollClass}</code><span class="small">保留标签，不静默删除</span></div>
      </div>
      <div class="callout amber"><strong>${zone.label}（market_id=${zone.marketId}）</strong><p>先把美国东部时间作为官方规则的主时区；只有完成时区转换后，才能与 UTC candle timestamp 对齐。</p></div>`;
  };

  const renderSchedule = () => {
    const front = Number.parseInt($("[data-role=front-weight]").value, 10);
    const zone = zones[$("[data-role=schedule-zone]").value];
    const valid = [80, 60, 40, 20, 0].includes(front);
    if (!valid) {
      $("[data-role=schedule-output]").innerHTML = `<div class="callout red">请选择官方示例中的展期阶段。</div>`;
      return;
    }
    $("[data-role=schedule-output]").innerHTML = `
      <div class="grid">
        <div class="card"><strong>${zone.label} 当前月权重</strong><code>${front}%</code></div>
        <div class="card"><strong>${zone.label} 下月权重</strong><code>${100 - front}%</code></div>
      </div>
      <div class="callout blue"><strong>${stage(front)}</strong><p>这描述的是底层期货价格组成比例，不是 WTI/BRENTOIL 基础数量比例，也不是两腿对冲比率。</p></div>`;
  };

  const checkQuiz = () => {
    const expected = {"q-time": "et", "q-utc": "2130", "q-difference": "different", "q-sample": "before", "q-action": "tag"};
    const checks = Object.entries(expected).map(([role, value]) => {
      const node = $(`[data-quiz-role=${role}]`);
      const ok = node.value === value;
      node.classList.toggle("answer-correct", ok);
      node.classList.toggle("answer-wrong", !ok);
      return ok;
    });
    const score = checks.filter(Boolean).length;
    const message = score === 5
      ? "通过：你已经能把官方 ET 规则、UTC 数据、两腿错位和样本标签连接起来。"
      : "先回到三步：先确认官方时区，再转换 UTC，最后保留状态标签而不是静默删除异常。";
    $("[data-role=quiz-feedback]").innerHTML = `<div class="callout ${score >= 4 ? "green" : "amber"}"><strong>得分：${score}/5</strong><p>${message}</p><p>正确映射：规则主时区→ET；2026 夏令时 17:30 ET→21:30 UTC；两腿时间不同→价格过程不可直接比较；旧样本在展期前结束→不能证明展期状态；异常→打标签并分层。</p></div>`;
  };

  $("[data-role=zone]").addEventListener("change", renderZone);
  ["schedule-zone", "front-weight"].forEach((role) => $("[data-role=" + role + "]").addEventListener("input", renderSchedule));
  $("[data-role=quiz-submit]").addEventListener("click", checkQuiz);
  renderZone();
  renderSchedule();
})();
