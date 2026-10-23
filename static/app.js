document.addEventListener("DOMContentLoaded", () => {
  const today = document.getElementById("todayLabel");
  if (today) {
    const now = new Date();
    today.textContent = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric" }).format(now);
  }

  const menu = document.getElementById("mobileMenu");
  const sidebar = document.getElementById("sidebar");
  if (menu && sidebar) menu.addEventListener("click", () => sidebar.classList.toggle("sidebar-open"));

  document.querySelectorAll("[data-open-modal]").forEach(btn => {
    btn.addEventListener("click", () => {
      const modal = document.getElementById(btn.dataset.openModal);
      if (modal) { modal.classList.add("modal-visible"); document.body.classList.add("modal-open"); }
    });
  });
  function closeModal(modal) {
    modal.classList.remove("modal-visible");
    if (!document.querySelector(".modal-visible")) document.body.classList.remove("modal-open");
  }
  document.querySelectorAll("[data-close-modal]").forEach(btn => btn.addEventListener("click", () => closeModal(btn.closest(".modal-backdrop"))));
  document.querySelectorAll(".modal-backdrop").forEach(modal => {
    modal.addEventListener("click", e => { if (e.target === modal) closeModal(modal); });
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") document.querySelectorAll(".modal-visible").forEach(closeModal);
  });

  const search = document.getElementById("globalSearch");
  if (search) {
    search.addEventListener("input", () => {
      const query = search.value.trim().toLocaleLowerCase("ru");
      document.querySelectorAll(".searchable-row").forEach(row => {
        row.hidden = !row.textContent.toLocaleLowerCase("ru").includes(query);
      });
    });
  }

  document.querySelectorAll(".filter-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-tab").forEach(t => t.classList.remove("active"));
      btn.classList.add("active");
      const filter = btn.dataset.filter;
      document.querySelectorAll("#transactionTable tr[data-kind]").forEach(row => {
        row.hidden = filter !== "all" && row.dataset.kind !== filter;
      });
    });
  });

  const toggle = document.getElementById("toggleBalance");
  const balance = document.getElementById("balanceValue");
  if (toggle && balance) {
    const actual = balance.textContent;
    toggle.addEventListener("click", () => {
      const hidden = balance.dataset.hidden === "true";
      balance.textContent = hidden ? actual : "••••••";
      balance.dataset.hidden = String(!hidden);
      toggle.textContent = hidden ? "◉" : "◎";
    });
  }

  const readData = id => {
    const el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (_) { return null; }
  };
  const chartData = readData("chartData");
  const analyticsData = readData("analyticsData");
  const hasChart = typeof Chart !== "undefined";
  const chartColors = ["#2563eb", "#16b897", "#8b5cf6", "#f59e0b", "#f06464", "#06b6d4", "#64748b", "#ec4899", "#84cc16", "#a78bfa"];
  if (hasChart && chartData) {
    const monthlyCanvas = document.getElementById("balanceChart");
    if (monthlyCanvas) {
      const any = chartData.labels.length && (chartData.income.some(v => v > 0) || chartData.expense.some(v => v > 0));
      document.getElementById("balanceEmpty")?.classList.toggle("is-visible", !any);
      new Chart(monthlyCanvas, {
        type: "line",
        data: { labels: chartData.labels, datasets: [
          { label: "Доходы", data: chartData.income, borderColor: "#16b897", backgroundColor: "rgba(22,184,151,.08)", fill: true, tension: .38, pointRadius: 3, pointHoverRadius: 5 },
          { label: "Расходы", data: chartData.expense, borderColor: "#f06464", backgroundColor: "rgba(240,100,100,.04)", fill: false, tension: .38, pointRadius: 3, pointHoverRadius: 5 }
        ]},
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: true, position: "top", align: "end", labels: { usePointStyle: true, boxWidth: 7, color: "#71809a", font: { family: "Inter", size: 11 } } } },
          scales: { x: { grid: { display: false }, ticks: { color: "#8490a5", font: { family: "Inter", size: 10 } } }, y: { beginAtZero: true, border: { display: false }, grid: { color: "#edf1f7" }, ticks: { color: "#8490a5", font: { family: "Inter", size: 10 } } } } }
      });
    }
    const donut = document.getElementById("categoryChart");
    if (donut) {
      const any = chartData.categoryValues.length > 0;
      document.getElementById("categoryEmpty")?.classList.toggle("is-visible", !any);
      new Chart(donut, { type: "doughnut", data: { labels: chartData.categoryLabels, datasets: [{ data: chartData.categoryValues, backgroundColor: chartColors, borderWidth: 0, hoverOffset: 5 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: "73%", plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` ${ctx.label}: € ${Number(ctx.raw).toLocaleString("ru-RU", {minimumFractionDigits:2, maximumFractionDigits:2})}` } } } } });
      const legend = document.getElementById("categoryLegend");
      if (legend) legend.querySelectorAll(".legend-dot").forEach((dot, i) => dot.style.backgroundColor = chartColors[i % chartColors.length]);
    }
  }
  if (hasChart && analyticsData) {
    const monthly = document.getElementById("analyticsMonthly");
    if (monthly) {
      const any = analyticsData.labels.length && (analyticsData.income.some(v => v > 0) || analyticsData.expense.some(v => v > 0));
      document.getElementById("monthlyEmpty")?.classList.toggle("is-visible", !any);
      new Chart(monthly, { type: "bar", data: { labels: analyticsData.labels, datasets: [
        { label: "Доходы", data: analyticsData.income, backgroundColor: "#16b897", borderRadius: 5 },
        { label: "Расходы", data: analyticsData.expense, backgroundColor: "#f06464", borderRadius: 5 }
      ] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { usePointStyle: true, boxWidth: 8, color: "#71809a" } } }, scales: { x: { grid: { display: false }, ticks: { color: "#8490a5" } }, y: { beginAtZero: true, grid: { color: "#edf1f7" }, ticks: { color: "#8490a5" } } } } });
    }
    const cat = document.getElementById("analyticsCategories");
    if (cat) {
      const any = analyticsData.categoryValues.length > 0;
      document.getElementById("analyticsCategoryEmpty")?.classList.toggle("is-visible", !any);
      new Chart(cat, { type: "doughnut", data: { labels: analyticsData.categoryLabels, datasets: [{ data: analyticsData.categoryValues, backgroundColor: chartColors, borderWidth: 0, hoverOffset: 5 }] }, options: { responsive: true, maintainAspectRatio: false, cutout: "68%", plugins: { legend: { display: false } } } });
      document.querySelectorAll(".analytics-legend .legend-dot").forEach((dot, i) => dot.style.backgroundColor = chartColors[i % chartColors.length]);
    }
  }
  document.querySelectorAll(".flash").forEach(flash => setTimeout(() => { flash.style.opacity = "0"; setTimeout(() => flash.remove(), 300); }, 3800));
});
