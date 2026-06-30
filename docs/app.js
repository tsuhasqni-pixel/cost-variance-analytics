/* Static SPA: load internal-accounting JSON, run variance + stats locally. */
(function () {
  "use strict";

  const LS_KEY = "cost-variance-analytics/v1";
  let state = load();

  function load() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }
  function save() { localStorage.setItem(LS_KEY, JSON.stringify(state)); }

  // ---------- formatters ----------
  const yen = (v) => { const n = Number(v) || 0; return (n < 0 ? "-¥" : "¥") + Math.round(Math.abs(n)).toLocaleString(); };
  const signedYen = (v) => { const n = Number(v) || 0; if (n > 0) return "+¥" + Math.round(n).toLocaleString(); if (n < 0) return "-¥" + Math.round(-n).toLocaleString(); return "¥0"; };
  const pct = (v) => ((Number(v) || 0) * 100).toFixed(2) + "%";
  const r3 = (v) => (Number(v) || 0).toFixed(3);
  const escapeHtml = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------- variance calc (mirror of Python) ----------
  function stdQtyForOutput(perUnit, stdOut, actOut) { return stdOut <= 0 ? 0 : (perUnit / stdOut) * actOut; }

  function calcVariance(product, actual) {
    const mode = product.mode || "detailed";
    if (mode === "simple") return calcSimple(product, actual);
    return calcDetailed(product, actual);
  }

  function calcDetailed(product, actual) {
    const cc = product.cost_card || {};
    const so = Number(product.std_output) || 1;
    const out = Number(actual.actual_output) || 1;
    const lines = [];
    const stdMats = (cc.materials || []).reduce((m, x) => (m[x.name] = x, m), {});
    const actMats = (actual.materials || []).reduce((m, x) => (m[x.name] = x, m), {});
    for (const name of Array.from(new Set([...Object.keys(stdMats), ...Object.keys(actMats)]))) {
      const s = stdMats[name] || { std_price: 0, std_qty: 0 };
      const a = actMats[name] || { actual_price: 0, actual_qty: 0 };
      const sq = stdQtyForOutput(s.std_qty, so, out);
      lines.push({ category: "材料価格", process: name, value: (a.actual_price - s.std_price) * a.actual_qty });
      lines.push({ category: "材料数量", process: name, value: (a.actual_qty - sq) * s.std_price });
    }
    const stdLabs = (cc.labors || []).reduce((m, x) => (m[x.process] = x, m), {});
    const actLabs = (actual.labors || []).reduce((m, x) => (m[x.process] = x, m), {});
    let totAct = 0, totStd = 0;
    for (const name of Array.from(new Set([...Object.keys(stdLabs), ...Object.keys(actLabs)]))) {
      const s = stdLabs[name] || { std_rate: 0, std_hours: 0 };
      const a = actLabs[name] || { actual_rate: 0, actual_hours: 0 };
      const sh = stdQtyForOutput(s.std_hours, so, out);
      lines.push({ category: "労務賃率", process: name, value: (a.actual_rate - s.std_rate) * a.actual_hours });
      lines.push({ category: "労務時間", process: name, value: (a.actual_hours - sh) * s.std_rate });
      totAct += a.actual_hours; totStd += sh;
    }
    const oh = cc.overhead || {};
    const aoh = actual.overhead || {};
    const sfr = oh.normal_hours ? (oh.fixed_budget || 0) / oh.normal_hours : 0;
    lines.push({ category: "変動OH予算", process: "OH", value: (aoh.actual_variable || 0) - (oh.var_rate || 0) * totAct });
    lines.push({ category: "変動OH能率", process: "OH", value: (oh.var_rate || 0) * (totAct - totStd) });
    lines.push({ category: "固定OH予算", process: "OH", value: (aoh.actual_fixed || 0) - (oh.fixed_budget || 0) });
    lines.push({ category: "固定OH操業度", process: "OH", value: (oh.fixed_budget || 0) - sfr * totStd });
    return { product_id: product.id, period: actual.period, mode: "detailed", lines };
  }

  function calcSimple(product, actual) {
    const sb = (product.cost_card && product.cost_card.simple_budget) || {};
    const sa = actual.simple || {};
    const lines = [];
    if (sb.material || sa.material) lines.push({ category: "材料費", process: "—", value: (sa.material || 0) - (sb.material || 0) });
    if (sb.labor || sa.labor) lines.push({ category: "労務費", process: "—", value: (sa.labor || 0) - (sb.labor || 0) });
    if (sb.overhead || sa.overhead) lines.push({ category: "経費", process: "—", value: (sa.overhead || 0) - (sb.overhead || 0) });
    const at = sa.total || ((sa.material || 0) + (sa.labor || 0) + (sa.overhead || 0));
    const bt = sb.total || ((sb.material || 0) + (sb.labor || 0) + (sb.overhead || 0));
    lines.push({ category: "総差異", process: "—", value: at - bt });
    return { product_id: product.id, period: actual.period, mode: "simple", lines };
  }

  // ---------- stats ----------
  function describe(vs) {
    if (!vs.length) return { n: 0, mean: 0, median: 0, stdev: 0, min: 0, max: 0, sum: 0 };
    const n = vs.length;
    const mean = vs.reduce((a, b) => a + b, 0) / n;
    const sorted = vs.slice().sort((a, b) => a - b);
    const median = n % 2 ? sorted[(n - 1) / 2] : (sorted[n / 2 - 1] + sorted[n / 2]) / 2;
    const stdev = n > 1 ? Math.sqrt(vs.reduce((s, v) => s + (v - mean) ** 2, 0) / (n - 1)) : 0;
    return { n, mean, median, stdev, min: Math.min(...vs), max: Math.max(...vs), sum: vs.reduce((a, b) => a + b, 0) };
  }
  // approximate two-sided t-test p value (normal approximation)
  function tTest1(vs) {
    const d = describe(vs);
    if (d.n < 2 || d.stdev === 0) return { ...d, t: 0, p: 1 };
    const se = d.stdev / Math.sqrt(d.n);
    const t = d.mean / se;
    // Student t -> Normal approx for simplicity
    const p = 2 * (1 - normalCdf(Math.abs(t)));
    return { ...d, t, p, se, ci95_low: d.mean - 1.96 * se, ci95_high: d.mean + 1.96 * se };
  }
  function normalCdf(x) {
    // Abramowitz/Stegun approximation
    const a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741, a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
    const sign = x < 0 ? -1 : 1;
    x = Math.abs(x) / Math.sqrt(2);
    const t = 1 / (1 + p * x);
    const y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
    return 0.5 * (1 + sign * y);
  }
  function linreg(xs, ys) {
    const n = xs.length;
    if (n < 2) return { slope: 0, intercept: ys[0] || 0, r2: 0 };
    const mx = xs.reduce((a, b) => a + b, 0) / n;
    const my = ys.reduce((a, b) => a + b, 0) / n;
    const sxy = xs.map((x, i) => (x - mx) * (ys[i] - my)).reduce((a, b) => a + b, 0);
    const sxx = xs.map((x) => (x - mx) ** 2).reduce((a, b) => a + b, 0);
    const syy = ys.map((y) => (y - my) ** 2).reduce((a, b) => a + b, 0);
    const slope = sxx ? sxy / sxx : 0;
    return { slope, intercept: my - slope * mx, r2: sxx && syy ? (sxy * sxy) / (sxx * syy) : 0 };
  }
  function imrChart(values) {
    const d = describe(values);
    const mrs = values.slice(1).map((v, i) => Math.abs(v - values[i]));
    const mrBar = mrs.length ? mrs.reduce((a, b) => a + b, 0) / mrs.length : 0;
    const ucl = d.mean + 2.66 * mrBar;
    const lcl = d.mean - 2.66 * mrBar;
    const ooc = values.map((v, i) => (v > ucl || v < lcl ? i : -1)).filter((i) => i >= 0);
    return { mean: d.mean, mrBar, ucl, lcl, ooc, values };
  }

  // ---------- aggregation ----------
  function buildBundle() {
    if (!state || !state.products) return null;
    const products = state.products || [];
    const actuals = state.actuals || [];
    const productsById = products.reduce((m, p) => (m[p.id] = p, m), {});
    const reports = actuals.map((a) => {
      const p = productsById[a.product_id]; if (!p) return null;
      const r = calcVariance(p, a);
      r.product_name = p.name;
      return r;
    }).filter(Boolean);

    const rows = [];
    for (const r of reports) for (const l of r.lines)
      rows.push({ product_id: r.product_id, product_name: r.product_name, period: r.period, mode: r.mode, category: l.category, process: l.process, value: l.value });

    const series = {};
    for (const r of rows) {
      const k = r.product_id + "||" + r.category;
      (series[k] ||= []).push({ period: r.period, value: r.value, product_name: r.product_name });
    }
    Object.values(series).forEach((arr) => arr.sort((a, b) => a.period.localeCompare(b.period)));

    const descriptive = Object.entries(series).map(([k, arr]) => {
      const [pid, cat] = k.split("||");
      const t = tTest1(arr.map((x) => x.value));
      return { product_id: pid, product_name: arr[0].product_name, category: cat, ...t, ci95_low: t.ci95_low || 0, ci95_high: t.ci95_high || 0, significant: (t.p || 1) < 0.05 };
    }).sort((a, b) => a.product_name.localeCompare(b.product_name) || a.category.localeCompare(b.category));

    // Pareto
    const agg = {};
    for (const r of rows) {
      if (r.value <= 0) continue;
      const k = r.product_id + "||" + r.category;
      agg[k] ||= { product_id: r.product_id, product_name: r.product_name, category: r.category, total: 0 };
      agg[k].total += r.value;
    }
    const paretoItems = Object.values(agg).sort((a, b) => b.total - a.total);
    const grand = paretoItems.reduce((s, x) => s + x.total, 0) || 1;
    let cum = 0;
    paretoItems.forEach((x, i) => { x.share = x.total / grand; cum += x.share; x.cum_share = cum; x.rank = i + 1; });

    // Control charts
    const controlCharts = Object.entries(series).filter(([k, arr]) => arr.length >= 2).map(([k, arr]) => {
      const [pid, cat] = k.split("||");
      const c = imrChart(arr.map((x) => x.value));
      return { product_id: pid, product_name: arr[0].product_name, category: cat, periods: arr.map((x) => x.period), ...c };
    }).sort((a, b) => a.product_name.localeCompare(b.product_name) || a.category.localeCompare(b.category));

    // Trends
    const trends = Object.entries(series).filter(([k, arr]) => arr.length >= 2).map(([k, arr]) => {
      const [pid, cat] = k.split("||");
      const ys = arr.map((x) => x.value);
      const xs = ys.map((_, i) => i);
      const reg = linreg(xs, ys);
      return { product_id: pid, product_name: arr[0].product_name, category: cat, periods: arr.map((x) => x.period), values: ys, ...reg };
    });

    return { products, actuals, rows, descriptive, pareto: paretoItems, controlCharts, trends };
  }

  // ---------- tab switching ----------
  function showTab(name) {
    document.querySelectorAll(".tab").forEach((el) => (el.hidden = el.id !== "tab-" + name));
  }
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-tab]");
    if (t) { e.preventDefault(); render(t.dataset.tab); }
  });

  // ---------- render ----------
  function chart(id, config) {
    const ctx = document.getElementById(id);
    if (!ctx) return;
    if (ctx.__chart) ctx.__chart.destroy();
    ctx.__chart = new Chart(ctx, config);
  }

  function render(tab) {
    const b = buildBundle();
    if (!b) { showTab("empty"); return; }
    if (!tab) tab = "dashboard";

    // dashboard
    document.getElementById("dashSummary").innerHTML = `
      <ul class="kv kv-grid">
        <li><span>製品数</span><b>${b.products.length}</b></li>
        <li><span>実績件数</span><b>${b.actuals.length}</b></li>
        <li><span>差異データ点数</span><b>${b.rows.length}</b></li>
        <li><span>差異シリーズ数</span><b>${b.descriptive.length}</b></li>
      </ul>`;
    document.getElementById("dashTop").innerHTML = renderDescriptiveTable(b.descriptive.slice().sort((a, b2) => (a.p || 1) - (b2.p || 1)).slice(0, 10));
    document.getElementById("dashPareto").innerHTML = renderParetoTable(b.pareto.slice(0, 10));

    // stats
    document.getElementById("statsTable").innerHTML = renderDescriptiveTable(b.descriptive);

    // pareto
    document.getElementById("paretoTable").innerHTML = renderParetoTable(b.pareto);
    chart("paretoChart", paretoConfig(b.pareto.slice(0, 15)));

    // control
    document.getElementById("controlContent").innerHTML = b.controlCharts.map((c, i) => `
      <section class="card">
        <h2>${escapeHtml(c.product_name)} — ${escapeHtml(c.category)} <small class="muted">(n=${c.values.length})</small></h2>
        <ul class="kv kv-grid">
          <li><span>平均</span><b>${signedYen(c.mean)}</b></li>
          <li><span>UCL_I</span><b>${signedYen(c.ucl)}</b></li>
          <li><span>LCL_I</span><b>${signedYen(c.lcl)}</b></li>
          <li><span>MR̄</span><b>${yen(c.mrBar)}</b></li>
          <li><span>OOC 数</span><b>${c.ooc.length}</b></li>
        </ul>
        <canvas id="cc_${i}" height="100"></canvas>
      </section>`).join("") || `<p class="muted">2 期以上の差異データがある系列がありません。</p>`;
    b.controlCharts.forEach((c, i) => chart("cc_" + i, ccConfig(c)));

    // trend
    document.getElementById("trendContent").innerHTML = b.trends.map((t, i) => `
      <section class="card">
        <h2>${escapeHtml(t.product_name)} — ${escapeHtml(t.category)} <small class="muted">(n=${t.values.length})</small></h2>
        <ul class="kv kv-grid">
          <li><span>傾き</span><b>${r3(t.slope)}</b></li>
          <li><span>切片</span><b>${r3(t.intercept)}</b></li>
          <li><span>R²</span><b>${r3(t.r2)}</b></li>
        </ul>
        <canvas id="tr_${i}" height="100"></canvas>
      </section>`).join("") || `<p class="muted">2 期以上の差異データがある系列がありません。</p>`;
    b.trends.forEach((t, i) => chart("tr_" + i, trendConfig(t)));

    showTab(tab);
  }

  function renderDescriptiveTable(rows) {
    if (!rows.length) return `<p class="muted">データがありません。</p>`;
    return `<table class="grid"><thead><tr>
      <th>製品</th><th>差異種別</th><th>n</th><th>平均</th><th>SD</th><th>min</th><th>max</th><th>t</th><th>p</th><th>判定</th>
    </tr></thead><tbody>${rows.map((d) => `
      <tr>
        <td>${escapeHtml(d.product_name)}</td><td>${escapeHtml(d.category)}</td><td>${d.n}</td>
        <td class="right">${signedYen(d.mean)}</td>
        <td class="right">${yen(d.stdev)}</td>
        <td class="right">${signedYen(d.min)}</td>
        <td class="right">${signedYen(d.max)}</td>
        <td class="right">${r3(d.t)}</td>
        <td class="right">${r3(d.p)}</td>
        <td>${d.significant && d.mean > 0 ? `<span class="badge sign-unfav">有意・不利</span>` : d.significant && d.mean < 0 ? `<span class="badge sign-fav">有意・有利</span>` : `<span class="badge sign-zero">非有意</span>`}</td>
      </tr>`).join("")}</tbody></table>`;
  }
  function renderParetoTable(rows) {
    if (!rows.length) return `<p class="muted">不利差異がありません。</p>`;
    return `<table class="grid"><thead><tr><th>順位</th><th>製品</th><th>差異種別</th><th>不利合計</th><th>シェア</th><th>累積</th></tr></thead><tbody>${rows.map((p) => `
      <tr><td>${p.rank}</td><td>${escapeHtml(p.product_name)}</td><td>${escapeHtml(p.category)}</td>
          <td class="right">${yen(p.total)}</td>
          <td class="right">${pct(p.share)}</td>
          <td class="right">${pct(p.cum_share)}</td></tr>`).join("")}</tbody></table>`;
  }
  function paretoConfig(p) {
    return {
      data: {
        labels: p.map((x) => x.product_name + " / " + x.category),
        datasets: [
          { type: "bar", label: "不利差異", data: p.map((x) => x.total), backgroundColor: "rgba(185,28,28,.7)", yAxisID: "y" },
          { type: "line", label: "累積%", data: p.map((x) => x.cum_share * 100), borderColor: "#2563eb", yAxisID: "y2", tension: 0.2 },
        ],
      },
      options: { responsive: true, scales: { y: { position: "left", ticks: { callback: (v) => "¥" + Number(v).toLocaleString() } }, y2: { position: "right", grid: { drawOnChartArea: false }, ticks: { callback: (v) => v + "%" }, min: 0, max: 100 } } },
    };
  }
  function ccConfig(c) {
    const oocSet = new Set(c.ooc);
    return {
      type: "line",
      data: {
        labels: c.periods,
        datasets: [
          { label: "個別値", data: c.values, borderColor: "#1f2933", pointBackgroundColor: c.values.map((_, i) => oocSet.has(i) ? "#b91c1c" : "#1f2933"), pointRadius: c.values.map((_, i) => oocSet.has(i) ? 6 : 3) },
          { label: "中心線", data: c.values.map(() => c.mean), borderColor: "#2563eb", borderDash: [6, 4], pointRadius: 0 },
          { label: "UCL", data: c.values.map(() => c.ucl), borderColor: "#dc2626", borderDash: [4, 4], pointRadius: 0 },
          { label: "LCL", data: c.values.map(() => c.lcl), borderColor: "#dc2626", borderDash: [4, 4], pointRadius: 0 },
        ],
      },
      options: { responsive: true, plugins: { tooltip: { callbacks: { label: (ctx) => "¥" + Math.round(ctx.raw).toLocaleString() } } } },
    };
  }
  function trendConfig(t) {
    const fit = t.values.map((_, i) => t.slope * i + t.intercept);
    return {
      type: "line",
      data: { labels: t.periods, datasets: [
        { label: "差異", data: t.values, borderColor: "#1f2933" },
        { label: "回帰", data: fit, borderColor: "#2563eb", borderDash: [6, 4], pointRadius: 0 },
      ] },
      options: { responsive: true, plugins: { tooltip: { callbacks: { label: (ctx) => "¥" + Math.round(ctx.raw).toLocaleString() } } } },
    };
  }

  // ---------- import/reset ----------
  document.getElementById("fileImport").addEventListener("change", (e) => {
    const f = e.target.files[0]; if (!f) return;
    const r = new FileReader();
    r.onload = () => {
      try {
        const s = JSON.parse(r.result);
        state = { products: s.products || [], actuals: s.actuals || [], cvp: s.cvp || null };
        save(); render("dashboard");
      } catch (err) { alert("JSON 読み込みエラー: " + err); }
    };
    r.readAsText(f); e.target.value = "";
  });
  document.getElementById("btnReset").addEventListener("click", () => {
    if (!confirm("読込済みデータを破棄します。よろしいですか?")) return;
    state = null; localStorage.removeItem(LS_KEY); render();
  });

  render();
})();
