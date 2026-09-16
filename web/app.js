(() => {
  const state = {
    expenses: [],
    totals: { all: 0, by_phase: {}, by_priority: {} },
  };

  const els = {
    phase: document.getElementById("filter-phase"),
    priority: document.getElementById("filter-priority"),
    category: document.getElementById("filter-category"),
    search: document.getElementById("filter-search"),
    rows: document.getElementById("expense-rows"),
    empty: document.getElementById("empty-state"),
    totalFiltered: document.getElementById("total-filtered"),
    totalAll: document.getElementById("total-all"),
    countFiltered: document.getElementById("count-filtered"),
    btnNew: document.getElementById("btn-new"),
    dialog: document.getElementById("expense-dialog"),
    form: document.getElementById("expense-form"),
    dialogTitle: document.getElementById("dialog-title"),
    fieldId: document.getElementById("field-id"),
    fieldPhase: document.getElementById("field-phase"),
    fieldPriority: document.getElementById("field-priority"),
    fieldCategory: document.getElementById("field-category"),
    fieldDescription: document.getElementById("field-description"),
    fieldValue: document.getElementById("field-value"),
    formError: document.getElementById("form-error"),
    btnCancel: document.getElementById("btn-cancel"),
    phaseSuggestions: document.getElementById("phase-suggestions"),
    categorySuggestions: document.getElementById("category-suggestions"),
  };

  const brl = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  });

  function formatMoney(value) {
    return brl.format(Number(value) || 0);
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
    if ([...select.options].some((o) => o.value === current)) {
      select.value = current;
    }
  }

  function fillDatalist(datalist, values) {
    datalist.innerHTML = "";
    for (const value of values) {
      const opt = document.createElement("option");
      opt.value = String(value);
      datalist.appendChild(opt);
    }
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
        const hay = `${expense.phase} ${expense.category} ${expense.description}`.toLowerCase();
        if (!hay.includes(search)) return false;
      }
      return true;
    });
  }

  function renderFilters() {
    const phases = uniqueSorted(state.expenses.map((e) => e.phase));
    const priorities = uniqueSorted(state.expenses.map((e) => String(e.priority))).sort(
      (a, b) => Number(a) - Number(b)
    );
    const categories = uniqueSorted(state.expenses.map((e) => e.category));

    fillSelect(els.phase, phases, "Todas");
    fillSelect(els.priority, priorities, "Todas");
    fillSelect(els.category, categories, "Todas");
    fillDatalist(els.phaseSuggestions, phases);
    fillDatalist(els.categorySuggestions, categories);
  }

  function renderTable() {
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
        <td>${escapeHtml(expense.description)}</td>
        <td class="num">${formatMoney(expense.value)}</td>
        <td class="actions">
          <div class="row-actions">
            <button type="button" class="btn" data-edit="${escapeAttr(expense.id)}">Editar</button>
            <button type="button" class="btn danger" data-delete="${escapeAttr(expense.id)}">Excluir</button>
          </div>
        </td>
      `;
      fragment.appendChild(tr);
    }
    els.rows.appendChild(fragment);
  }

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

  function applyState(payload) {
    state.expenses = payload.expenses || [];
    state.totals = payload.totals || { all: 0, by_phase: {}, by_priority: {} };
    renderFilters();
    renderTable();
  }

  async function loadState() {
    const response = await fetch("/api/state");
    const payload = await response.json();
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || "Falha ao carregar dados");
    }
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
    } else {
      els.dialogTitle.textContent = "Nova despesa";
      els.fieldId.value = "";
      els.fieldPhase.value = els.phase.value || "";
      els.fieldPriority.value = els.priority.value || "1";
      els.fieldCategory.value = els.category.value || "";
      els.fieldDescription.value = "";
      els.fieldValue.value = "0.00";
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
    };
    if (els.fieldId.value) {
      payload.id = els.fieldId.value;
    }

    try {
      const response = await fetch("/api/expenses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok || result.ok === false) {
        throw new Error(result.error || "Não foi possível salvar");
      }
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
    if (!window.confirm(`Excluir a despesa “${label}”?`)) {
      return;
    }
    const response = await fetch(`/api/expenses/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    const result = await response.json();
    if (!response.ok || result.ok === false) {
      window.alert(result.error || "Não foi possível excluir");
      return;
    }
    applyState(result.state);
  }

  els.phase.addEventListener("change", renderTable);
  els.priority.addEventListener("change", renderTable);
  els.category.addEventListener("change", renderTable);
  els.search.addEventListener("input", renderTable);
  els.btnNew.addEventListener("click", () => openDialog(null));
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
    if (deleteId) {
      deleteExpense(deleteId);
    }
  });

  loadState().catch((err) => {
    els.empty.classList.remove("hidden");
    els.empty.textContent = err.message || String(err);
  });
})();
