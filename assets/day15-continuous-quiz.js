/* Day 15 interaction logic. Reads the DAY15 data global (assets/day15-continuous-data.js). */
(() => {
  const D = window.DAY15;
  if (!D) {
    document.getElementById("session-id").textContent = "数据文件缺失";
    return;
  }
  const fmt = (v, digits = 2) => (typeof v === "number" ? v.toFixed(digits) : v);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function output(id, html, state) {
    const node = document.getElementById(id);
    node.innerHTML = html;
    if (state) {
      node.classList.remove("good", "bad");
      node.classList.add(state);
    }
  }

  document.getElementById("session-id").textContent = D.session_id;

  // ---- 真实基线 ----
  document.getElementById("show-baseline").addEventListener("click", () => {
    const rows = D.baselines.map((b) => `<tr>
      <td><code>${esc(b.label || b.market)}</code></td><td>${esc(b.venue)}</td>
      <td>${fmt(b.n_events, 0)}</td>
      <td>${fmt(b.span_s, 0)} s</td>
      <td>${fmt(b.interarrival_median_s, 2)} s</td>
      <td>${fmt(b.spread_median_bps, 2)}</td>
      <td>${fmt(b.spread_p95_bps, 2)}</td>
      <td>${fmt(b.depth_top1_median, 1)}</td>
      <td>${fmt(b.ret_10s_std_bps, 2)}</td>
      <td>${b.silent_gap_count}</td></tr>`).join("");
    output("baseline-output",
      `<div class="table-scroll"><table><thead><tr><th>市场</th><th>场所</th><th>事件数</th><th>覆盖</th><th>更新间隔中位</th><th>价差中位 bps</th><th>价差 p95 bps</th><th>档1深度中位</th><th>10s 波动 bps</th><th>静默缺口</th></tr></thead><tbody>${rows}</tbody></table></div>
       <p><strong>读法：</strong>更新间隔中位数决定"5 秒价差"对该市场意味着什么；价差 p95 与中位数的距离决定该市场自己的"异常"尺度；静默缺口数告诉你这段数据里有多少时间管道没有发言。</p>`,
      "good");
  });

  // ---- 数据健康 ----
  document.getElementById("show-health").addEventListener("click", () => {
    if (!D.health_events.length) {
      output("health-output", "本次会话没有健康事件（连接正常，无静默缺口、无解析失败）。", "good");
      return;
    }
    const rows = D.health_events.map((h) => `<tr>
      <td>${esc(h.at_utc)}</td><td>${esc(h.venue)}</td><td><code>${esc(h.kind)}</code></td>
      <td>${esc(JSON.stringify(h.detail || {}))}</td></tr>`).join("");
    output("health-output",
      `<div class="table-scroll"><table><thead><tr><th>时间 UTC</th><th>场所</th><th>事件</th><th>详情</th></tr></thead><tbody>${rows}</tbody></table></div>
       <p>健康事件与行情事件分开保存：候选页展示异常窗口时，必须同时展示同一时间段的数据健康，否则无法区分市场异常与管道故障。</p>`,
      "good");
  });

  // ---- 时段结构 ----
  document.getElementById("show-history").addEventListener("click", () => {
    const rows = D.hour_history.map((h) => `<tr>
      <td>${String(h.hour_utc).padStart(2, "0")}:00</td>
      <td>${h.n_rows}</td>
      <td>${fmt(h.volume_median_base, 0)}</td>
      <td>${fmt(h.spread_median_usd, 3)}</td>
      <td>${h.structural ? "✔ 结构" : "—"}</td></tr>`).join("");
    output("history-output",
      `<div class="table-scroll"><table><thead><tr><th>UTC 时段</th><th>样本数</th><th>WTI 成交量中位 (base)</th><th>Brent−WTI 价差中位 $</th><th>活跃结构</th></tr></thead><tbody>${rows}</tbody></table></div>
       <p><strong>真实数字：</strong>成交最活跃的 12:00 UTC（中位 ${fmt(D.hour_history.find((h) => h.hour_utc === 12).volume_median_base, 0)}）比最安静的 04:00 UTC（${fmt(D.hour_history.find((h) => h.hour_utc === 4).volume_median_base, 0)}）高约 ${fmt(D.hour_history.find((h) => h.hour_utc === 12).volume_median_base / D.hour_history.find((h) => h.hour_utc === 4).volume_median_base, 1)} 倍；基差中位数从活跃时段的 ${fmt(D.hour_history.find((h) => h.hour_utc === 12).spread_median_usd, 3)} 放宽到安静时段的 ${fmt(D.hour_history.find((h) => h.hour_utc === 4).spread_median_usd, 3)}。时段结构是真实存在且可迁移的。`,
      "good");
  });

  document.getElementById("show-history-check").addEventListener("click", () => {
    output("history-check-output",
      `<strong>核对要点：</strong>是的，基差最窄（3.07）与成交量峰值（9,841）都落在 12:00 UTC（08:00 ET 纽约开盘附近）。"活跃时段做市竞争更充分"是一个候选解释；竞争解释包括：① NYMEX 原油电子盘主力时段的跨所套利者更活跃，把两所价格拉近；② 该时段 Lighter 自身盘口更新与做市激励更强；③ 数据本身在活跃时段更密，中位数估计更稳（安静时段样本同样存在，所以不是纯采样效应）。要区分它们，需要同一时段的逐秒盘口与成交方向数据——这正是 Day 17 区分性实验的原料。`,
      "good");
  });

  // ---- 三个候选 ----
  function renderCandidates() {
    const cards = D.candidates.map((c, i) => `<div class="scenario" style="margin-top:10px">
      <h3>${String.fromCharCode(65 + i)} · ${esc(c.title)} <span class="pill">${esc(c.kind)}</span></h3>
      <p>${esc(c.description)}</p>
      <table><thead><tr><th>证据</th><th>值</th></tr></thead><tbody>
        ${Object.entries(c.evidence).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("")}
      </tbody></table>
      <p class="muted">数据质量诊断：${esc(c.diagnosis)}</p>
    </div>`).join("");
    output("candidate-list", cards, null);
  }
  if (D.candidates && D.candidates.length) renderCandidates();
  else output("candidate-list", "没有达到证据标准的候选；按里程碑规定转入方法训练（升级检测器或数据健康视图）。", null);

  const agentExplanations = {
    a: "A 的解释：它是单次越界、短于阈值时长、之后回到自身基线。研究价值在于：① 它可复现吗（需要更多连续窗口）？② 它出现在盘口还是成交之后（冲击 vs 报价抖动）？如果只是想确认'机会是否持续'，A 是最弱的方向——一次噪声不能构成可回放的候选。",
    b: "B 的解释：持续或重复越界意味着市场自身结构（流动性、做市激励、机制）在某段时间内系统性变化。研究价值：重复模式可以做事件研究（什么触发、持续多久、恢复条件），也是唯一能直接喂给 Day 18 回放的候选。危险：重复出现不等于可交易，必须先排除数据管道假象（见健康事件）。",
    c: "C 的解释：时段结构可迁移——如果异常总在同一 UTC 时段出现，它可以被预测，这是三候选中唯一自带'前置时间'的。研究价值：先确认外部事件日历（NY 开盘、EIA 发布、维护窗口）是否对齐；然后才问该时段的价差是否在扣费后可成交。危险：时段相关不等于因果，且安静时段样本稀疏。",
  };
  document.getElementById("submit-choice").addEventListener("click", () => {
    const choice = document.getElementById("candidate-choice").value;
    const reason = document.getElementById("candidate-reason").value.trim();
    if (!choice) {
      output("candidate-feedback", "先选择一个候选。", "bad");
      return;
    }
    if (!reason) {
      output("candidate-feedback", "写一句你的理由——哪怕只有半句。没有解释的选择不算研究动作。", "bad");
      return;
    }
    const selected = D.candidates.find((_, i) => String.fromCharCode(65 + i) === choice.toUpperCase());
    output("candidate-feedback",
      `<strong>你的选择：${esc(selected.title)}</strong><p>你的理由：${esc(reason)}</p><hr><p>${agentExplanations[choice]}</p>
       <p class="muted">下一步：在 Telegram 告诉 Agent 你的选择与理由，Agent 会展示竞争解释和数据质量诊断，然后由你决定做哪个区分性实验（Day 17 机制实验室）。</p>`,
      "good");
  });

  // ---- 综合迁移 ----
  document.getElementById("check-transfer").addEventListener("click", () => {
    const answer = document.getElementById("transfer-answer").value;
    if (answer === "structural") {
      output("transfer-feedback",
        `<strong>正确判断：structural。</strong>同一 UTC 时段、跨三个日期重复出现，已经满足"跨不同小时/日期的同时段重复"标准，不是每天一次的噪声。<p>下一步实验（按优先级）：① 对齐外部事件日历（数据发布/维护窗口）验证时段解释；② 检查该时段两个场所的数据健康与更新频率，排除管道假象；③ 若时段解释成立，再问该窗口的价差在扣费后可成交规模（Day 16）。</p>`,
        "good");
    } else if (answer) {
      output("transfer-feedback",
        `再想一层：transient 要求"只出现一次"；persistent 要求"长时间不回落"（这里 20 分钟每天都有，但 12:30 之前和 13:30 之后完全正常）。"每天同一时段出现"正是 structural 的定义——分类不是看绝对时长，而是看重复是否绑定时段。`,
        "bad");
    }
  });
})();
