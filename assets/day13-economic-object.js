(() => {
  function show(id, html, good) {
    const node = document.getElementById(id);
    node.innerHTML = html;
    node.classList.toggle("good", good === true);
    node.classList.toggle("bad", good === false);
  }

  const mapButton = document.getElementById("reveal-map");
  if (mapButton) {
    mapButton.addEventListener("click", () => {
      show(
        "map-output",
        `<table><thead><tr><th>配对</th><th>程序决定</th><th>原因</th></tr></thead><tbody>
          <tr><td>WTI ↔ xyz:CL</td><td><code>unknown</code></td><td><code>CONTRACT_YEAR_UNKNOWN</code></td></tr>
          <tr><td>BRENTOIL ↔ xyz:BRENTOIL</td><td><code>unknown</code></td><td><code>CONTRACT_YEAR_UNKNOWN</code></td></tr>
          <tr><td>WTI ↔ xyz:BRENTOIL</td><td><code>not_comparable</code></td><td><code>BENCHMARK_MISMATCH</code></td></tr>
        </tbody></table>
        <p>前两对不是“配对失败”，而是完整合约身份仍缺证据。第三对已有 WTI/Brent 基准冲突，明确不能配对。</p>`,
        true,
      );
    });
  }

  const stateButton = document.getElementById("run-state-demo");
  if (stateButton) {
    stateButton.addEventListener("click", () => {
      const source = document.getElementById("source-evidence").value;
      const roll = document.getElementById("roll-evidence").value;
      let status = "unknown";
      let reason = "价格源或展期证据缺失，时钟不能替代观测。";
      if (source === "external" && roll === "no") {
        status = "external";
        reason = "外部价格可用且 oracle fresh，并有证据表明不在展期切换。";
      } else if (source === "internal" && roll === "no") {
        status = "internal";
        reason = "外部价格不可用且 oracle 已进入内部更新，并有证据表明不在展期切换。";
      } else if (roll === "yes") {
        status = "roll_transition";
        reason = "处于展期权重变化期；先记录两边合同权重，不能把差异直接解释为价差。";
      }
      show("state-output", `<strong>${status}</strong><p>${reason}</p>`, status !== "unknown");
    });
  }

  const check = document.getElementById("check-case");
  if (check) {
    check.addEventListener("click", () => {
      const answer = document.getElementById("case-answer").value;
      if (answer === "exclude") {
        show(
          "case-feedback",
          `<strong>方向正确：先排除。</strong> 17:40 ET 时，两边虽有 bid/ask，但 Lighter 已执行当天展期权重更新，而 trade.xyz 的外部市场处于维护窗口。还需要两边同一时刻的<strong>合约月份/权重</strong>、<strong>external price 可用性</strong>、<strong>oracle freshness</strong>以及<strong>当前 external/internal 状态</strong>，才能决定何时重新纳入。`,
          true,
        );
      } else if (answer) {
        show(
          "case-feedback",
          `这会把“盘口仍在更新”误当成“价格来源相同”。8 bps 可能来自展期权重和外部/内部定价状态差异，当前不能进入可比较样本。`,
          false,
        );
      }
    });
  }
})();
