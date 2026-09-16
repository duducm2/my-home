(() => {
  const state = {
    expenses: [],
    totals: { all: 0, materials: 0, services: 0, by_phase: {}, by_priority: {} },
    timeline: [],
    materials: [],
    project: null,
    iconCatalog: { defaults: {}, icons: {} },
    view: "dashboard",
    pendingImportRows: null,
    pendingPackText: "",
    lastPrompt: "",
    lastFix: "",
  };

  const $ = (id) => document.getElementById(id);

  const els = {
    phase: $("filter-phase"),
    priority: $("filter-priority"),
    category: $("filter-category"),
    search: $("filter-search"),
    rows: $("expense-rows"),
    empty: $("empty-state"),
    totalFiltered: $("total-filtered"),
    totalAll: $("total-all"),
    countFiltered: $("count-filtered"),
    btnNew: $("btn-new"),
    btnPush: $("btn-push"),
    pushStatus: $("push-status"),
    dialog: $("expense-dialog"),
    form: $("expense-form"),
    dialogTitle: $("dialog-title"),
    fieldId: $("field-id"),
    fieldPhase: $("field-phase"),
    fieldPriority: $("field-priority"),
    fieldCategory: $("field-category"),
    fieldDescription: $("field-description"),
    fieldIconKey: $("field-icon-key"),
    iconEditor: $("icon-editor"),
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
    phaseSuggestions: $("phase-suggestions"),
    categorySuggestions: $("category-suggestions"),
    dashTotalAll: $("dash-total-all"),
    dashTotalMaterials: $("dash-total-materials"),
    dashTotalServices: $("dash-total-services"),
    timelineGroups: $("timeline-groups"),
    dashMaterials: $("dash-materials"),
    fundsTotal: $("funds-total"),
    overallCoverage: $("overall-coverage"),
    overallGap: $("overall-gap"),
    fundsDonut: $("funds-donut"),
    fundsDonutTotal: $("funds-donut-total"),
    fundsDonutFgts: $("funds-donut-fgts"),
    fundsDonutFlexible: $("funds-donut-flexible"),
    entryCoverage: $("entry-coverage"),
    entryBar: $("entry-bar"),
    fgtsBalance: $("fgts-balance"),
    entryTarget: $("entry-target"),
    entryGap: $("entry-gap"),
    otherCoverage: $("other-coverage"),
    otherBar: $("other-bar"),
    flexibleBalance: $("flexible-balance"),
    otherTarget: $("other-target"),
    otherGap: $("other-gap"),
    budgetMaterialBar: $("budget-material-bar"),
    budgetServiceBar: $("budget-service-bar"),
    materialShare: $("material-share"),
    serviceShare: $("service-share"),
    phaseChart: $("phase-chart"),
    financeInsight: $("finance-insight"),
    promptOutput: $("prompt-output"),
    promptMissingOnly: $("prompt-missing-only"),
    btnGenPrompt: $("btn-gen-prompt"),
    btnCopyPrompt: $("btn-copy-prompt"),
    btnDlPrompt: $("btn-dl-prompt"),
    packInput: $("pack-input"),
    packFile: $("pack-file"),
    btnPreviewImport: $("btn-preview-import"),
    btnCommitImport: $("btn-commit-import"),
    btnCopyFix: $("btn-copy-fix"),
    btnDlFix: $("btn-dl-fix"),
    importStatus: $("import-status"),
    importPreviewRows: $("import-preview-rows"),
    fixOutput: $("fix-output"),
    houseBlueprint: $("house-blueprint"),
    houseLot: $("house-lot"),
    houseExterior: $("house-exterior"),
    houseRooms: $("house-rooms"),
    houseAudit: $("house-audit"),
    house3dStatus: $("house-3d-status"),
    house3dAssumptions: $("house-3d-assumptions"),
    projectOverview: $("project-overview"),
  };

  const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  const formatMoney = (v) => brl.format(Number(v) || 0);
  const formatDate = (value) => {
    if (!value) return "Data definida após o evento de referência";
    const date = new Date(`${value}T12:00:00`);
    return new Intl.DateTimeFormat("pt-BR", { dateStyle: "long" }).format(date);
  };

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }
  function escapeAttr(value) {
    return escapeHtml(value).replaceAll("'", "&#39;");
  }

  function iconEntry(iconKey, kind = "material") {
    const catalog = state.iconCatalog || { defaults: {}, icons: {} };
    const fallbackKey = (catalog.defaults || {})[kind] || "";
    const key = iconKey && catalog.icons[iconKey] ? iconKey : fallbackKey;
    return key && catalog.icons[key] ? { key, ...catalog.icons[key] } : null;
  }

  function itemIconMarkup(iconKey, altText, size = "sm", kind = "material") {
    const icon = iconEntry(iconKey, kind);
    if (!icon) return "";
    return `<span class="item-icon item-icon-${escapeAttr(size)}" title="${escapeAttr(icon.label || altText)}"><img src="${escapeAttr(icon.url)}" alt="" loading="lazy" /></span>`;
  }

  function itemLabelMarkup(description, iconKey, note = "") {
    return `<div class="item-label">${itemIconMarkup(iconKey, description)}<div><strong>${escapeHtml(description)}</strong>${note ? `<small>${escapeHtml(note)}</small>` : ""}</div></div>`;
  }

  function renderIconPicker(selectedKey = "") {
    if (!els.iconEditor || !els.iconPicker || !els.fieldIconKey) return;
    els.iconEditor.classList.remove("hidden");
    const kind = els.fieldCategory.value.trim() === "Material" ? "material" : "expense";
    const icons = Object.entries((state.iconCatalog || {}).icons || {})
      .sort(([, a], [, b]) => String(a.label).localeCompare(String(b.label), "pt-BR"));
    const selected = iconEntry(selectedKey || els.fieldIconKey.value, kind);
    els.fieldIconKey.value = selected ? selected.key : "";
    els.iconPreview.innerHTML = selected
      ? `${itemIconMarkup(selected.key, selected.label, "lg")}<span>${escapeHtml(selected.label)}</span>`
      : "";
    els.iconPicker.innerHTML = icons.map(([key, icon]) => `
      <button type="button" class="icon-choice${key === els.fieldIconKey.value ? " selected" : ""}"
        data-icon-key="${escapeAttr(key)}" role="radio" aria-checked="${key === els.fieldIconKey.value}"
        title="${escapeAttr(icon.label)}">
        ${itemIconMarkup(key, icon.label, "picker")}<span>${escapeHtml(icon.label)}</span>
      </button>`).join("");
  }

  function uniqueSorted(values) {
    return [...new Set(values.filter(Boolean))].sort((a, b) =>
      String(a).localeCompare(String(b), "pt-BR", { sensitivity: "base" })
    );
  }

  function fillSelect(select, values, allLabel) {
    const current = select.value;
    select.innerHTML = "";
    const all = document.createElement("option");
    all.value = "";
    all.textContent = allLabel;
    select.appendChild(all);
    for (const value of values) {
      const opt = document.createElement("option");
      opt.value = String(value);
      opt.textContent = String(value);
      select.appendChild(opt);
    }
    if ([...select.options].some((o) => o.value === current)) select.value = current;
  }

  function fillDatalist(datalist, values) {
    datalist.innerHTML = "";
    for (const value of values) {
      const opt = document.createElement("option");
      opt.value = String(value);
      datalist.appendChild(opt);
    }
  }

  function setStatus(el, kind, text) {
    el.classList.remove("hidden", "ok", "err");
    if (kind) el.classList.add(kind);
    el.textContent = text;
  }

  function showView(name) {
    state.view = name;
    document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
    const target = document.getElementById(`view-${name}`);
    if (target) target.classList.remove("hidden");
    document.querySelectorAll(".nav-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-view") === name);
    });
  }

  function filteredExpenses() {
    const phase = els.phase.value;
    const priority = els.priority.value;
    const category = els.category.value;
    const search = els.search.value.trim().toLowerCase();
    return state.expenses.filter((expense) => {
      if (phase && expense.phase !== phase) return false;
      if (priority && String(expense.priority) !== priority) return false;
      if (category && expense.category !== category) return false;
      if (search) {
        const hay = `${expense.phase} ${expense.category} ${expense.description} ${expense.vendor || ""}`.toLowerCase();
        if (!hay.includes(search)) return false;
      }
      return true;
    });
  }

  function renderFilters() {
    fillSelect(els.phase, uniqueSorted(state.expenses.map((e) => e.phase)), "Todas");
    fillSelect(
      els.priority,
      uniqueSorted(state.expenses.map((e) => String(e.priority))).sort((a, b) => Number(a) - Number(b)),
      "Todas"
    );
    fillSelect(els.category, uniqueSorted(state.expenses.map((e) => e.category)), "Todas");
    fillDatalist(els.phaseSuggestions, uniqueSorted(state.expenses.map((e) => e.phase)));
    fillDatalist(els.categorySuggestions, uniqueSorted(state.expenses.map((e) => e.category)));
  }

  function priceCell(expense) {
    const bits = [];
    if (expense.unit_price != null) bits.push(formatMoney(expense.unit_price));
    if (expense.vendor) bits.push(escapeHtml(expense.vendor));
    if (expense.product_url) {
      bits.push(`<a class="link-btn" href="${escapeAttr(expense.product_url)}" target="_blank" rel="noopener">abrir</a>`);
    }
    if (expense.price_checked_at) bits.push(`<span title="verificado">${escapeHtml(expense.price_checked_at)}</span>`);
    return bits.length ? `<div class="price-cell">${bits.join(" · ")}</div>` : "—";
  }

  function renderExpenseTable() {
    const rows = filteredExpenses();
    const filteredTotal = rows.reduce((sum, e) => sum + Number(e.value || 0), 0);
    els.totalFiltered.textContent = formatMoney(filteredTotal);
    els.totalAll.textContent = formatMoney(state.totals.all || 0);
    els.countFiltered.textContent = String(rows.length);
    els.rows.innerHTML = "";
    if (!rows.length) {
      els.empty.classList.remove("hidden");
      return;
    }
    els.empty.classList.add("hidden");
    const fragment = document.createDocumentFragment();
    for (const expense of rows) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(expense.phase)}</td>
        <td><span class="badge">${escapeHtml(String(expense.priority))}</span></td>
        <td>${escapeHtml(expense.category)}</td>
        <td>${itemLabelMarkup(expense.description, expense.icon_key, expense.price_notes || "")}</td>
        <td class="num">${formatMoney(expense.value)}</td>
        <td>${priceCell(expense)}</td>
        <td class="actions">
          <div class="row-actions">
            <button type="button" class="btn" data-edit="${escapeAttr(expense.id)}">Editar</button>
            <button type="button" class="btn danger" data-delete="${escapeAttr(expense.id)}">Excluir</button>
          </div>
        </td>`;
      fragment.appendChild(tr);
    }
    els.rows.appendChild(fragment);
  }

  function clampPercent(value) {
    return Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  }

  function percentOf(part, whole) {
    return whole > 0 ? (part / whole) * 100 : 0;
  }

  function formatPercent(value) {
    return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value)}%`;
  }

  function setGap(element, available, planned) {
    const difference = available - planned;
    element.classList.toggle("positive", difference >= 0);
    element.classList.toggle("negative", difference < 0);
    element.textContent = difference >= 0
      ? `Sobra projetada: ${formatMoney(difference)}`
      : `Lacuna: ${formatMoney(Math.abs(difference))}`;
    return difference;
  }

  function renderFinancialCockpit() {
    const project = state.project || {};
    const funding = project.funding || {};
    const sources = funding.sources || [];
    const fgts = sources.find((source) => source.id === "fgts") || {};
    const flexible = sources.find((source) => source.id === "flexible_funds") || {};
    const fgtsBalance = Number(fgts.balance) || 0;
    const flexibleBalance = Number(flexible.balance) || 0;
    const fundsTotal = fgtsBalance + flexibleBalance;
    const plannedTotal = Number(state.totals.all) || 0;
    const entryExpense = state.expenses.find((expense) => expense.id === funding.entry_expense_id)
      || state.expenses.find((expense) => String(expense.description).toLowerCase() === "entrada");
    const entryTarget = Number(entryExpense && entryExpense.value) || 0;
    const otherTarget = Math.max(0, plannedTotal - entryTarget);
    const entryPct = percentOf(fgtsBalance, entryTarget);
    const otherPct = percentOf(flexibleBalance, otherTarget);
    const overallPct = percentOf(fundsTotal, plannedTotal);
    const materialPct = percentOf(Number(state.totals.materials) || 0, plannedTotal);
    const servicePct = Math.max(0, 100 - materialPct);
    const fgtsShare = percentOf(fgtsBalance, fundsTotal);
    const flexibleShare = Math.max(0, 100 - fgtsShare);

    els.fundsTotal.textContent = formatMoney(fundsTotal);
    els.overallCoverage.textContent = formatPercent(overallPct);
    setGap(els.overallGap, fundsTotal, plannedTotal);

    els.fundsDonut.style.setProperty("--fgts-angle", `${clampPercent(fgtsShare) * 3.6}deg`);
    els.fundsDonutTotal.textContent = formatMoney(fundsTotal);
    els.fundsDonutFgts.textContent = formatPercent(fgtsShare);
    els.fundsDonutFlexible.textContent = formatPercent(flexibleShare);
    els.fundsDonut.setAttribute("aria-label", `FGTS ${formatPercent(fgtsShare)}; recursos livres ${formatPercent(flexibleShare)}`);

    els.entryCoverage.textContent = formatPercent(entryPct);
    els.entryBar.style.width = `${clampPercent(entryPct)}%`;
    els.fgtsBalance.textContent = `${formatMoney(fgtsBalance)} disponíveis`;
    els.entryTarget.textContent = `${formatMoney(entryTarget)} planejados`;
    const entryGap = setGap(els.entryGap, fgtsBalance, entryTarget);

    els.otherCoverage.textContent = formatPercent(otherPct);
    els.otherBar.style.width = `${clampPercent(otherPct)}%`;
    els.flexibleBalance.textContent = `${formatMoney(flexibleBalance)} disponíveis`;
    els.otherTarget.textContent = `${formatMoney(otherTarget)} planejados`;
    const otherGap = setGap(els.otherGap, flexibleBalance, otherTarget);

    els.budgetMaterialBar.style.width = `${clampPercent(materialPct)}%`;
    els.budgetServiceBar.style.width = `${clampPercent(servicePct)}%`;
    els.materialShare.textContent = formatPercent(materialPct);
    els.serviceShare.textContent = formatPercent(servicePct);

    const phaseTotals = Object.entries(state.totals.by_phase || {});
    const maxPhase = Math.max(1, ...phaseTotals.map(([, amount]) => Number(amount) || 0));
    els.phaseChart.innerHTML = phaseTotals.map(([phase, amount]) => {
      const value = Number(amount) || 0;
      const width = clampPercent((value / maxPhase) * 100);
      return `<div class="phase-bar-row">
        <div class="phase-bar-head"><span>${escapeHtml(phase)}</span><strong>${formatMoney(value)}</strong></div>
        <div class="phase-bar-track"><span style="width:${width}%"></span></div>
      </div>`;
    }).join("");

    const decisionRule = ((project.financial_strategy || {}).decision_rule || "").trim();
    const insights = [
      { tone: "info", title: "FGTS é restrito", text: `${formatMoney(fgtsBalance)} só pode financiar a entrada.` },
      { tone: entryGap < 0 ? "warn" : "ok", title: entryGap < 0 ? "Entrada ainda não coberta" : "Entrada coberta", text: entryGap < 0 ? `Faltam ${formatMoney(Math.abs(entryGap))}.` : `Margem de ${formatMoney(entryGap)}.` },
      { tone: otherGap < 0 ? "warn" : "ok", title: otherGap < 0 ? "Demais custos exigem priorização" : "Demais custos cobertos", text: otherGap < 0 ? `Lacuna de ${formatMoney(Math.abs(otherGap))} nos recursos livres.` : `Margem de ${formatMoney(otherGap)}.` },
    ];
    if (decisionRule) insights.push({ tone: "rule", title: "Regra do projeto", text: decisionRule });
    els.financeInsight.innerHTML = insights.map((item) => `
      <div class="insight ${item.tone}"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.text)}</span></div>`).join("");
  }

  function renderDashboard() {
    els.dashTotalAll.textContent = formatMoney(state.totals.all || 0);
    els.dashTotalMaterials.textContent = formatMoney(state.totals.materials || 0);
    els.dashTotalServices.textContent = formatMoney(state.totals.services || 0);
    renderFinancialCockpit();

    els.timelineGroups.innerHTML = "";
    for (const group of state.timeline || []) {
      const card = document.createElement("article");
      card.className = "timeline-card";
      const services = group.pending_services || [];
      const serviceList = services.length
        ? `<ul>${services
            .map(
              (s) =>
                `<li class="timeline-service-item">${itemIconMarkup(s.icon_key, s.description)}<span><strong>${escapeHtml(s.category)}</strong> — ${escapeHtml(s.description)} (${formatMoney(s.value)})</span></li>`
            )
            .join("")}</ul>`
        : `<p class="section-sub">Sem serviços pendentes nesta etapa (somente materiais ou itens já listados).</p>`;
      card.innerHTML = `
        <h3>${escapeHtml(group.label)}</h3>
        <div class="timeline-meta">${group.count} itens · ${formatMoney(group.total)} · ${services.length} pendência(s)</div>
        ${serviceList}`;
      els.timelineGroups.appendChild(card);
    }

    els.dashMaterials.innerHTML = "";
    const frag = document.createDocumentFragment();
    for (const m of state.materials || []) {
      const tr = document.createElement("tr");
      const link = m.product_url
        ? `<a class="link-btn" href="${escapeAttr(m.product_url)}" target="_blank" rel="noopener">abrir</a>`
        : "—";
      tr.innerHTML = `
        <td>${escapeHtml(m.phase)}</td>
        <td><span class="badge">${escapeHtml(String(m.priority))}</span></td>
        <td>${itemLabelMarkup(m.description, m.icon_key)}</td>
        <td class="num">${m.quantity == null ? "—" : m.quantity}</td>
        <td>${escapeHtml(m.unit || "—")}</td>
        <td class="num">${formatMoney(m.value)}</td>
        <td class="num">${m.unit_price == null ? "—" : formatMoney(m.unit_price)}</td>
        <td>${escapeHtml(m.vendor || "—")}</td>
        <td>${link}</td>`;
      frag.appendChild(tr);
    }
    els.dashMaterials.appendChild(frag);
  }

  function applyState(payload) {
    state.expenses = payload.expenses || [];
    state.totals = payload.totals || { all: 0, materials: 0, services: 0 };
    state.timeline = payload.timeline || [];
    state.materials = payload.materials || [];
    state.iconCatalog = payload.icon_catalog || { defaults: {}, icons: {} };
    renderFilters();
    renderExpenseTable();
    renderDashboard();
    if (state.project) renderProject(state.project);
  }

  async function loadState() {
    const response = await fetch("/api/state");
    const payload = await response.json();
    if (!response.ok || payload.ok === false) throw new Error(payload.error || "Falha ao carregar");
    applyState(payload);
  }

  function openDialog(expense) {
    els.formError.classList.add("hidden");
    els.formError.textContent = "";
    if (expense) {
      els.dialogTitle.textContent = "Editar despesa";
      els.fieldId.value = expense.id;
      els.fieldPhase.value = expense.phase;
      els.fieldPriority.value = expense.priority;
      els.fieldCategory.value = expense.category;
      els.fieldDescription.value = expense.description;
      els.fieldIconKey.value = expense.icon_key || "";
      els.fieldValue.value = Number(expense.value).toFixed(2);
      els.fieldQuantity.value = expense.quantity == null ? "" : expense.quantity;
      els.fieldUnit.value = expense.unit || "";
      els.fieldUnitPrice.value = expense.unit_price == null ? "" : Number(expense.unit_price).toFixed(2);
      els.fieldVendor.value = expense.vendor || "";
      els.fieldProductUrl.value = expense.product_url || "";
      els.fieldPriceNotes.value = expense.price_notes || "";
    } else {
      els.dialogTitle.textContent = "Nova despesa";
      els.fieldId.value = "";
      els.fieldPhase.value = els.phase.value || "";
      els.fieldPriority.value = els.priority.value || "1";
      els.fieldCategory.value = els.category.value || "";
      els.fieldDescription.value = "";
      els.fieldIconKey.value = "";
      els.fieldValue.value = "0.00";
      els.fieldQuantity.value = "";
      els.fieldUnit.value = "";
      els.fieldUnitPrice.value = "";
      els.fieldVendor.value = "";
      els.fieldProductUrl.value = "";
      els.fieldPriceNotes.value = "";
    }
    renderIconPicker(els.fieldIconKey.value);
    els.dialog.showModal();
    els.fieldPhase.focus();
  }

  async function saveExpense(event) {
    event.preventDefault();
    els.formError.classList.add("hidden");
    const payload = {
      phase: els.fieldPhase.value.trim(),
      priority: Number(els.fieldPriority.value),
      category: els.fieldCategory.value.trim(),
      description: els.fieldDescription.value.trim(),
      icon_key: els.fieldIconKey.value,
      value: Number(els.fieldValue.value),
      unit: els.fieldUnit.value.trim(),
      vendor: els.fieldVendor.value.trim(),
      product_url: els.fieldProductUrl.value.trim(),
      price_notes: els.fieldPriceNotes.value.trim(),
    };
    if (els.fieldId.value) payload.id = els.fieldId.value;
    if (els.fieldQuantity.value !== "") payload.quantity = Number(els.fieldQuantity.value);
    if (els.fieldUnitPrice.value !== "") payload.unit_price = Number(els.fieldUnitPrice.value);
    try {
      const response = await fetch("/api/expenses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok || result.ok === false) throw new Error(result.error || "Nao foi possivel salvar");
      applyState(result.state);
      els.dialog.close();
      await pushToRemote();
    } catch (err) {
      els.formError.textContent = err.message || String(err);
      els.formError.classList.remove("hidden");
    }
  }

  async function deleteExpense(id) {
    const expense = state.expenses.find((e) => e.id === id);
    const label = expense ? expense.description : id;
    if (!window.confirm(`Excluir a despesa "${label}"?`)) return;
    const response = await fetch(`/api/expenses/${encodeURIComponent(id)}`, { method: "DELETE" });
    const result = await response.json();
    if (!response.ok || result.ok === false) {
      window.alert(result.error || "Nao foi possivel excluir");
      return;
    }
    applyState(result.state);
    await pushToRemote();
  }

  async function pushToRemote() {
    els.btnPush.disabled = true;
    setStatus(els.pushStatus, "", "Salvando todos os dados e enviando a cópia segura…");
    try {
      const response = await fetch("/api/push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      const result = await response.json();
      if (!response.ok || result.ok === false) throw new Error(result.error || "Falha ao enviar");
      if (result.pushed) {
        setStatus(els.pushStatus, "ok", `Tudo salvo e enviado com segurança.${result.commit ? " Versão " + result.commit + "." : ""}`);
      } else {
        setStatus(els.pushStatus, "ok", result.message || "Tudo já estava salvo e atualizado.");
      }
    } catch (err) {
      setStatus(els.pushStatus, "err", err.message || String(err));
    } finally {
      els.btnPush.disabled = false;
    }
  }

  async function generatePrompt() {
    els.btnGenPrompt.disabled = true;
    try {
      let ids = null;
      if (!els.promptMissingOnly.checked) {
        ids = state.materials.map((m) => m.id);
      }
      const response = await fetch("/api/prompts/price-discovery", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(ids ? { ids } : {}),
      });
      const result = await response.json();
      if (!response.ok || result.ok === false) throw new Error(result.error || "Falha ao gerar prompt");
      state.lastPrompt = result.prompt || "";
      els.promptOutput.value = state.lastPrompt;
      els.btnCopyPrompt.disabled = !state.lastPrompt;
      els.btnDlPrompt.disabled = !state.lastPrompt;
    } catch (err) {
      window.alert(err.message || String(err));
    } finally {
      els.btnGenPrompt.disabled = false;
    }
  }

  function downloadText(filename, text) {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function previewImport() {
    const pack_text = els.packInput.value;
    state.pendingImportRows = null;
    state.pendingPackText = pack_text;
    els.btnCommitImport.disabled = true;
    els.btnCopyFix.disabled = true;
    els.btnDlFix.disabled = true;
    els.fixOutput.classList.add("hidden");
    els.importPreviewRows.innerHTML = "";
    setStatus(els.importStatus, "", "Validando pack…");
    try {
      const response = await fetch("/api/import/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pack_text, pack_id: "price" }),
      });
      const result = await response.json();
      if (!result.ok) {
        state.lastFix = result.fix_text || "";
        els.fixOutput.value = state.lastFix;
        els.fixOutput.classList.remove("hidden");
        els.btnCopyFix.disabled = !state.lastFix;
        els.btnDlFix.disabled = !state.lastFix;
        setStatus(els.importStatus, "err", result.error || "Pack rejeitado — use o AI_FIX");
        return;
      }
      state.pendingImportRows = result.rows || [];
      els.btnCommitImport.disabled = !state.pendingImportRows.length;
      const frag = document.createDocumentFragment();
      for (const row of state.pendingImportRows) {
        const tr = document.createElement("tr");
        const link = row.product_url
          ? `<a class="link-btn" href="${escapeAttr(row.product_url)}" target="_blank" rel="noopener">abrir</a>`
          : "—";
        tr.innerHTML = `
          <td>${escapeHtml(row.id || "")}</td>
          <td>${(() => {
            const current = state.expenses.find((expense) => expense.id === row.id)
              || state.expenses.find((expense) => expense.description === row.description);
            return itemLabelMarkup(row.description || "", current && current.icon_key);
          })()}</td>
          <td class="num">${formatMoney(row.unit_price)}</td>
          <td>${escapeHtml(row.vendor || "—")}</td>
          <td>${link}</td>`;
        frag.appendChild(tr);
      }
      els.importPreviewRows.appendChild(frag);
      setStatus(els.importStatus, "ok", `${state.pendingImportRows.length} linha(s) prontas para importar.`);
    } catch (err) {
      setStatus(els.importStatus, "err", err.message || String(err));
    }
  }

  async function commitImport() {
    if (!state.pendingImportRows || !state.pendingImportRows.length) return;
    els.btnCommitImport.disabled = true;
    setStatus(els.importStatus, "", "Importando…");
    try {
      const response = await fetch("/api/import/commit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rows: state.pendingImportRows,
          pack_text: state.pendingPackText,
          pack_id: "price",
        }),
      });
      const result = await response.json();
      if (!response.ok || result.ok === false) throw new Error(result.error || "Falha na importacao");
      applyState(result.state);
      const extra = result.errors && result.errors.length ? ` Avisos: ${result.errors.length}.` : "";
      setStatus(
        els.importStatus,
        "ok",
        `Importados ${result.updated.length} item(ns).${result.archived ? " Arquivo: " + result.archived + "." : ""}${extra}`
      );
      state.pendingImportRows = null;
      await pushToRemote();
    } catch (err) {
      setStatus(els.importStatus, "err", err.message || String(err));
      els.btnCommitImport.disabled = false;
    }
  }


  function dimsText(obj) {
    if (!obj || typeof obj !== "object") return "—";
    return Object.entries(obj)
      .map(([k, v]) => `${k}: ${v} m`)
      .join(" · ");
  }


  function listHtml(items) {
    if (!items || !items.length) return "";
    return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
  }

  function renderProject(project) {
    if (!els.projectOverview) return;
    if (!project) {
      els.projectOverview.innerHTML = '<p class="section-sub">Resumo do projeto não disponível.</p>';
      return;
    }

    const property = project.property || {};
    const address = property.address || {};
    const financing = property.financing || {};
    const contracts = project.contracts || {};
    const workContracts = project.work_contracts || [];
    const people = project.people || [];
    const purchaseContract = project.purchase_contract || {};
    const contractDocument = purchaseContract.document || {};
    const contractParties = purchaseContract.parties || {};
    const contractProperty = purchaseContract.property_legal_identification || {};
    const contractFinancial = purchaseContract.financial_terms || {};
    const financial = project.financial_strategy || {};
    const rear = (project.official_dimensions || {}).rear_area || {};
    const currentRear = rear.current_effective_space || {};
    const largerRear = rear.larger_coverage_scenario || {};

    const workflow = (project.purchase_workflow || [])
      .map((step, index) => `<li><span class="badge">${index + 1}</span> ${escapeHtml(step)}</li>`)
      .join("");

    const phaseCards = (project.phases || []).map((phase) => {
      const labor = phase.labor || {};
      const services = phase.services || [];
      const requiredTools = labor.required_tools || [];
      const priorityWork = phase.priority_work || [];
      const workHtml = priorityWork.map((work) => `
        <details class="project-detail">
          <summary>${escapeHtml(work.label)}</summary>
          ${listHtml(work.items || work.current_priority || [])}
          ${work.deferred_finishings ? `<p class="project-note">Pode ficar para depois:</p>${listHtml(work.deferred_finishings)}` : ""}
        </details>`).join("");
      const toolsHtml = requiredTools.map((tool) => `
        <article class="required-tool">
          ${itemIconMarkup(tool.icon_key, tool.name, "tool", "tool")}
          <div class="required-tool-copy"><strong>${escapeHtml(tool.name)}</strong>
          <p>${escapeHtml(tool.purpose || "")}</p>
          <small>${escapeHtml(tool.responsibility || "")}${tool.related_expense_id ? ` · ${escapeHtml(tool.related_expense_id)}` : ""}</small></div>
        </article>`).join("");
      return `
        <article class="project-phase">
          <div class="project-phase-head">
            <h3>${escapeHtml(phase.label)}</h3>
            ${labor.planned_amount != null ? `<strong>${formatMoney(labor.planned_amount)} mão de obra</strong>` : ""}
          </div>
          <p><strong>Início:</strong> ${escapeHtml(phase.trigger || "")}</p>
          <p>${escapeHtml(phase.objective || "")}</p>
          ${phase.deadline && phase.deadline.duration_days ? `<p><strong>Prazo:</strong> ${phase.deadline.duration_days} dias a partir de ${escapeHtml(phase.deadline.starts_from)}.</p>` : ""}
          ${toolsHtml ? `<div class="phase-required-tools"><h4>Ferramentas necessárias do pedreiro</h4><div>${toolsHtml}</div></div>` : ""}
          ${services.length ? `<details class="project-detail"><summary>${services.length} serviços</summary>${listHtml(services)}</details>` : ""}
          ${workHtml}
        </article>`;
    }).join("");

    const roofRows = ((project.roof_study || {}).materials_only_estimates || [])
      .map((row) => `<tr><td>${escapeHtml(row.system)}</td><td class="num">${formatMoney(row.min)}</td><td class="num">${formatMoney(row.max)}</td></tr>`)
      .join("");

    const contractDeadlines = (purchaseContract.deadlines || []).map((deadline) => `
      <article class="contract-deadline">
        <div class="contract-deadline-head"><strong>${escapeHtml(deadline.label)}</strong><span>Cl. ${escapeHtml(deadline.clause)}</span></div>
        <p>${deadline.duration_days} dias · ${escapeHtml(deadline.trigger)}</p>
        <p class="contract-date">${escapeHtml(formatDate(deadline.calculated_due_date))}</p>
        <small>${escapeHtml(deadline.responsible_party || "")}</small>
        ${deadline.extension_note ? `<p class="contract-note">${escapeHtml(deadline.extension_note)}</p>` : ""}
      </article>`).join("");

    const contractObligations = (purchaseContract.operational_obligations || []).map((item) => `
      <article class="contract-item">
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.summary)}</p>
        <small>Cláusulas ${escapeHtml((item.clauses || []).join(", "))}</small>
      </article>`).join("");

    const contractProtections = (purchaseContract.buyer_protections || []).map((item) => `
      <article class="contract-item protection">
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.summary)}</p>
        <small>Cláusulas ${escapeHtml((item.clauses || []).join(", "))}</small>
      </article>`).join("");

    const contractPenalties = (purchaseContract.penalties || []).map((item) => {
      let value = `${item.value}%`;
      if (item.value_type === "daily_amount") value = `${formatMoney(item.value)}/dia`;
      if (item.value_type === "monthly_percentage") value = `${item.value}%/mês · ${formatMoney(item.calculated_monthly_amount)}`;
      if (item.value_type === "percentage" && item.calculated_base_amount != null) value = `${item.value}% · base ${formatMoney(item.calculated_base_amount)}`;
      return `<div class="penalty-row"><span>${escapeHtml(item.title)}</span><strong>${escapeHtml(value)}</strong><small>Cl. ${escapeHtml(item.clause)}</small></div>`;
    }).join("");

    const workContractCards = workContracts.map((contract) => {
      const document = contract.document || {};
      const deadline = contract.deadline || {};
      const start = contract.start_condition || {};
      const scope = (contract.scope || []).map((item) => `
        <li><span>${item.number}</span><div><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.note || "")}</small></div></li>`).join("");
      const terms = (contract.common_operational_terms || []).map((item) => `
        <article class="work-term"><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.summary)}</p><small>Cl. ${escapeHtml(item.clause)}</small></article>`).join("");
      const blanks = (contract.unfilled_fields || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
      const discrepancies = (contract.discrepancies || []).map((item) => `
        <article class="work-conflict ${escapeAttr(item.severity || "attention")}">
          <strong>${escapeHtml(item.topic)}</strong>
          <p><span>Plano:</span> ${escapeHtml(item.project_plan || "")}</p>
          <p><span>Rascunho:</span> ${escapeHtml(item.draft_contract || "")}</p>
          <small>${escapeHtml(item.recommended_action || "")}</small>
        </article>`).join("");
      const deadlineText = deadline.duration_days
        ? `${deadline.duration_days} dias corridos a partir do ${deadline.starts_from}`
        : (deadline.summary || "Sem prazo global definido");
      return `
        <article class="work-contract-card">
          <div class="work-contract-head">
            <div><span>${escapeHtml(contract.phase_id === "phase_1" ? "Contrato 01" : "Contrato 02")}</span><h4>${escapeHtml(contract.label)}</h4></div>
            <span class="draft-badge">Rascunho não assinado</span>
          </div>
          <div class="work-contract-metrics">
            <div><span>Mão de obra</span><strong>${formatMoney(contract.labor_price)}</strong></div>
            <div><span>Início</span><strong>${escapeHtml(start.summary || "A definir")}</strong></div>
            <div><span>Prazo</span><strong>${escapeHtml(deadlineText)}</strong></div>
          </div>
          <div class="document-actions">
            <a class="btn primary" href="${escapeAttr(document.url || "#")}" target="_blank" rel="noopener">Abrir rascunho</a>
            <a class="btn" href="${escapeAttr(document.url || "#")}" download="${escapeAttr(document.filename || "contrato.pdf")}">Baixar PDF</a>
          </div>
          <div class="work-draft-warning"><strong>Antes de assinar</strong><span>Preencher e conferir os campos em branco.</span></div>
          <details class="work-contract-detail" open>
            <summary>Escopo contratado · ${(contract.scope || []).length} itens</summary>
            <ol class="work-scope">${scope}</ol>
          </details>
          <details class="work-contract-detail">
            <summary>Campos ainda não preenchidos</summary>
            <ul class="work-blank-list">${blanks}</ul>
          </details>
          <details class="work-contract-detail">
            <summary>Regras e responsabilidades</summary>
            <div class="work-terms">${terms}</div>
          </details>
          <div class="work-conflicts">
            <h5>Pontos para reconciliar antes da assinatura</h5>
            ${discrepancies}
          </div>
          <p class="contract-source-note">Resumo operacional do rascunho. Consulte o PDF e formalize alterações por escrito.</p>
        </article>`;
    }).join("");

    const contractUrl = contractDocument.url || "/api/project/documents/purchase-contract.pdf";
    const contractStatus = purchaseContract.status === "signed" ? "Assinado" : "Pendente";
    const peopleCards = people.map((person) => `
      <article class="person-card">
        <img src="${escapeAttr(person.image_url || "")}" alt="Foto de ${escapeAttr(person.name || "participante")}" loading="lazy" />
        <div class="person-card-body">
          <span>${escapeHtml(person.role || "Participante")}</span>
          <h4>${escapeHtml(person.name || "")}</h4>
          <p>${escapeHtml(person.story_role || "")}</p>
        </div>
      </article>`).join("");

    els.projectOverview.innerHTML = `
      <h3 class="project-heading people-heading">Pessoas do projeto</h3>
      <div class="people-grid">${peopleCards}</div>

      <h3 class="project-heading">Resumo da casa e da compra</h3>
      <div class="project-summary-grid">
        <article class="house-card">
          <h3>Imóvel e compra</h3>
          <p>${escapeHtml([address.street, address.neighborhood, address.city, address.state].filter(Boolean).join(" · "))}</p>
          <p><strong>${formatMoney(property.purchase_price)}</strong> · ${escapeHtml(financing.institution || "")}</p>
          <p>${escapeHtml(financing.ownership_note || "")}</p>
          <p>Ocupante: até ${property.occupancy_after_financing_signature_days || 0} dias após assinatura do financiamento.</p>
        </article>
        <article class="house-card">
          <h3>Áreas consolidadas</h3>
          <p>Área interna útil: ${(project.official_dimensions || {}).interior_useful_area_m2 || "—"} m²</p>
          <p>Fundos agora: ${currentRear.width_m || "—"} × ${currentRear.depth_m || "—"} m = ${currentRear.area_m2 || "—"} m²</p>
          <p>Cobertura maior em estudo: ${largerRear.width_m || "—"} × ${largerRear.depth_m || "—"} m = ${largerRear.area_m2 || "—"} m²</p>
        </article>
        <article class="house-card">
          <div class="contract-card-head"><h3>Contratos de obra — Gelson</h3><span class="draft-badge compact">2 rascunhos</span></div>
          <p>Fase 1: ${formatMoney(contracts.phase_1_amount)}</p>
          <p>Fase 2: ${formatMoney(contracts.phase_2_amount)}</p>
          <p><strong>Total: ${formatMoney(contracts.total_labor_amount)}</strong></p>
          <small class="work-summary-warning">Não assinados · preencher antes da execução</small>
        </article>
        <article class="house-card contract-summary-card">
          <div class="contract-card-head"><h3>Contrato de compra e venda</h3><span class="contract-status">${contractStatus}</span></div>
          <p>${escapeHtml(formatDate(purchaseContract.contract_date))}</p>
          <p>${escapeHtml(contractParties.buyer || "")} · ${escapeHtml(contractParties.intermediary || "")}</p>
          <p><strong>${formatMoney(contractFinancial.purchase_price)}</strong> · lote ${escapeHtml(contractProperty.lot || "—")}, quadra ${escapeHtml(contractProperty.block || "—")}</p>
          <div class="document-actions">
            <a class="btn primary" href="${escapeAttr(contractUrl)}" target="_blank" rel="noopener">Abrir contrato</a>
            <a class="btn" href="${escapeAttr(contractUrl)}" download="${escapeAttr(contractDocument.filename || "contrato.pdf")}">Baixar PDF</a>
          </div>
        </article>
      </div>

      <h3 class="project-heading">Contratos de obra — Gelson</h3>
      <p class="section-sub">Dois rascunhos separados. Ambos precisam ser preenchidos, conferidos e assinados antes da execução.</p>
      <section class="work-contracts-grid">${workContractCards}</section>

      <h3 class="project-heading">Contrato de compra e venda assinado</h3>
      <section class="contract-panel panel">
        <div class="contract-overview">
          <div><span>Imóvel</span><strong>Lote ${escapeHtml(contractProperty.lot || "—")} · Quadra ${escapeHtml(contractProperty.block || "—")}</strong><small>Matrícula ${escapeHtml(contractProperty.registry_number || "—")} · cadastro ${escapeHtml(contractProperty.municipal_registration || "—")}</small></div>
          <div><span>Preço contratual</span><strong>${formatMoney(contractFinancial.purchase_price)}</strong><small>${escapeHtml(contractFinancial.contract_payment_wording || "")}</small></div>
          <div><span>Foro</span><strong>${escapeHtml(purchaseContract.forum || "—")}</strong><small>Cláusula ${escapeHtml(purchaseContract.forum_clause || "—")}</small></div>
        </div>
        <p class="contract-reconciliation">${escapeHtml(contractFinancial.funding_reconciliation_note || "")}</p>
        <h4>Prazos contratuais</h4>
        <div class="contract-deadlines">${contractDeadlines}</div>
        <div class="contract-columns">
          <div><h4>Obrigações operacionais</h4><div class="contract-items">${contractObligations}</div></div>
          <div><h4>Proteções do comprador</h4><div class="contract-items">${contractProtections}</div></div>
        </div>
        <h4>Penalidades e valores de atenção</h4>
        <div class="penalty-grid">${contractPenalties}</div>
        <p class="contract-source-note">${escapeHtml((purchaseContract.source || {}).note || "Consulte o documento assinado para o teor integral.")}</p>
      </section>

      <h3 class="project-heading">Sequência da compra</h3>
      <ol class="project-workflow">${workflow}</ol>

      <h3 class="project-heading">Plano de obras</h3>
      <div class="project-phases">${phaseCards}</div>

      <h3 class="project-heading">Estudo de novo telhado</h3>
      <p class="section-sub">Não confirmado; estimativas preliminares somente de materiais.</p>
      <div class="table-wrap">
        <table><thead><tr><th>Sistema</th><th class="num">Mínimo</th><th class="num">Máximo</th></tr></thead><tbody>${roofRows}</tbody></table>
      </div>

      <h3 class="project-heading">Estratégia financeira</h3>
      <article class="timeline-card">
        <p><strong>Regra:</strong> ${escapeHtml(financial.decision_rule || "")}</p>
        ${listHtml(financial.priorities || [])}
      </article>

      <h3 class="project-heading">Princípios</h3>
      <div class="principle-grid">${(project.principles || []).map((p) => `<div class="principle">${escapeHtml(p)}</div>`).join("")}</div>
      <p class="project-financial-priority">${escapeHtml(project.financial_priority || "")}</p>`;
  }

  async function renderHouse3D(house) {
    const model = house && house.model_3d;
    if (els.house3dAssumptions) {
      els.house3dAssumptions.innerHTML = (model && model.assumptions || [])
        .map((item) => `<li>${escapeHtml(item)}</li>`)
        .join("");
    }
    if (!model) {
      setStatus(els.house3dStatus, "err", "Geometria 3D ainda não disponível.");
      return;
    }
    setStatus(els.house3dStatus, "", "Carregando modelo 3D…");
    try {
      const module = await import("/house-3d.js?v=20260915-4");
      module.mountHouse3D(model);
    } catch (err) {
      setStatus(els.house3dStatus, "err", `Não foi possível abrir o modelo 3D: ${err.message || err}`);
    }
  }

  function renderHouse(payload) {
    if (!payload || !payload.ok || !payload.house) {
      if (els.houseAudit) {
        els.houseAudit.innerHTML = `<p class="section-sub">${escapeHtml((payload && payload.error) || "Casa não carregada.")}</p>`;
      }
      return;
    }
    const house = payload.house;
    renderHouse3D(house);
    state.project = payload.project || null;
    renderProject(state.project);
    renderDashboard();
    if (els.houseBlueprint) {
      els.houseBlueprint.src = payload.blueprint_url || "/api/house/blueprint.jpg";
    }

    const lot = house.lot_dimensions_meters || {};
    els.houseLot.innerHTML = `
      <div><span class="summary-label">Largura</span><strong>${lot.width ?? "—"} m</strong></div>
      <div><span class="summary-label">Comprimento</span><strong>${lot.length ?? "—"} m</strong></div>
      <div><span class="summary-label">Área</span><strong>${lot.area_m2 ?? "—"} m²</strong></div>`;

    els.houseExterior.innerHTML = "";
    for (const space of house.exterior_spaces || []) {
      const card = document.createElement("article");
      card.className = "house-card";
      const usable = space.usable_dimensions_meters
        ? `<p>${escapeHtml(dimsText(space.usable_dimensions_meters))}${space.area_m2 != null ? ` · ${space.area_m2} m²` : ""}</p>`
        : "";
      const notes = space.architectural_notes ? `<p>${escapeHtml(space.architectural_notes)}</p>` : "";
      card.innerHTML = `<h3>${escapeHtml(space.label)}</h3><p>${escapeHtml(space.location || "")}</p>${usable}${notes}`;
      els.houseExterior.appendChild(card);
    }

    els.houseRooms.innerHTML = "";
    for (const room of house.interior_rooms || []) {
      const card = document.createElement("article");
      card.className = "house-card";
      const feats = (room.features || []).map((f) => `<li>${escapeHtml(f)}</li>`).join("");
      const area = room.approx_area_m2 != null ? `<p>Área aprox.: ${room.approx_area_m2} m²</p>` : "";
      const height = room.wall_height_m != null ? `<p>Pé-direito: ${room.wall_height_m} m</p>` : "";
      card.innerHTML = `
        <h3>${escapeHtml(room.label)}</h3>
        <p>${escapeHtml(dimsText(room.measured_walls_meters))}</p>
        ${area}${height}
        ${feats ? `<ul>${feats}</ul>` : ""}`;
      els.houseRooms.appendChild(card);
    }

    const audit = house.blueprint_audit || {};
    const issues = (audit.issues_found_in_source_json || [])
      .map((i) => `<li><strong>${escapeHtml(i.id)}</strong> — ${escapeHtml(i.severity)} <em>${escapeHtml(i.resolution || "")}</em></li>`)
      .join("");
    els.houseAudit.innerHTML = `
      <h3>${escapeHtml(audit.status || "audit")}</h3>
      <p class="section-sub">${escapeHtml(audit.summary || "")}</p>
      <ul class="audit-list">${issues || "<li>Sem pendências registradas.</li>"}</ul>`;
  }

  async function loadHouse() {
    const response = await fetch("/api/house");
    const payload = await response.json();
    renderHouse(payload);
  }

  function navigateTo(view) {
    showView(view);
    if (view === "house") loadHouse();
  }

  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => navigateTo(btn.getAttribute("data-view")));
  });

  document.getElementById("home-link").addEventListener("click", (event) => {
    event.preventDefault();
    navigateTo("dashboard");
  });


  document.getElementById("dashboard-house-link").addEventListener("click", (event) => {
    event.preventDefault();
    navigateTo("house");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  const navigationShortcuts = {
    h: "dashboard",
    "1": "dashboard",
    "2": "expenses",
    "3": "house",
    "4": "prices",
  };

  document.addEventListener("keydown", (event) => {
    if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const view = navigationShortcuts[event.key.toLowerCase()];
    if (!view) return;
    event.preventDefault();
    navigateTo(view);
  });

  els.phase.addEventListener("change", renderExpenseTable);
  els.priority.addEventListener("change", renderExpenseTable);
  els.category.addEventListener("change", renderExpenseTable);
  els.search.addEventListener("input", renderExpenseTable);
  els.btnNew.addEventListener("click", () => openDialog(null));
  els.btnPush.addEventListener("click", pushToRemote);
  els.btnCancel.addEventListener("click", () => els.dialog.close());
  els.form.addEventListener("submit", saveExpense);
  els.fieldCategory.addEventListener("change", () => renderIconPicker(els.fieldIconKey.value));
  els.iconPicker.addEventListener("click", (event) => {
    const button = event.target.closest("[data-icon-key]");
    if (!button) return;
    renderIconPicker(button.getAttribute("data-icon-key") || "");
  });
  els.rows.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const editId = target.getAttribute("data-edit");
    const deleteId = target.getAttribute("data-delete");
    if (editId) {
      const expense = state.expenses.find((e) => e.id === editId);
      if (expense) openDialog(expense);
      return;
    }
    if (deleteId) deleteExpense(deleteId);
  });

  els.btnGenPrompt.addEventListener("click", generatePrompt);
  els.btnCopyPrompt.addEventListener("click", async () => {
    if (!state.lastPrompt) return;
    await navigator.clipboard.writeText(state.lastPrompt);
    setStatus(els.importStatus, "ok", "Prompt copiado.");
  });
  els.btnDlPrompt.addEventListener("click", () => {
    if (!state.lastPrompt) return;
    downloadText("price-discovery-prompt.txt", state.lastPrompt);
  });
  els.packFile.addEventListener("change", async () => {
    const file = els.packFile.files && els.packFile.files[0];
    if (!file) return;
    els.packInput.value = await file.text();
  });
  els.btnPreviewImport.addEventListener("click", previewImport);
  els.btnCommitImport.addEventListener("click", commitImport);
  els.btnCopyFix.addEventListener("click", async () => {
    if (!state.lastFix) return;
    await navigator.clipboard.writeText(state.lastFix);
  });
  els.btnDlFix.addEventListener("click", () => {
    if (!state.lastFix) return;
    downloadText("PRICE_AI_FIX.txt", state.lastFix);
  });

  showView("dashboard");
  loadHouse().catch(() => {});
  loadState().catch((err) => {
    els.empty.classList.remove("hidden");
    els.empty.textContent = err.message || String(err);
  });
})();
