(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const state = {
    expenses: [],
    tasks: [],
    providers: [],
    contracts: [],
    totals: {
      all: 0,
      materials: 0,
      services: 0,
      by_category: {},
      by_priority: {},
    },
    materials: [],
    iconCatalog: { defaults: {}, icons: {} },
    house: null,
    project: null,
    importRows: [],
    zoom: "week",
    expandedMacros: new Set(),
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
    dashboardHoverTooltip: $("dashboard-hover-tooltip"),
    dashboardPeople: $("dashboard-people"),
    cashflowTotalSavings: $("cashflow-total-savings"),
    cashflowAverageSavings: $("cashflow-average-savings"),
    cashflowTotalExpenses: $("cashflow-total-expenses"),
    expenseTreemap: $("expense-treemap"),
    cashflowLineChart: $("cashflow-line-chart"),
    monthlySavingsGrid: $("monthly-savings-grid"),
    cashflowMethod: $("cashflow-method"),
    macroTimeline: $("macro-timeline"),
    taskSummary: $("task-summary"),
    gantt: $("gantt"),
    ganttZoom: $("gantt-zoom"),
    btnGanttToday: $("btn-gantt-today"),
    btnNewTask: $("btn-new-task"),
    btnExpandAll: $("btn-expand-all"),
    btnCollapseAll: $("btn-collapse-all"),
    generalNotes: $("general-notes"),
    generalNotesStatus: $("general-notes-status"),
    taskDialog: $("task-dialog"),
    taskForm: $("task-form"),
    taskDialogTitle: $("task-dialog-title"),
    taskDateBadge: $("task-date-badge"),
    taskId: $("task-id"),
    taskTitle: $("task-title"),
    taskDescription: $("task-description"),
    taskActivityType: $("task-activity-type"),
    taskParent: $("task-parent"),
    taskParentLabel: $("task-parent-label"),
    taskPriority: $("task-priority"),
    taskSequence: $("task-sequence"),
    taskStart: $("task-start"),
    taskEnd: $("task-end"),
    taskStatus: $("task-status"),
    taskExpense: $("task-expense"),
    taskIcon: $("task-icon"),
    taskIconMode: $("task-icon-mode"),
    taskIconPreview: $("task-icon-preview"),
    taskIconPicker: $("task-icon-picker"),
    btnTaskIconAuto: $("btn-task-icon-auto"),
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
    fieldRecordType: $("field-record-type"),
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
    expenseServiceLinks: $("expense-service-links"),
    fieldProvider: $("field-provider"),
    fieldContract: $("field-contract"),
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
    btnModel3dHome: $("btn-model3d-home"),
    btnToggleEditor: $("btn-toggle-editor"),
    btnCloseEditor: $("btn-close-editor"),
    sceneEditorPanel: $("scene-editor-panel"),
    editorSelection: $("editor-selection"),
    editorStatus: $("editor-status"),
    editorSnap: $("editor-snap"),
    editorDimensions: $("editor-dimensions"),
    editorWidth: $("editor-width"),
    editorHeight: $("editor-height"),
    editorDepth: $("editor-depth"),
    btnApplyDimensions: $("btn-apply-dimensions"),
    assetPalette: $("asset-palette"),
    btnDuplicateObject: $("btn-duplicate-object"),
    btnResetObject: $("btn-reset-object"),
    btnDeleteObject: $("btn-delete-object"),
    btnSaveLayout: $("btn-save-layout"),
    btnToggleMedia: $("btn-toggle-media"),
    btnCloseMedia: $("btn-close-media"),
    mediaExportPanel: $("media-export-panel"),
    snapshotFormat: $("snapshot-format"),
    btnCaptureSnapshot: $("btn-capture-snapshot"),
    videoMode: $("video-mode"),
    videoDuration: $("video-duration"),
    btnStartRecording: $("btn-start-recording"),
    btnStopRecording: $("btn-stop-recording"),
    mediaProgressWrap: $("media-progress-wrap"),
    mediaProgress: $("media-progress"),
    mediaTime: $("media-time"),
    mediaResult: $("media-result"),
    mediaImagePreview: $("media-image-preview"),
    mediaVideoPreview: $("media-video-preview"),
    mediaFilename: $("media-filename"),
    btnShareMedia: $("btn-share-media"),
    btnDownloadMedia: $("btn-download-media"),
    mediaStatus: $("media-status"),
    projectOverview: $("project-overview"),
    showArchivedContracts: $("show-archived-contracts"),
    btnNewProvider: $("btn-new-provider"),
    btnNewContract: $("btn-new-contract"),
    contractSummary: $("contract-summary"),
    contractList: $("contract-list"),
    providerList: $("provider-list"),
    providerDialog: $("provider-dialog"),
    providerForm: $("provider-form"),
    providerDialogTitle: $("provider-dialog-title"),
    providerId: $("provider-id"),
    providerName: $("provider-name"),
    providerServiceType: $("provider-service-type"),
    providerContact: $("provider-contact"),
    providerNotes: $("provider-notes"),
    providerFormError: $("provider-form-error"),
    btnArchiveProvider: $("btn-archive-provider"),
    btnCancelProvider: $("btn-cancel-provider"),
    contractDialog: $("contract-dialog"),
    contractForm: $("contract-form"),
    contractDialogTitle: $("contract-dialog-title"),
    contractId: $("contract-id"),
    contractType: $("contract-type"),
    contractStatus: $("contract-status"),
    contractTitle: $("contract-title"),
    contractProvider: $("contract-provider"),
    contractAmount: $("contract-amount"),
    contractStart: $("contract-start"),
    contractEnd: $("contract-end"),
    contractExpenses: $("contract-expenses"),
    contractNotes: $("contract-notes"),
    contractPdf: $("contract-pdf"),
    contractFormError: $("contract-form-error"),
    btnArchiveContract: $("btn-archive-contract"),
    btnCancelContract: $("btn-cancel-contract"),
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

  const money = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
  const formatMoney = (value) => money.format(Number(value || 0));
  const escapeHtml = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (char) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[char],
    );
  const escapeAttr = escapeHtml;
  const iso = (date) => date.toISOString().slice(0, 10);
  const parseDate = (value) => new Date(`${value}T12:00:00`);
  const addDays = (value, days) => {
    const date = typeof value === "string" ? parseDate(value) : new Date(value);
    date.setDate(date.getDate() + days);
    return iso(date);
  };
  const dayDiff = (from, to) =>
    Math.round((parseDate(to) - parseDate(from)) / 86400000);

  function setStatus(element, tone, text) {
    if (!element) return;
    element.textContent = text;
    element.classList.remove("hidden", "ok", "err", "warn");
    if (tone) element.classList.add(tone);
  }

  async function request(url, options = {}) {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok || payload.ok === false)
      throw new Error(payload.error || "Falha na operação");
    return payload;
  }

  function iconEntry(key, kind = "expense") {
    const catalog = state.iconCatalog;
    const fallback =
      (catalog.defaults || {})[kind] ||
      catalog.defaults.expense ||
      "home-expense";
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
    select.innerHTML = allLabel
      ? `<option value="">${escapeHtml(allLabel)}</option>`
      : "";
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = String(value);
      option.textContent = String(value);
      select.appendChild(option);
    });
    if ([...select.options].some((option) => option.value === current))
      select.value = current;
  }

  function renderFilters() {
    fillSelect(
      els.priority,
      [...new Set(state.expenses.map((item) => item.priority))].sort(
        (a, b) => a - b,
      ),
      "Todas",
    );
    fillSelect(
      els.category,
      [...new Set(state.expenses.map((item) => item.category))].sort(),
      "Todas",
    );
    els.categorySuggestions.innerHTML = [
      ...new Set(state.expenses.map((item) => item.category)),
    ]
      .sort()
      .map((value) => `<option value="${escapeAttr(value)}"></option>`)
      .join("");
  }

  function filteredExpenses() {
    const term = els.search.value.trim().toLowerCase();
    return state.expenses.filter((item) => {
      if (els.priority.value && String(item.priority) !== els.priority.value)
        return false;
      if (els.category.value && item.category !== els.category.value)
        return false;
      return (
        !term ||
        `${item.category} ${item.description} ${item.vendor || ""}`
          .toLowerCase()
          .includes(term)
      );
    });
  }

  function priceCell(item) {
    const parts = [];
    if (item.unit_price != null) parts.push(formatMoney(item.unit_price));
    if (item.vendor) parts.push(escapeHtml(item.vendor));
    if (item.product_url)
      parts.push(
        `<a class="link-btn" href="${escapeAttr(item.product_url)}" target="_blank" rel="noopener">abrir</a>`,
      );
    return parts.join(" · ") || "—";
  }

  function renderExpenseTable() {
    const rows = filteredExpenses();
    els.totalFiltered.textContent = formatMoney(
      rows.reduce((sum, item) => sum + Number(item.value || 0), 0),
    );
    els.totalAll.textContent = formatMoney(state.totals.all);
    els.countFiltered.textContent = String(rows.length);
    els.empty.classList.toggle("hidden", rows.length > 0);
    els.rows.innerHTML = rows
      .map(
        (item) => `<tr>
      <td><span class="badge">${item.priority}</span></td><td>${escapeHtml(item.category)}</td>
      <td>${itemLabel(item.description, item.icon_key)}</td><td class="num">${formatMoney(item.value)}</td>
      <td>${priceCell(item)}</td><td class="actions"><button class="btn" data-edit-expense="${item.id}">Editar</button><button class="btn danger" data-delete-expense="${item.id}">Excluir</button></td>
    </tr>`,
      )
      .join("");
  }

  function cashflowMonthLabel(value) {
    const [year, month] = value.split("-").map(Number);
    return new Intl.DateTimeFormat("pt-BR", {
      month: "short",
      year: "2-digit",
      timeZone: "UTC",
    })
      .format(new Date(Date.UTC(year, month - 1, 1)))
      .replace(".", "");
  }

  function treemapLayout(items, x = 0, y = 0, width = 1000, height = 360) {
    if (!items.length) return [];
    if (items.length === 1) return [{ ...items[0], x, y, width, height }];
    const total = items.reduce((sum, item) => sum + item.value, 0);
    let split = 1;
    let running = items[0].value;
    while (
      split < items.length - 1 &&
      running + items[split].value <= total / 2
    ) {
      running += items[split].value;
      split += 1;
    }
    const first = items.slice(0, split);
    const second = items.slice(split);
    const firstTotal = first.reduce((sum, item) => sum + item.value, 0);
    const ratio = firstTotal / total;
    if (width >= height) {
      const firstWidth = width * ratio;
      return [
        ...treemapLayout(first, x, y, firstWidth, height),
        ...treemapLayout(second, x + firstWidth, y, width - firstWidth, height),
      ];
    }
    const firstHeight = height * ratio;
    return [
      ...treemapLayout(first, x, y, width, firstHeight),
      ...treemapLayout(second, x, y + firstHeight, width, height - firstHeight),
    ];
  }

  function renderCashflow(payload) {
    const months = payload.months || [];
    const categories = payload.categories || [];
    const totalSavings = months.reduce(
      (sum, item) => sum + Number(item.net_savings || 0),
      0,
    );
    const totalIncome = months.reduce(
      (sum, item) => sum + Number(item.gross_income || 0),
      0,
    );
    const totalExpenses = totalIncome - totalSavings;
    els.cashflowTotalSavings.textContent = formatMoney(totalSavings);
    els.cashflowAverageSavings.textContent = formatMoney(
      months.length ? totalSavings / months.length : 0,
    );
    els.cashflowTotalExpenses.textContent = formatMoney(totalExpenses);

    const categoryTotals = categories
      .map((category, index) => ({
        ...category,
        value: months.reduce(
          (sum, month) => sum + Number(month[category.key] || 0),
          0,
        ),
        color: [
          "#f1c40f",
          "#3498db",
          "#9b59b6",
          "#e67e22",
          "#2ecc71",
          "#e74c3c",
        ][index % 6],
      }))
      .sort((a, b) => b.value - a.value);
    const rectangles = treemapLayout(categoryTotals);
    els.expenseTreemap.innerHTML = `<svg viewBox="0 0 1000 360" role="img" aria-label="Treemap da distribuição das despesas">${rectangles
      .map(
        (item) => `
      <g><rect x="${item.x + 2}" y="${item.y + 2}" width="${Math.max(0, item.width - 4)}" height="${Math.max(0, item.height - 4)}" rx="8" fill="${item.color}" fill-opacity=".78"></rect>
      <text x="${item.x + 15}" y="${item.y + 27}" class="treemap-label">${escapeHtml(item.label)}</text>
      <text x="${item.x + 15}" y="${item.y + 49}" class="treemap-value">${formatMoney(item.value)}</text>
      <title>${escapeHtml(item.label)}: ${formatMoney(item.value)}</title></g>`,
      )
      .join("")}</svg>`;

    const width = 1000;
    const height = 280;
    const margin = { left: 62, right: 22, top: 20, bottom: 42 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const maximum = Math.max(
      3000,
      ...months.map((item) => Number(item.net_savings || 0)),
    );
    const point = (item, index) => ({
      x:
        margin.left +
        (months.length > 1 ? (index / (months.length - 1)) * plotWidth : 0),
      y:
        margin.top +
        plotHeight -
        (Number(item.net_savings || 0) / maximum) * plotHeight,
      item,
    });
    const points = months.map(point);
    const polyline = points.map(({ x, y }) => `${x},${y}`).join(" ");
    const area = `${margin.left},${margin.top + plotHeight} ${polyline} ${margin.left + plotWidth},${margin.top + plotHeight}`;
    const grid = [0, 0.25, 0.5, 0.75, 1]
      .map((ratio) => {
        const y = margin.top + plotHeight - ratio * plotHeight;
        return `<line x1="${margin.left}" y1="${y}" x2="${margin.left + plotWidth}" y2="${y}" class="cashflow-grid-line"></line><text x="${margin.left - 9}" y="${y + 4}" text-anchor="end" class="cashflow-axis-label">${formatMoney(maximum * ratio).replace(",00", "")}</text>`;
      })
      .join("");
    els.cashflowLineChart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Fluxo de caixa líquido mensal projetado">${grid}<polygon points="${area}" class="cashflow-area"></polygon><polyline points="${polyline}" class="cashflow-line"></polyline>${points.map(({ x, y, item }, index) => `<g><circle cx="${x}" cy="${y}" r="5" class="cashflow-point"></circle><title>${cashflowMonthLabel(item.month)}: ${formatMoney(item.net_savings)}</title>${index % 2 === 0 || index === points.length - 1 ? `<text x="${x}" y="${height - 15}" text-anchor="middle" class="cashflow-axis-label">${cashflowMonthLabel(item.month)}</text>` : ""}</g>`).join("")}</svg>`;

    let cumulative = 0;
    els.monthlySavingsGrid.innerHTML = months
      .map((item) => {
        cumulative += Number(item.net_savings || 0);
        return `<article><span>${cashflowMonthLabel(item.month)}${item.estimated ? " · estimado" : ""}</span><strong>${formatMoney(item.net_savings)}</strong><small>Acumulado ${formatMoney(cumulative)}</small></article>`;
      })
      .join("");
    els.cashflowMethod.textContent = (payload.interpolation || {}).method || "";
  }

  function dashboardExpenseGroup(item) {
    const category = String(item.category || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
    if (item.record_type === "material") return "materials";
    if (["diligencia", "cartorio", "impostos"].includes(category))
      return "diligences";
    if (category === "financiamento") return "financing";
    if (category === "reserva") return "reserve";
    return "services";
  }

  function renderDashboardExpenseCategories() {
    const definitions = [
      { id: "materials", label: "Materiais", icon: "materials-crate" },
      { id: "diligences", label: "Diligências", icon: "notary-services" },
      { id: "financing", label: "Financiamento", icon: "mortgage-contract" },
      { id: "services", label: "Serviços", icon: "mason-service" },
      { id: "reserve", label: "Reservas", icon: "emergency-reserve" },
    ];
    const grouped = Object.fromEntries(
      definitions.map((group) => [group.id, []]),
    );
    state.expenses.forEach((item) => {
      grouped[dashboardExpenseGroup(item)].push(item);
    });
    els.dashMaterials.innerHTML = definitions
      .map((group) => {
        const items = grouped[group.id];
        const total = items.reduce(
          (sum, item) => sum + Number(item.value || 0),
          0,
        );
        return `<article class="dashboard-expense-category">
          <div class="dashboard-expense-category-head">
            <span class="expense-hover-target category-hover-target" tabindex="0" data-hover-name="${escapeAttr(group.label)}" data-hover-amount="${escapeAttr(formatMoney(total))}" aria-label="${escapeAttr(`${group.label}: ${formatMoney(total)}`)}">${iconMarkup(group.icon, group.label)}</span>
            <span><strong>${escapeHtml(group.label)}</strong><small>${formatMoney(total)} · ${items.length} ${items.length === 1 ? "item" : "itens"}</small></span>
          </div>
          <div class="dashboard-expense-icons" aria-label="${escapeAttr(`Itens de ${group.label}`)}">
            ${items
              .map(
                (item) =>
                  `<span class="expense-hover-target dashboard-expense-icon" tabindex="0" data-hover-name="${escapeAttr(item.description)}" data-hover-amount="${escapeAttr(formatMoney(item.value))}" aria-label="${escapeAttr(`${item.description}: ${formatMoney(item.value)}`)}">${iconMarkup(item.icon_key, item.description)}</span>`,
              )
              .join("")}
          </div>
        </article>`;
      })
      .join("");
  }

  function positionDashboardTooltip(x, y) {
    const tooltip = els.dashboardHoverTooltip;
    const left = Math.max(
      8,
      Math.min(x + 12, window.innerWidth - tooltip.offsetWidth - 8),
    );
    const preferredTop = y + 14;
    const top =
      preferredTop + tooltip.offsetHeight < window.innerHeight
        ? preferredTop
        : Math.max(8, y - tooltip.offsetHeight - 12);
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  }

  function showDashboardTooltip(target, x, y) {
    els.dashboardHoverTooltip.innerHTML = `<strong>${escapeHtml(target.dataset.hoverName || "")}</strong><span>${escapeHtml(target.dataset.hoverAmount || "")}</span>`;
    els.dashboardHoverTooltip.classList.add("visible");
    els.dashboardHoverTooltip.setAttribute("aria-hidden", "false");
    positionDashboardTooltip(x, y);
  }

  function hideDashboardTooltip() {
    els.dashboardHoverTooltip.classList.remove("visible");
    els.dashboardHoverTooltip.setAttribute("aria-hidden", "true");
  }

  function renderDashboard() {
    els.dashTotalAll.textContent = formatMoney(state.totals.all);
    els.dashTotalMaterials.textContent = formatMoney(state.totals.materials);
    els.dashTotalServices.textContent = formatMoney(state.totals.services);
    const funding = (state.project || {}).funding || {};
    const sources = funding.sources || [];
    const fundsTotal = sources.reduce(
      (sum, item) => sum + Number(item.amount || 0),
      0,
    );
    els.fundsTotal.textContent = formatMoney(fundsTotal);
    els.fundsDetail.textContent = sources
      .map((item) => `${item.label}: ${formatMoney(item.amount)}`)
      .join(" · ");
    const coverage = state.totals.all
      ? Math.min(999, (fundsTotal / state.totals.all) * 100)
      : 0;
    els.overallCoverage.textContent = `${coverage.toFixed(1).replace(".", ",")}%`;
    els.coverageDonut.style.setProperty(
      "--coverage-angle",
      `${Math.min(100, coverage) * 3.6}deg`,
    );
    els.coverageDonut.setAttribute(
      "aria-label",
      `${coverage.toFixed(1).replace(".", ",")}% do orçamento coberto`,
    );
    els.coverageFunded.textContent = formatMoney(fundsTotal);
    const gap = fundsTotal - Number(state.totals.all || 0);
    els.overallGap.textContent =
      gap >= 0
        ? `Margem de ${formatMoney(gap)}`
        : `Lacuna de ${formatMoney(Math.abs(gap))}`;
    const categories = Object.entries(state.totals.by_category || {});
    const maximum = Math.max(
      1,
      ...categories.map(([, value]) => Number(value)),
    );
    els.categoryChart.innerHTML = categories
      .map(
        ([label, value]) =>
          `<div class="budget-bar-row"><div class="budget-bar-head"><span>${escapeHtml(label)}</span><strong>${formatMoney(value)}</strong></div><div class="budget-bar-track"><span style="width:${Math.max(1, (Number(value) / maximum) * 100)}%"></span></div></div>`,
      )
      .join("");
    const people = (state.project || {}).people || [];
    els.dashboardPeople.innerHTML = people
      .map(
        (person) => `<article class="dashboard-person">
      <img src="${escapeAttr(person.image_url)}" alt="${escapeAttr(person.name)}" loading="lazy">
      <div><strong>${escapeHtml(person.name)}</strong><span>${escapeHtml(person.role || person.story_role || "")}</span></div>
    </article>`,
      )
      .join("");
    renderDashboardExpenseCategories();
    renderGantt();
    renderMacroTimeline();
  }

  function macroTasks() {
    return state.tasks.filter((task) => task.activity_type === "macro");
  }

  function childTasks(macroId) {
    return state.tasks.filter((task) => task.parent_id === macroId);
  }

  function visibleGanttTasks() {
    const visible = [];
    macroTasks().forEach((macro) => {
      visible.push(macro);
      if (state.expandedMacros.has(macro.id))
        visible.push(...childTasks(macro.id));
    });
    return visible;
  }

  function persistExpandedMacros() {
    localStorage.setItem(
      "my-home:gantt-expanded",
      JSON.stringify([...state.expandedMacros]),
    );
  }

  function renderMacroTimeline() {
    if (!els.macroTimeline) return;
    const macros = macroTasks();
    if (!macros.length) {
      els.macroTimeline.innerHTML =
        '<p class="muted">Nenhuma macroatividade cadastrada.</p>';
      return;
    }
    const start = macros.reduce(
      (value, item) => (item.start_date < value ? item.start_date : value),
      macros[0].start_date,
    );
    const end = macros.reduce(
      (value, item) => (item.end_date > value ? item.end_date : value),
      macros[0].end_date,
    );
    const totalDays = Math.max(1, dayDiff(start, end) + 1);
    els.macroTimeline.innerHTML = macros
      .map((macro) => {
        const left = (dayDiff(start, macro.start_date) / totalDays) * 100;
        const width =
          (Math.max(1, dayDiff(macro.start_date, macro.end_date) + 1) /
            totalDays) *
          100;
        return `<button type="button" class="macro-timeline-row" data-open-macro="${macro.id}">
          <span class="macro-timeline-copy"><strong>${escapeHtml(macro.title)}</strong><small>${escapeHtml(macro.start_date)} — ${escapeHtml(macro.end_date)} · ${macro.progress || 0}%</small></span>
          <span class="macro-timeline-track"><i class="status-${macro.status}" style="left:${left}%;width:${width}%"></i></span>
          <span class="task-count status-${macro.status}">${escapeHtml(statusLabels[macro.status])}</span>
        </button>`;
      })
      .join("");
    els.macroTimeline.querySelectorAll("[data-open-macro]").forEach((row) => {
      row.addEventListener("click", () => {
        state.expandedMacros.add(row.dataset.openMacro);
        persistExpandedMacros();
        renderGantt();
        showView("gantt");
      });
    });
  }

  function ganttGeometry(tasks) {
    const dates = tasks.flatMap((task) => [
      parseDate(task.start_date),
      parseDate(task.end_date),
    ]);
    const today = parseDate(iso(new Date()));
    const start = new Date(Math.min(today, ...dates));
    start.setDate(start.getDate() - 7);
    const end = new Date(Math.max(today, ...dates));
    end.setDate(end.getDate() + 14);
    const dayWidth = { day: 34, week: 14, month: 5 }[state.zoom] || 14;
    return {
      start: iso(start),
      end: iso(end),
      days: dayDiff(iso(start), iso(end)) + 1,
      dayWidth,
    };
  }

  function ganttHeader(geometry) {
    const chunks = [];
    let cursor = geometry.start;
    while (cursor <= geometry.end) {
      const date = parseDate(cursor);
      const isMajor =
        state.zoom === "day" ? date.getDate() === 1 : date.getDay() === 1;
      if (state.zoom === "month") {
        if (date.getDate() === 1)
          chunks.push({
            date: cursor,
            label: date.toLocaleDateString("pt-BR", {
              month: "short",
              year: "2-digit",
            }),
          });
      } else if (state.zoom === "week") {
        if (date.getDay() === 1)
          chunks.push({
            date: cursor,
            label: date.toLocaleDateString("pt-BR", {
              day: "2-digit",
              month: "short",
            }),
          });
      } else {
        chunks.push({
          date: cursor,
          label: isMajor
            ? date.toLocaleDateString("pt-BR", {
                day: "2-digit",
                month: "short",
              })
            : String(date.getDate()),
        });
      }
      cursor = addDays(cursor, 1);
    }
    return chunks
      .map(
        (chunk) =>
          `<span class="gantt-tick" style="left:${dayDiff(geometry.start, chunk.date) * geometry.dayWidth}px">${escapeHtml(chunk.label)}</span>`,
      )
      .join("");
  }

  function renderGantt() {
    if (!els.gantt) return;
    const allDetails = state.tasks.filter(
      (task) => task.activity_type === "task",
    );
    const tasks = visibleGanttTasks();
    const counts = allDetails.reduce(
      (map, task) => ((map[task.status] = (map[task.status] || 0) + 1), map),
      {},
    );
    els.taskSummary.innerHTML = Object.entries(statusLabels)
      .map(
        ([key, label]) =>
          `<span class="task-count status-${key}"><strong>${counts[key] || 0}</strong>${label}</span>`,
      )
      .join("");
    if (!tasks.length) {
      els.gantt.innerHTML = `<div class="gantt-empty">Nenhuma tarefa. Crie a primeira para começar o cronograma.</div>`;
      return;
    }
    const geometry = ganttGeometry(state.tasks);
    els.gantt.style.setProperty("--day-width", `${geometry.dayWidth}px`);
    els.gantt.style.setProperty(
      "--timeline-width",
      `${geometry.days * geometry.dayWidth}px`,
    );
    const todayLeft =
      dayDiff(geometry.start, iso(new Date())) * geometry.dayWidth;
    els.gantt.innerHTML = `<div class="gantt-label-head">Macroatividade / atividade</div>
      <div class="gantt-scroll" id="gantt-scroll"><div class="gantt-timeline">
        <div class="gantt-header">${ganttHeader(geometry)}</div>
        <div class="gantt-today" style="left:${todayLeft}px"><span>Hoje</span></div>
        ${tasks
          .map((task) => {
            const left =
              dayDiff(geometry.start, task.start_date) * geometry.dayWidth;
            const width = Math.max(
              geometry.dayWidth,
              (dayDiff(task.start_date, task.end_date) + 1) * geometry.dayWidth,
            );
            const isMacro = task.activity_type === "macro";
            return `<div class="gantt-track${isMacro ? " macro" : " child"}" data-track-id="${task.id}">
            <button type="button" class="gantt-bar status-${task.status}${isMacro ? " macro" : ""}" ${isMacro ? `data-macro-bar="${task.id}"` : `data-task-bar="${task.id}"`} style="left:${left}px;width:${width}px" title="${escapeAttr(`${task.title} · ${task.start_date} — ${task.end_date}`)}">
              ${isMacro ? "" : '<i class="gantt-handle start" data-resize="start"></i>'}<span>${escapeHtml(task.title)}</span>${isMacro ? "" : '<i class="gantt-handle end" data-resize="end"></i>'}
            </button></div>`;
          })
          .join("")}
      </div></div>
      <div class="gantt-labels">${tasks
        .map((task) => {
          const detail = `${task.activity_type === "macro" ? `${childTasks(task.id).length} atividades · ${task.progress || 0}%` : `P${task.priority} · #${task.sequence}`} · ${escapeHtml(statusLabels[task.status])}${task.date_status === "estimated" ? " · estimada" : ""}`;
          const content = `${iconMarkup(task.icon_key, task.title)}<span><strong>${escapeHtml(task.title)}</strong><small>${detail}</small></span>`;
          if (task.activity_type === "macro")
            return `<div class="gantt-label-row macro">
              <button type="button" class="macro-disclosure" data-toggle-macro="${task.id}" aria-label="${state.expandedMacros.has(task.id) ? "Recolher" : "Expandir"} ${escapeAttr(task.title)}">${state.expandedMacros.has(task.id) ? "−" : "+"}</button>
              <button type="button" class="gantt-label-content" data-task-label="${task.id}" title="Editar macroatividade">${content}</button>
            </div>`;
          return `<button type="button" class="gantt-label-row task" draggable="true" data-task-label="${task.id}" title="Arraste para trocar a sequência"><i class="child-indent"></i>${content}</button>`;
        })
        .join("")}</div>`;
    bindGanttInteractions(geometry);
  }

  function bindGanttInteractions(geometry) {
    let draggedLabel = "";
    els.gantt.querySelectorAll("[data-toggle-macro]").forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const id = toggle.dataset.toggleMacro;
        if (state.expandedMacros.has(id)) state.expandedMacros.delete(id);
        else state.expandedMacros.add(id);
        persistExpandedMacros();
        renderGantt();
      });
    });
    els.gantt.querySelectorAll("[data-macro-bar]").forEach((bar) => {
      bar.addEventListener("click", () =>
        openTaskDialog(
          state.tasks.find((task) => task.id === bar.dataset.macroBar),
        ),
      );
    });
    els.gantt.querySelectorAll("[data-task-label]").forEach((row) => {
      row.addEventListener("click", () => {
        openTaskDialog(
          state.tasks.find((task) => task.id === row.dataset.taskLabel),
        );
      });
      row.addEventListener("dragstart", () => {
        const task = state.tasks.find(
          (item) => item.id === row.dataset.taskLabel,
        );
        if (task?.activity_type !== "task") return;
        draggedLabel = row.dataset.taskLabel;
        row.classList.add("dragging");
      });
      row.addEventListener("dragend", () => row.classList.remove("dragging"));
      row.addEventListener("dragover", (event) => event.preventDefault());
      row.addEventListener("drop", async (event) => {
        event.preventDefault();
        const targetId = row.dataset.taskLabel;
        if (!draggedLabel || draggedLabel === targetId) return;
        const first = state.tasks.find((task) => task.id === draggedLabel);
        const second = state.tasks.find((task) => task.id === targetId);
        if (!first || !second || first.parent_id !== second.parent_id) return;
        const firstSequence = first.sequence;
        first.sequence = second.sequence;
        second.sequence = firstSequence;
        renderGantt();
        try {
          await saveTaskRecord(first);
          await saveTaskRecord(second);
          renderMacroTimeline();
        } catch (error) {
          await loadTasks();
          setStatus(els.appStatus, "err", error.message);
        }
      });
    });
    els.gantt.querySelectorAll("[data-task-bar]").forEach((bar) => {
      bar.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        const task = state.tasks.find(
          (item) => item.id === bar.dataset.taskBar,
        );
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
          const deltaDays = Math.round(
            (upEvent.clientX - originX) / geometry.dayWidth,
          );
          if (!deltaDays) return;
          const previous = {
            start_date: task.start_date,
            end_date: task.end_date,
            date_status: task.date_status,
          };
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
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(task),
    });
    state.tasks = payload.tasks || state.tasks;
    renderGantt();
    renderMacroTimeline();
    return payload;
  }

  function fillTaskOptions(currentId = "") {
    els.taskExpense.innerHTML = `<option value="">Nenhuma</option>${state.expenses.map((item) => `<option value="${item.id}">${escapeHtml(`${item.id} · ${item.description}`)}</option>`).join("")}`;
    els.taskParent.innerHTML = macroTasks()
      .filter((item) => item.id !== currentId)
      .map(
        (item) =>
          `<option value="${escapeAttr(item.id)}">${escapeHtml(item.title)}</option>`,
      )
      .join("");
  }

  function suggestTaskIcon() {
    const expense = state.expenses.find(
      (item) => item.id === els.taskExpense.value,
    );
    if (expense?.icon_key) return expense.icon_key;
    const text = `${els.taskTitle.value} ${els.taskDescription.value}`
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
    const rules = [
      ["porta-balcao", "sliding-door"],
      ["vitro", "bathroom-window"],
      ["janela", "window"],
      ["demoli", "demolition"],
      ["infiltra", "waterproofing-additive"],
      ["impermeabili", "waterproofing-additive"],
      ["telha", "roof-tiles"],
      ["quadro de distribuicao", "breaker-panel"],
      ["conduite", "conduit"],
      ["fiacao", "electrical-wires"],
      ["tomada", "outlet"],
      ["eletric", "electrician-service"],
      ["esgoto", "plumbing-pipes"],
      ["hidraul", "plumber-service"],
      ["ralo", "drains"],
      ["pia", "sink-countertop"],
      ["porcelanato", "porcelain-tiles"],
      ["piso", "porcelain-tiles"],
      ["pintura", "painter-service"],
      ["limpeza", "cleaning-service"],
      ["mudanca", "moving-service"],
      ["financiamento", "mortgage-contract"],
      ["contrato de compra", "down-payment"],
      ["reboco", "masonry-work"],
      ["reforma", "masonry-work"],
    ];
    const match = rules.find(([term]) => text.includes(term));
    if (match && state.iconCatalog.icons[match[1]]) return match[1];
    const parent = state.tasks.find((item) => item.id === els.taskParent.value);
    return parent?.icon_key || "home-expense";
  }

  function renderTaskIconPicker(selected = "", mode = "auto") {
    const icons = Object.entries(state.iconCatalog.icons || {}).sort((a, b) =>
      String(a[1].label).localeCompare(String(b[1].label), "pt-BR"),
    );
    const iconMode = mode === "manual" ? "manual" : "auto";
    const key = state.iconCatalog.icons[selected]
      ? selected
      : suggestTaskIcon();
    els.taskIcon.value = key;
    els.taskIconMode.value = iconMode;
    const entry = iconEntry(key);
    els.taskIconPreview.innerHTML = entry
      ? `${iconMarkup(key, entry.label, "lg")}<span>${escapeHtml(entry.label)}<small>${iconMode === "auto" ? "Sugestão automática" : "Escolha manual"}</small></span>`
      : "";
    els.taskIconPicker.innerHTML = icons
      .map(
        ([iconKey, icon]) =>
          `<button type="button" class="icon-choice ${iconKey === key ? "selected" : ""}" data-task-icon="${escapeAttr(iconKey)}" title="${escapeAttr(icon.label)}">${iconMarkup(iconKey, icon.label, "picker")}<span>${escapeHtml(icon.label)}</span></button>`,
      )
      .join("");
    els.btnTaskIconAuto.classList.toggle("active", iconMode === "auto");
  }

  function syncTaskHierarchyFields() {
    const isMacro = els.taskActivityType.value === "macro";
    els.taskParentLabel.classList.toggle("hidden", isMacro);
    els.taskParent.required = !isMacro;
    document.querySelectorAll(".task-rollup-field").forEach((field) => {
      field.disabled = isMacro;
    });
    els.taskExpense.disabled = isMacro;
    els.taskDateBadge.textContent = isMacro
      ? "Datas, prioridade e status calculados pelas atividades"
      : "Datas confirmadas";
    if (!els.taskId.value) {
      const siblings = isMacro
        ? macroTasks()
        : childTasks(els.taskParent.value);
      els.taskSequence.value =
        Math.max(0, ...siblings.map((item) => item.sequence)) + 1;
    }
  }

  function openTaskDialog(task = null) {
    fillTaskOptions(task?.id || "");
    const tomorrow = addDays(iso(new Date()), 1);
    els.taskDialogTitle.textContent = task
      ? "Editar atividade"
      : "Nova atividade";
    els.taskId.value = task?.id || "";
    els.taskTitle.value = task?.title || "";
    els.taskDescription.value = task?.description || "";
    els.taskActivityType.value = task?.activity_type || "task";
    els.taskParent.value =
      task?.parent_id || els.taskParent.options[0]?.value || "";
    els.taskPriority.value = task?.priority || 1;
    els.taskSequence.value = task?.sequence || 1;
    els.taskStart.value = task?.start_date || tomorrow;
    els.taskEnd.value = task?.end_date || addDays(tomorrow, 2);
    els.taskStatus.value = task?.status || "pending";
    els.taskExpense.value = task?.expense_id || "";
    renderTaskIconPicker(task?.icon_key || "", task?.icon_mode || "auto");
    els.taskDateBadge.textContent =
      task?.date_status === "estimated"
        ? "Datas estimadas"
        : "Datas confirmadas";
    syncTaskHierarchyFields();
    const hasChildren =
      task?.activity_type === "macro" && childTasks(task.id).length > 0;
    els.taskActivityType.disabled = Boolean(hasChildren);
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
      activity_type: els.taskActivityType.value,
      parent_id:
        els.taskActivityType.value === "macro" ? "" : els.taskParent.value,
      priority: Number(els.taskPriority.value),
      sequence: Number(els.taskSequence.value),
      start_date: els.taskStart.value,
      end_date: els.taskEnd.value,
      status: els.taskStatus.value,
      expense_id: els.taskExpense.value,
      icon_key: els.taskIcon.value,
      icon_mode: els.taskIconMode.value,
      date_status: "confirmed",
    };
    try {
      const result = await saveTaskRecord(payload);
      state.tasks = result.tasks;
      els.taskDialog.close();
      renderGantt();
      renderMacroTimeline();
      setStatus(
        els.appStatus,
        "ok",
        "Atividade salva. Clique em “Salvar tudo” para enviar a cópia segura.",
      );
    } catch (error) {
      setStatus(els.taskFormError, "err", error.message);
    }
  }

  async function deleteTask() {
    const id = els.taskId.value;
    if (!id || !window.confirm("Excluir esta atividade?")) return;
    try {
      const result = await request(`/api/tasks/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      state.tasks = result.tasks;
      els.taskDialog.close();
      renderGantt();
      renderMacroTimeline();
      setStatus(els.appStatus, "ok", "Atividade excluída.");
    } catch (error) {
      setStatus(els.taskFormError, "err", error.message);
    }
  }

  function renderIconPicker(selected) {
    const icons = Object.entries(state.iconCatalog.icons || {}).sort((a, b) =>
      String(a[1].label).localeCompare(String(b[1].label), "pt-BR"),
    );
    const key = state.iconCatalog.icons[selected]
      ? selected
      : state.iconCatalog.defaults.expense || "home-expense";
    els.fieldIconKey.value = key;
    const entry = iconEntry(key);
    els.iconPreview.innerHTML = entry
      ? `${iconMarkup(key, entry.label, "lg")}<span>${escapeHtml(entry.label)}</span>`
      : "";
    els.iconPicker.innerHTML = icons
      .map(
        ([iconKey, icon]) =>
          `<button type="button" class="icon-choice ${iconKey === key ? "selected" : ""}" data-icon-key="${escapeAttr(iconKey)}" title="${escapeAttr(icon.label)}">${iconMarkup(iconKey, icon.label, "picker")}<span>${escapeHtml(icon.label)}</span></button>`,
      )
      .join("");
  }

  function providerOptions(selected = "", includeArchived = false) {
    return `<option value="">Nenhum</option>${state.providers
      .filter(
        (item) => includeArchived || !item.archived || item.id === selected,
      )
      .map(
        (item) =>
          `<option value="${escapeAttr(item.id)}" ${item.id === selected ? "selected" : ""}>${escapeHtml(item.name)}${item.archived ? " (arquivado)" : ""}</option>`,
      )
      .join("")}`;
  }

  function updateExpenseServiceLinks(
    provider = els.fieldProvider.value,
    contract = els.fieldContract.value,
  ) {
    const isService = els.fieldRecordType.value === "service";
    els.expenseServiceLinks.classList.toggle("hidden", !isService);
    if (!isService) {
      els.fieldProvider.value = "";
      els.fieldContract.value = "";
      return;
    }
    els.fieldProvider.innerHTML = providerOptions(provider);
    els.fieldProvider.value = [...els.fieldProvider.options].some(
      (item) => item.value === provider,
    )
      ? provider
      : "";
    const available = state.contracts.filter(
      (item) =>
        !item.archived &&
        item.type === "service" &&
        (!els.fieldProvider.value ||
          item.provider_id === els.fieldProvider.value),
    );
    els.fieldContract.innerHTML = `<option value="">Nenhum</option>${available.map((item) => `<option value="${escapeAttr(item.id)}">${escapeHtml(item.title)}</option>`).join("")}`;
    els.fieldContract.value = available.some((item) => item.id === contract)
      ? contract
      : "";
  }

  function openExpenseDialog(item = null) {
    els.dialogTitle.textContent = item ? "Editar despesa" : "Nova despesa";
    els.fieldId.value = item?.id || "";
    els.fieldRecordType.value =
      item?.record_type ||
      (item?.category === "Material" ? "material" : "service");
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
    updateExpenseServiceLinks(item?.provider_id || "", item?.contract_id || "");
    renderIconPicker(item?.icon_key || "");
    els.formError.classList.add("hidden");
    els.dialog.showModal();
    els.fieldDescription.focus();
  }

  async function submitExpense(event) {
    event.preventDefault();
    const payload = {
      id: els.fieldId.value,
      record_type: els.fieldRecordType.value,
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
      provider_id: els.fieldProvider.value,
      contract_id: els.fieldContract.value,
    };
    try {
      const result = await request("/api/expenses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      applyExpenseState(result.state);
      await loadContracts();
      renderContractCenter();
      els.dialog.close();
      await pushToRemote();
    } catch (error) {
      setStatus(els.formError, "err", error.message);
    }
  }

  async function deleteExpense(id) {
    const item = state.expenses.find((expense) => expense.id === id);
    if (!window.confirm(`Excluir “${item?.description || id}”?`)) return;
    const result = await request(`/api/expenses/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    applyExpenseState(result.state);
    await loadContracts();
    renderContractCenter();
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
    try {
      const saved = JSON.parse(
        localStorage.getItem("my-home:gantt-expanded") || "[]",
      );
      state.expandedMacros = new Set(
        saved.filter((id) => state.tasks.some((item) => item.id === id)),
      );
    } catch {
      state.expandedMacros = new Set();
    }
    renderGantt();
    renderMacroTimeline();
  }

  async function loadNotes() {
    const payload = await request("/api/notes");
    els.generalNotes.value = payload.text || "";
    els.generalNotesStatus.textContent = payload.updated_at
      ? `Salvo em ${payload.updated_at}`
      : "Salvo automaticamente";
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
      const result = await request("/api/push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      setStatus(
        els.appStatus,
        "ok",
        result.message || "Dados salvos e enviados.",
      );
      els.pushStatus.textContent = result.pushed
        ? "Cópia segura atualizada"
        : "Tudo já estava salvo";
    } catch (error) {
      setStatus(
        els.appStatus,
        "err",
        `Dados locais salvos; envio pendente: ${error.message}`,
      );
    } finally {
      els.btnPush.disabled = false;
    }
  }

  function renderProject(project) {
    if (!els.projectOverview || !project) return;
    const people = (project.people || [])
      .map(
        (person) =>
          `<article class="person-card"><img src="${escapeAttr(person.image_url)}" alt="${escapeAttr(person.name)}"><div><strong>${escapeHtml(person.name)}</strong><span>${escapeHtml(person.role || person.story_role || "")}</span><p>${escapeHtml(person.story_role || "")}</p></div></article>`,
      )
      .join("");
    const tools = ((project.construction_resources || {}).required_tools || [])
      .map(
        (tool) =>
          `<article class="required-tool">${iconMarkup(tool.icon_key, tool.name, "tool")}<div><strong>${escapeHtml(tool.name)}</strong><p>${escapeHtml(tool.purpose || "")}</p></div></article>`,
      )
      .join("");
    els.projectOverview.innerHTML = `<h3 class="project-heading">Pessoas do projeto</h3><div class="people-grid">${people}</div><h3 class="project-heading">Ferramentas necessárias</h3><div class="required-tools-grid">${tools || "<p>Nenhuma ferramenta cadastrada.</p>"}</div>`;
  }

  const contractStatusLabels = {
    draft: "Rascunho",
    signed: "Assinado",
    active: "Ativo",
    completed: "Concluído",
    cancelled: "Cancelado",
  };

  function renderContractCenter() {
    const includeArchived = els.showArchivedContracts.checked;
    const visibleContracts = state.contracts.filter(
      (item) => includeArchived || !item.archived,
    );
    const visibleProviders = state.providers.filter(
      (item) => includeArchived || !item.archived,
    );
    const providerMap = Object.fromEntries(
      state.providers.map((item) => [item.id, item]),
    );
    const signed = state.contracts.filter(
      (item) =>
        !item.archived &&
        ["signed", "active", "completed"].includes(item.status),
    ).length;
    const total = state.contracts
      .filter((item) => !item.archived)
      .reduce((sum, item) => sum + Number(item.amount || 0), 0);
    els.contractSummary.innerHTML = `<span><strong>${state.contracts.filter((item) => !item.archived).length}</strong> ativos</span><span><strong>${signed}</strong> assinados/confirmados</span><span><strong>${formatMoney(total)}</strong> valor registrado</span>`;
    els.contractList.innerHTML =
      visibleContracts
        .map((contract) => {
          const versions = contract.document_versions || [];
          const current = versions.find(
            (item) => item.id === contract.current_document_id,
          );
          const expenseNames = (contract.expense_ids || []).map(
            (id) =>
              state.expenses.find((item) => item.id === id)?.description || id,
          );
          const versionHistory = versions
            .slice()
            .reverse()
            .map(
              (version) =>
                `<a href="/api/contracts/${encodeURIComponent(contract.id)}/documents/${encodeURIComponent(version.id)}" target="_blank">${escapeHtml(version.id)} · ${escapeHtml(version.original_filename)}${version.pages ? ` · ${version.pages} pág.` : ""}</a>`,
            )
            .join("");
          return `<article class="contract-card ${contract.archived ? "archived" : ""}">
        <div class="contract-card-head"><div><span>${contract.type === "purchase" ? "Compra" : "Serviço"}</span><h4>${escapeHtml(contract.title)}</h4></div><span class="contract-status status-${escapeAttr(contract.status)}">${contract.archived ? "Arquivado" : escapeHtml(contractStatusLabels[contract.status] || contract.status)}</span></div>
        <div class="contract-meta"><span>${formatMoney(contract.amount)}</span><span>${escapeHtml(providerMap[contract.provider_id]?.name || "Sem prestador")}</span><span>${escapeHtml(contract.start_date || "Sem data")}</span></div>
        ${contract.metadata?.signature_status ? `<p class="contract-signature">${escapeHtml(contract.metadata.signature_status)} · conclusão ${escapeHtml(contract.metadata.signature_completed_at || "")}</p>` : ""}
        ${expenseNames.length ? `<p>Vínculos: ${escapeHtml(expenseNames.join(", "))}</p>` : ""}
        <div class="contract-card-actions">${current ? `<a class="btn primary" href="/api/contracts/${encodeURIComponent(contract.id)}/documents/current" target="_blank">Abrir PDF atual</a>` : `<span class="muted">Sem PDF</span>`}<button class="btn" type="button" data-edit-contract="${escapeAttr(contract.id)}">Editar</button></div>
        ${versionHistory ? `<details><summary>${versions.length} versão(ões) preservada(s)</summary><div class="contract-versions">${versionHistory}</div></details>` : ""}
      </article>`;
        })
        .join("") || '<p class="empty">Nenhum contrato nesta visualização.</p>';
    els.providerList.innerHTML =
      visibleProviders
        .map(
          (provider) =>
            `<article class="provider-card ${provider.archived ? "archived" : ""}"><div><strong>${escapeHtml(provider.name)}</strong><span>${escapeHtml(provider.service_type || "Prestador")}</span></div><button class="btn" type="button" data-edit-provider="${escapeAttr(provider.id)}">Editar</button></article>`,
        )
        .join("") || '<p class="empty">Nenhum prestador cadastrado.</p>';
  }

  function openProviderDialog(provider = null) {
    els.providerDialogTitle.textContent = provider
      ? "Editar prestador"
      : "Novo prestador";
    els.providerId.value = provider?.id || "";
    els.providerName.value = provider?.name || "";
    els.providerServiceType.value = provider?.service_type || "";
    els.providerContact.value = provider?.contact || "";
    els.providerNotes.value = provider?.notes || "";
    els.btnArchiveProvider.classList.toggle(
      "hidden",
      !provider || provider.archived,
    );
    els.providerFormError.classList.add("hidden");
    els.providerDialog.showModal();
  }

  async function submitProvider(event) {
    event.preventDefault();
    try {
      const result = await request("/api/providers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: els.providerId.value,
          name: els.providerName.value.trim(),
          service_type: els.providerServiceType.value.trim(),
          contact: els.providerContact.value.trim(),
          notes: els.providerNotes.value.trim(),
        }),
      });
      state.providers = result.providers || [];
      els.providerDialog.close();
      renderContractCenter();
      setStatus(
        els.appStatus,
        "ok",
        "Prestador salvo. Use “Salvar tudo” para enviar a cópia segura.",
      );
    } catch (error) {
      setStatus(els.providerFormError, "err", error.message);
    }
  }

  function openContractDialog(contract = null) {
    els.contractDialogTitle.textContent = contract
      ? "Editar contrato"
      : "Novo contrato";
    els.contractId.value = contract?.id || "";
    els.contractType.value = contract?.type || "service";
    els.contractStatus.value = contract?.status || "draft";
    els.contractTitle.value = contract?.title || "";
    els.contractProvider.innerHTML = providerOptions(
      contract?.provider_id || "",
      true,
    );
    els.contractProvider.value = contract?.provider_id || "";
    els.contractAmount.value = contract?.amount ?? "";
    els.contractStart.value = contract?.start_date || "";
    els.contractEnd.value = contract?.end_date || "";
    const selected = new Set(contract?.expense_ids || []);
    els.contractExpenses.innerHTML = state.expenses
      .filter((item) => item.record_type === "service")
      .map(
        (item) =>
          `<option value="${escapeAttr(item.id)}" ${selected.has(item.id) ? "selected" : ""}>${escapeHtml(item.description)}</option>`,
      )
      .join("");
    els.contractNotes.value = contract?.notes || "";
    els.contractPdf.value = "";
    els.btnArchiveContract.classList.toggle(
      "hidden",
      !contract || contract.archived,
    );
    els.contractFormError.classList.add("hidden");
    els.contractDialog.showModal();
  }

  async function submitContract(event) {
    event.preventDefault();
    try {
      let result = await request("/api/contracts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: els.contractId.value,
          type: els.contractType.value,
          status: els.contractStatus.value,
          title: els.contractTitle.value.trim(),
          provider_id: els.contractProvider.value,
          amount: Number(els.contractAmount.value || 0),
          start_date: els.contractStart.value,
          end_date: els.contractEnd.value,
          expense_ids: [...els.contractExpenses.selectedOptions].map(
            (item) => item.value,
          ),
          notes: els.contractNotes.value.trim(),
        }),
      });
      const contractId = result.contract_id;
      const file = els.contractPdf.files[0];
      if (file)
        result = await request(
          `/api/contracts/${encodeURIComponent(contractId)}/documents`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/pdf",
              "X-Filename": encodeURIComponent(file.name),
            },
            body: file,
          },
        );
      state.contracts = result.contracts || [];
      await loadState();
      els.contractDialog.close();
      renderContractCenter();
      setStatus(
        els.appStatus,
        "ok",
        "Contrato salvo com histórico preservado.",
      );
    } catch (error) {
      setStatus(els.contractFormError, "err", error.message);
    }
  }

  async function archiveEntity(kind, id) {
    if (
      !window.confirm(
        `Arquivar este ${kind === "contracts" ? "contrato" : "prestador"}? O histórico e os PDFs serão preservados.`,
      )
    )
      return;
    const result = await request(`/api/${kind}/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    if (kind === "contracts") state.contracts = result.contracts || [];
    else state.providers = result.providers || [];
    (kind === "contracts" ? els.contractDialog : els.providerDialog).close();
    renderContractCenter();
  }

  async function loadProviders() {
    state.providers = (await request("/api/providers")).providers || [];
  }

  async function loadContracts() {
    state.contracts = (await request("/api/contracts")).contracts || [];
  }

  let house3dModule = null;
  let sceneEditorOpen = false;
  let mediaPanelOpen = false;
  let mediaRecording = false;
  let mediaBlob = null;
  let mediaFilename = "";
  let mediaObjectUrl = "";

  async function renderHouse3D() {
    const model = state.house?.model_3d;
    els.house3dAssumptions.innerHTML = (model?.assumptions || [])
      .map((item) => `<li>${escapeHtml(item)}</li>`)
      .join("");
    if (!model)
      return setStatus(els.house3dStatus, "warn", "Geometria 3D indisponível.");
    try {
      house3dModule ||= await import("/house-3d.js?v=20260916-5");
      house3dModule.mountHouse3D(model);
      requestAnimationFrame(() => house3dModule.resizeHouse3D());
    } catch (error) {
      setStatus(
        els.house3dStatus,
        "err",
        `Não foi possível abrir o modelo 3D: ${error.message}`,
      );
    }
  }

  function setSceneEditorOpen(open) {
    if (open && mediaRecording) {
      els.mediaStatus.textContent =
        "Finalize a gravação antes de abrir o editor.";
      return;
    }
    sceneEditorOpen = Boolean(open);
    if (sceneEditorOpen && mediaPanelOpen) setMediaPanelOpen(false);
    els.sceneEditorPanel.classList.toggle("hidden", !sceneEditorOpen);
    els.btnToggleEditor.classList.toggle("active", sceneEditorOpen);
    els.btnToggleEditor.setAttribute("aria-pressed", String(sceneEditorOpen));
    house3dModule?.setSceneEditorEnabled(sceneEditorOpen);
    if (sceneEditorOpen) {
      house3dModule?.setSceneSnap(els.editorSnap.value);
      els.editorStatus.textContent =
        "Clique em um elemento ou escolha um objeto.";
    }
  }

  function updateEditorState(event) {
    const detail = event.detail || {};
    els.editorSelection.textContent =
      detail.selected?.label || "Nenhum objeto selecionado";
    els.editorStatus.textContent = detail.message || "";
    const hasSelection = Boolean(detail.selected);
    els.editorDimensions.disabled = !hasSelection;
    const dimensionMax = detail.selected?.isPlacedAsset ? "10" : "100";
    els.editorWidth.max = dimensionMax;
    els.editorHeight.max = dimensionMax;
    els.editorDepth.max = dimensionMax;
    if (detail.selected?.dimensions) {
      els.editorWidth.value = detail.selected.dimensions.width.toFixed(2);
      els.editorHeight.value = detail.selected.dimensions.height.toFixed(2);
      els.editorDepth.value = detail.selected.dimensions.depth.toFixed(2);
    } else {
      els.editorWidth.value = "";
      els.editorHeight.value = "";
      els.editorDepth.value = "";
    }
    els.btnDuplicateObject.disabled = !detail.selected?.isPlacedAsset;
    els.btnDeleteObject.disabled = !detail.selected?.isPlacedAsset;
    els.btnResetObject.disabled = !hasSelection;
    els.assetPalette.classList.toggle("placing", Boolean(detail.placing));
  }

  async function saveSceneLayout() {
    if (!house3dModule) return;
    els.btnSaveLayout.disabled = true;
    els.editorStatus.textContent = "Salvando layout…";
    try {
      const layout = house3dModule.getSceneLayoutState();
      const result = await request("/api/house/model3d-layout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(layout),
      });
      state.house.model_3d.layout_overrides = result.layout_overrides;
      state.house.model_3d.placed_assets = result.placed_assets;
      els.editorStatus.textContent =
        "Layout salvo localmente. Use “Salvar tudo” para enviar a cópia segura.";
    } catch (error) {
      els.editorStatus.textContent = `Erro ao salvar: ${error.message}`;
    } finally {
      els.btnSaveLayout.disabled = false;
    }
  }

  function setMediaPanelOpen(open) {
    mediaPanelOpen = Boolean(open);
    if (mediaPanelOpen && sceneEditorOpen) setSceneEditorOpen(false);
    if (!mediaPanelOpen) {
      if (mediaRecording) house3dModule?.stopHouseRecording();
      clearMediaPreview();
      mediaBlob = null;
      mediaFilename = "";
      els.mediaResult.classList.add("hidden");
    }
    els.mediaExportPanel.classList.toggle("hidden", !mediaPanelOpen);
    els.btnToggleMedia.classList.toggle("active", mediaPanelOpen);
    els.btnToggleMedia.setAttribute("aria-pressed", String(mediaPanelOpen));
  }

  function mediaStamp() {
    return new Date()
      .toISOString()
      .replace(/\.\d{3}Z$/, "")
      .replaceAll(":", "-");
  }

  function clearMediaPreview() {
    if (mediaObjectUrl) URL.revokeObjectURL(mediaObjectUrl);
    mediaObjectUrl = "";
    els.mediaImagePreview.removeAttribute("src");
    els.mediaVideoPreview.pause();
    els.mediaVideoPreview.removeAttribute("src");
    els.mediaVideoPreview.load();
  }

  function showMediaResult(blob, filename, kind) {
    clearMediaPreview();
    mediaBlob = blob;
    mediaFilename = filename;
    mediaObjectUrl = URL.createObjectURL(blob);
    const isImage = kind === "image";
    els.mediaImagePreview.classList.toggle("hidden", !isImage);
    els.mediaVideoPreview.classList.toggle("hidden", isImage);
    if (isImage) els.mediaImagePreview.src = mediaObjectUrl;
    else els.mediaVideoPreview.src = mediaObjectUrl;
    els.mediaFilename.textContent = filename;
    els.mediaResult.classList.remove("hidden");
  }

  function downloadMedia() {
    if (!mediaBlob) return;
    const link = document.createElement("a");
    link.href = mediaObjectUrl || URL.createObjectURL(mediaBlob);
    link.download = mediaFilename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    els.mediaStatus.textContent = `${mediaFilename} baixado.`;
  }

  async function shareMedia() {
    if (!mediaBlob) return;
    const file = new File([mediaBlob], mediaFilename, { type: mediaBlob.type });
    if (
      navigator.share &&
      (!navigator.canShare || navigator.canShare({ files: [file] }))
    ) {
      try {
        await navigator.share({
          files: [file],
          title: "Modelo 3D da casa",
          text: "Visual do projeto my-home",
        });
        els.mediaStatus.textContent =
          "Arquivo enviado ao menu de compartilhamento.";
        return;
      } catch (error) {
        if (error.name === "AbortError") {
          els.mediaStatus.textContent = "Compartilhamento cancelado.";
          return;
        }
      }
    }
    downloadMedia();
    els.mediaStatus.textContent =
      "Compartilhamento direto indisponível; o arquivo foi baixado.";
  }

  async function captureSnapshot() {
    if (!house3dModule || mediaRecording) return;
    els.btnCaptureSnapshot.disabled = true;
    els.mediaStatus.textContent = "Renderizando foto em alta qualidade…";
    try {
      const mimeType = els.snapshotFormat.value;
      const blob = await house3dModule.captureHouseSnapshot(mimeType);
      if (!mediaPanelOpen) return;
      const extension = mimeType === "image/jpeg" ? "jpg" : "png";
      const filename = `my-home-modelo-3d-${mediaStamp()}.${extension}`;
      showMediaResult(blob, filename, "image");
      els.mediaStatus.textContent = "Foto pronta para compartilhar ou baixar.";
    } catch (error) {
      els.mediaStatus.textContent = `Não foi possível tirar a foto: ${error.message}`;
    } finally {
      els.btnCaptureSnapshot.disabled = false;
    }
  }

  async function convertRecording(blob) {
    try {
      const response = await fetch("/api/media/convert-video", {
        method: "POST",
        headers: { "Content-Type": blob.type || "video/webm" },
        body: blob,
      });
      if (!response.ok) {
        const failure = await response.json().catch(() => ({}));
        throw new Error(failure.error || `Falha HTTP ${response.status}`);
      }
      return {
        blob: await response.blob(),
        extension: "mp4",
        converted: true,
      };
    } catch (error) {
      return {
        blob,
        extension: "webm",
        converted: false,
        error,
      };
    }
  }

  function setRecordingControls(recording) {
    mediaRecording = recording;
    els.btnStartRecording.disabled = recording;
    els.btnStopRecording.disabled = !recording;
    els.videoMode.disabled = recording;
    els.videoDuration.disabled = recording;
    els.btnCaptureSnapshot.disabled = recording;
    els.mediaProgressWrap.classList.toggle("hidden", !recording);
  }

  async function startRecording() {
    if (!house3dModule || mediaRecording) return;
    if (sceneEditorOpen) setSceneEditorOpen(false);
    setRecordingControls(true);
    els.mediaResult.classList.add("hidden");
    els.mediaProgress.style.width = "0%";
    els.mediaTime.textContent = "0:00";
    els.mediaStatus.textContent =
      els.videoMode.value === "orbit"
        ? "Gravando uma volta automática…"
        : "Gravando. Movimente a câmera livremente.";
    try {
      const webm = await house3dModule.startHouseRecording({
        mode: els.videoMode.value,
        durationSeconds: Number(els.videoDuration.value),
      });
      if (!mediaPanelOpen) return;
      els.mediaStatus.textContent =
        "Convertendo para MP4 compatível com WhatsApp…";
      const result = await convertRecording(webm);
      const filename = `my-home-modelo-3d-${mediaStamp()}.${result.extension}`;
      showMediaResult(result.blob, filename, "video");
      els.mediaStatus.textContent = result.converted
        ? "Vídeo MP4 pronto para compartilhar."
        : "FFmpeg indisponível ou falhou; o vídeo WebM original foi preservado.";
    } catch (error) {
      els.mediaStatus.textContent = `Não foi possível gravar: ${error.message}`;
    } finally {
      setRecordingControls(false);
    }
  }

  function updateMediaProgress(event) {
    const detail = event.detail || {};
    const seconds = Math.max(
      0,
      Math.ceil((detail.durationMs - detail.elapsedMs) / 1000),
    );
    els.mediaProgress.style.width = `${Math.round((detail.progress || 0) * 100)}%`;
    els.mediaTime.textContent =
      detail.state === "complete"
        ? "Pronto"
        : `0:${String(seconds).padStart(2, "0")}`;
  }

  function renderHouse(payload) {
    if (!payload.ok || !payload.house) return;
    const house = payload.house;
    state.house = house;
    state.project = payload.project || null;
    els.houseBlueprint.src =
      payload.blueprint_url || "/api/house/blueprint.jpg";
    const lot = house.lot_dimensions_meters || {};
    els.houseLot.innerHTML = `<div><span class="summary-label">Largura</span><strong>${lot.width ?? "—"} m</strong></div><div><span class="summary-label">Comprimento</span><strong>${lot.length ?? "—"} m</strong></div><div><span class="summary-label">Área</span><strong>${lot.area_m2 ?? "—"} m²</strong></div>`;
    els.houseExterior.innerHTML = (house.exterior_spaces || [])
      .map(
        (space) =>
          `<article class="house-card"><h3>${escapeHtml(space.label || space.name)}</h3><p>${escapeHtml(space.notes || space.description || "")}</p></article>`,
      )
      .join("");
    els.houseRooms.innerHTML = (house.interior_rooms || [])
      .map(
        (room) =>
          `<article class="house-card"><h3>${escapeHtml(room.label || room.name)}</h3><p>${escapeHtml(room.measured_dimensions || room.dimensions || "")}</p></article>`,
      )
      .join("");
    const audit = house.blueprint_audit || {};
    els.houseAudit.innerHTML = `<h3>${escapeHtml(audit.status || "Auditoria")}</h3><p>${escapeHtml(audit.summary || "")}</p>`;
    renderProject(state.project);
    renderDashboard();
    if (!document.getElementById("view-model3d").classList.contains("hidden"))
      renderHouse3D();
  }

  async function loadHouse() {
    try {
      renderHouse(await request("/api/house"));
    } catch (error) {
      setStatus(els.appStatus, "err", error.message);
    }
  }

  async function generatePrompt() {
    const ids = els.promptMissingOnly.checked
      ? state.materials
          .filter((item) => item.unit_price == null)
          .map((item) => item.id)
      : state.materials.map((item) => item.id);
    const result = await request("/api/prompts/price-discovery", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    });
    els.promptOutput.value = result.prompt || result.text || "";
  }

  async function previewImport() {
    const result = await request("/api/import/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pack_text: els.packInput.value,
        pack_id: "price",
      }),
    });
    state.importRows = result.rows || [];
    els.btnCommitImport.disabled = !result.ok || !state.importRows.length;
    setStatus(
      els.importStatus,
      result.ok ? "ok" : "err",
      result.ok
        ? `${state.importRows.length} linha(s) pronta(s).`
        : (result.errors || []).join(" · "),
    );
    els.importPreviewRows.innerHTML = state.importRows
      .map(
        (row) =>
          `<tr><td>${escapeHtml(row.id || "")}</td><td>${escapeHtml(row.description || "")}</td><td>${formatMoney(row.unit_price)}</td><td>${escapeHtml(row.vendor || "")}</td><td>${row.product_url ? `<a href="${escapeAttr(row.product_url)}" target="_blank">abrir</a>` : "—"}</td></tr>`,
      )
      .join("");
    const fix = result.fix_pack || result.fix_output || "";
    els.fixOutput.value = fix;
    els.fixOutput.classList.toggle("hidden", !fix);
    els.btnCopyFix.classList.toggle("hidden", !fix);
    els.btnDlFix.classList.toggle("hidden", !fix);
  }

  async function commitImport() {
    const result = await request("/api/import/commit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rows: state.importRows,
        pack_text: els.packInput.value,
        pack_id: "price",
      }),
    });
    if (result.state) applyExpenseState(result.state);
    await pushToRemote();
  }

  function downloadText(filename, text) {
    const url = URL.createObjectURL(
      new Blob([text], { type: "text/plain;charset=utf-8" }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function showView(name) {
    const validViews = new Set([
      "dashboard",
      "expenses",
      "house",
      "prices",
      "model3d",
      "gantt",
    ]);
    if (!validViews.has(name)) name = "dashboard";
    const isModel3D = name === "model3d";
    const wasModel3D = document.body.classList.contains("model3d-active");
    document
      .querySelectorAll(".view")
      .forEach((view) =>
        view.classList.toggle("hidden", view.id !== `view-${name}`),
      );
    document
      .querySelectorAll(".nav-btn")
      .forEach((button) =>
        button.classList.toggle("active", button.dataset.view === name),
      );
    document.body.classList.toggle("model3d-active", isModel3D);
    const hero = document.querySelector(".hero");
    hero.inert = isModel3D;
    hero.setAttribute("aria-hidden", String(isModel3D));
    history.replaceState(null, "", `#${name}`);
    if (isModel3D) {
      renderHouse3D();
      requestAnimationFrame(() =>
        els.btnModel3dHome.focus({ preventScroll: true }),
      );
    } else {
      if (sceneEditorOpen) setSceneEditorOpen(false);
      if (mediaPanelOpen) setMediaPanelOpen(false);
      window.scrollTo(0, 0);
      if (wasModel3D)
        requestAnimationFrame(() =>
          $("home-link").focus({ preventScroll: true }),
        );
    }
  }

  document
    .querySelectorAll("[data-view]")
    .forEach((button) =>
      button.addEventListener("click", () => showView(button.dataset.view)),
    );
  document.querySelectorAll("[data-view-link]").forEach((link) =>
    link.addEventListener("click", (event) => {
      event.preventDefault();
      showView(link.dataset.viewLink);
    }),
  );
  $("home-link").addEventListener("click", (event) => {
    event.preventDefault();
    showView("dashboard");
  });
  document.addEventListener(
    "keydown",
    (event) => {
      if (
        event.key === "Escape" &&
        !document.getElementById("view-model3d").classList.contains("hidden")
      ) {
        event.preventDefault();
        showView("dashboard");
        return;
      }
      const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(
        document.activeElement?.tagName,
      );
      if (
        sceneEditorOpen &&
        !typing &&
        !event.altKey &&
        !event.ctrlKey &&
        !event.metaKey
      ) {
        const mode = { t: "translate", r: "rotate", s: "scale" }[
          event.key.toLowerCase()
        ];
        if (mode) {
          event.preventDefault();
          document.querySelector(`[data-editor-mode="${mode}"]`)?.click();
          return;
        }
        if (event.key === "Delete") {
          event.preventDefault();
          els.btnDeleteObject.click();
          return;
        }
      }
      if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey)
        return;
      const view = {
        d: "dashboard",
        e: "expenses",
        c: "house",
        p: "prices",
        m: "model3d",
        g: "gantt",
        h: "dashboard",
      }[event.key.toLowerCase()];
      if (view) {
        event.preventDefault();
        showView(view);
      }
    },
    true,
  );
  els.btnModel3dHome.addEventListener("click", () => showView("dashboard"));
  els.btnToggleMedia.addEventListener("click", () =>
    setMediaPanelOpen(!mediaPanelOpen),
  );
  els.btnCloseMedia.addEventListener("click", () => setMediaPanelOpen(false));
  els.btnCaptureSnapshot.addEventListener("click", captureSnapshot);
  els.btnStartRecording.addEventListener("click", startRecording);
  els.btnStopRecording.addEventListener("click", () => {
    if (house3dModule?.stopHouseRecording())
      els.mediaStatus.textContent = "Finalizando gravação…";
  });
  els.btnShareMedia.addEventListener("click", shareMedia);
  els.btnDownloadMedia.addEventListener("click", downloadMedia);
  document
    .getElementById("house-3d-canvas")
    .addEventListener("scene-media-progress", updateMediaProgress);
  window.addEventListener("pagehide", clearMediaPreview);
  els.btnToggleEditor.addEventListener("click", () =>
    setSceneEditorOpen(!sceneEditorOpen),
  );
  els.btnCloseEditor.addEventListener("click", () => setSceneEditorOpen(false));
  document
    .getElementById("house-3d-canvas")
    .addEventListener("scene-editor-state", updateEditorState);
  document.querySelectorAll("[data-editor-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      document
        .querySelectorAll("[data-editor-mode]")
        .forEach((item) => item.classList.toggle("active", item === button));
      house3dModule?.setSceneTransformMode(button.dataset.editorMode);
    });
  });
  els.editorSnap.addEventListener("change", () =>
    house3dModule?.setSceneSnap(els.editorSnap.value),
  );
  els.btnApplyDimensions.addEventListener("click", () => {
    try {
      house3dModule?.setSceneSelectionDimensions({
        width: els.editorWidth.value,
        height: els.editorHeight.value,
        depth: els.editorDepth.value,
      });
    } catch (error) {
      els.editorStatus.textContent = error.message;
    }
  });
  els.assetPalette.addEventListener("click", (event) => {
    const button = event.target.closest("[data-asset-type]");
    if (button)
      house3dModule?.beginSceneAssetPlacement(button.dataset.assetType);
  });
  els.assetPalette.addEventListener("dragstart", (event) => {
    const button = event.target.closest("[data-asset-type]");
    if (!button) return;
    event.dataTransfer.setData(
      "application/x-my-home-asset",
      button.dataset.assetType,
    );
    event.dataTransfer.effectAllowed = "copy";
    house3dModule?.beginSceneAssetPlacement(button.dataset.assetType);
  });
  els.btnDuplicateObject.addEventListener("click", () => {
    if (!house3dModule?.duplicateSceneSelection())
      els.editorStatus.textContent =
        "Somente objetos adicionados podem ser duplicados.";
  });
  els.btnDeleteObject.addEventListener("click", () => {
    if (!house3dModule?.deleteSceneSelection())
      els.editorStatus.textContent =
        "A arquitetura original não pode ser excluída.";
  });
  els.btnResetObject.addEventListener("click", () =>
    house3dModule?.resetSceneSelection(),
  );
  els.btnSaveLayout.addEventListener("click", saveSceneLayout);

  els.priority.addEventListener("change", renderExpenseTable);
  els.category.addEventListener("change", renderExpenseTable);
  els.search.addEventListener("input", renderExpenseTable);
  els.dashMaterials.addEventListener("mouseover", (event) => {
    const target = event.target.closest(".expense-hover-target");
    if (target) showDashboardTooltip(target, event.clientX, event.clientY);
  });
  els.dashMaterials.addEventListener("mousemove", (event) => {
    if (event.target.closest(".expense-hover-target"))
      positionDashboardTooltip(event.clientX, event.clientY);
  });
  els.dashMaterials.addEventListener("mouseout", (event) => {
    const target = event.target.closest(".expense-hover-target");
    if (target && !target.contains(event.relatedTarget)) hideDashboardTooltip();
  });
  els.dashMaterials.addEventListener("focusin", (event) => {
    const target = event.target.closest(".expense-hover-target");
    if (!target) return;
    const rect = target.getBoundingClientRect();
    showDashboardTooltip(target, rect.right, rect.top);
  });
  els.dashMaterials.addEventListener("focusout", hideDashboardTooltip);
  els.btnNew.addEventListener("click", () => openExpenseDialog());
  els.form.addEventListener("submit", submitExpense);
  els.btnCancel.addEventListener("click", () => els.dialog.close());
  els.fieldRecordType.addEventListener("change", () =>
    updateExpenseServiceLinks(),
  );
  els.fieldProvider.addEventListener("change", () =>
    updateExpenseServiceLinks(els.fieldProvider.value, ""),
  );
  els.iconPicker.addEventListener("click", (event) => {
    const button = event.target.closest("[data-icon-key]");
    if (button) renderIconPicker(button.dataset.iconKey);
  });
  els.rows.addEventListener("click", async (event) => {
    const edit = event.target.closest("[data-edit-expense]");
    const remove = event.target.closest("[data-delete-expense]");
    if (edit)
      openExpenseDialog(
        state.expenses.find((item) => item.id === edit.dataset.editExpense),
      );
    if (remove) {
      try {
        await deleteExpense(remove.dataset.deleteExpense);
      } catch (error) {
        setStatus(els.appStatus, "err", error.message);
      }
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
  els.taskActivityType.addEventListener("change", syncTaskHierarchyFields);
  els.taskParent.addEventListener("change", () => {
    syncTaskHierarchyFields();
    if (els.taskIconMode.value === "auto") renderTaskIconPicker("", "auto");
  });
  [els.taskTitle, els.taskDescription, els.taskExpense].forEach((field) => {
    field.addEventListener("change", () => {
      if (els.taskIconMode.value === "auto") renderTaskIconPicker("", "auto");
    });
  });
  els.taskIconPicker.addEventListener("click", (event) => {
    const button = event.target.closest("[data-task-icon]");
    if (button) renderTaskIconPicker(button.dataset.taskIcon, "manual");
  });
  els.btnTaskIconAuto.addEventListener("click", () =>
    renderTaskIconPicker("", "auto"),
  );
  els.btnCancelTask.addEventListener("click", () => els.taskDialog.close());
  els.btnDeleteTask.addEventListener("click", deleteTask);
  els.btnExpandAll.addEventListener("click", () => {
    state.expandedMacros = new Set(macroTasks().map((item) => item.id));
    persistExpandedMacros();
    renderGantt();
  });
  els.btnCollapseAll.addEventListener("click", () => {
    state.expandedMacros.clear();
    persistExpandedMacros();
    renderGantt();
  });
  els.ganttZoom.addEventListener("change", () => {
    state.zoom = els.ganttZoom.value;
    renderGantt();
  });
  els.btnGanttToday.addEventListener("click", () => {
    const scroll = $("gantt-scroll");
    const line = els.gantt.querySelector(".gantt-today");
    if (scroll && line)
      scroll.scrollTo({
        left: Math.max(0, parseFloat(line.style.left) - scroll.clientWidth / 2),
        behavior: "smooth",
      });
  });
  els.btnGenPrompt.addEventListener("click", () =>
    generatePrompt().catch((error) =>
      setStatus(els.appStatus, "err", error.message),
    ),
  );
  els.btnCopyPrompt.addEventListener("click", () =>
    navigator.clipboard.writeText(els.promptOutput.value),
  );
  els.btnDlPrompt.addEventListener("click", () =>
    downloadText("price-discovery-prompt.txt", els.promptOutput.value),
  );
  els.packFile.addEventListener("change", async () => {
    if (els.packFile.files[0])
      els.packInput.value = await els.packFile.files[0].text();
  });
  els.btnPreviewImport.addEventListener("click", () =>
    previewImport().catch((error) =>
      setStatus(els.importStatus, "err", error.message),
    ),
  );
  els.btnCommitImport.addEventListener("click", () =>
    commitImport().catch((error) =>
      setStatus(els.importStatus, "err", error.message),
    ),
  );
  els.btnCopyFix.addEventListener("click", () =>
    navigator.clipboard.writeText(els.fixOutput.value),
  );
  els.btnDlFix.addEventListener("click", () =>
    downloadText("price-pack-fix.txt", els.fixOutput.value),
  );
  els.showArchivedContracts.addEventListener("change", renderContractCenter);
  els.btnNewProvider.addEventListener("click", () => openProviderDialog());
  els.btnNewContract.addEventListener("click", () => openContractDialog());
  els.providerForm.addEventListener("submit", submitProvider);
  els.btnCancelProvider.addEventListener("click", () =>
    els.providerDialog.close(),
  );
  els.btnArchiveProvider.addEventListener("click", () =>
    archiveEntity("providers", els.providerId.value).catch((error) =>
      setStatus(els.providerFormError, "err", error.message),
    ),
  );
  els.contractForm.addEventListener("submit", submitContract);
  els.btnCancelContract.addEventListener("click", () =>
    els.contractDialog.close(),
  );
  els.btnArchiveContract.addEventListener("click", () =>
    archiveEntity("contracts", els.contractId.value).catch((error) =>
      setStatus(els.contractFormError, "err", error.message),
    ),
  );
  els.contractList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-edit-contract]");
    if (button)
      openContractDialog(
        state.contracts.find((item) => item.id === button.dataset.editContract),
      );
  });
  els.providerList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-edit-provider]");
    if (button)
      openProviderDialog(
        state.providers.find((item) => item.id === button.dataset.editProvider),
      );
  });

  Promise.all([
    loadState(),
    loadTasks(),
    loadNotes(),
    loadCashflow(),
    loadHouse(),
    loadProviders(),
    loadContracts(),
  ])
    .then(() => {
      renderContractCenter();
      showView(location.hash.slice(1) || "dashboard");
    })
    .catch((error) => setStatus(els.appStatus, "err", error.message));
})();
