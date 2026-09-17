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
    cashflow: null,
    quotationExpenseId: "",
    quotationImportRows: [],
    editingQuotationMetadata: {},
    editingQuotationSource: "manual",
    editingPayments: [],
    editingTaskAllocations: [],
    editingContractPayments: [],
    zoom: "week",
    ganttStatusFilter: "",
    ganttPriorityFilter: 0,
    expandedMacros: new Set(),
  };
  const statusLabels = {
    pending: "Pendente",
    in_progress: "Em andamento",
    blocked: "Bloqueada",
    completed: "Concluída",
  };
  const dashboardCategoryDefinitions = [
    { id: "materials", label: "Materiais", icon: "materials-crate" },
    { id: "diligences", label: "Diligências", icon: "notary-services" },
    { id: "financing", label: "Financiamento", icon: "mortgage-contract" },
    { id: "services", label: "Serviços", icon: "mason-service" },
    { id: "reserve", label: "Reservas", icon: "emergency-reserve" },
  ];

  const els = {
    appStatus: $("app-status"),
    houseNameInput: $("house-name-input"),
    houseNameStatus: $("house-name-status"),
    model3dHouseName: $("model3d-house-name"),
    btnPush: $("btn-push"),
    pushStatus: $("push-status"),
    dashTotalAll: $("dash-total-all"),
    dashTotalMinimum: $("dash-total-minimum"),
    dashTotalMaximum: $("dash-total-maximum"),
    dashUnpricedCount: $("dash-unpriced-count"),
    fundsTotal: $("funds-total"),
    fundsDetail: $("funds-detail"),
    fundingPie: $("funding-pie"),
    overallCoverage: $("overall-coverage"),
    coverageDonut: $("coverage-donut"),
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
    houseSavingsLineChart: $("house-savings-line-chart"),
    houseSavingsPlanSummary: $("house-savings-plan-summary"),
    paymentProjectionChart: $("payment-projection-chart"),
    paymentProjectionSummary: $("payment-projection-summary"),
    monthlySavingsGrid: $("monthly-savings-grid"),
    cashflowMethod: $("cashflow-method"),
    macroTimeline: $("macro-timeline"),
    taskSummary: $("task-summary"),
    taskPriorityFilter: $("task-priority-filter"),
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
    taskAllocationEditor: $("task-allocation-editor"),
    taskAllocationList: $("task-allocation-list"),
    taskAllocationTotal: $("task-allocation-total"),
    btnAddTaskAllocation: $("btn-add-task-allocation"),
    taskIcon: $("task-icon"),
    taskIconMode: $("task-icon-mode"),
    taskIconPreview: $("task-icon-preview"),
    taskIconPicker: $("task-icon-picker"),
    btnTaskIconAuto: $("btn-task-icon-auto"),
    taskFormError: $("task-form-error"),
    btnDeleteTask: $("btn-delete-task"),
    btnCancelTask: $("btn-cancel-task"),
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
    fieldCategory: $("field-category"),
    fieldDescription: $("field-description"),
    fieldIconKey: $("field-icon-key"),
    iconPreview: $("icon-preview"),
    iconPicker: $("icon-picker"),
    fieldQuantity: $("field-quantity"),
    fieldUnit: $("field-unit"),
    expensePaymentList: $("expense-payment-list"),
    expensePaymentTotal: $("expense-payment-total"),
    btnAddPayment: $("btn-add-payment"),
    expenseServiceLinks: $("expense-service-links"),
    fieldProvider: $("field-provider"),
    fieldContract: $("field-contract"),
    formError: $("form-error"),
    btnCancel: $("btn-cancel"),
    categorySuggestions: $("category-suggestions"),
    quotationDialog: $("quotation-dialog"),
    quotationExpenseTitle: $("quotation-expense-title"),
    quotationExpenseMeta: $("quotation-expense-meta"),
    quotationList: $("quotation-list"),
    quotationEmpty: $("quotation-empty"),
    quotationForm: $("quotation-form"),
    quotationFormTitle: $("quotation-form-title"),
    quotationId: $("quotation-id"),
    quotationVendor: $("quotation-vendor"),
    quotationUnitPrice: $("quotation-unit-price"),
    quotationQuantity: $("quotation-quantity"),
    quotationUnit: $("quotation-unit"),
    quotationShipping: $("quotation-shipping"),
    quotationTotal: $("quotation-total"),
    quotationCheckedAt: $("quotation-checked-at"),
    quotationUrl: $("quotation-url"),
    quotationNotes: $("quotation-notes"),
    quotationFormError: $("quotation-form-error"),
    quotationAiPanel: $("quotation-ai-panel"),
    quotationSourceInput: $("quotation-source-input"),
    quotationSourceFile: $("quotation-source-file"),
    quotationSourceStatus: $("quotation-source-status"),
    quotationPromptOutput: $("quotation-prompt-output"),
    quotationPackInput: $("quotation-pack-input"),
    quotationCorrectionInstructions: $("quotation-correction-instructions"),
    quotationPackFile: $("quotation-pack-file"),
    quotationImportStatus: $("quotation-import-status"),
    quotationFixOutput: $("quotation-fix-output"),
    quotationLimitLabel: $("quotation-limit-label"),
    btnCloseQuotations: $("btn-close-quotations"),
    btnNewQuotation: $("btn-new-quotation"),
    btnCancelQuotation: $("btn-cancel-quotation"),
    btnQuotationPrompt: $("btn-quotation-prompt"),
    btnCopyQuotationPrompt: $("btn-copy-quotation-prompt"),
    btnPreviewQuotationImport: $("btn-preview-quotation-import"),
    btnCommitQuotationImport: $("btn-commit-quotation-import"),
    btnCopyQuotationFix: $("btn-copy-quotation-fix"),
    houseBlueprint: $("house-blueprint"),
    blueprintViewport: $("blueprint-viewport"),
    blueprintZoomLabel: $("blueprint-zoom-label"),
    btnExportBlueprint: $("btn-export-blueprint"),
    houseLot: $("house-lot"),
    houseExterior: $("house-exterior"),
    houseRooms: $("house-rooms"),
    house3dStatus: $("house-3d-status"),
    house3dAssumptions: $("house-3d-assumptions"),
    btnModel3dHome: $("btn-model3d-home"),
    btnModel3dHelp: $("btn-model3d-help"),
    model3dHelpDialog: $("model3d-help-dialog"),
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
    assetPaletteSearch: $("asset-palette-search"),
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
    requiredTools: $("required-tools"),
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
    contractPaymentPlan: $("contract-payment-plan"),
    contractPaymentFrequency: $("contract-payment-frequency"),
    contractWorkPeriod: $("contract-work-period"),
    contractPaymentSummary: $("contract-payment-summary"),
    contractPaymentSchedule: $("contract-payment-schedule"),
    btnAddContractPayment: $("btn-add-contract-payment"),
    contractExpenses: $("contract-expenses"),
    contractNotes: $("contract-notes"),
    contractPdf: $("contract-pdf"),
    contractFormError: $("contract-form-error"),
    btnArchiveContract: $("btn-archive-contract"),
    btnCancelContract: $("btn-cancel-contract"),
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
    const { allowPayloadError = false, ...fetchOptions } = options;
    const response = await fetch(url, fetchOptions);
    const payload = await response.json();
    if (!response.ok || (payload.ok === false && !allowPayloadError))
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
    const count = (item.quotations || []).length;
    if (item.unit_price != null) parts.push(formatMoney(item.unit_price));
    parts.push(
      `${item.scenario?.expected_quantity ?? item.quantity ?? 0} ${escapeHtml(item.unit || "")}`,
    );
    if (item.scenario?.minimum != null && item.scenario?.maximum != null)
      parts.push(
        `mín. ${formatMoney(item.scenario.minimum)} · máx. ${formatMoney(item.scenario.maximum)}`,
      );
    if (item.scenario?.unpriced)
      parts.push('<span class="badge">Sem cotação</span>');
    if (item.vendor) parts.push(escapeHtml(item.vendor));
    if (item.product_url)
      parts.push(
        `<a class="link-btn" href="${escapeAttr(item.product_url)}" target="_blank" rel="noopener">abrir</a>`,
      );
    parts.push(
      `<span class="quote-count">${count}/5 ${count === 1 ? "cotação" : "cotações"}</span>`,
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
        (
          item,
        ) => `<tr class="expense-row" data-open-quotations="${escapeAttr(item.id)}" tabindex="0" aria-label="Gerenciar cotações de ${escapeAttr(item.description)}">
      <td>${escapeHtml(item.category)}</td>
      <td>${itemLabel(item.description, item.icon_key)}</td><td class="num">${formatMoney(item.value)}</td>
      <td>${priceCell(item)}</td><td class="actions"><button class="btn quotation-action-btn" data-open-expense-quotations="${escapeAttr(item.id)}" title="Abrir análise de preços e cotações">Cotações <span>${(item.quotations || []).length}/5</span></button><button class="btn" data-edit-expense="${item.id}">Editar</button><button class="btn danger" data-delete-expense="${item.id}">Excluir</button></td>
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

  function formatPaymentDate(value) {
    const [year, month, day] = String(value).split("-").map(Number);
    if (!year || !month || !day) return String(value || "");
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      timeZone: "UTC",
    }).format(new Date(Date.UTC(year, month - 1, day)));
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
    state.cashflow = payload;
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
    if (els.cashflowTotalSavings)
      els.cashflowTotalSavings.textContent = formatMoney(totalSavings);
    if (els.cashflowAverageSavings)
      els.cashflowAverageSavings.textContent = formatMoney(
        months.length ? totalSavings / months.length : 0,
      );
    if (els.cashflowTotalExpenses)
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
    if (els.expenseTreemap)
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
    if (els.cashflowLineChart)
      els.cashflowLineChart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Fluxo de caixa líquido mensal projetado">${grid}<polygon points="${area}" class="cashflow-area"></polygon><polyline points="${polyline}" class="cashflow-line"></polyline>${points.map(({ x, y, item }, index) => `<g><circle cx="${x}" cy="${y}" r="5" class="cashflow-point"></circle><title>${cashflowMonthLabel(item.month)}: ${formatMoney(item.net_savings)}</title>${index % 2 === 0 || index === points.length - 1 ? `<text x="${x}" y="${height - 15}" text-anchor="middle" class="cashflow-axis-label">${cashflowMonthLabel(item.month)}</text>` : ""}</g>`).join("")}</svg>`;

    const savingsPlan = payload.house_savings_plan || {};
    const monthlyContribution =
      Number(savingsPlan.combined_monthly) ||
      Number(savingsPlan.eduardo_monthly || 0) +
        Number(savingsPlan.leonardo_monthly || 0);
    let plannedSavings = 0;
    const savingsMonths = months
      .filter(
        (item) =>
          (!savingsPlan.start || item.month >= savingsPlan.start) &&
          (!savingsPlan.end || item.month <= savingsPlan.end),
      )
      .map((item) => ({
        month: item.month,
        contribution: monthlyContribution,
        cumulative: (plannedSavings += monthlyContribution),
      }));
    const savingsMaximum = Math.max(
      monthlyContribution,
      ...savingsMonths.map((item) => item.cumulative),
    );
    const savingsPoints = savingsMonths.map((item, index) => ({
      x:
        margin.left +
        (savingsMonths.length > 1
          ? (index / (savingsMonths.length - 1)) * plotWidth
          : 0),
      y:
        margin.top +
        plotHeight -
        (item.cumulative / savingsMaximum) * plotHeight,
      item,
    }));
    const savingsPolyline = savingsPoints
      .map(({ x, y }) => `${x},${y}`)
      .join(" ");
    const savingsArea = `${margin.left},${margin.top + plotHeight} ${savingsPolyline} ${margin.left + plotWidth},${margin.top + plotHeight}`;
    const savingsGrid = [0, 0.25, 0.5, 0.75, 1]
      .map((ratio) => {
        const y = margin.top + plotHeight - ratio * plotHeight;
        return `<line x1="${margin.left}" y1="${y}" x2="${margin.left + plotWidth}" y2="${y}" class="cashflow-grid-line"></line><text x="${margin.left - 9}" y="${y + 4}" text-anchor="end" class="cashflow-axis-label">${formatMoney(savingsMaximum * ratio).replace(",00", "")}</text>`;
      })
      .join("");
    const projectedTotal =
      Number(savingsPlan.projected_total) || plannedSavings;
    els.houseSavingsPlanSummary.textContent = `${formatMoney(savingsPlan.eduardo_monthly || 0)} Eduardo + ${formatMoney(savingsPlan.leonardo_monthly || 0)} Leo/mês · total ${formatMoney(projectedTotal)}`;
    els.houseSavingsLineChart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Reserva acumulada de ${formatMoney(projectedTotal)} para despesas da casa">${savingsGrid}<polygon points="${savingsArea}" class="house-savings-area"></polygon><polyline points="${savingsPolyline}" class="house-savings-line"></polyline>${savingsPoints.map(({ x, y, item }, index) => `<g><circle cx="${x}" cy="${y}" r="5" class="house-savings-point"></circle><title>${cashflowMonthLabel(item.month)}: aporte ${formatMoney(item.contribution)} · acumulado ${formatMoney(item.cumulative)}</title>${index % 2 === 0 || index === savingsPoints.length - 1 ? `<text x="${x}" y="${height - 15}" text-anchor="middle" class="cashflow-axis-label">${cashflowMonthLabel(item.month)}</text>` : ""}</g>`).join("")}</svg>`;

    if (els.monthlySavingsGrid) {
      let cumulative = 0;
      els.monthlySavingsGrid.innerHTML = months
        .map((item) => {
          cumulative += Number(item.net_savings || 0);
          return `<article><span>${cashflowMonthLabel(item.month)}${item.estimated ? " · estimado" : ""}</span><strong>${formatMoney(item.net_savings)}</strong><small>Acumulado ${formatMoney(cumulative)}</small></article>`;
        })
        .join("");
    }
    if (els.cashflowMethod)
      els.cashflowMethod.textContent =
        (payload.interpolation || {}).method || "";
    renderDashboard();
  }

  function paymentEvents() {
    const scheduledContracts = state.contracts.filter(
      (contract) =>
        contract.type === "service" &&
        !contract.archived &&
        contract.status !== "cancelled" &&
        (contract.payment_schedule || []).length,
    );
    const contractExpenseIds = new Set(
      scheduledContracts.flatMap((contract) => contract.expense_ids || []),
    );
    const expenseEvents = state.expenses
      .filter((expense) => !contractExpenseIds.has(expense.id))
      .flatMap((expense) =>
        (expense.payments || []).map((payment) => ({
          ...payment,
          expenseId: expense.id,
          expenseIds: [expense.id],
          taskId: payment.task_id || "",
          description: expense.description,
          category: expense.category,
          iconKey: expense.icon_key,
          amount: Number(payment.amount || 0),
        })),
      );
    const contractEvents = scheduledContracts.flatMap((contract) => {
      const provider = state.providers.find(
        (item) => item.id === contract.provider_id,
      );
      return (contract.payment_schedule || []).map((payment) => ({
        ...payment,
        contractId: contract.id,
        expenseIds: contract.expense_ids || [],
        description: provider?.name || contract.title,
        category: "Mão de obra",
        iconKey: "mason-service",
        amount: Number(payment.amount || 0),
      }));
    });
    return [...expenseEvents, ...contractEvents]
      .filter((payment) => payment.date && Number.isFinite(payment.amount))
      .sort((left, right) => left.date.localeCompare(right.date));
  }

  function renderPaymentProjection() {
    if (!els.paymentProjectionChart) return;
    const grouped = new Map();
    for (const payment of paymentEvents()) {
      if (!grouped.has(payment.date))
        grouped.set(payment.date, {
          date: payment.date,
          amount: 0,
          payments: [],
          estimated: false,
        });
      const day = grouped.get(payment.date);
      day.amount += payment.amount;
      day.payments.push(payment);
      day.estimated ||= payment.date_status === "estimated";
    }
    const days = [...grouped.values()];
    if (!days.length) {
      els.paymentProjectionSummary.textContent =
        "Cadastre datas nas despesas para criar a projeção.";
      els.paymentProjectionChart.innerHTML =
        '<p class="payment-projection-empty">Nenhum pagamento programado.</p>';
      return;
    }
    const width = Math.max(1000, days.length * 58);
    const height = 300;
    const margin = { left: 72, right: 28, top: 24, bottom: 48 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const firstDate = days[0].date;
    const lastDate = days.at(-1).date;
    const span = Math.max(1, dayDiff(firstDate, lastDate));
    const maximum = Math.max(1, ...days.map((item) => item.amount));
    const points = days.map((item) => ({
      x: margin.left + (dayDiff(firstDate, item.date) / span) * plotWidth,
      y: margin.top + plotHeight - (item.amount / maximum) * plotHeight,
      item,
    }));
    const grid = [0, 0.25, 0.5, 0.75, 1]
      .map((ratio) => {
        const y = margin.top + plotHeight - ratio * plotHeight;
        return `<line x1="${margin.left}" y1="${y}" x2="${margin.left + plotWidth}" y2="${y}" class="cashflow-grid-line"></line><text x="${margin.left - 9}" y="${y + 4}" text-anchor="end" class="cashflow-axis-label">${formatMoney(maximum * ratio).replace(",00", "")}</text>`;
      })
      .join("");
    const labelStep = Math.max(1, Math.ceil(days.length / 14));
    const polyline = points.map(({ x, y }) => `${x},${y}`).join(" ");
    const today = iso(new Date());
    const todayX =
      today >= firstDate && today <= lastDate
        ? margin.left + (dayDiff(firstDate, today) / span) * plotWidth
        : null;
    const total = days.reduce((sum, item) => sum + item.amount, 0);
    const estimatedCount = paymentEvents().filter(
      (item) => item.date_status === "estimated",
    ).length;
    els.paymentProjectionSummary.textContent = `${days.length} dias · ${formatMoney(total)} · ${estimatedCount} datas presumidas`;
    els.paymentProjectionChart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" style="min-width:${width}px" role="img" aria-label="Projeção de despesas por dia de pagamento">${grid}${todayX === null ? "" : `<line x1="${todayX}" y1="${margin.top}" x2="${todayX}" y2="${margin.top + plotHeight}" class="payment-today-line"></line><path d="M ${todayX - 7} ${margin.top + plotHeight + 9} L ${todayX + 7} ${margin.top + plotHeight + 9} L ${todayX} ${margin.top + plotHeight - 3} Z" class="payment-today-marker"><title>Hoje · ${formatPaymentDate(today)}</title></path>`}<polyline points="${polyline}" class="payment-projection-line"></polyline>${points
      .map(({ x, y, item }, index) => {
        const details = item.payments
          .map(
            (payment) =>
              `${payment.description}: ${formatMoney(payment.amount)}${payment.date_status === "estimated" ? " (presumido)" : ""}`,
          )
          .join(" · ");
        return `<g class="${item.estimated ? "estimated" : "confirmed"}"><line x1="${x}" y1="${margin.top}" x2="${x}" y2="${margin.top + plotHeight}" class="payment-day-line"></line><circle cx="${x}" cy="${y}" r="6" class="payment-day-point"></circle><title>${escapeHtml(`${formatPaymentDate(item.date)} · ${formatMoney(item.amount)} · ${details}`)}</title>${index % labelStep === 0 || index === points.length - 1 ? `<text x="${x}" y="${height - 18}" text-anchor="middle" class="cashflow-axis-label">${formatPaymentDate(item.date).slice(0, 5)}</text>` : ""}</g>`;
      })
      .join("")}</svg>`;
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
    const grouped = Object.fromEntries(
      dashboardCategoryDefinitions.map((group) => [group.id, []]),
    );
    state.expenses.forEach((item) => {
      grouped[dashboardExpenseGroup(item)].push(item);
    });
    els.dashMaterials.innerHTML = dashboardCategoryDefinitions
      .map((group) => {
        const items = grouped[group.id];
        const total = items.reduce(
          (sum, item) => sum + Number(item.value || 0),
          0,
        );
        const minimum = items.reduce(
          (sum, item) => sum + Number(item.scenario?.minimum || 0),
          0,
        );
        const maximum = items.reduce(
          (sum, item) => sum + Number(item.scenario?.maximum || 0),
          0,
        );
        const range = `${formatMoney(total)} · mín. ${formatMoney(minimum)} · máx. ${formatMoney(maximum)}`;
        return `<article class="dashboard-expense-category">
          <div class="dashboard-expense-category-head">
            <span class="expense-hover-target category-hover-target" tabindex="0" data-hover-name="${escapeAttr(group.label)}" data-hover-amount="${escapeAttr(range)}" aria-label="${escapeAttr(`${group.label}: ${range}`)}">${iconMarkup(group.icon, group.label)}</span>
            <span><strong>${escapeHtml(group.label)}</strong><small>${formatMoney(total)} · ${items.length} ${items.length === 1 ? "item" : "itens"}</small></span>
          </div>
          <div class="dashboard-expense-icons" aria-label="${escapeAttr(`Itens de ${group.label}`)}">
            ${items
              .map(
                (item) =>
                  `<span class="expense-hover-target dashboard-expense-icon" tabindex="0" data-hover-name="${escapeAttr(item.description)}" data-hover-amount="${escapeAttr(`${formatMoney(item.value)} · mín. ${formatMoney(item.scenario?.minimum || 0)} · máx. ${formatMoney(item.scenario?.maximum || 0)}`)}" aria-label="${escapeAttr(`${item.description}: ${formatMoney(item.value)}`)}">${iconMarkup(item.icon_key, item.description)}</span>`,
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
    els.dashTotalMinimum.textContent = formatMoney(
      state.totals.scenarios?.minimum || 0,
    );
    els.dashTotalMaximum.textContent = formatMoney(
      state.totals.scenarios?.maximum || 0,
    );
    els.dashUnpricedCount.textContent = `${state.totals.scenarios?.unpriced_count || 0} sem cotação`;
    const funding = (state.project || {}).funding || {};
    const sources = funding.sources || [];
    const fundsTotal = sources.reduce(
      (sum, item) => sum + Number(item.amount || 0),
      0,
    );
    const savingsPlan = state.cashflow?.house_savings_plan || {};
    const monthlySavings =
      Number(savingsPlan.combined_monthly) ||
      Number(savingsPlan.eduardo_monthly || 0) +
        Number(savingsPlan.leonardo_monthly || 0);
    const projectedSavings =
      Number(savingsPlan.projected_total) ||
      monthlySavings * Number(savingsPlan.installments || 0);
    const fundingSlices = [
      {
        id: "fgts",
        label: sources.find((item) => item.id === "fgts")?.label || "FGTS",
        value: Number(sources.find((item) => item.id === "fgts")?.amount || 0),
      },
      {
        id: "flexible",
        label: "Recursos livres",
        value: sources
          .filter((item) => item.id !== "fgts")
          .reduce((sum, item) => sum + Number(item.amount || 0), 0),
      },
      {
        id: "projected",
        label: "Economia projetada",
        value: projectedSavings,
      },
    ];
    const projectedFundsTotal = fundsTotal + projectedSavings;
    let pieAngle = 0;
    const pieStops = fundingSlices
      .map((slice) => {
        const start = pieAngle;
        pieAngle += projectedFundsTotal
          ? (slice.value / projectedFundsTotal) * 360
          : 0;
        return `var(--funding-${slice.id}) ${start}deg ${pieAngle}deg`;
      })
      .join(", ");
    els.fundsTotal.textContent = formatMoney(projectedFundsTotal);
    els.fundsDetail.innerHTML = fundingSlices
      .map(
        (slice) =>
          `<div><i class="funding-swatch ${slice.id}" aria-hidden="true"></i><span>${escapeHtml(slice.label)}</span><strong>${formatMoney(slice.value)}</strong></div>`,
      )
      .join("");
    els.fundingPie.style.background = `conic-gradient(${pieStops})`;
    els.fundingPie.setAttribute(
      "aria-label",
      fundingSlices
        .map((slice) => `${slice.label}: ${formatMoney(slice.value)}`)
        .join(" · "),
    );
    const projectedCovered = fundsTotal + projectedSavings;
    const coverage = state.totals.all
      ? (projectedCovered / state.totals.all) * 100
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
    const gap = projectedCovered - Number(state.totals.all || 0);
    els.overallGap.textContent = `${formatMoney(fundsTotal)} atuais + ${formatMoney(projectedSavings)} projetados · ${
      gap >= 0
        ? `margem de ${formatMoney(gap)}`
        : `lacuna de ${formatMoney(Math.abs(gap))}`
    }`;
    const categories = dashboardCategoryDefinitions.map((group) => ({
      ...group,
      value: state.expenses
        .filter((item) => dashboardExpenseGroup(item) === group.id)
        .reduce((sum, item) => sum + Number(item.value || 0), 0),
    }));
    const maximum = Math.max(1, ...categories.map((item) => item.value));
    els.categoryChart.innerHTML = categories
      .map(
        (item) =>
          `<div class="budget-bar-row"><div class="budget-bar-head"><span class="budget-category-label">${iconMarkup(item.icon, item.label)}<span>${escapeHtml(item.label)}</span></span><strong>${formatMoney(item.value)}</strong></div><div class="budget-bar-track"><span style="width:${Math.max(1, (item.value / maximum) * 100)}%"></span></div></div>`,
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
    renderPaymentProjection();
    renderGantt();
    renderMacroTimeline();
  }

  function macroTasks() {
    return state.tasks.filter((task) => task.activity_type === "macro");
  }

  function childTasks(macroId) {
    return state.tasks.filter((task) => task.parent_id === macroId);
  }

  function matchesGanttFilters(task) {
    return (
      (!state.ganttStatusFilter || task.status === state.ganttStatusFilter) &&
      (!state.ganttPriorityFilter ||
        Number(task.priority) === state.ganttPriorityFilter)
    );
  }

  function visibleGanttTasks() {
    const visible = [];
    macroTasks().forEach((macro) => {
      const children = childTasks(macro.id).filter(matchesGanttFilters);
      if (
        (state.ganttStatusFilter || state.ganttPriorityFilter) &&
        !children.length
      )
        return;
      visible.push(macro);
      if (state.expandedMacros.has(macro.id)) visible.push(...children);
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
    dates.push(...paymentEvents().map((payment) => parseDate(payment.date)));
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
          `<button type="button" class="task-count status-${key}${state.ganttStatusFilter === key ? " active" : ""}" data-gantt-status="${key}" aria-pressed="${state.ganttStatusFilter === key}"><strong>${counts[key] || 0}</strong>${label}</button>`,
      )
      .join("");
    const priorityCounts = allDetails.reduce(
      (map, task) => (
        (map[task.priority] = (map[task.priority] || 0) + 1),
        map
      ),
      {},
    );
    els.taskPriorityFilter.innerHTML = [1, 2, 3]
      .map(
        (priority) =>
          `<button type="button" class="task-count priority-filter${state.ganttPriorityFilter === priority ? " active" : ""}" data-gantt-priority="${priority}" aria-pressed="${state.ganttPriorityFilter === priority}"><strong>${priorityCounts[priority] || 0}</strong>P${priority}</button>`,
      )
      .join("");
    if (!tasks.length) {
      els.gantt.innerHTML = `<div class="gantt-empty">${
        state.ganttStatusFilter || state.ganttPriorityFilter
          ? "Nenhuma atividade corresponde aos filtros selecionados."
          : "Nenhuma tarefa. Crie a primeira para começar o cronograma."
      }</div>`;
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
    const paymentDays = new Map();
    for (const payment of paymentEvents()) {
      if (!paymentDays.has(payment.date))
        paymentDays.set(payment.date, {
          amount: 0,
          estimated: false,
          descriptions: [],
        });
      const item = paymentDays.get(payment.date);
      item.amount += payment.amount;
      item.estimated ||= payment.date_status === "estimated";
      item.descriptions.push(payment.description);
    }
    els.gantt.innerHTML = `<div class="gantt-label-head">Macroatividade / atividade</div>
      <div class="gantt-scroll" id="gantt-scroll"><div class="gantt-timeline">
        <div class="gantt-header">${ganttHeader(geometry)}</div>
        <div class="gantt-today" style="left:${todayLeft}px"><span>Hoje</span></div>
        ${[...paymentDays.entries()]
          .map(
            ([paymentDate, item]) =>
              `<div class="gantt-payment-day${item.estimated ? " estimated" : ""}" style="left:${dayDiff(geometry.start, paymentDate) * geometry.dayWidth}px" title="${escapeAttr(`${formatPaymentDate(paymentDate)} · ${formatMoney(item.amount)} · ${item.descriptions.join(", ")}`)}"><span></span></div>`,
          )
          .join("")}
        ${tasks
          .map((task) => {
            const left =
              dayDiff(geometry.start, task.start_date) * geometry.dayWidth;
            const width = Math.max(
              geometry.dayWidth,
              (dayDiff(task.start_date, task.end_date) + 1) * geometry.dayWidth,
            );
            const isMacro = task.activity_type === "macro";
            const taskPayments = isMacro
              ? []
              : paymentEvents().filter(
                  (payment) =>
                    payment.taskId === task.id ||
                    (task.expense_allocations || []).some((allocation) =>
                      (payment.expenseIds || []).includes(
                        allocation.expense_id,
                      ),
                    ),
                );
            return `<div class="gantt-track${isMacro ? " macro" : " child"}" data-track-id="${task.id}">
            <button type="button" class="gantt-bar status-${task.status}${isMacro ? " macro" : ""}" ${isMacro ? `data-macro-bar="${task.id}"` : `data-task-bar="${task.id}"`} style="left:${left}px;width:${width}px" title="${escapeAttr(`${task.title} · ${task.start_date} — ${task.end_date}`)}">
              ${isMacro ? "" : '<i class="gantt-handle start" data-resize="start"></i>'}<span>${escapeHtml(task.title)}</span>${isMacro ? "" : '<i class="gantt-handle end" data-resize="end"></i>'}
            </button>${taskPayments
              .map(
                (payment) =>
                  `<i class="gantt-task-payment${payment.date_status === "estimated" ? " estimated" : ""}" style="left:${dayDiff(geometry.start, payment.date) * geometry.dayWidth}px" title="${escapeAttr(`${formatPaymentDate(payment.date)} · ${payment.description} · ${formatMoney(payment.amount)}`)}"></i>`,
              )
              .join("")}</div>`;
          })
          .join("")}
      </div></div>
      <div class="gantt-labels">${tasks
        .map((task) => {
          const taskExpenses = (task.expense_allocations || [])
            .map((allocation) => {
              const expense = state.expenses.find(
                (item) => item.id === allocation.expense_id,
              );
              const cost = allocationCost(
                expense,
                allocation.expected_quantity,
                "planned",
              );
              return expense
                ? `${allocation.expected_quantity} ${expense.unit} ${expense.description}${cost == null ? " (sem cotação)" : ` ${formatMoney(cost)}`}`
                : "";
            })
            .filter(Boolean)
            .join(" + ");
          const macroChildren = childTasks(task.id);
          const filteredChildren = macroChildren.filter(matchesGanttFilters);
          const macroCount =
            state.ganttStatusFilter || state.ganttPriorityFilter
              ? `${filteredChildren.length} de ${macroChildren.length} atividades`
              : `${macroChildren.length} atividades`;
          const detail = `${task.activity_type === "macro" ? `${macroCount} · ${task.progress || 0}%` : `P${task.priority} · #${task.sequence}`} · ${escapeHtml(statusLabels[task.status])}${task.date_status === "estimated" ? " · estimada" : ""}${taskExpenses ? ` · ${escapeHtml(taskExpenses)}` : ""}`;
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
    if (payload.expense_state) applyExpenseState(payload.expense_state);
    renderGantt();
    renderMacroTimeline();
    return payload;
  }

  function fillTaskOptions(currentId = "") {
    els.taskParent.innerHTML = macroTasks()
      .filter((item) => item.id !== currentId)
      .map(
        (item) =>
          `<option value="${escapeAttr(item.id)}">${escapeHtml(item.title)}</option>`,
      )
      .join("");
  }

  function allocationCost(expense, quantity, scenarioName) {
    const total = expense?.scenario?.[scenarioName];
    const expenseQuantity = Number(expense?.scenario?.expected_quantity || 0);
    if (total == null || expenseQuantity <= 0) return null;
    const quoteId = expense.scenario[`${scenarioName}_quotation_id`];
    const quote = (expense.quotations || []).find((item) => item.id === quoteId);
    return Number(quantity || 0) * Number(quote?.unit_price || 0);
  }

  function renderTaskAllocations() {
    els.taskAllocationList.innerHTML = state.editingTaskAllocations
      .map((allocation, index) => {
        const expense = state.expenses.find(
          (item) => item.id === allocation.expense_id,
        );
        const options = state.expenses
          .map(
            (item) =>
              `<option value="${escapeAttr(item.id)}" ${item.id === allocation.expense_id ? "selected" : ""}>${escapeHtml(`${item.description} · ${item.unit}`)}</option>`,
          )
          .join("");
        const planned = allocationCost(
          expense,
          allocation.expected_quantity,
          "planned",
        );
        const minimum = allocationCost(
          expense,
          allocation.expected_quantity,
          "minimum",
        );
        const maximum = allocationCost(
          expense,
          allocation.expected_quantity,
          "maximum",
        );
        return `<div class="task-allocation-row" data-allocation-index="${index}">
          <label>Despesa<select data-allocation-field="expense_id" required><option value="">Selecione</option>${options}</select></label>
          <label>Quantidade<input data-allocation-field="expected_quantity" type="number" min="0.0001" step="any" value="${Number(allocation.expected_quantity || 1)}" required></label>
          <span class="task-allocation-unit">${escapeHtml(expense?.unit || "—")}</span>
          <span class="task-allocation-scenarios">${planned == null ? "Sem cotação" : `Plan. ${formatMoney(planned)} · mín. ${formatMoney(minimum)} · máx. ${formatMoney(maximum)}`}</span>
          <button type="button" class="btn danger" data-delete-allocation="${index}" aria-label="Remover despesa">×</button>
        </div>`;
      })
      .join("");
    const plannedTotal = state.editingTaskAllocations.reduce((sum, allocation) => {
      const expense = state.expenses.find(
        (item) => item.id === allocation.expense_id,
      );
      return (
        sum +
        Number(
          allocationCost(expense, allocation.expected_quantity, "planned") || 0,
        )
      );
    }, 0);
    els.taskAllocationTotal.textContent = state.editingTaskAllocations.length
      ? `Custo unitário planejado da atividade: ${formatMoney(plannedTotal)} (frete aplicado na projeção geral)`
      : "Nenhuma despesa vinculada.";
  }

  function addTaskAllocation() {
    const used = new Set(
      state.editingTaskAllocations.map((item) => item.expense_id),
    );
    const expense = state.expenses.find((item) => !used.has(item.id));
    if (!expense) return;
    state.editingTaskAllocations.push({
      expense_id: expense.id,
      expected_quantity: expense.default_expected_quantity || 1,
    });
    renderTaskAllocations();
  }

  function suggestTaskIcon() {
    const expense = state.expenses.find(
      (item) => item.id === state.editingTaskAllocations[0]?.expense_id,
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
    els.taskAllocationEditor.classList.toggle("hidden", isMacro);
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
    state.editingTaskAllocations = structuredClone(
      task?.expense_allocations || [],
    );
    renderTaskAllocations();
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
      expense_allocations:
        els.taskActivityType.value === "macro"
          ? []
          : state.editingTaskAllocations,
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
      if (result.expense_state) applyExpenseState(result.expense_state);
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
    els.fieldCategory.value = item?.category || "";
    els.fieldDescription.value = item?.description || "";
    els.fieldQuantity.value = item?.default_expected_quantity ?? 1;
    els.fieldUnit.value = item?.unit || "";
    updateExpenseServiceLinks(item?.provider_id || "", item?.contract_id || "");
    renderIconPicker(item?.icon_key || "");
    state.editingPayments = structuredClone(
      (item?.payments || []).filter(
        (payment) => payment.date_status === "confirmed",
      ),
    );
    renderExpensePayments();
    els.formError.classList.add("hidden");
    els.dialog.showModal();
    els.fieldDescription.focus();
  }

  function renderExpensePaymentTotal() {
    const total = state.editingPayments.reduce(
      (sum, item) => sum + Number(item.amount || 0),
      0,
    );
    els.expensePaymentTotal.classList.remove("mismatch");
    els.expensePaymentTotal.textContent = state.editingPayments.length
      ? `Pagamentos confirmados: ${formatMoney(total)}`
      : "Sem pagamentos confirmados; a projeção seguirá as atividades.";
  }

  function renderExpensePayments() {
    els.expensePaymentList.innerHTML = state.editingPayments
      .map(
        (
          payment,
        ) => `<div class="expense-payment-row" data-payment-id="${escapeAttr(payment.id)}">
          <label>Data<input type="date" data-payment-field="date" value="${escapeAttr(payment.date || "")}" required></label>
          <label>Valor<input type="number" data-payment-field="amount" min="0" step="0.01" value="${Number(payment.amount || 0).toFixed(2)}" required></label>
          <label>Precisão<select data-payment-field="date_status"><option value="estimated" ${payment.date_status === "estimated" ? "selected" : ""}>Presumida</option><option value="confirmed" ${payment.date_status === "confirmed" ? "selected" : ""}>Confirmada</option></select></label>
          <label class="payment-note">Observação<input data-payment-field="notes" maxlength="500" value="${escapeAttr(payment.notes || "")}" placeholder="Parcela, entrada..."></label>
          <button type="button" class="btn danger" data-delete-payment="${escapeAttr(payment.id)}" aria-label="Excluir pagamento">×</button>
        </div>`,
      )
      .join("");
    renderExpensePaymentTotal();
  }

  function updateEditingPayment(target) {
    const row = target.closest("[data-payment-id]");
    const payment = state.editingPayments.find(
      (item) => item.id === row?.dataset.paymentId,
    );
    if (!payment) return;
    const field = target.dataset.paymentField;
    payment[field] =
      field === "amount" ? Number(target.value || 0) : target.value;
    if (field === "date") {
      payment.date_status = "confirmed";
      row.querySelector('[data-payment-field="date_status"]').value =
        "confirmed";
    }
    renderExpensePaymentTotal();
  }

  function addExpensePayment() {
    if (state.editingPayments.length >= 36) return;
    const maximum = state.editingPayments.reduce((value, item) => {
      const match = String(item.id || "").match(/^PAY_(\d+)$/);
      return Math.max(value, Number(match?.[1] || 0));
    }, 0);
    const previous = state.editingPayments.at(-1);
    state.editingPayments.push({
      id: `PAY_${String(maximum + 1).padStart(3, "0")}`,
      date: previous?.date
        ? addDays(previous.date, 30)
        : addDays(iso(new Date()), 7),
      amount: 0,
      date_status: "confirmed",
      source: "manual",
      notes: "",
    });
    renderExpensePayments();
  }

  function currentQuotationExpense() {
    return state.expenses.find((item) => item.id === state.quotationExpenseId);
  }

  function renderQuotationManager() {
    const expense = currentQuotationExpense();
    if (!expense) return;
    const quotations = expense.quotations || [];
    els.quotationExpenseTitle.textContent = expense.description;
    els.quotationExpenseMeta.textContent = `${expense.category} · orçamento ativo ${formatMoney(expense.value)}`;
    els.quotationLimitLabel.textContent = `${quotations.length} de 5 cotações`;
    els.btnNewQuotation.disabled = quotations.length >= 5;
    els.quotationEmpty.classList.toggle("hidden", quotations.length > 0);
    els.quotationList.innerHTML = quotations
      .map((quote) => {
        const isSelected = quote.id === expense.selected_quotation_id;
        const projectedQuoteTotal =
          Number(quote.unit_price || 0) *
            Number(expense.scenario?.expected_quantity || 0) +
          Number(quote.shipping_cost || 0);
        const metadata = quote.metadata || {};
        const specification = [
          metadata.brand,
          metadata.model,
          metadata.specifications,
          metadata.package_size,
        ]
          .filter(Boolean)
          .join(" · ");
        const evidence = [
          metadata.source_type,
          metadata.source_name,
          metadata.source_page ? `p. ${metadata.source_page}` : "",
        ]
          .filter(Boolean)
          .join(" · ");
        return `<article class="quotation-card ${isSelected ? "selected" : ""}">
          <header><div><strong>${escapeHtml(quote.vendor)}</strong><span class="quote-badges"><span class="badge">${quote.source === "ai" ? "Importada" : "Manual"}</span>${isSelected ? '<span class="badge selected">Escolhida</span>' : ""}</span></div><strong class="quotation-total">${formatMoney(projectedQuoteTotal)}</strong></header>
          <dl><div><dt>Unitário</dt><dd>${formatMoney(quote.unit_price)} × ${quote.quantity} ${escapeHtml(quote.unit || "")}</dd></div><div><dt>Frete</dt><dd>${formatMoney(quote.shipping_cost)}</dd></div><div><dt>Verificada</dt><dd>${escapeHtml(quote.checked_at || "—")}</dd></div></dl>
          ${specification ? `<p><strong>Especificação:</strong> ${escapeHtml(specification)}</p>` : ""}
          ${evidence ? `<p><strong>Fonte:</strong> ${escapeHtml(evidence)}</p>` : ""}
          ${metadata.ambiguities ? `<p><strong>Pendências:</strong> ${escapeHtml(metadata.ambiguities)}</p>` : ""}
          ${quote.notes ? `<p>${escapeHtml(quote.notes)}</p>` : ""}
          <div class="quotation-card-actions">
            ${quote.product_url ? `<a class="btn" href="${escapeAttr(quote.product_url)}" target="_blank" rel="noopener">Abrir oferta</a>` : ""}
            ${!isSelected ? `<button type="button" class="btn primary" data-select-quotation="${escapeAttr(quote.id)}">Escolher</button>` : ""}
            <button type="button" class="btn" data-edit-quotation="${escapeAttr(quote.id)}">Editar</button>
            <button type="button" class="btn danger" data-delete-quotation="${escapeAttr(quote.id)}">Excluir</button>
          </div>
        </article>`;
      })
      .join("");
  }

  function openQuotationForm(quotation = null) {
    const expense = currentQuotationExpense();
    state.editingQuotationMetadata = quotation?.metadata || {};
    state.editingQuotationSource = quotation?.source || "manual";
    els.quotationFormTitle.textContent = quotation
      ? "Editar cotação"
      : "Nova cotação";
    els.quotationId.value = quotation?.id || "";
    els.quotationVendor.value = quotation?.vendor || "";
    els.quotationUnitPrice.value = quotation?.unit_price ?? "";
    els.quotationQuantity.value = quotation?.quantity ?? expense?.quantity ?? 1;
    els.quotationUnit.value = quotation?.unit || expense?.unit || "";
    els.quotationShipping.value = quotation?.shipping_cost ?? 0;
    els.quotationTotal.value = quotation?.total_price ?? "";
    els.quotationCheckedAt.value = String(
      quotation?.checked_at || new Date().toISOString().slice(0, 10),
    ).slice(0, 10);
    els.quotationUrl.value = quotation?.product_url || "";
    els.quotationNotes.value = quotation?.notes || "";
    els.quotationFormError.classList.add("hidden");
    els.quotationForm.classList.remove("hidden");
    els.quotationVendor.focus();
  }

  function openQuotationManager(item) {
    state.quotationExpenseId = item.id;
    state.quotationImportRows = [];
    els.quotationForm.classList.add("hidden");
    els.quotationAiPanel.open = false;
    els.quotationSourceInput.value = "";
    els.quotationSourceFile.value = "";
    els.quotationSourceStatus.classList.add("hidden");
    els.quotationPromptOutput.value = "";
    els.quotationPackInput.value = "";
    els.quotationCorrectionInstructions.value = "";
    els.quotationFixOutput.value = "";
    els.quotationFixOutput.classList.add("hidden");
    els.btnCopyQuotationFix.classList.add("hidden");
    els.btnCommitQuotationImport.disabled = true;
    renderQuotationManager();
    els.quotationDialog.showModal();
  }

  async function submitQuotation(event) {
    event.preventDefault();
    const expenseId = state.quotationExpenseId;
    try {
      const result = await request(
        `/api/expenses/${encodeURIComponent(expenseId)}/quotations`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            id: els.quotationId.value,
            source: state.editingQuotationSource,
            vendor: els.quotationVendor.value.trim(),
            unit_price: els.quotationUnitPrice.value,
            quantity: els.quotationQuantity.value,
            unit: els.quotationUnit.value.trim(),
            shipping_cost: els.quotationShipping.value,
            total_price: els.quotationTotal.value,
            checked_at: els.quotationCheckedAt.value,
            product_url: els.quotationUrl.value.trim(),
            notes: els.quotationNotes.value.trim(),
            metadata: state.editingQuotationMetadata,
          }),
        },
      );
      applyExpenseState(result.state);
      els.quotationForm.classList.add("hidden");
      renderQuotationManager();
    } catch (error) {
      setStatus(els.quotationFormError, "err", error.message);
    }
  }

  async function selectQuotation(quotationId) {
    const result = await request(
      `/api/expenses/${encodeURIComponent(state.quotationExpenseId)}/quotations/${encodeURIComponent(quotationId)}/select`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      },
    );
    applyExpenseState(result.state);
    renderQuotationManager();
  }

  async function deleteQuotation(quotationId) {
    if (!window.confirm("Excluir esta cotação?")) return;
    const result = await request(
      `/api/expenses/${encodeURIComponent(state.quotationExpenseId)}/quotations/${encodeURIComponent(quotationId)}`,
      { method: "DELETE" },
    );
    applyExpenseState(result.state);
    renderQuotationManager();
  }

  function quotationSourceTag(type, name, text, page = "") {
    const safeName = String(name || "quotation")
      .replaceAll("&", "&amp;")
      .replaceAll('"', "&quot;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
    const safeText = String(text || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
    const pageAttribute = page ? ` page="${page}"` : "";
    return `<quotation_source type="${type}" name="${safeName}"${pageAttribute}>\n${safeText.trim()}\n</quotation_source>`;
  }

  function normalizedQuotationSource() {
    const source = els.quotationSourceInput.value.trim();
    if (!source) return "";
    return source.startsWith("<quotation_source")
      ? source
      : quotationSourceTag("text", "pasted-text", source);
  }

  async function extractQuotationPdf(file) {
    if (file.size > 25 * 1024 * 1024)
      throw new Error("O PDF excede o limite de 25 MB.");
    setStatus(
      els.quotationSourceStatus,
      "pending",
      "Extraindo texto do PDF localmente...",
    );
    const pdfjs = await import(
      "/vendor/pdfjs/node_modules/pdfjs-dist/build/pdf.mjs"
    );
    pdfjs.GlobalWorkerOptions.workerSrc =
      "/vendor/pdfjs/node_modules/pdfjs-dist/build/pdf.worker.mjs";
    const document = await pdfjs.getDocument({
      data: new Uint8Array(await file.arrayBuffer()),
    }).promise;
    if (document.numPages > 100)
      throw new Error("O PDF excede o limite de 100 páginas.");
    const pages = [];
    let characterCount = 0;
    for (let pageNumber = 1; pageNumber <= document.numPages; pageNumber += 1) {
      const page = await document.getPage(pageNumber);
      const content = await page.getTextContent();
      const text = content.items
        .map((item) => `${item.str || ""}${item.hasEOL ? "\n" : " "}`)
        .join("")
        .replace(/[ \t]+\n/g, "\n")
        .replace(/[ \t]{2,}/g, " ")
        .trim();
      if (text) {
        characterCount += text.length;
        if (characterCount > 500000)
          throw new Error("O texto extraído excede 500.000 caracteres.");
        pages.push(quotationSourceTag("pdf", file.name, text, pageNumber));
      }
    }
    if (!pages.length)
      throw new Error(
        "Este PDF não contém texto selecionável. Use OCR ou anexe o PDF diretamente à sua IA.",
      );
    return { text: pages.join("\n\n"), pages: document.numPages };
  }

  async function loadQuotationSourceFile() {
    const file = els.quotationSourceFile.files[0];
    if (!file) return;
    try {
      if (
        file.type === "application/pdf" ||
        file.name.toLowerCase().endsWith(".pdf")
      ) {
        const extracted = await extractQuotationPdf(file);
        els.quotationSourceInput.value = extracted.text;
        setStatus(
          els.quotationSourceStatus,
          "ok",
          `${extracted.pages} página(s) extraída(s) localmente. Revise o texto antes de gerar o prompt.`,
        );
      } else {
        if (file.size > 2 * 1024 * 1024)
          throw new Error("O arquivo de texto excede o limite de 2 MB.");
        const text = await file.text();
        if (!text.trim()) throw new Error("O arquivo de texto está vazio.");
        els.quotationSourceInput.value = quotationSourceTag(
          "text",
          file.name,
          text,
        );
        setStatus(
          els.quotationSourceStatus,
          "ok",
          "Texto carregado localmente. Revise antes de gerar o prompt.",
        );
      }
    } catch (error) {
      const encrypted =
        /password|encrypted/i.test(`${error?.name || ""} ${error?.message || ""}`);
      setStatus(
        els.quotationSourceStatus,
        "err",
        encrypted
          ? "O PDF está protegido por senha. Remova a proteção ou anexe-o diretamente à sua IA."
          : error.message,
      );
    }
  }

  async function generateQuotationPrompt() {
    const sourceText = normalizedQuotationSource();
    const result = await request("/api/prompts/quotation-ingestion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ids: [state.quotationExpenseId],
        source_text: sourceText,
      }),
    });
    els.quotationPromptOutput.value = result.prompt || "";
    setStatus(
      els.quotationSourceStatus,
      sourceText ? "ok" : "pending",
      sourceText
        ? "Prompt pronto. Copie e envie para sua IA."
        : "Prompt pronto para usar com um PDF anexado diretamente à sua IA.",
    );
  }

  async function previewQuotationImport() {
    const expense = currentQuotationExpense();
    const result = await request("/api/import/preview", {
      allowPayloadError: true,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pack_text: els.quotationPackInput.value,
        pack_id: "price",
        correction_instructions:
          els.quotationCorrectionInstructions.value.trim(),
        expense_context: expense
          ? `${expense.id}: ${expense.description} (${expense.category})`
          : "",
      }),
    });
    const wrongScope = (result.rows || []).some(
      (row) => row.id !== state.quotationExpenseId,
    );
    state.quotationImportRows = wrongScope ? [] : result.rows || [];
    els.btnCommitQuotationImport.disabled =
      !result.ok || wrongScope || !state.quotationImportRows.length;
    const message = wrongScope
      ? "A resposta contém cotações de outra despesa. Peça à IA para manter o ID indicado."
      : result.ok
        ? `${state.quotationImportRows.length} cotação(ões) pronta(s).`
        : (result.errors || [result.error]).filter(Boolean).join(" · ");
    setStatus(
      els.quotationImportStatus,
      result.ok && !wrongScope ? "ok" : "err",
      message,
    );
    const fix =
      result.fix_text ||
      (wrongScope
        ? `The importer rejected the pack because it contains a quotation for another expense.\n\nUse only expense id ${expense?.id || state.quotationExpenseId}: ${expense?.description || ""}.\nRepair and return the complete PRICE_PACK.txt with the exact required markers and headers.\nDo not browse, research, or invent values. Use only the quotation evidence already supplied.\n\nREJECTED RESPONSE FOR REPAIR\n${els.quotationPackInput.value}`
        : "");
    els.quotationFixOutput.value = fix;
    els.quotationFixOutput.classList.toggle("hidden", !fix);
    els.btnCopyQuotationFix.classList.toggle("hidden", !fix);
  }

  async function commitQuotationImport() {
    const expense = currentQuotationExpense();
    const result = await request("/api/import/commit", {
      allowPayloadError: true,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rows: state.quotationImportRows,
        pack_text: els.quotationPackInput.value,
        pack_id: "price",
        expense_context: expense
          ? `${expense.id}: ${expense.description} (${expense.category})`
          : "",
      }),
    });
    if (!result.ok) {
      const fix = result.fix_text || "";
      els.quotationFixOutput.value = fix;
      els.quotationFixOutput.classList.toggle("hidden", !fix);
      els.btnCopyQuotationFix.classList.toggle("hidden", !fix);
      setStatus(
        els.quotationImportStatus,
        "err",
        (result.errors || ["Falha ao validar a importação."]).join(" · "),
      );
      els.btnCommitQuotationImport.disabled = true;
      return;
    }
    applyExpenseState(result.state);
    state.quotationImportRows = [];
    els.btnCommitQuotationImport.disabled = true;
    setStatus(els.quotationImportStatus, "ok", "Cotações importadas.");
    renderQuotationManager();
  }

  async function submitExpense(event) {
    event.preventDefault();
    const payload = {
      id: els.fieldId.value,
      record_type: els.fieldRecordType.value,
      category: els.fieldCategory.value.trim(),
      description: els.fieldDescription.value.trim(),
      icon_key: els.fieldIconKey.value,
      default_expected_quantity: els.fieldQuantity.value,
      unit: els.fieldUnit.value.trim(),
      provider_id: els.fieldProvider.value,
      contract_id: els.fieldContract.value,
      ...(state.editingPayments.length
        ? { payments: state.editingPayments }
        : {}),
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

  function renderRequiredTools(project) {
    if (!els.requiredTools || !project) return;
    const tools = ((project.construction_resources || {}).required_tools || [])
      .map(
        (tool) =>
          `<article class="required-tool">${iconMarkup(tool.icon_key, tool.name, "tool")}<div><strong>${escapeHtml(tool.name)}</strong><p>${escapeHtml(tool.purpose || "")}</p></div></article>`,
      )
      .join("");
    els.requiredTools.innerHTML =
      tools || "<p>Nenhuma ferramenta cadastrada.</p>";
  }

  const contractStatusLabels = {
    draft: "Rascunho",
    signed: "Assinado",
    active: "Ativo",
    completed: "Concluído",
    cancelled: "Cancelado",
  };
  const contractPaymentLabels = {
    one_time: "Pagamento único",
    weekly: "Semanal",
    monthly: "Mensal",
    custom: "Personalizado",
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
        <div class="contract-meta"><span>${formatMoney(contract.amount)}</span><span>${escapeHtml(providerMap[contract.provider_id]?.name || "Sem prestador")}</span><span>${contract.type === "service" ? `${formatPaymentDate(contract.start_date)} — ${formatPaymentDate(contract.end_date)} · ${contract.work_days} dias${contract.work_period_status === "estimated" ? " · presumido" : ""}` : escapeHtml(contract.start_date || "Sem data")}</span></div>
        ${contract.type === "service" ? `<p class="contract-payment-resume">${escapeHtml(contractPaymentLabels[contract.payment_frequency] || contract.payment_frequency)} · ${(contract.payment_schedule || []).length} pagamento(s) · ${formatMoney((contract.payment_schedule || []).reduce((sum, payment) => sum + Number(payment.amount || 0), 0))}</p>` : ""}
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

  function addMonths(value, months = 1) {
    const source = parseDate(value);
    const day = source.getDate();
    source.setDate(1);
    source.setMonth(source.getMonth() + months);
    source.setDate(
      Math.min(
        day,
        new Date(source.getFullYear(), source.getMonth() + 1, 0).getDate(),
      ),
    );
    return iso(source);
  }

  function generatedContractPaymentDates(frequency, start, end) {
    if (!start || !end || end < start) return [];
    if (frequency === "one_time") return [end];
    const dates = [start];
    let cursor = start;
    while (true) {
      const next =
        frequency === "weekly" ? addDays(cursor, 7) : addMonths(cursor);
      if (next >= end) break;
      dates.push(next);
      cursor = next;
    }
    if (dates.at(-1) !== end) dates.push(end);
    return dates;
  }

  function equalContractPayments(dates, amount, frequency) {
    const totalCents = Math.round(Number(amount || 0) * 100);
    const count = Math.max(1, dates.length);
    const base = Math.floor(totalCents / count);
    const remainder = totalCents - base * count;
    return dates.map((date, index) => ({
      id: `PAY_${String(index + 1).padStart(3, "0")}`,
      date,
      amount: (base + (index < remainder ? 1 : 0)) / 100,
      date_status: "confirmed",
      source: `contract_${frequency}`,
      notes: "",
    }));
  }

  function renderContractPaymentSummary() {
    const amount = Number(els.contractAmount.value || 0);
    const scheduledTotal = state.editingContractPayments.reduce(
      (sum, payment) => sum + Number(payment.amount || 0),
      0,
    );
    els.contractPaymentSummary.classList.toggle(
      "mismatch",
      Math.abs(scheduledTotal - amount) > 0.01,
    );
    els.contractPaymentSummary.textContent = `${state.editingContractPayments.length} pagamento(s) · ${formatMoney(scheduledTotal)}${Math.abs(scheduledTotal - amount) > 0.01 ? ` · diferença ${formatMoney(amount - scheduledTotal)}` : ""}`;
  }

  function renderContractPaymentPlan() {
    const isService = els.contractType.value === "service";
    els.contractPaymentPlan.classList.toggle("hidden", !isService);
    if (!isService) return;
    const frequency = els.contractPaymentFrequency.value;
    const start = els.contractStart.value;
    const end = els.contractEnd.value;
    const amount = Number(els.contractAmount.value || 0);
    const workDays = start && end && end >= start ? dayDiff(start, end) + 1 : 0;
    els.contractWorkPeriod.textContent = workDays
      ? `${formatPaymentDate(start)} — ${formatPaymentDate(end)} · ${workDays} dias de trabalho`
      : "Defina o período total de trabalho";
    if (frequency !== "custom") {
      state.editingContractPayments = equalContractPayments(
        generatedContractPaymentDates(frequency, start, end),
        amount,
        frequency,
      );
    }
    els.btnAddContractPayment.classList.toggle(
      "hidden",
      frequency !== "custom",
    );
    els.contractPaymentSchedule.innerHTML =
      state.editingContractPayments
        .map((payment) =>
          frequency === "custom"
            ? `<div class="contract-payment-row" data-contract-payment-id="${escapeAttr(payment.id)}"><label>Data<input type="date" data-contract-payment-field="date" value="${escapeAttr(payment.date || "")}" required></label><label>Valor<input type="number" data-contract-payment-field="amount" min="0" step="0.01" value="${Number(payment.amount || 0).toFixed(2)}" required></label><label>Observação<input data-contract-payment-field="notes" value="${escapeAttr(payment.notes || "")}" maxlength="500"></label><button type="button" class="btn danger" data-delete-contract-payment="${escapeAttr(payment.id)}" ${state.editingContractPayments.length === 1 ? "disabled" : ""}>×</button></div>`
            : `<article class="contract-payment-chip"><span>${formatPaymentDate(payment.date)}</span><strong>${formatMoney(payment.amount)}</strong></article>`,
        )
        .join("") ||
      '<p class="muted">Informe o preço total, o início e o fim do trabalho.</p>';
    renderContractPaymentSummary();
  }

  function addCustomContractPayment() {
    const maximum = state.editingContractPayments.reduce((value, item) => {
      const match = String(item.id || "").match(/^PAY_(\d+)$/);
      return Math.max(value, Number(match?.[1] || 0));
    }, 0);
    const previous = state.editingContractPayments.at(-1);
    const end = els.contractEnd.value;
    let paymentDate = previous?.date
      ? addDays(previous.date, 7)
      : els.contractStart.value;
    if (end && paymentDate > end) paymentDate = end;
    state.editingContractPayments.push({
      id: `PAY_${String(maximum + 1).padStart(3, "0")}`,
      date: paymentDate,
      amount: 0,
      date_status: "confirmed",
      source: "contract_custom",
      notes: "",
    });
    renderContractPaymentPlan();
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
    els.contractPaymentFrequency.value =
      contract?.payment_frequency || "one_time";
    state.editingContractPayments = structuredClone(
      contract?.payment_schedule || [],
    );
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
    renderContractPaymentPlan();
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
          payment_frequency: els.contractPaymentFrequency.value,
          payment_schedule: state.editingContractPayments,
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
    if (kind === "contracts") {
      renderPaymentProjection();
      renderGantt();
    }
  }

  async function loadProviders() {
    state.providers = (await request("/api/providers")).providers || [];
  }

  async function loadContracts() {
    state.contracts = (await request("/api/contracts")).contracts || [];
    renderPaymentProjection();
    renderGantt();
  }

  let house3dModule = null;
  let sceneAssetCatalog = [];
  let sceneEditorOpen = false;
  let mediaPanelOpen = false;
  let mediaRecording = false;
  let mediaBlob = null;
  let mediaFilename = "";
  let mediaObjectUrl = "";
  let persistedHouseName = "my-home";

  function applyHouseName(name, updateInput = true) {
    const displayName = String(name || "").trim() || "my-home";
    persistedHouseName = displayName;
    if (updateInput) els.houseNameInput.value = displayName;
    els.model3dHouseName.textContent = displayName;
    document.title = displayName;
  }

  async function saveHouseName() {
    const name = els.houseNameInput.value.replace(/\s+/g, " ").trim();
    if (!name) {
      els.houseNameStatus.textContent = "Digite um nome.";
      els.houseNameInput.value = persistedHouseName;
      return;
    }
    if (name === persistedHouseName) {
      els.houseNameInput.value = name;
      return;
    }
    els.houseNameInput.disabled = true;
    els.houseNameStatus.textContent = "Salvando…";
    try {
      const result = await request("/api/house/name", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      state.house = result.house;
      applyHouseName(result.house?.display_name);
      els.houseNameStatus.textContent = "Nome salvo.";
      window.setTimeout(() => {
        if (els.houseNameStatus.textContent === "Nome salvo.")
          els.houseNameStatus.textContent = "";
      }, 1800);
    } catch (error) {
      els.houseNameInput.value = persistedHouseName;
      els.houseNameStatus.textContent = error.message;
    } finally {
      els.houseNameInput.disabled = false;
    }
  }

  function renderSceneAssetPalette(catalog) {
    if (Array.isArray(catalog)) sceneAssetCatalog = catalog;
    const query = String(els.assetPaletteSearch.value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
    const groups = new Map();
    for (const asset of sceneAssetCatalog) {
      const group = asset.group || "Outros";
      const searchable = `${asset.label} ${group} ${asset.keywords || ""}`
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase();
      if (query && !searchable.includes(query)) continue;
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group).push(asset);
    }
    els.assetPalette.innerHTML =
      [...groups.entries()]
        .sort(([left], [right]) => left.localeCompare(right, "pt-BR"))
        .map(
          (
            [group, assets],
            index,
          ) => `<details class="asset-palette-group" ${query || index < 2 ? "open" : ""}>
          <summary><strong>${escapeHtml(group)}</strong><span>${assets.length}</span></summary>
          <div>${assets
            .sort((left, right) =>
              left.label.localeCompare(right.label, "pt-BR"),
            )
            .map(
              (asset) =>
                `<button type="button" draggable="true" data-asset-type="${escapeAttr(asset.id)}" aria-label="Adicionar ${escapeAttr(asset.label)}" title="${escapeAttr(`${asset.label} · ${asset.width} × ${asset.depth} × ${asset.height} m`)}">
                  ${
                    asset.previewUrl
                      ? `<img src="${escapeAttr(asset.previewUrl)}" alt="" loading="lazy"><span class="asset-preview-fallback" aria-hidden="true">3D</span>`
                      : `<span class="asset-preview-fallback visible" aria-hidden="true">3D</span>`
                  }
                  <span>${escapeHtml(asset.label)}</span>
                </button>`,
            )
            .join("")}</div>
        </details>`,
        )
        .join("") ||
      '<p class="asset-palette-empty">Nenhum objeto encontrado.</p>';
    els.assetPalette.querySelectorAll("img").forEach((image) => {
      image.addEventListener("error", () => {
        image.classList.add("hidden");
        image.nextElementSibling?.classList.add("visible");
      });
    });
  }

  async function renderHouse3D() {
    const model = state.house?.model_3d;
    els.house3dAssumptions.innerHTML = (model?.assumptions || [])
      .map((item) => `<li>${escapeHtml(item)}</li>`)
      .join("");
    if (!model)
      return setStatus(els.house3dStatus, "warn", "Geometria 3D indisponível.");
    try {
      house3dModule ||= await import("/house-3d.js?v=20260916-8");
      renderSceneAssetPalette(house3dModule.getSceneAssetCatalog());
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

  const blueprintView = {
    x: 0,
    y: 0,
    scale: 1,
    dragging: false,
    pointerId: null,
    lastX: 0,
    lastY: 0,
  };

  function renderBlueprintTransform() {
    els.houseBlueprint.style.transform = `translate(-50%, -50%) translate(${blueprintView.x}px, ${blueprintView.y}px) scale(${blueprintView.scale})`;
    els.blueprintZoomLabel.textContent = `${Math.round(blueprintView.scale * 100)}%`;
    els.blueprintViewport.classList.toggle("dragging", blueprintView.dragging);
  }

  function resetBlueprintView() {
    blueprintView.x = 0;
    blueprintView.y = 0;
    blueprintView.scale = 1;
    renderBlueprintTransform();
  }

  function zoomBlueprint(nextScale, clientX = null, clientY = null) {
    const previousScale = blueprintView.scale;
    const scale = Math.min(5, Math.max(0.5, nextScale));
    if (scale === previousScale) return;
    if (clientX != null && clientY != null) {
      const rect = els.blueprintViewport.getBoundingClientRect();
      const pointerX = clientX - rect.left - rect.width / 2;
      const pointerY = clientY - rect.top - rect.height / 2;
      const imageX = (pointerX - blueprintView.x) / previousScale;
      const imageY = (pointerY - blueprintView.y) / previousScale;
      blueprintView.x = pointerX - imageX * scale;
      blueprintView.y = pointerY - imageY * scale;
    }
    blueprintView.scale = scale;
    renderBlueprintTransform();
  }

  function exportBlueprintJson() {
    if (!state.house) return;
    const payload = {
      schema: "my-home/house-blueprint-export",
      version: 1,
      exported_at: new Date().toISOString(),
      blueprint_image_url: els.houseBlueprint.src,
      house: state.house,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const houseName = String(state.house.display_name || "house")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/gi, "-")
      .replace(/^-|-$/g, "")
      .toLowerCase();
    anchor.href = url;
    anchor.download = `${houseName || "house"}-blueprint.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function renderHouse(payload) {
    if (!payload.ok || !payload.house) return;
    const house = payload.house;
    state.house = house;
    state.project = payload.project || null;
    applyHouseName(house.display_name);
    els.houseBlueprint.src =
      payload.blueprint_url || "/api/house/blueprint.jpg";
    resetBlueprintView();
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
    renderRequiredTools(state.project);
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

  function showView(name) {
    const validViews = new Set([
      "dashboard",
      "expenses",
      "house",
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
  els.btnExportBlueprint.addEventListener("click", exportBlueprintJson);
  document.querySelectorAll("[data-blueprint-action]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.blueprintAction === "reset") resetBlueprintView();
      if (button.dataset.blueprintAction === "zoom-in")
        zoomBlueprint(blueprintView.scale * 1.25);
      if (button.dataset.blueprintAction === "zoom-out")
        zoomBlueprint(blueprintView.scale / 1.25);
    });
  });
  els.blueprintViewport.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    blueprintView.dragging = true;
    blueprintView.pointerId = event.pointerId;
    blueprintView.lastX = event.clientX;
    blueprintView.lastY = event.clientY;
    els.blueprintViewport.setPointerCapture(event.pointerId);
    renderBlueprintTransform();
  });
  els.blueprintViewport.addEventListener("pointermove", (event) => {
    if (!blueprintView.dragging || event.pointerId !== blueprintView.pointerId)
      return;
    blueprintView.x += event.clientX - blueprintView.lastX;
    blueprintView.y += event.clientY - blueprintView.lastY;
    blueprintView.lastX = event.clientX;
    blueprintView.lastY = event.clientY;
    renderBlueprintTransform();
  });
  const stopBlueprintDrag = (event) => {
    if (event.pointerId !== blueprintView.pointerId) return;
    blueprintView.dragging = false;
    blueprintView.pointerId = null;
    renderBlueprintTransform();
  };
  els.blueprintViewport.addEventListener("pointerup", stopBlueprintDrag);
  els.blueprintViewport.addEventListener("pointercancel", stopBlueprintDrag);
  els.blueprintViewport.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      zoomBlueprint(
        blueprintView.scale * (event.deltaY < 0 ? 1.12 : 1 / 1.12),
        event.clientX,
        event.clientY,
      );
    },
    { passive: false },
  );
  els.blueprintViewport.addEventListener("dblclick", resetBlueprintView);
  els.blueprintViewport.addEventListener("keydown", (event) => {
    const amount = event.shiftKey ? 60 : 24;
    const movement = {
      ArrowLeft: [amount, 0],
      ArrowRight: [-amount, 0],
      ArrowUp: [0, amount],
      ArrowDown: [0, -amount],
    }[event.key];
    if (movement) {
      event.preventDefault();
      blueprintView.x += movement[0];
      blueprintView.y += movement[1];
      renderBlueprintTransform();
    } else if (event.key === "+" || event.key === "=") {
      event.preventDefault();
      zoomBlueprint(blueprintView.scale * 1.25);
    } else if (event.key === "-") {
      event.preventDefault();
      zoomBlueprint(blueprintView.scale / 1.25);
    } else if (event.key === "0") {
      event.preventDefault();
      resetBlueprintView();
    }
  });
  els.houseNameInput.addEventListener("input", () => {
    const liveName = els.houseNameInput.value.trim() || "my-home";
    els.model3dHouseName.textContent = liveName;
    document.title = liveName;
    els.houseNameStatus.textContent = "Enter ou clique fora para salvar";
  });
  els.houseNameInput.addEventListener("blur", saveHouseName);
  els.houseNameInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      els.houseNameInput.blur();
    } else if (event.key === "Escape") {
      event.preventDefault();
      els.houseNameInput.value = persistedHouseName;
      els.model3dHouseName.textContent = persistedHouseName;
      document.title = persistedHouseName;
      els.houseNameStatus.textContent = "";
      els.houseNameInput.blur();
    }
  });
  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key === "Escape" && els.model3dHelpDialog.open) {
        event.preventDefault();
        els.model3dHelpDialog.close();
        return;
      }
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
      if (
        !event.shiftKey ||
        event.ctrlKey ||
        event.metaKey ||
        event.altKey ||
        typing
      )
        return;
      const view = {
        d: "dashboard",
        e: "expenses",
        c: "house",
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
  els.btnModel3dHelp.addEventListener("click", () =>
    els.model3dHelpDialog.showModal(),
  );
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
  els.assetPaletteSearch.addEventListener("input", () =>
    renderSceneAssetPalette(),
  );
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
  els.btnAddPayment.addEventListener("click", addExpensePayment);
  els.expensePaymentList.addEventListener("input", (event) => {
    if (event.target.matches("[data-payment-field]"))
      updateEditingPayment(event.target);
  });
  els.expensePaymentList.addEventListener("change", (event) => {
    if (event.target.matches("[data-payment-field]"))
      updateEditingPayment(event.target);
  });
  els.expensePaymentList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-delete-payment]");
    if (!button) return;
    state.editingPayments = state.editingPayments.filter(
      (item) => item.id !== button.dataset.deletePayment,
    );
    renderExpensePayments();
  });
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
    const quotations = event.target.closest("[data-open-expense-quotations]");
    const edit = event.target.closest("[data-edit-expense]");
    const remove = event.target.closest("[data-delete-expense]");
    if (quotations) {
      const item = state.expenses.find(
        (expense) => expense.id === quotations.dataset.openExpenseQuotations,
      );
      if (item) openQuotationManager(item);
      return;
    }
    if (edit) {
      openExpenseDialog(
        state.expenses.find((item) => item.id === edit.dataset.editExpense),
      );
      return;
    }
    if (remove) {
      try {
        await deleteExpense(remove.dataset.deleteExpense);
      } catch (error) {
        setStatus(els.appStatus, "err", error.message);
      }
      return;
    }
    if (event.target.closest("a")) return;
    const row = event.target.closest("[data-open-quotations]");
    const item = state.expenses.find(
      (expense) => expense.id === row?.dataset.openQuotations,
    );
    if (item) openQuotationManager(item);
  });
  els.rows.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = event.target.closest("[data-open-quotations]");
    if (!row || event.target !== row) return;
    const item = state.expenses.find(
      (expense) => expense.id === row?.dataset.openQuotations,
    );
    if (item) {
      event.preventDefault();
      openQuotationManager(item);
    }
  });
  els.btnCloseQuotations.addEventListener("click", () =>
    els.quotationDialog.close(),
  );
  els.btnNewQuotation.addEventListener("click", () => openQuotationForm());
  els.btnCancelQuotation.addEventListener("click", () =>
    els.quotationForm.classList.add("hidden"),
  );
  els.quotationForm.addEventListener("submit", submitQuotation);
  [
    els.quotationUnitPrice,
    els.quotationQuantity,
    els.quotationShipping,
  ].forEach((field) =>
    field.addEventListener("input", () => {
      const unitPrice = Number(els.quotationUnitPrice.value);
      const quantity = Number(els.quotationQuantity.value || 1);
      const shipping = Number(els.quotationShipping.value || 0);
      if (
        Number.isFinite(unitPrice) &&
        Number.isFinite(quantity) &&
        Number.isFinite(shipping)
      )
        els.quotationTotal.value = (unitPrice * quantity + shipping).toFixed(2);
    }),
  );
  els.quotationList.addEventListener("click", (event) => {
    const edit = event.target.closest("[data-edit-quotation]");
    const select = event.target.closest("[data-select-quotation]");
    const remove = event.target.closest("[data-delete-quotation]");
    const expense = currentQuotationExpense();
    if (edit)
      openQuotationForm(
        (expense?.quotations || []).find(
          (item) => item.id === edit.dataset.editQuotation,
        ),
      );
    if (select)
      selectQuotation(select.dataset.selectQuotation).catch((error) =>
        setStatus(els.quotationImportStatus, "err", error.message),
      );
    if (remove)
      deleteQuotation(remove.dataset.deleteQuotation).catch((error) =>
        setStatus(els.quotationImportStatus, "err", error.message),
      );
  });
  els.btnQuotationPrompt.addEventListener("click", () =>
    generateQuotationPrompt().catch((error) =>
      setStatus(els.quotationImportStatus, "err", error.message),
    ),
  );
  els.btnCopyQuotationPrompt.addEventListener("click", () =>
    navigator.clipboard.writeText(els.quotationPromptOutput.value),
  );
  els.quotationSourceFile.addEventListener("change", loadQuotationSourceFile);
  els.quotationSourceInput.addEventListener("input", () => {
    state.quotationImportRows = [];
    els.quotationPromptOutput.value = "";
    els.btnCommitQuotationImport.disabled = true;
    if (els.quotationSourceInput.value.trim())
      setStatus(
        els.quotationSourceStatus,
        "pending",
        "Fonte alterada. Gere um novo prompt de processamento.",
      );
  });
  els.quotationPackFile.addEventListener("change", async () => {
    if (els.quotationPackFile.files[0])
      els.quotationPackInput.value =
        await els.quotationPackFile.files[0].text();
  });
  els.btnPreviewQuotationImport.addEventListener("click", () =>
    previewQuotationImport().catch((error) =>
      setStatus(els.quotationImportStatus, "err", error.message),
    ),
  );
  els.btnCommitQuotationImport.addEventListener("click", () =>
    commitQuotationImport().catch((error) =>
      setStatus(els.quotationImportStatus, "err", error.message),
    ),
  );
  els.btnCopyQuotationFix.addEventListener("click", () =>
    navigator.clipboard.writeText(els.quotationFixOutput.value),
  );
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
  [els.taskTitle, els.taskDescription].forEach((field) => {
    field.addEventListener("change", () => {
      if (els.taskIconMode.value === "auto") renderTaskIconPicker("", "auto");
    });
  });
  els.btnAddTaskAllocation.addEventListener("click", addTaskAllocation);
  els.taskAllocationList.addEventListener("change", (event) => {
    const row = event.target.closest("[data-allocation-index]");
    const field = event.target.dataset.allocationField;
    if (!row || !field) return;
    const allocation = state.editingTaskAllocations[Number(row.dataset.allocationIndex)];
    allocation[field] =
      field === "expected_quantity"
        ? Number(event.target.value || 0)
        : event.target.value;
    renderTaskAllocations();
    if (els.taskIconMode.value === "auto") renderTaskIconPicker("", "auto");
  });
  els.taskAllocationList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-delete-allocation]");
    if (!button) return;
    state.editingTaskAllocations.splice(
      Number(button.dataset.deleteAllocation),
      1,
    );
    renderTaskAllocations();
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
  els.taskSummary.addEventListener("click", (event) => {
    const button = event.target.closest("[data-gantt-status]");
    if (!button) return;
    state.ganttStatusFilter =
      state.ganttStatusFilter === button.dataset.ganttStatus
        ? ""
        : button.dataset.ganttStatus;
    renderGantt();
  });
  els.taskPriorityFilter.addEventListener("click", (event) => {
    const button = event.target.closest("[data-gantt-priority]");
    if (!button) return;
    const priority = Number(button.dataset.ganttPriority);
    state.ganttPriorityFilter =
      state.ganttPriorityFilter === priority ? 0 : priority;
    renderGantt();
  });
  els.ganttZoom.addEventListener("change", () => {
    state.zoom =
      els.ganttZoom.querySelector('input[name="gantt-zoom"]:checked')?.value ||
      "week";
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
  els.contractType.addEventListener("change", renderContractPaymentPlan);
  els.contractPaymentFrequency.addEventListener(
    "change",
    renderContractPaymentPlan,
  );
  [els.contractAmount, els.contractStart, els.contractEnd].forEach((input) =>
    input.addEventListener("input", renderContractPaymentPlan),
  );
  els.btnAddContractPayment.addEventListener("click", addCustomContractPayment);
  els.contractPaymentSchedule.addEventListener("input", (event) => {
    const target = event.target.closest("[data-contract-payment-field]");
    const row = target?.closest("[data-contract-payment-id]");
    const payment = state.editingContractPayments.find(
      (item) => item.id === row?.dataset.contractPaymentId,
    );
    if (!payment) return;
    const field = target.dataset.contractPaymentField;
    payment[field] =
      field === "amount" ? Number(target.value || 0) : target.value;
    renderContractPaymentSummary();
  });
  els.contractPaymentSchedule.addEventListener("click", (event) => {
    const button = event.target.closest("[data-delete-contract-payment]");
    if (!button || state.editingContractPayments.length === 1) return;
    state.editingContractPayments = state.editingContractPayments.filter(
      (item) => item.id !== button.dataset.deleteContractPayment,
    );
    renderContractPaymentPlan();
  });
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
