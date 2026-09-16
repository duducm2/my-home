(() => {
  const state = {
    expenses: [],
    totals: { all: 0, materials: 0, services: 0, by_phase: {}, by_priority: {} },
    timeline: [],
    materials: [],
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
  };

  const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  const formatMoney = (v) => brl.format(Number(v) || 0);

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
        <td>${escapeHtml(expense.description)}${expense.price_notes ? `<div class="price-cell">${escapeHtml(expense.price_notes)}</div>` : ""}</td>
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

  function renderDashboard() {
    els.dashTotalAll.textContent = formatMoney(state.totals.all || 0);
    els.dashTotalMaterials.textContent = formatMoney(state.totals.materials || 0);
    els.dashTotalServices.textContent = formatMoney(state.totals.services || 0);

    els.timelineGroups.innerHTML = "";
    for (const group of state.timeline || []) {
      const card = document.createElement("article");
      card.className = "timeline-card";
      const services = group.pending_services || [];
      const serviceList = services.length
        ? `<ul>${services
            .map(
              (s) =>
                `<li><strong>${escapeHtml(s.category)}</strong> — ${escapeHtml(s.description)} (${formatMoney(s.value)})</li>`
            )
            .join("")}</ul>`
        : `<p class="section-sub">Sem servicos pendentes nesta etapa (somente materiais ou itens ja listados).</p>`;
      card.innerHTML = `
        <h3>${escapeHtml(group.label)}</h3>
        <div class="timeline-meta">${group.count} itens · ${formatMoney(group.total)} · ${services.length} pendencia(s)</div>
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
        <td>${escapeHtml(m.description)}</td>
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
    renderFilters();
    renderExpenseTable();
    renderDashboard();
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
      els.fieldValue.value = "0.00";
      els.fieldQuantity.value = "";
      els.fieldUnit.value = "";
      els.fieldUnitPrice.value = "";
      els.fieldVendor.value = "";
      els.fieldProductUrl.value = "";
      els.fieldPriceNotes.value = "";
    }
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
  }

  async function pushToRemote() {
    els.btnPush.disabled = true;
    setStatus(els.pushStatus, "", "Salvando e enviando para o GitHub…");
    try {
      const response = await fetch("/api/push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      const result = await response.json();
      if (!response.ok || result.ok === false) throw new Error(result.error || "Falha ao enviar");
      if (result.pushed) {
        setStatus(els.pushStatus, "ok", `Enviado ao remoto.${result.commit ? " Commit " + result.commit + "." : ""}`);
      } else {
        setStatus(els.pushStatus, "ok", result.message || "Nada novo para enviar.");
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
          <td>${escapeHtml(row.description || "")}</td>
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
    } catch (err) {
      setStatus(els.importStatus, "err", err.message || String(err));
      els.btnCommitImport.disabled = false;
    }
  }

  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => showView(btn.getAttribute("data-view")));
  });

  els.phase.addEventListener("change", renderExpenseTable);
  els.priority.addEventListener("change", renderExpenseTable);
  els.category.addEventListener("change", renderExpenseTable);
  els.search.addEventListener("input", renderExpenseTable);
  els.btnNew.addEventListener("click", () => openDialog(null));
  els.btnPush.addEventListener("click", pushToRemote);
  els.btnCancel.addEventListener("click", () => els.dialog.close());
  els.form.addEventListener("submit", saveExpense);
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
  loadState().catch((err) => {
    els.empty.classList.remove("hidden");
    els.empty.textContent = err.message || String(err);
  });
})();
