(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const state = {
    expenses: [],
    tasks: [],
    totals: { all: 0, materials: 0, services: 0, by_category: {}, by_priority: {} },
    materials: [],
    iconCatalog: { defaults: {}, icons: {} },
    house: null,
    project: null,
    importRows: [],
    zoom: "week",
  };
  const statusLabels = {
    pending: "Pendente",
    in_progress: "Em andamento",
    blocked: "Bloqueada",
    completed: "Concluída",
  };

  const els = {
    appStatus: $("app-status"),
    btnPush: $("btn-push"),
    pushStatus: $("push-status"),
    dashTotalAll: $("dash-total-all"),
    dashTotalMaterials: $("dash-total-materials"),
    dashTotalServices: $("dash-total-services"),
    fundsTotal: $("funds-total"),
    fundsDetail: $("funds-detail"),
    overallCoverage: $("overall-coverage"),
    coverageDonut: $("coverage-donut"),
    coverageFunded: $("coverage-funded"),
    overallGap: $("overall-gap"),
    categoryChart: $("category-chart"),
    dashMaterials: $("dash-materials"),
    dashboardPeople: $("dashboard-people"),
    cashflowTotalSavings: $("cashflow-total-savings"),
    cashflowAverageSavings: $("cashflow-average-savings"),
    cashflowTotalExpenses: $("cashflow-total-expenses"),
    expenseTreemap: $("expense-treemap"),
    cashflowLineChart: $("cashflow-line-chart"),
    monthlySavingsGrid: $("monthly-savings-grid"),
    cashflowMethod: $("cashflow-method"),
    taskSummary: $("task-summary"),
    gantt: $("gantt"),
    ganttZoom: $("gantt-zoom"),
    btnGanttToday: $("btn-gantt-today"),
    btnNewTask: $("btn-new-task"),
    generalNotes: $("general-notes"),
    generalNotesStatus: $("general-notes-status"),
    taskDialog: $("task-dialog"),
    taskForm: $("task-form"),
    taskDialogTitle: $("task-dialog-title"),
    taskDateBadge: $("task-date-badge"),
    taskId: $("task-id"),
    taskTitle: $("task-title"),
    taskDescription: $("task-description"),
    taskPriority: $("task-priority"),
    taskSequence: $("task-sequence"),
    taskStart: $("task-start"),
    taskEnd: $("task-end"),
    taskStatus: $("task-status"),
    taskExpense: $("task-expense"),
    taskIcon: $("task-icon"),
    taskFormError: $("task-form-error"),
    btnDeleteTask: $("btn-delete-task"),
    btnCancelTask: $("btn-cancel-task"),
    priority: $("filter-priority"),
    category: $("filter-category"),
    search: $("filter-search"),
    rows: $("expense-rows"),
    empty: $("empty-state"),
    totalFiltered: $("total-filtered"),
    totalAll: $("total-all"),
    countFiltered: $("count-filtered"),
    btnNew: $("btn-new"),
    dialog: $("expense-dialog"),
    form: $("expense-form"),
    dialogTitle: $("dialog-title"),
    fieldId: $("field-id"),
    fieldPriority: $("field-priority"),
    fieldCategory: $("field-category"),
    fieldDescription: $("field-description"),
    fieldIconKey: $("field-icon-key"),
    iconPreview: $("icon-preview"),
    iconPicker: $("icon-picker"),
    fieldValue: $("field-value"),
    fieldQuantity: $("field-quantity"),
    fieldUnit: $("field-unit"),
    fieldUnitPrice: $("field-unit-price"),
    fieldVendor: $("field-vendor"),
    fieldProductUrl: $("field-product-url"),
    fieldPriceNotes: $("field-price-notes"),
    formError: $("form-error"),
    btnCancel: $("btn-cancel"),
    categorySuggestions: $("category-suggestions"),
    houseBlueprint: $("house-blueprint"),
    houseLot: $("house-lot"),
    houseExterior: $("house-exterior"),
    houseRooms: $("house-rooms"),
    houseAudit: $("house-audit"),
    house3dStatus: $("house-3d-status"),
    house3dAssumptions: $("house-3d-assumptions"),
    projectOverview: $("project-overview"),
    promptOutput: $("prompt-output"),
    promptMissingOnly: $("prompt-missing-only"),
    btnGenPrompt: $("btn-gen-prompt"),
    btnCopyPrompt: $("btn-copy-prompt"),
    btnDlPrompt: $("btn-dl-prompt"),
    packInput: $("pack-input"),
    packFile: $("pack-file"),
    btnPreviewImport: $("btn-preview-import"),
    btnCommitImport: $("btn-commit-import"),
    importStatus: $("import-status"),
    importPreviewRows: $("import-preview-rows"),
    fixOutput: $("fix-output"),
    btnCopyFix: $("btn-copy-fix"),
    btnDlFix: $("btn-dl-fix"),
  };

  const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  const formatMoney = (value) => money.format(Number(value || 0));
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
  const escapeAttr = escapeHtml;
  const iso = (date) => date.toISOString().slice(0, 10);
  const parseDate = (value) => new Date(`${value}T12:00:00`);
  const addDays = (value, days) => {
    const date = typeof value === "string" ? parseDate(value) : new Date(value);
    date.setDate(date.getDate() + days);
    return iso(date);
  };
  const dayDiff = (from, to) => Math.round((parseDate(to) - parseDate(from)) / 86400000);

  function setStatus(element, tone, text) {
    if (!element) return;
    element.textContent = text;
    element.classList.remove("hidden", "ok", "err", "warn");
    if (tone) element.classList.add(tone);
  }

  async function request(url, options = {}) {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok || payload.ok === false) throw new Error(payload.error || "Falha na operação");
    return payload;
  }

  function iconEntry(key, kind = "expense") {
    const catalog = state.iconCatalog;
    const fallback = (catalog.defaults || {})[kind] || catalog.defaults.expense || "home-expense";
    return catalog.icons[key] || catalog.icons[fallback] || null;
  }

  function iconMarkup(key, alt, size = "sm") {
    const icon = iconEntry(key);
    if (!icon) return "";
    return `<span class="item-icon item-icon-${size}"><img src="${escapeAttr(icon.url)}" alt="${escapeAttr(alt || icon.label || "")}" loading="lazy"></span>`;
  }

  function itemLabel(description, key, note = "") {
    return `<div class="item-label">${iconMarkup(key, description)}<span><strong>${escapeHtml(description)}</strong>${note ? `<small>${escapeHtml(note)}</small>` : ""}</span></div>`;
  }

  function fillSelect(select, values, allLabel) {
    const current = select.value;
    select.innerHTML = allLabel ? `<option value="">${escapeHtml(allLabel)}</option>` : "";
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = String(value);
      option.textContent = String(value);
      select.appendChild(option);
    });
    if ([...select.options].some((option) => option.value === current)) select.value = current;
  }

  function renderFilters() {
    fillSelect(els.priority, [...new Set(state.expenses.map((item) => item.priority))].sort((a, b) => a - b), "Todas");
    fillSelect(els.category, [...new Set(state.expenses.map((item) => item.category))].sort(), "Todas");
    els.categorySuggestions.innerHTML = [...new Set(state.expenses.map((item) => item.category))]
      .sort().map((value) => `<option value="${escapeAttr(value)}"></option>`).join("");
  }

  function filteredExpenses() {
    const term = els.search.value.trim().toLowerCase();
    return state.expenses.filter((item) => {
      if (els.priority.value && String(item.priority) !== els.priority.value) return false;
      if (els.category.value && item.category !== els.category.value) return false;
      return !term || `${item.category} ${item.description} ${item.vendor || ""}`.toLowerCase().includes(term);
    });
  }

  function priceCell(item) {
    const parts = [];
    if (item.unit_price != null) parts.push(formatMoney(item.unit_price));
    if (item.vendor) parts.push(escapeHtml(item.vendor));
    if (item.product_url) parts.push(`<a class="link-btn" href="${escapeAttr(item.product_url)}" target="_blank" rel="noopener">abrir</a>`);
    return parts.join(" · ") || "—";
  }

  function renderExpenseTable() {
    const rows = filteredExpenses();
    els.totalFiltered.textContent = formatMoney(rows.reduce((sum, item) => sum + Number(item.value || 0), 0));
    els.totalAll.textContent = formatMoney(state.totals.all);
    els.countFiltered.textContent = String(rows.length);
    els.empty.classList.toggle("hidden", rows.length > 0);
    els.rows.innerHTML = rows.map((item) => `<tr>
      <td><span class="badge">${item.priority}</span></td><td>${escapeHtml(item.category)}</td>
      <td>${itemLabel(item.description, item.icon_key)}</td><td class="num">${formatMoney(item.value)}</td>
      <td>${priceCell(item)}</td><td class="actions"><button class="btn" data-edit-expense="${item.id}">Editar</button><button class="btn danger" data-delete-expense="${item.id}">Excluir</button></td>
    </tr>`).join("");
  }

  function cashflowMonthLabel(value) {
    const [year, month] = value.split("-").map(Number);
    return new Intl.DateTimeFormat("pt-BR", { month: "short", year: "2-digit", timeZone: "UTC" })
      .format(new Date(Date.UTC(year, month - 1, 1))).replace(".", "");
  }

  function treemapLayout(items, x = 0, y = 0, width = 1000, height = 360) {
    if (!items.length) return [];
    if (items.length === 1) return [{ ...items[0], x, y, width, height }];
    const total = items.reduce((sum, item) => sum + item.value, 0);
    let split = 1;
    let running = items[0].value;
    while (split < items.length - 1 && running + items[split].value <= total / 2) {
      running += items[split].value;
      split += 1;
    }
    const first = items.slice(0, split);
    const second = items.slice(split);
    const firstTotal = first.reduce((sum, item) => sum + item.value, 0);
    const ratio = firstTotal / total;
    if (width >= height) {
      const firstWidth = width * ratio;
      return [...treemapLayout(first, x, y, firstWidth, height), ...treemapLayout(second, x + firstWidth, y, width - firstWidth, height)];
    }
    const firstHeight = height * ratio;
    return [...treemapLayout(first, x, y, width, firstHeight), ...treemapLayout(second, x, y + firstHeight, width, height - firstHeight)];
  }

  function renderCashflow(payload) {
    const months = payload.months || [];
    const categories = payload.categories || [];
    const totalSavings = months.reduce((sum, item) => sum + Number(item.net_savings || 0), 0);
    const totalIncome = months.reduce((sum, item) => sum + Number(item.gross_income || 0), 0);
    const totalExpenses = totalIncome - totalSavings;
    els.cashflowTotalSavings.textContent = formatMoney(totalSavings);
    els.cashflowAverageSavings.textContent = formatMoney(months.length ? totalSavings / months.length : 0);
    els.cashflowTotalExpenses.textContent = formatMoney(totalExpenses);

    const categoryTotals = categories.map((category, index) => ({
      ...category,
      value: months.reduce((sum, month) => sum + Number(month[category.key] || 0), 0),
      color: ["#f1c40f", "#3498db", "#9b59b6", "#e67e22", "#2ecc71", "#e74c3c"][index % 6],
    })).sort((a, b) => b.value - a.value);
    const rectangles = treemapLayout(categoryTotals);
    els.expenseTreemap.innerHTML = `<svg viewBox="0 0 1000 360" role="img" aria-label="Treemap da distribuição das despesas">${rectangles.map((item) => `
      <g><rect x="${item.x + 2}" y="${item.y + 2}" width="${Math.max(0, item.width - 4)}" height="${Math.max(0, item.height - 4)}" rx="8" fill="${item.color}" fill-opacity=".78"></rect>
      <text x="${item.x + 15}" y="${item.y + 27}" class="treemap-label">${escapeHtml(item.label)}</text>
      <text x="${item.x + 15}" y="${item.y + 49}" class="treemap-value">${formatMoney(item.value)}</text>
      <title>${escapeHtml(item.label)}: ${formatMoney(item.value)}</title></g>`).join("")}</svg>`;

    const width = 1000;
    const height = 280;
    const margin = { left: 62, right: 22, top: 20, bottom: 42 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const maximum = Math.max(3000, ...months.map((item) => Number(item.net_savings || 0)));
    const point = (item, index) => ({
      x: margin.left + (months.length > 1 ? index / (months.length - 1) * plotWidth : 0),
      y: margin.top + plotHeight - Number(item.net_savings || 0) / maximum * plotHeight,
      item,
    });
    const points = months.map(point);
    const polyline = points.map(({ x, y }) => `${x},${y}`).join(" ");
    const area = `${margin.left},${margin.top + plotHeight} ${polyline} ${margin.left + plotWidth},${margin.top + plotHeight}`;
    const grid = [0, .25, .5, .75, 1].map((ratio) => {
      const y = margin.top + plotHeight - ratio * plotHeight;
      return `<line x1="${margin.left}" y1="${y}" x2="${margin.left + plotWidth}" y2="${y}" class="cashflow-grid-line"></line><text x="${margin.left - 9}" y="${y + 4}" text-anchor="end" class="cashflow-axis-label">${formatMoney(maximum * ratio).replace(",00", "")}</text>`;
    }).join("");
    els.cashflowLineChart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Fluxo de caixa líquido mensal projetado">${grid}<polygon points="${area}" class="cashflow-area"></polygon><polyline points="${polyline}" class="cashflow-line"></polyline>${points.map(({ x, y, item }, index) => `<g><circle cx="${x}" cy="${y}" r="5" class="cashflow-point"></circle><title>${cashflowMonthLabel(item.month)}: ${formatMoney(item.net_savings)}</title>${index % 2 === 0 || index === points.length - 1 ? `<text x="${x}" y="${height - 15}" text-anchor="middle" class="cashflow-axis-label">${cashflowMonthLabel(item.month)}</text>` : ""}</g>`).join("")}</svg>`;

    let cumulative = 0;
    els.monthlySavingsGrid.innerHTML = months.map((item) => {
      cumulative += Number(item.net_savings || 0);
      return `<article><span>${cashflowMonthLabel(item.month)}${item.estimated ? " · estimado" : ""}</span><strong>${formatMoney(item.net_savings)}</strong><small>Acumulado ${formatMoney(cumulative)}</small></article>`;
    }).join("");
    els.cashflowMethod.textContent = (payload.interpolation || {}).method || "";
  }

  function renderDashboard() {
    els.dashTotalAll.textContent = formatMoney(state.totals.all);
    els.dashTotalMaterials.textContent = formatMoney(state.totals.materials);
    els.dashTotalServices.textContent = formatMoney(state.totals.services);
    const funding = (state.project || {}).funding || {};
    const sources = funding.sources || [];
    const fundsTotal = sources.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    els.fundsTotal.textContent = formatMoney(fundsTotal);
    els.fundsDetail.textContent = sources.map((item) => `${item.label}: ${formatMoney(item.amount)}`).join(" · ");
    const coverage = state.totals.all ? Math.min(999, fundsTotal / state.totals.all * 100) : 0;
    els.overallCoverage.textContent = `${coverage.toFixed(1).replace(".", ",")}%`;
    els.coverageDonut.style.setProperty("--coverage-angle", `${Math.min(100, coverage) * 3.6}deg`);
    els.coverageDonut.setAttribute("aria-label", `${coverage.toFixed(1).replace(".", ",")}% do orçamento coberto`);
    els.coverageFunded.textContent = formatMoney(fundsTotal);
    const gap = fundsTotal - Number(state.totals.all || 0);
    els.overallGap.textContent = gap >= 0 ? `Margem de ${formatMoney(gap)}` : `Lacuna de ${formatMoney(Math.abs(gap))}`;
    const categories = Object.entries(state.totals.by_category || {});
    const maximum = Math.max(1, ...categories.map(([, value]) => Number(value)));
    els.categoryChart.innerHTML = categories.map(([label, value]) => `<div class="budget-bar-row"><div class="budget-bar-head"><span>${escapeHtml(label)}</span><strong>${formatMoney(value)}</strong></div><div class="budget-bar-track"><span style="width:${Math.max(1, Number(value) / maximum * 100)}%"></span></div></div>`).join("");
    const people = ((state.project || {}).people || []);
    els.dashboardPeople.innerHTML = people.map((person) => `<article class="dashboard-person">
      <img src="${escapeAttr(person.image_url)}" alt="${escapeAttr(person.name)}" loading="lazy">
      <div><strong>${escapeHtml(person.name)}</strong><span>${escapeHtml(person.role || person.story_role || "")}</span></div>
    </article>`).join("");
    els.dashMaterials.innerHTML = state.materials.map((item) => `<tr><td><span class="badge">${item.priority}</span></td><td>${itemLabel(item.description, item.icon_key)}</td><td class="num">${item.quantity ?? "—"}</td><td>${escapeHtml(item.unit || "—")}</td><td class="num">${formatMoney(item.value)}</td><td>${escapeHtml(item.vendor || "—")}</td></tr>`).join("");
    renderGantt();
  }

  function sortedTasks() {
    return [...state.tasks].sort((a, b) => a.priority - b.priority || a.sequence - b.sequence || a.start_date.localeCompare(b.start_date));
  }

  function ganttGeometry(tasks) {
    const dates = tasks.flatMap((task) => [parseDate(task.start_date), parseDate(task.end_date)]);
    const today = parseDate(iso(new Date()));
    const start = new Date(Math.min(today, ...dates));
    start.setDate(start.getDate() - 7);
    const end = new Date(Math.max(today, ...dates));
    end.setDate(end.getDate() + 14);
    const dayWidth = { day: 34, week: 14, month: 5 }[state.zoom] || 14;
    return { start: iso(start), end: iso(end), days: dayDiff(iso(start), iso(end)) + 1, dayWidth };
  }

  function ganttHeader(geometry) {
    const chunks = [];
    let cursor = geometry.start;
    while (cursor <= geometry.end) {
      const date = parseDate(cursor);
      const isMajor = state.zoom === "day" ? date.getDate() === 1 : date.getDay() === 1;
      if (state.zoom === "month") {
        if (date.getDate() === 1) chunks.push({ date: cursor, label: date.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" }) });
      } else if (state.zoom === "week") {
        if (date.getDay() === 1) chunks.push({ date: cursor, label: date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }) });
      } else {
        chunks.push({ date: cursor, label: isMajor ? date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }) : String(date.getDate()) });
      }
      cursor = addDays(cursor, 1);
    }
    return chunks.map((chunk) => `<span class="gantt-tick" style="left:${dayDiff(geometry.start, chunk.date) * geometry.dayWidth}px">${escapeHtml(chunk.label)}</span>`).join("");
  }

  function renderGantt() {
    if (!els.gantt) return;
    const tasks = sortedTasks();
    const counts = tasks.reduce((map, task) => ((map[task.status] = (map[task.status] || 0) + 1), map), {});
    els.taskSummary.innerHTML = Object.entries(statusLabels).map(([key, label]) => `<span class="task-count status-${key}"><strong>${counts[key] || 0}</strong>${label}</span>`).join("");
    if (!tasks.length) {
      els.gantt.innerHTML = `<div class="gantt-empty">Nenhuma tarefa. Crie a primeira para começar o cronograma.</div>`;
      return;
    }
    const geometry = ganttGeometry(tasks);
    els.gantt.style.setProperty("--day-width", `${geometry.dayWidth}px`);
    els.gantt.style.setProperty("--timeline-width", `${geometry.days * geometry.dayWidth}px`);
    const todayLeft = dayDiff(geometry.start, iso(new Date())) * geometry.dayWidth;
    els.gantt.innerHTML = `<div class="gantt-label-head">Tarefa / prioridade</div>
      <div class="gantt-scroll" id="gantt-scroll"><div class="gantt-timeline">
        <div class="gantt-header">${ganttHeader(geometry)}</div>
        <div class="gantt-today" style="left:${todayLeft}px"><span>Hoje</span></div>
        ${tasks.map((task) => {
          const left = dayDiff(geometry.start, task.start_date) * geometry.dayWidth;
          const width = Math.max(geometry.dayWidth, (dayDiff(task.start_date, task.end_date) + 1) * geometry.dayWidth);
          return `<div class="gantt-track" data-track-id="${task.id}">
            <button type="button" class="gantt-bar status-${task.status}" data-task-bar="${task.id}" style="left:${left}px;width:${width}px" title="${escapeAttr(`${task.title} · ${task.start_date} — ${task.end_date}`)}">
              <i class="gantt-handle start" data-resize="start"></i><span>${escapeHtml(task.title)}</span><i class="gantt-handle end" data-resize="end"></i>
            </button></div>`;
        }).join("")}
      </div></div>
      <div class="gantt-labels">${tasks.map((task) => `<button type="button" class="gantt-label-row" draggable="true" data-task-label="${task.id}" title="Arraste para trocar a sequência">
        ${iconMarkup(task.icon_key, task.title)}<span><strong>${escapeHtml(task.title)}</strong><small>P${task.priority} · #${task.sequence} · ${escapeHtml(statusLabels[task.status])}${task.date_status === "estimated" ? " · estimada" : ""}</small></span>
      </button>`).join("")}</div>`;
    bindGanttInteractions(geometry);
  }

  function bindGanttInteractions(geometry) {
    let draggedLabel = "";
    els.gantt.querySelectorAll("[data-task-label]").forEach((row) => {
      row.addEventListener("click", () => openTaskDialog(state.tasks.find((task) => task.id === row.dataset.taskLabel)));
      row.addEventListener("dragstart", () => { draggedLabel = row.dataset.taskLabel; row.classList.add("dragging"); });
      row.addEventListener("dragend", () => row.classList.remove("dragging"));
      row.addEventListener("dragover", (event) => event.preventDefault());
      row.addEventListener("drop", async (event) => {
        event.preventDefault();
        const targetId = row.dataset.taskLabel;
        if (!draggedLabel || draggedLabel === targetId) return;
        const first = state.tasks.find((task) => task.id === draggedLabel);
        const second = state.tasks.find((task) => task.id === targetId);
        if (!first || !second) return;
        const firstSequence = first.sequence;
        first.sequence = second.sequence;
        second.sequence = firstSequence;
        renderGantt();
        try {
          await saveTaskRecord(first);
          await saveTaskRecord(second);
        } catch (error) {
          await loadTasks();
          setStatus(els.appStatus, "err", error.message);
        }
      });
    });
    els.gantt.querySelectorAll("[data-task-bar]").forEach((bar) => {
      bar.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        const task = state.tasks.find((item) => item.id === bar.dataset.taskBar);
        if (!task) return;
        const mode = event.target.dataset.resize || "move";
        const originX = event.clientX;
        let moved = false;
        bar.setPointerCapture(event.pointerId);
        const onMove = (moveEvent) => {
          const delta = moveEvent.clientX - originX;
          moved ||= Math.abs(delta) > 3;
          bar.style.transform = `translateX(${delta}px)`;
        };
        const onUp = async (upEvent) => {
          bar.removeEventListener("pointermove", onMove);
          bar.removeEventListener("pointerup", onUp);
          bar.style.transform = "";
          if (!moved) {
            openTaskDialog(task);
            return;
          }
          const deltaDays = Math.round((upEvent.clientX - originX) / geometry.dayWidth);
          if (!deltaDays) return;
          const previous = { start_date: task.start_date, end_date: task.end_date, date_status: task.date_status };
          if (mode === "move") {
            task.start_date = addDays(task.start_date, deltaDays);
            task.end_date = addDays(task.end_date, deltaDays);
          } else if (mode === "start") {
            const next = addDays(task.start_date, deltaDays);
            if (next <= task.end_date) task.start_date = next;
          } else {
            const next = addDays(task.end_date, deltaDays);
            if (next >= task.start_date) task.end_date = next;
          }
          task.date_status = "confirmed";
          renderGantt();
          try {
            await saveTaskRecord(task);
          } catch (error) {
            Object.assign(task, previous);
            renderGantt();
            setStatus(els.appStatus, "err", error.message);
          }
        };
        bar.addEventListener("pointermove", onMove);
        bar.addEventListener("pointerup", onUp);
      });
    });
  }

  async function saveTaskRecord(task) {
    const payload = await request("/api/tasks", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(task),
    });
    state.tasks = payload.tasks || state.tasks;
    return payload;
  }

  function fillTaskOptions() {
    els.taskExpense.innerHTML = `<option value="">Nenhuma</option>${state.expenses.map((item) => `<option value="${item.id}">${escapeHtml(`${item.id} · ${item.description}`)}</option>`).join("")}`;
    els.taskIcon.innerHTML = Object.entries(state.iconCatalog.icons || {}).sort((a, b) => String(a[1].label).localeCompare(String(b[1].label), "pt-BR")).map(([key, item]) => `<option value="${escapeAttr(key)}">${escapeHtml(item.label || key)}</option>`).join("");
  }

  function openTaskDialog(task = null) {
    fillTaskOptions();
    const tomorrow = addDays(iso(new Date()), 1);
    els.taskDialogTitle.textContent = task ? "Editar tarefa" : "Nova tarefa";
    els.taskId.value = task?.id || "";
    els.taskTitle.value = task?.title || "";
    els.taskDescription.value = task?.description || "";
    els.taskPriority.value = task?.priority || 1;
    els.taskSequence.value = task?.sequence || (Math.max(0, ...state.tasks.map((item) => item.sequence)) + 1);
    els.taskStart.value = task?.start_date || tomorrow;
    els.taskEnd.value = task?.end_date || addDays(tomorrow, 2);
    els.taskStatus.value = task?.status || "pending";
    els.taskExpense.value = task?.expense_id || "";
    els.taskIcon.value = task?.icon_key || "home-expense";
    els.taskDateBadge.textContent = task?.date_status === "estimated" ? "Datas estimadas" : "Datas confirmadas";
    els.btnDeleteTask.classList.toggle("hidden", !task);
    els.taskFormError.classList.add("hidden");
    els.taskDialog.showModal();
    els.taskTitle.focus();
  }

  async function submitTask(event) {
    event.preventDefault();
    const payload = {
      id: els.taskId.value,
      title: els.taskTitle.value.trim(),
      description: els.taskDescription.value.trim(),
      priority: Number(els.taskPriority.value),
      sequence: Number(els.taskSequence.value),
      start_date: els.taskStart.value,
      end_date: els.taskEnd.value,
      status: els.taskStatus.value,
      expense_id: els.taskExpense.value,
      icon_key: els.taskIcon.value,
      date_status: "confirmed",
    };
    try {
      const result = await saveTaskRecord(payload);
      state.tasks = result.tasks;
      els.taskDialog.close();
      renderGantt();
      setStatus(els.appStatus, "ok", "Tarefa salva. Clique em “Salvar tudo” para enviar a cópia segura.");
    } catch (error) {
      setStatus(els.taskFormError, "err", error.message);
    }
  }

  async function deleteTask() {
    const id = els.taskId.value;
    if (!id || !window.confirm("Excluir esta tarefa?")) return;
    try {
      const result = await request(`/api/tasks/${encodeURIComponent(id)}`, { method: "DELETE" });
      state.tasks = result.tasks;
      els.taskDialog.close();
      renderGantt();
      setStatus(els.appStatus, "ok", "Tarefa excluída.");
    } catch (error) {
      setStatus(els.taskFormError, "err", error.message);
    }
  }

  function renderIconPicker(selected) {
    const icons = Object.entries(state.iconCatalog.icons || {}).sort((a, b) => String(a[1].label).localeCompare(String(b[1].label), "pt-BR"));
    const key = state.iconCatalog.icons[selected] ? selected : (state.iconCatalog.defaults.expense || "home-expense");
    els.fieldIconKey.value = key;
    const entry = iconEntry(key);
    els.iconPreview.innerHTML = entry ? `${iconMarkup(key, entry.label, "lg")}<span>${escapeHtml(entry.label)}</span>` : "";
    els.iconPicker.innerHTML = icons.map(([iconKey, icon]) => `<button type="button" class="icon-choice ${iconKey === key ? "selected" : ""}" data-icon-key="${escapeAttr(iconKey)}" title="${escapeAttr(icon.label)}">${iconMarkup(iconKey, icon.label, "picker")}<span>${escapeHtml(icon.label)}</span></button>`).join("");
  }

  function openExpenseDialog(item = null) {
    els.dialogTitle.textContent = item ? "Editar despesa" : "Nova despesa";
    els.fieldId.value = item?.id || "";
    els.fieldPriority.value = item?.priority || 1;
    els.fieldCategory.value = item?.category || "";
    els.fieldDescription.value = item?.description || "";
    els.fieldValue.value = item ? Number(item.value).toFixed(2) : "0.00";
    els.fieldQuantity.value = item?.quantity ?? "";
    els.fieldUnit.value = item?.unit || "";
    els.fieldUnitPrice.value = item?.unit_price ?? "";
    els.fieldVendor.value = item?.vendor || "";
    els.fieldProductUrl.value = item?.product_url || "";
    els.fieldPriceNotes.value = item?.price_notes || "";
    renderIconPicker(item?.icon_key || "");
    els.formError.classList.add("hidden");
    els.dialog.showModal();
    els.fieldDescription.focus();
  }

  async function submitExpense(event) {
    event.preventDefault();
    const payload = {
      id: els.fieldId.value,
      priority: Number(els.fieldPriority.value),
      category: els.fieldCategory.value.trim(),
      description: els.fieldDescription.value.trim(),
      icon_key: els.fieldIconKey.value,
      value: Number(els.fieldValue.value),
      quantity: els.fieldQuantity.value,
      unit: els.fieldUnit.value.trim(),
      unit_price: els.fieldUnitPrice.value,
      vendor: els.fieldVendor.value.trim(),
      product_url: els.fieldProductUrl.value.trim(),
      price_notes: els.fieldPriceNotes.value.trim(),
    };
    try {
      const result = await request("/api/expenses", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      applyExpenseState(result.state);
      els.dialog.close();
      await pushToRemote();
    } catch (error) {
      setStatus(els.formError, "err", error.message);
    }
  }

  async function deleteExpense(id) {
    const item = state.expenses.find((expense) => expense.id === id);
    if (!window.confirm(`Excluir “${item?.description || id}”?`)) return;
    const result = await request(`/api/expenses/${encodeURIComponent(id)}`, { method: "DELETE" });
    applyExpenseState(result.state);
    await pushToRemote();
  }

  function applyExpenseState(payload) {
    state.expenses = payload.expenses || [];
    state.totals = payload.totals || state.totals;
    state.materials = payload.materials || [];
    state.iconCatalog = payload.icon_catalog || state.iconCatalog;
    renderFilters();
    renderExpenseTable();
    renderDashboard();
  }

  async function loadState() {
    applyExpenseState(await request("/api/state"));
  }

  async function loadCashflow() {
    renderCashflow(await request("/api/cashflow"));
  }

  async function loadTasks() {
    const payload = await request("/api/tasks");
    state.tasks = payload.tasks || [];
    renderGantt();
  }

  async function loadNotes() {
    const payload = await request("/api/notes");
    els.generalNotes.value = payload.text || "";
    els.generalNotesStatus.textContent = payload.updated_at ? `Salvo em ${payload.updated_at}` : "Salvo automaticamente";
  }

  let notesSaveTimer = null;
  async function saveNotes() {
    els.generalNotesStatus.textContent = "Salvando...";
    try {
      const payload = await request("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: els.generalNotes.value }),
      });
      els.generalNotesStatus.textContent = `Salvo em ${payload.updated_at}`;
    } catch (error) {
      els.generalNotesStatus.textContent = `Erro ao salvar: ${error.message}`;
      els.generalNotesStatus.classList.add("err");
    }
  }

  async function pushToRemote() {
    els.btnPush.disabled = true;
    setStatus(els.appStatus, "", "Salvando e enviando...");
    try {
      const result = await request("/api/push", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      setStatus(els.appStatus, "ok", result.message || "Dados salvos e enviados.");
      els.pushStatus.textContent = result.pushed ? "Cópia segura atualizada" : "Tudo já estava salvo";
    } catch (error) {
      setStatus(els.appStatus, "err", `Dados locais salvos; envio pendente: ${error.message}`);
    } finally {
      els.btnPush.disabled = false;
    }
  }

  function renderProject(project) {
    if (!els.projectOverview || !project) return;
    const people = (project.people || []).map((person) => `<article class="person-card"><img src="${escapeAttr(person.image_url)}" alt="${escapeAttr(person.name)}"><div><strong>${escapeHtml(person.name)}</strong><span>${escapeHtml(person.role || person.story_role || "")}</span><p>${escapeHtml(person.story_role || "")}</p></div></article>`).join("");
    const contracts = (project.work_contracts || []).map((contract, index) => `<article class="work-contract-card"><div class="work-contract-head"><div><span>Contrato ${String(index + 1).padStart(2, "0")}</span><h4>${escapeHtml(contract.label)}</h4></div><span class="draft-badge">Rascunho não assinado</span></div><p>${escapeHtml((contract.scope || []).length)} itens de escopo</p><a class="btn primary" href="${escapeAttr((contract.document || {}).url)}" target="_blank">Abrir PDF</a></article>`).join("");
    const tools = ((project.construction_resources || {}).required_tools || []).map((tool) => `<article class="required-tool">${iconMarkup(tool.icon_key, tool.name, "tool")}<div><strong>${escapeHtml(tool.name)}</strong><p>${escapeHtml(tool.purpose || "")}</p></div></article>`).join("");
    els.projectOverview.innerHTML = `<h3 class="project-heading">Pessoas do projeto</h3><div class="people-grid">${people}</div><h3 class="project-heading">Contratos de obra</h3><div class="work-contracts-grid">${contracts}</div><h3 class="project-heading">Ferramentas necessárias</h3><div class="required-tools-grid">${tools || "<p>Nenhuma ferramenta cadastrada.</p>"}</div>`;
  }

  async function renderHouse3D(house) {
    const model = house?.model_3d;
    els.house3dAssumptions.innerHTML = (model?.assumptions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    if (!model) return setStatus(els.house3dStatus, "warn", "Geometria 3D indisponível.");
    try {
      const module = await import("/house-3d.js?v=20260916-1");
      module.mountHouse3D(model);
    } catch (error) {
      setStatus(els.house3dStatus, "err", `Não foi possível abrir o modelo 3D: ${error.message}`);
    }
  }

  function renderHouse(payload) {
    if (!payload.ok || !payload.house) return;
    const house = payload.house;
    state.house = house;
    state.project = payload.project || null;
    els.houseBlueprint.src = payload.blueprint_url || "/api/house/blueprint.jpg";
    const lot = house.lot_dimensions_meters || {};
    els.houseLot.innerHTML = `<div><span class="summary-label">Largura</span><strong>${lot.width ?? "—"} m</strong></div><div><span class="summary-label">Comprimento</span><strong>${lot.length ?? "—"} m</strong></div><div><span class="summary-label">Área</span><strong>${lot.area_m2 ?? "—"} m²</strong></div>`;
    els.houseExterior.innerHTML = (house.exterior_spaces || []).map((space) => `<article class="house-card"><h3>${escapeHtml(space.label || space.name)}</h3><p>${escapeHtml(space.notes || space.description || "")}</p></article>`).join("");
    els.houseRooms.innerHTML = (house.interior_rooms || []).map((room) => `<article class="house-card"><h3>${escapeHtml(room.label || room.name)}</h3><p>${escapeHtml(room.measured_dimensions || room.dimensions || "")}</p></article>`).join("");
    const audit = house.blueprint_audit || {};
    els.houseAudit.innerHTML = `<h3>${escapeHtml(audit.status || "Auditoria")}</h3><p>${escapeHtml(audit.summary || "")}</p>`;
    renderProject(state.project);
    renderDashboard();
    renderHouse3D(house);
  }

  async function loadHouse() {
    try { renderHouse(await request("/api/house")); } catch (error) { setStatus(els.appStatus, "err", error.message); }
  }

  async function generatePrompt() {
    const ids = els.promptMissingOnly.checked ? state.materials.filter((item) => item.unit_price == null).map((item) => item.id) : state.materials.map((item) => item.id);
    const result = await request("/api/prompts/price-discovery", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ids }) });
    els.promptOutput.value = result.prompt || result.text || "";
  }

  async function previewImport() {
    const result = await request("/api/import/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pack_text: els.packInput.value, pack_id: "price" }) });
    state.importRows = result.rows || [];
    els.btnCommitImport.disabled = !result.ok || !state.importRows.length;
    setStatus(els.importStatus, result.ok ? "ok" : "err", result.ok ? `${state.importRows.length} linha(s) pronta(s).` : (result.errors || []).join(" · "));
    els.importPreviewRows.innerHTML = state.importRows.map((row) => `<tr><td>${escapeHtml(row.id || "")}</td><td>${escapeHtml(row.description || "")}</td><td>${formatMoney(row.unit_price)}</td><td>${escapeHtml(row.vendor || "")}</td><td>${row.product_url ? `<a href="${escapeAttr(row.product_url)}" target="_blank">abrir</a>` : "—"}</td></tr>`).join("");
    const fix = result.fix_pack || result.fix_output || "";
    els.fixOutput.value = fix;
    els.fixOutput.classList.toggle("hidden", !fix);
    els.btnCopyFix.classList.toggle("hidden", !fix);
    els.btnDlFix.classList.toggle("hidden", !fix);
  }

  async function commitImport() {
    const result = await request("/api/import/commit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rows: state.importRows, pack_text: els.packInput.value, pack_id: "price" }) });
    if (result.state) applyExpenseState(result.state);
    await pushToRemote();
  }

  function downloadText(filename, text) {
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
  }

  function showView(name) {
    document.querySelectorAll(".view").forEach((view) => view.classList.toggle("hidden", view.id !== `view-${name}`));
    document.querySelectorAll(".nav-btn").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
    history.replaceState(null, "", `#${name}`);
  }

  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => showView(button.dataset.view)));
  document.querySelectorAll("[data-view-link]").forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); showView(link.dataset.viewLink); }));
  $("home-link").addEventListener("click", (event) => { event.preventDefault(); showView("dashboard"); });
  document.addEventListener("keydown", (event) => {
    if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const view = { "1": "dashboard", "2": "expenses", "3": "house", "4": "prices", h: "dashboard" }[event.key.toLowerCase()];
    if (view) { event.preventDefault(); showView(view); }
  });

  els.priority.addEventListener("change", renderExpenseTable);
  els.category.addEventListener("change", renderExpenseTable);
  els.search.addEventListener("input", renderExpenseTable);
  els.btnNew.addEventListener("click", () => openExpenseDialog());
  els.form.addEventListener("submit", submitExpense);
  els.btnCancel.addEventListener("click", () => els.dialog.close());
  els.iconPicker.addEventListener("click", (event) => {
    const button = event.target.closest("[data-icon-key]");
    if (button) renderIconPicker(button.dataset.iconKey);
  });
  els.rows.addEventListener("click", async (event) => {
    const edit = event.target.closest("[data-edit-expense]");
    const remove = event.target.closest("[data-delete-expense]");
    if (edit) openExpenseDialog(state.expenses.find((item) => item.id === edit.dataset.editExpense));
    if (remove) {
      try { await deleteExpense(remove.dataset.deleteExpense); } catch (error) { setStatus(els.appStatus, "err", error.message); }
    }
  });
  els.btnPush.addEventListener("click", pushToRemote);
  els.generalNotes.addEventListener("input", () => {
    els.generalNotesStatus.classList.remove("err");
    els.generalNotesStatus.textContent = "Alterações pendentes...";
    clearTimeout(notesSaveTimer);
    notesSaveTimer = setTimeout(saveNotes, 700);
  });
  els.btnNewTask.addEventListener("click", () => openTaskDialog());
  els.taskForm.addEventListener("submit", submitTask);
  els.btnCancelTask.addEventListener("click", () => els.taskDialog.close());
  els.btnDeleteTask.addEventListener("click", deleteTask);
  els.ganttZoom.addEventListener("change", () => { state.zoom = els.ganttZoom.value; renderGantt(); });
  els.btnGanttToday.addEventListener("click", () => {
    const scroll = $("gantt-scroll");
    const line = els.gantt.querySelector(".gantt-today");
    if (scroll && line) scroll.scrollTo({ left: Math.max(0, parseFloat(line.style.left) - scroll.clientWidth / 2), behavior: "smooth" });
  });
  els.btnGenPrompt.addEventListener("click", () => generatePrompt().catch((error) => setStatus(els.appStatus, "err", error.message)));
  els.btnCopyPrompt.addEventListener("click", () => navigator.clipboard.writeText(els.promptOutput.value));
  els.btnDlPrompt.addEventListener("click", () => downloadText("price-discovery-prompt.txt", els.promptOutput.value));
  els.packFile.addEventListener("change", async () => { if (els.packFile.files[0]) els.packInput.value = await els.packFile.files[0].text(); });
  els.btnPreviewImport.addEventListener("click", () => previewImport().catch((error) => setStatus(els.importStatus, "err", error.message)));
  els.btnCommitImport.addEventListener("click", () => commitImport().catch((error) => setStatus(els.importStatus, "err", error.message)));
  els.btnCopyFix.addEventListener("click", () => navigator.clipboard.writeText(els.fixOutput.value));
  els.btnDlFix.addEventListener("click", () => downloadText("price-pack-fix.txt", els.fixOutput.value));

  Promise.all([loadState(), loadTasks(), loadNotes(), loadCashflow(), loadHouse()])
    .then(() => showView(location.hash.slice(1) || "dashboard"))
    .catch((error) => setStatus(els.appStatus, "err", error.message));
})();
