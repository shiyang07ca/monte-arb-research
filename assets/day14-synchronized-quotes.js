(() => {
  const observations = [
    { venue: "Lighter", market: "WTI/145", bid: "84.056", ask: "84.070", source: "缺失", receive: "0 ms（组内基准）" },
    { venue: "Lighter", market: "BRENTOIL/159", bid: "89.20", ask: "89.22", source: "缺失", receive: "约 +30 ms" },
    { venue: "Hyperliquid xyz", market: "xyz:CL/110029", bid: "84.075", ask: "84.076", source: "1787017114726", receive: "约 -531 ms vs Lighter WTI" },
    { venue: "Hyperliquid xyz", market: "xyz:BRENTOIL/110049", bid: "89.236", ask: "89.239", source: "1787017114726", receive: "约 -501 ms vs Lighter Brent" },
  ];

  function output(id, html, state) {
    const node = document.getElementById(id);
    node.innerHTML = html;
    node.classList.toggle("good", state === "good");
    node.classList.toggle("bad", state === "bad");
  }

  document.getElementById("show-capture").addEventListener("click", () => {
    const rows = observations.map((o) => `<tr><td>${o.venue}</td><td><code>${o.market}</code></td><td>${o.bid}</td><td>${o.ask}</td><td>${o.source}</td><td>${o.receive}</td></tr>`).join("");
    output("capture-output", `<div class="table-scroll"><table><thead><tr><th>场所</th><th>市场</th><th>Bid</th><th>Ask</th><th>来源时间</th><th>本机接收关系</th></tr></thead><tbody>${rows}</tbody></table></div><p><strong>采集轮次宽度：</strong>1124.0355 ms。四份盘口都有双边，但两个 Lighter 响应没有交易所来源时间。</p>`, "good");
  });

  document.getElementById("classify-time").addEventListener("click", () => {
    const value = document.getElementById("time-field").value;
    const explanations = {
      request: ["request_started_ns", "本机开始发请求的单调时钟；用于定义采集窗口，不是交易所事件时间。"],
      receive: ["response_received_ns", "本机完整收到响应的单调时钟；可比较同一进程内的接收先后。"],
      source: ["source_time_ms", "交易所随响应提供的快照时间。Lighter 本轮缺失，不能用接收时间代填。"],
    };
    if (!explanations[value]) return;
    output("time-output", `<strong>${explanations[value][0]}</strong><p>${explanations[value][1]}</p>`, "good");
  });

  document.getElementById("run-admission").addEventListener("click", () => {
    const reasons = [];
    if (document.getElementById("economic").value !== "same") reasons.push("ECONOMIC_MAPPING_UNKNOWN");
    if (document.getElementById("weights").value !== "matched") reasons.push("CONTRACT_WEIGHT_UNKNOWN");
    if (document.getElementById("oracle-left").value === "unknown" || document.getElementById("oracle-right").value === "unknown") reasons.push("ORACLE_STATE_UNKNOWN");
    else if (document.getElementById("oracle-left").value !== document.getElementById("oracle-right").value) reasons.push("ORACLE_STATE_MISMATCH");
    const status = reasons.length ? "exclude" : "eligible";
    output("admission-output", `<strong>${status}</strong><p>${reasons.length ? reasons.map((r) => `<code>${r}</code>`).join(" · ") : "静态定义、权重和 oracle 状态均通过；仍需检查盘口和接收偏差。"}</p>`, status === "eligible" ? "good" : "bad");
  });

  document.getElementById("check-transfer").addEventListener("click", () => {
    const answer = document.getElementById("transfer-answer").value;
    if (answer === "exclude") {
      output("transfer-feedback", `<strong>正确。</strong> 20ms 只改善本机接收偏差；合约权重和 oracle 状态仍未知，研究结论继续是 <code>exclude</code>。原始观察应保留，因为将来取得规则状态后可以重新计算派生准入决定。`, "good");
    } else if (answer) {
      output("transfer-feedback", `接收更接近不能补出经济定义或价格来源。快速收到两份不可比价格，仍然是不可比样本。`, "bad");
    }
  });
})();
