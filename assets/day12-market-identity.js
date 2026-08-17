(() => {
  const completeKey = "monte-arb-day12-complete";

  function show(id, html, good) {
    const node = document.getElementById(id);
    node.innerHTML = html;
    node.classList.toggle("good", Boolean(good));
    node.classList.toggle("bad", good === false);
  }

  function bindScenarioButtons() {
    document.querySelectorAll("[data-scenario]").forEach((button) => {
      button.addEventListener("click", () => {
        const scenario = button.dataset.scenario;
        const answers = {
          "request-identity": [
            true,
            "正确。Lighter 的裸盘口响应不能证明自己属于哪个 symbol。适配器必须保存请求时的完整身份：<code>venue + product_type + namespace + symbol + market_id</code>，并把它与响应绑定。",
          ],
          "response-order": [
            false,
            "不够。并发请求完成顺序不稳定；只按返回顺序贴标签，会把成功响应静默挂到错误市场。",
          ],
          "symbol-only": [
            false,
            "不够。<code>symbol</code> 会在场所、产品类型或命名空间之间复用；Hyperliquid 还必须保留 <code>xyz:CL</code> 这样的完整名称和本地资产编号。",
          ],
        };
        const [good, message] = answers[scenario];
        show("identity-feedback", message, good);
      });
    });
  }

  function bindPairingDemo() {
    const run = document.getElementById("run-pairing-demo");
    if (!run) return;
    run.addEventListener("click", () => {
      const universe = ["xyz:OLD (delisted)", "xyz:CL", "xyz:BRENTOIL"];
      const contexts = ["mid=null", "mid=81.15", "mid=85.05"];
      const unsafe = universe.filter((x) => !x.includes("delisted"))
        .map((name, i) => `${name} ← ${contexts[i]}`);
      const safe = universe.map((name, i) => `${name} ← ${contexts[i]}`)
        .filter((row) => !row.includes("delisted"));
      show(
        "pairing-output",
        `<strong>先过滤再 zip（错误）</strong><pre>${unsafe.join("\n")}</pre>` +
        `<strong>先按原 index 配对（正确）</strong><pre>${safe.join("\n")}</pre>` +
        `<p>错误路径把 <code>xyz:CL</code> 配到了下架市场的 context；数值仍像价格，所以这种错误不会自动报警。</p>`,
        true,
      );
    });
  }

  function bindExitCheck() {
    const select = document.getElementById("transfer-answer");
    const button = document.getElementById("check-transfer");
    if (!button) return;
    button.addEventListener("click", () => {
      if (select.value === "bind-request") {
        localStorage.setItem(completeKey, "true");
        show(
          "transfer-feedback",
          "通过。新场景换成任意两个 Lighter 市场时，仍应在发请求前构造完整市场身份，并将该身份、请求参数和响应共同保存；不能依赖返回顺序。Day 12 的关键技能已完成。",
          true,
        );
        document.getElementById("completion").textContent = "本页关键迁移：已通过";
      } else if (select.value) {
        show(
          "transfer-feedback",
          "还不够。这个方案可能得到合理价格，但不能证明响应属于请求的那个市场。回到上面的 Lighter 身份边界再检查一次。",
          false,
        );
      }
    });
  }

  bindScenarioButtons();
  bindPairingDemo();
  bindExitCheck();
  if (localStorage.getItem(completeKey) === "true") {
    document.getElementById("completion").textContent = "本页关键迁移：已通过（本机记录）";
  }
})();
