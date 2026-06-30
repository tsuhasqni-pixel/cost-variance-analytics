(function () {
  if (window.__pareto && document.getElementById("paretoChart")) {
    const p = window.__pareto.slice(0, 15);
    new Chart(document.getElementById("paretoChart"), {
      data: {
        labels: p.map((x) => x.product_name + " / " + x.category),
        datasets: [
          { type: "bar", label: "不利差異", data: p.map((x) => x.total), backgroundColor: "rgba(185,28,28,.7)", yAxisID: "y" },
          { type: "line", label: "累積%", data: p.map((x) => x.cum_share * 100), borderColor: "#2563eb", backgroundColor: "transparent", yAxisID: "y2", tension: 0.2 },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: { position: "left", ticks: { callback: (v) => "¥" + Number(v).toLocaleString() } },
          y2: { position: "right", grid: { drawOnChartArea: false }, ticks: { callback: (v) => v + "%" }, min: 0, max: 100 },
        },
      },
    });
  }

  (window.__controlCharts || []).forEach((c) => {
    const ctx = document.getElementById(c.id);
    if (!ctx) return;
    const oocSet = new Set(c.ooc);
    new Chart(ctx, {
      type: "line",
      data: {
        labels: c.periods,
        datasets: [
          {
            label: c.label, data: c.values, borderColor: "#1f2933", backgroundColor: "transparent",
            pointBackgroundColor: c.values.map((_, i) => (oocSet.has(i) ? "#b91c1c" : "#1f2933")),
            pointRadius: c.values.map((_, i) => (oocSet.has(i) ? 6 : 3)),
          },
          { label: "中心線", data: c.values.map(() => c.mean), borderColor: "#2563eb", borderDash: [6, 4], pointRadius: 0 },
          { label: "UCL", data: c.values.map(() => c.ucl), borderColor: "#dc2626", borderDash: [4, 4], pointRadius: 0 },
          { label: "LCL", data: c.values.map(() => c.lcl), borderColor: "#dc2626", borderDash: [4, 4], pointRadius: 0 },
        ],
      },
      options: { responsive: true, plugins: { tooltip: { callbacks: { label: (ctx) => "¥" + Math.round(ctx.raw).toLocaleString() } } } },
    });
  });

  (window.__trends || []).forEach((t) => {
    const ctx = document.getElementById(t.id);
    if (!ctx) return;
    const xs = t.periods.map((_, i) => i);
    const fit = xs.map((x) => t.slope * x + t.intercept);
    new Chart(ctx, {
      type: "line",
      data: {
        labels: t.periods,
        datasets: [
          { label: "差異", data: t.values, borderColor: "#1f2933", backgroundColor: "transparent" },
          { label: "回帰直線", data: fit, borderColor: "#2563eb", borderDash: [6, 4], pointRadius: 0 },
        ],
      },
      options: { responsive: true, plugins: { tooltip: { callbacks: { label: (ctx) => "¥" + Math.round(ctx.raw).toLocaleString() } } } },
    });
  });
})();
