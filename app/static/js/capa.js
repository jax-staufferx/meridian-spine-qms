// CAPA module: list (filterable), create, detail with stepper + audit trail,
// and the strict one-step-forward transition form.

import {
  CAPA_STATUSES,
  alertBox,
  api,
  capaBadge,
  clampText,
  el,
  emptyState,
  fmtDate,
  fmtDateTime,
  linkBtn,
  pageHeader,
  tableWrap,
} from "./core.js";

function relatedLink(capa) {
  if (capa.related_lot_id) {
    return el(
      "a",
      { href: `#/traceability?lot=${encodeURIComponent(capa.related_lot_id)}` },
      `Lot ${capa.related_lot_id}`
    );
  }
  if (capa.related_serial_number) {
    return el(
      "a",
      { href: `#/traceability?serial=${encodeURIComponent(capa.related_serial_number)}` },
      `Device ${capa.related_serial_number}`
    );
  }
  return "—";
}

// ---- List ----

export async function renderCapaList(container, initialStatus) {
  container.replaceChildren(el("p", { class: "loading", text: "Loading CAPAs…" }));
  const status = CAPA_STATUSES.includes(initialStatus) ? initialStatus : "";
  const capas = await api(status ? `/capas?status=${encodeURIComponent(status)}` : "/capas");

  const statusSelect = el(
    "select",
    {
      id: "capa-status-filter",
      onchange: (e) => {
        const value = e.target.value;
        window.location.hash = value ? `#/capas?status=${encodeURIComponent(value)}` : "#/capas";
      },
    },
    [el("option", { value: "", text: "(All statuses)" })].concat(
      CAPA_STATUSES.map((s) => el("option", { value: s, text: s }))
    )
  );
  statusSelect.value = status;

  container.replaceChildren(
    pageHeader(
      "CAPA & Nonconformance",
      "Corrective and preventive actions, driven through a strict six-stage workflow.",
      linkBtn("#/capas/new", "New CAPA")
    ),
    el(
      "div",
      { class: "filter-bar" },
      el(
        "div",
        {},
        el("label", { class: "filter-label", for: "capa-status-filter", text: "Filter by status" }),
        statusSelect
      )
    ),
    capas.length === 0
      ? emptyState("No CAPAs match this filter.")
      : tableWrap(
          ["CAPA", "Status", "Source type", "Related to", "Opened", "Description"],
          capas.map((capa) => [
            el("a", { href: `#/capas/${capa.capa_id}`, text: `#${capa.capa_id}` }),
            capaBadge(capa.status),
            capa.source_type,
            relatedLink(capa),
            fmtDate(capa.opened_date),
            clampText(capa.description),
          ])
        )
  );
}

// ---- Create ----

export async function renderCapaNew(container) {
  const msg = el("div");

  const descriptionInput = el("textarea", { id: "capa-description", rows: 4, required: true });
  const sourceInput = el("input", { id: "capa-source-type", type: "text", value: "Nonconformance" });
  const lotInput = el("input", {
    id: "capa-lot",
    type: "text",
    autocomplete: "off",
    placeholder: "e.g. TI-2025-0101",
  });
  const serialInput = el("input", {
    id: "capa-serial",
    type: "text",
    autocomplete: "off",
    placeholder: "e.g. PS-2001",
  });

  async function onSubmit(e) {
    e.preventDefault();
    msg.replaceChildren();
    const description = descriptionInput.value.trim();
    const lotId = lotInput.value.trim();
    const serial = serialInput.value.trim();

    if (!description) {
      msg.replaceChildren(alertBox("error", "Description is required."));
      return;
    }
    if (lotId && serial) {
      msg.replaceChildren(alertBox("error", "A CAPA may link to a lot or a device, not both. Fill in only one."));
      return;
    }
    try {
      const capa = await api("/capas", {
        method: "POST",
        body: {
          description,
          source_type: sourceInput.value.trim() || "Nonconformance",
          related_lot_id: lotId || null,
          related_serial_number: serial || null,
        },
      });
      window.location.hash = `#/capas/${capa.capa_id}`;
    } catch (err) {
      msg.replaceChildren(alertBox("error", err.message));
    }
  }

  container.replaceChildren(
    el("a", { class: "back-link", href: "#/capas", text: "All CAPAs" }),
    pageHeader("New CAPA", "Open a corrective or preventive action record."),
    el(
      "form",
      { class: "card", onsubmit: onSubmit },
      el(
        "fieldset",
        {},
        el("legend", {}, "CAPA record"),
        el(
          "div",
          { class: "form-row" },
          el("label", { for: "capa-description", text: "Description (required)" }),
          descriptionInput,
          el("p", { class: "help-text", text: "What was the nonconformance? Be specific — this text is the anchor of the audit trail." })
        ),
        el(
          "div",
          { class: "form-row" },
          el("label", { for: "capa-source-type", text: "Source type" }),
          sourceInput
        )
      ),
      el(
        "fieldset",
        {},
        el("legend", {}, "Link to an existing record (optional)"),
        el("p", { class: "help-text", text: "Link the CAPA to exactly one raw material lot OR one device — not both. Leave both blank for an unlinked CAPA (e.g. a process or training finding)." }),
        el(
          "div",
          { class: "form-grid" },
          el(
            "div",
            { class: "form-row" },
            el("label", { for: "capa-lot", text: "Related raw material lot ID" }),
            lotInput
          ),
          el(
            "div",
            { class: "form-row" },
            el("label", { for: "capa-serial", text: "Related device serial number" }),
            serialInput
          )
        )
      ),
      msg,
      el("button", { class: "btn btn-primary", type: "submit", text: "Create CAPA" })
    )
  );
}

// ---- Detail ----

export async function renderCapaDetail(container, capaId, notice) {
  container.replaceChildren(el("p", { class: "loading", text: "Loading CAPA…" }));
  const capa = await api(`/capas/${capaId}`);
  const currentIndex = CAPA_STATUSES.indexOf(capa.status);
  const nextStatus = currentIndex < CAPA_STATUSES.length - 1 ? CAPA_STATUSES[currentIndex + 1] : null;

  container.replaceChildren(
    el("a", { class: "back-link", href: "#/capas", text: "All CAPAs" }),
    notice ? alertBox("success", notice) : null,
    el(
      "div",
      { class: "detail-head" },
      el(
        "h1",
        { class: "page-title" },
        `CAPA #${capa.capa_id} `,
        capaBadge(capa.status)
      ),
      el(
        "p",
        { class: "page-lede" },
        `${capa.source_type} · Opened ${fmtDate(capa.opened_date)} · Linked to: `,
        capa.related_lot_id || capa.related_serial_number ? relatedLink(capa) : "no lot or device"
      ),
      capa.closed_date ? el("p", { class: "page-lede", text: `Closed ${fmtDate(capa.closed_date)}` }) : null
    ),
    stepper(capa),
    documentationCard(capa),
    transitionsCard(capa),
    nextStatus
      ? transitionCard(capa, nextStatus, container)
      : el("div", { class: "alert alert-info", text: "This CAPA is Closed — no further transitions are allowed." })
  );
}

function stepper(capa) {
  const currentIndex = CAPA_STATUSES.indexOf(capa.status);
  return el(
    "nav",
    { class: "stepper", "aria-label": `CAPA workflow progress — stage ${currentIndex + 1} of 6: ${capa.status}` },
    CAPA_STATUSES.map((status, i) =>
      el(
        "div",
        { class: `step ${i < currentIndex ? "step-done" : i === currentIndex ? "step-current" : ""}` },
        el("span", { class: "step-circle", "aria-hidden": "true", text: i < currentIndex ? "✓" : String(i + 1) }),
        el(
          "span",
          { class: "step-label" },
          status,
          i === currentIndex ? el("span", { class: "visually-hidden", text: " (current stage)" }) : null
        )
      )
    )
  );
}

function documentationCard(capa) {
  const block = (label, value) =>
    el(
      "div",
      { class: "doc-block" },
      el("h3", { class: "doc-label", text: label }),
      value && value.trim()
        ? el("p", { class: "doc-value", text: value })
        : el("p", { class: "doc-value doc-empty", text: "(not yet documented)" })
    );

  return el(
    "section",
    { class: "card" },
    el("h2", { class: "card-title", text: "Documentation" }),
    el(
      "div",
      { class: "doc-grid" },
      block("Root cause", capa.root_cause),
      block("Corrective action", capa.corrective_action),
      block("Verification notes", capa.verification_notes)
    )
  );
}

function transitionsCard(capa) {
  return el(
    "section",
    { class: "card" },
    el("h2", { class: "card-title", text: "Transition history (audit trail)" }),
    capa.transitions.length === 0
      ? emptyState("No transitions yet — this CAPA is newly opened.")
      : el(
          "ol",
          { class: "timeline" },
          capa.transitions.map((t) =>
            el(
              "li",
              { class: "timeline-entry" },
              el(
                "p",
                { class: "timeline-head" },
                el("span", { class: "timeline-date", text: fmtDateTime(t.changed_date) }),
                " — ",
                capaBadge(t.from_status),
                " → ",
                capaBadge(t.to_status)
              ),
              el("p", { class: "timeline-note", text: t.note }),
              el("p", { class: "timeline-by", text: `Recorded by ${t.changed_by}` })
            )
          )
        )
  );
}

const STAGE_HINT = {
  "Investigation": "Investigate the nonconformance and record your findings in the transition note.",
  "Root Cause": "This is the Root Cause stage — document the underlying cause in the Root cause field.",
  "Corrective Action": "Document the action taken in the Corrective action field.",
  "Verification": "Record evidence that the corrective action was effective in the Verification notes field.",
  "Closed": "Closing records the final disposition of the CAPA.",
};

function transitionCard(capa, nextStatus, container) {
  const msg = el("div");
  const noteInput = el("textarea", { id: "capa-note", rows: 3, required: true });
  const byInput = el("input", { id: "capa-changed-by", type: "text", required: true, autocomplete: "off", placeholder: "e.g. J. Alvarez" });
  const rcInput = el("textarea", { id: "capa-rc", rows: 2, placeholder: capa.root_cause || "" });
  const caInput = el("textarea", { id: "capa-ca", rows: 2, placeholder: capa.corrective_action || "" });
  const vnInput = el("textarea", { id: "capa-vn", rows: 2, placeholder: capa.verification_notes || "" });

  const hasRootCause = () => Boolean((capa.root_cause && capa.root_cause.trim()) || rcInput.value.trim());
  const submitBtn = el("button", { class: "btn btn-primary", type: "submit", text: `Advance to “${nextStatus}”` });

  const closeBlocked = nextStatus === "Closed" && !hasRootCause();
  const closeWarning = closeBlocked
    ? el(
        "div",
        { class: "alert alert-warn", role: "alert" },
        "Closing this CAPA requires a documented root cause. Enter it in the Root cause field below — the submit button stays disabled until it is filled in."
      )
    : null;

  if (nextStatus === "Closed") {
    rcInput.addEventListener("input", () => {
      submitBtn.disabled = !hasRootCause();
    });
    submitBtn.disabled = !hasRootCause();
  }

  async function onSubmit(e) {
    e.preventDefault();
    msg.replaceChildren();
    const note = noteInput.value.trim();
    const changedBy = byInput.value.trim();
    if (!note) {
      msg.replaceChildren(alertBox("error", "A note is required for every transition."));
      return;
    }
    if (!changedBy) {
      msg.replaceChildren(alertBox("error", "Changed by is required for every transition."));
      return;
    }
    try {
      const updated = await api(`/capas/${capa.capa_id}/transition`, {
        method: "POST",
        body: {
          to_status: nextStatus,
          note,
          changed_by: changedBy,
          root_cause: rcInput.value.trim() || null,
          corrective_action: caInput.value.trim() || null,
          verification_notes: vnInput.value.trim() || null,
        },
      });
      await renderCapaDetail(container, capa.capa_id, `CAPA advanced to “${updated.status}”.`);
    } catch (err) {
      msg.replaceChildren(alertBox("error", err.message));
    }
  }

  return el(
    "section",
    { class: "card" },
    el("h2", { class: "card-title", text: `Advance to “${nextStatus}”` }),
    el("p", { class: "help-text", text: STAGE_HINT[nextStatus] || "" }),
    el("p", { class: "help-text", text: "Every transition requires a note and is recorded in the audit trail with your name and a timestamp. The workflow moves exactly one stage at a time — no skipping, no reopening." }),
    closeWarning,
    el(
      "form",
      { onsubmit: onSubmit },
      el(
        "div",
        { class: "form-row" },
        el("label", { for: "capa-note", text: "Transition note (required)" }),
        noteInput
      ),
      el(
        "div",
        { class: "form-row" },
        el("label", { for: "capa-changed-by", text: "Changed by (required)" }),
        byInput
      ),
      el(
        "div",
        { class: "form-grid" },
        el(
          "div",
          { class: "form-row" },
          el("label", { for: "capa-rc", text: "Root cause" }),
          rcInput,
          el("p", { class: "help-text", text: "Required before a CAPA can be closed. Fill in on or after the Root Cause stage." })
        ),
        el(
          "div",
          { class: "form-row" },
          el("label", { for: "capa-ca", text: "Corrective action" }),
          caInput,
          el("p", { class: "help-text", text: "Fill in on or after the Corrective Action stage." })
        ),
        el(
          "div",
          { class: "form-row" },
          el("label", { for: "capa-vn", text: "Verification notes" }),
          vnInput,
          el("p", { class: "help-text", text: "Fill in on or after the Verification stage." })
        )
      ),
      msg,
      submitBtn
    )
  );
}
