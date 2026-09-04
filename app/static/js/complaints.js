// Complaints & MDR module: list (filterable by decision), intake,
// detail with reasoning card + evaluation history, and re-evaluation.

import {
  SERIOUS_INJURY_DEFINITION,
  alertBox,
  api,
  dueChip,
  el,
  emptyState,
  fmtDate,
  fmtDateTime,
  linkBtn,
  mdrBadge,
  pageHeader,
  tableWrap,
  todayISO,
} from "./core.js";

const DECISION_FILTERS = ["Reportable", "Not Reportable", "Needs Human Review", "Not Yet Evaluated"];

const ENUMS = {
  injury_occurred: ["Unknown", "Yes", "No"],
  injury_severity: ["Unknown", "None", "Minor", "Serious", "Death"],
  device_malfunctioned: ["Unknown", "Yes", "No"],
  device_causality: ["Unknown", "Caused", "Contributed", "Unrelated"],
  recurrence_would_be_dangerous: ["Unknown", "Yes", "No"],
};

const FIELD_LABELS = {
  injury_occurred: "Injury occurred",
  injury_severity: "Injury severity",
  device_malfunctioned: "Device malfunctioned",
  device_causality: "Device causality",
  recurrence_would_be_dangerous: "Recurrence would be dangerous",
  remedial_action_taken: "Remedial action taken",
};

function seriousInjuryDefinitionPanel() {
  return el(
    "div",
    { class: "definition-panel" },
    el("p", { class: "def-title", text: "Legal definition — serious injury (21 CFR 803)" }),
    el("p", {}, SERIOUS_INJURY_DEFINITION)
  );
}

// ---- List ----

export async function renderComplaintList(container, initialFilter) {
  container.replaceChildren(el("p", { class: "loading", text: "Loading complaints…" }));
  const filter = DECISION_FILTERS.includes(initialFilter) ? initialFilter : "";

  let complaints;
  if (!filter) {
    complaints = await api("/complaints");
  } else if (filter === "Not Yet Evaluated") {
    complaints = (await api("/complaints")).filter((c) => !c.mdr_decision);
  } else {
    complaints = await api(`/complaints?mdr_decision=${encodeURIComponent(filter)}`);
  }

  const filterSelect = el(
    "select",
    {
      id: "complaint-filter",
      onchange: (e) => {
        const value = e.target.value;
        window.location.hash = value
          ? `#/complaints?mdr_decision=${encodeURIComponent(value)}`
          : "#/complaints";
      },
    },
    [el("option", { value: "", text: "(All decisions)" })].concat(
      DECISION_FILTERS.map((d) => el("option", { value: d, text: d }))
    )
  );
  filterSelect.value = filter;

  container.replaceChildren(
    pageHeader(
      "Complaints & MDR",
      "Complaint intake and the deterministic 21 CFR 803 reportability decision engine.",
      linkBtn("#/complaints/new", "New complaint")
    ),
    el(
      "div",
      { class: "filter-bar" },
      el(
        "div",
        {},
        el("label", { class: "filter-label", for: "complaint-filter", text: "Filter by MDR decision" }),
        filterSelect
      )
    ),
    complaints.length === 0
      ? emptyState("No complaints match this filter.")
      : tableWrap(
          ["Complaint", "MDR decision", "Received", "Device", "Complainant", "Description"],
          complaints.map((c) => [
            el("a", { href: `#/complaints/${c.complaint_id}`, text: `#${c.complaint_id}` }),
            el(
              "span",
              { class: "stack" },
              mdrBadge(c.mdr_decision),
              dueChip(c) || el("span")
            ),
            fmtDate(c.date_received),
            c.serial_number || "—",
            el("span", { class: "truncate", title: c.complainant, text: c.complainant }),
            el("span", { class: "truncate", title: c.description, text: c.description }),
          ])
        )
  );
}

// ---- Intake ----

export async function renderComplaintNew(container) {
  container.replaceChildren(el("p", { class: "loading", text: "Loading…" }));
  const devices = await api("/devices");
  const msg = el("div");

  const serialInput = el("input", {
    id: "complaint-serial",
    type: "text",
    list: "complaint-device-options",
    autocomplete: "off",
    placeholder: "e.g. PS-2005",
  });
  const dateInput = el("input", { id: "complaint-date", type: "date", value: todayISO(), required: true });
  const complainantInput = el("input", { id: "complaint-complainant", type: "text", required: true, autocomplete: "off" });
  const descriptionInput = el("textarea", { id: "complaint-description", rows: 4, required: true });

  const enumSelects = {};
  for (const [field, values] of Object.entries(ENUMS)) {
    enumSelects[field] = el(
      "select",
      { id: `complaint-${field}` },
      values.map((v) => el("option", { value: v, text: v }))
    );
    enumSelects[field].value = "Unknown";
  }
  const remedialInput = el("input", { id: "complaint-remedial", type: "checkbox" });

  async function onSubmit(e) {
    e.preventDefault();
    msg.replaceChildren();
    try {
      const complaint = await api("/complaints", {
        method: "POST",
        body: {
          serial_number: serialInput.value.trim() || null,
          date_received: dateInput.value,
          complainant: complainantInput.value.trim(),
          description: descriptionInput.value.trim(),
          injury_occurred: enumSelects.injury_occurred.value,
          injury_severity: enumSelects.injury_severity.value,
          device_malfunctioned: enumSelects.device_malfunctioned.value,
          device_causality: enumSelects.device_causality.value,
          recurrence_would_be_dangerous: enumSelects.recurrence_would_be_dangerous.value,
          remedial_action_taken: remedialInput.checked,
        },
      });
      window.location.hash = `#/complaints/${complaint.complaint_id}`;
    } catch (err) {
      msg.replaceChildren(alertBox("error", err.message));
    }
  }

  const field = (labelText, control, help) =>
    el(
      "div",
      { class: "form-row" },
      el("label", { for: control.id, text: labelText }),
      control,
      help ? el("p", { class: "help-text", text: help }) : null
    );

  container.replaceChildren(
    el("a", { class: "back-link", href: "#/complaints", text: "All complaints" }),
    pageHeader("New complaint", "Log a complaint and capture the structured inputs the decision engine needs."),
    el(
      "form",
      { class: "card", onsubmit: onSubmit },
      el(
        "fieldset",
        {},
        el("legend", {}, "Complaint report"),
        el("p", { class: "help-text", text: "Identify the unit if possible — the serial number enables backward traceability. Leave blank if the unit cannot be identified." }),
        el(
          "div",
          { class: "form-grid" },
          field("Related device serial number (optional)", serialInput),
          field("Date received (required)", dateInput),
          field("Complainant (required)", complainantInput)
        ),
        field("Description (required)", descriptionInput, "What was reported, by whom, in as close to their words as possible.")
      ),
      el(
        "fieldset",
        {},
        el("legend", {}, "Structured decision inputs"),
        el("p", { class: "help-text", text: "These six fields drive the deterministic MDR decision engine. “Unknown” is a valid, expected entry — it signals missing information and routes the complaint to human review rather than guessing a value. Never record a guess." }),
        el(
          "div",
          { class: "form-grid" },
          field("Injury occurred", enumSelects.injury_occurred),
          field("Device malfunctioned", enumSelects.device_malfunctioned),
          field("Device causality", enumSelects.device_causality),
          field("Recurrence would be dangerous", enumSelects.recurrence_would_be_dangerous,
            "If this same failure recurred, would it be reasonably likely to cause or contribute to death or serious injury?"),
          el(
            "div",
            { class: "form-row" },
            el("label", { for: "complaint-injury_severity", text: "Injury severity" }),
            enumSelects.injury_severity,
            seriousInjuryDefinitionPanel()
          ),
          el(
            "div",
            { class: "form-row" },
            el("label", { class: "check-row", for: "complaint-remedial" },
              remedialInput,
              "Remedial action taken"
            ),
            el("p", { class: "help-text", text: "e.g. a field action or notification to reduce a risk to health — triggers the expedited 5-working-day MDR deadline when the complaint is reportable." })
          )
        )
      ),
      msg,
      el("button", { class: "btn btn-primary", type: "submit", text: "Create complaint" })
    ),
    el("datalist", { id: "complaint-device-options" }, devices.map((d) => el("option", { value: d.serial_number })))
  );
}

// ---- Detail ----

export async function renderComplaintDetail(container, complaintId, notice) {
  container.replaceChildren(el("p", { class: "loading", text: "Loading complaint…" }));
  const c = await api(`/complaints/${complaintId}`);

  container.replaceChildren(
    el("a", { class: "back-link", href: "#/complaints", text: "All complaints" }),
    notice ? alertBox("success", notice) : null,
    el(
      "div",
      { class: "detail-head" },
      el("h1", { class: "page-title" }, `Complaint #${c.complaint_id} `, mdrBadge(c.mdr_decision)),
      el(
        "p",
        { class: "page-lede" },
        `Received ${fmtDate(c.date_received)} · From ${c.complainant} · `,
        c.serial_number
          ? el("a", { href: `#/traceability?serial=${encodeURIComponent(c.serial_number)}`, text: `Device ${c.serial_number}` })
          : "Unit unidentified"
      )
    ),
    reportCard(c),
    inputsCard(c),
    reasoningCard(c),
    historyCard(c),
    evaluateCard(c, container)
  );
}

function reportCard(c) {
  return el(
    "section",
    { class: "card" },
    el("h2", { class: "card-title", text: "Reported issue" }),
    el("p", { class: "doc-value", text: c.description })
  );
}

function inputsCard(c) {
  const row = (label, value) => [
    el("dt", { text: label }),
    el("dd", { text: value }),
  ];
  return el(
    "section",
    { class: "card" },
    el("h2", { class: "card-title", text: "Decision inputs" }),
    el(
      "dl",
      { class: "field-list" },
      row(FIELD_LABELS.injury_occurred, c.injury_occurred),
      row(FIELD_LABELS.injury_severity, c.injury_severity),
      row(FIELD_LABELS.device_malfunctioned, c.device_malfunctioned),
      row(FIELD_LABELS.device_causality, c.device_causality),
      row(FIELD_LABELS.recurrence_would_be_dangerous, c.recurrence_would_be_dangerous),
      row(FIELD_LABELS.remedial_action_taken, c.remedial_action_taken ? "Yes" : "No"),
      el("dt", { text: "Linked CAPA" }),
      c.capa_id
        ? el("dd", {}, el("a", { href: `#/capas/${c.capa_id}`, text: `CAPA #${c.capa_id}` }))
        : el("dd", { text: "—" })
    )
  );
}

function reasoningCard(c) {
  if (!c.mdr_decision) {
    return el(
      "section",
      { class: "card reasoning-card" },
      el("h2", { class: "card-title", text: "MDR decision reasoning" }),
      el("p", { class: "empty-state", text: "Not yet evaluated — update the fields below and run the decision engine to record a determination." })
    );
  }
  return el(
    "section",
    { class: "card reasoning-card" },
    el("h2", { class: "card-title", text: "MDR decision reasoning" }),
    el(
      "div",
      { class: "reasoning-head" },
      mdrBadge(c.mdr_decision),
      dueChip(c) || el("span"),
      c.mdr_due_date
        ? el("span", { class: "reasoning-due", text: `Due ${fmtDate(c.mdr_due_date)} (${c.mdr_deadline_days}-day deadline)` })
        : el("span")
    ),
    el("p", { class: "reasoning-text", text: c.mdr_reasoning }),
    c.mdr_evaluated_date
      ? el("p", { class: "help-text", text: `Last evaluated ${fmtDateTime(c.mdr_evaluated_date)}` })
      : null
  );
}

function historyCard(c) {
  return el(
    "section",
    { class: "card" },
    el("h2", { class: "card-title", text: "Evaluation history" }),
    el("p", { class: "help-text", text: "Append-only record of every decision-engine run, including the field values each decision was based on — how the determination evolved as new information came in." }),
    c.evaluation_logs.length === 0
      ? emptyState("No evaluations yet — the decision engine has not been run for this complaint.")
      : el(
          "ol",
          { class: "timeline" },
          c.evaluation_logs.map((log) =>
            el(
              "li",
              { class: "timeline-entry" },
              el(
                "p",
                { class: "timeline-head" },
                el("span", { class: "timeline-date", text: fmtDateTime(log.evaluated_date) }),
                " — ",
                mdrBadge(log.mdr_decision)
              ),
              el(
                "p",
                {
                  class: "timeline-fields",
                  text:
                    `Severity: ${log.injury_severity} · Causality: ${log.device_causality} · ` +
                    `Malfunction: ${log.device_malfunctioned} · Recurrence dangerous: ${log.recurrence_would_be_dangerous} · ` +
                    `Remedial: ${log.remedial_action_taken ? "Yes" : "No"}`,
                }
              ),
              el(
                "details",
                { class: "timeline-details" },
                el("summary", { text: "View reasoning from this evaluation" }),
                el("p", { class: "timeline-note", text: log.mdr_reasoning })
              )
            )
          )
        )
  );
}

// ---- Update fields & re-run decision ----

function evaluateCard(c, container) {
  const msg = el("div");

  const selects = {};
  for (const [field, values] of Object.entries(ENUMS)) {
    selects[field] = el(
      "select",
      { id: `eval-${field}` },
      [el("option", { value: "", text: "(no change)" })].concat(
        values.map((v) => el("option", { value: v, text: v }))
      )
    );
  }
  const remedialSelect = el(
    "select",
    { id: "eval-remedial" },
    el("option", { value: "", text: "(no change)" }),
    el("option", { value: "true", text: "Yes" }),
    el("option", { value: "false", text: "No" })
  );
  const capaInput = el("input", { id: "eval-capa", type: "number", min: "1", step: "1", placeholder: c.capa_id ? `currently #${c.capa_id}` : "e.g. 3" });

  async function onSubmit(e) {
    e.preventDefault();
    msg.replaceChildren();

    const body = {};
    for (const field of Object.keys(ENUMS)) {
      if (selects[field].value) body[field] = selects[field].value;
    }
    if (remedialSelect.value) body.remedial_action_taken = remedialSelect.value === "true";
    const capaRaw = capaInput.value.trim();
    if (capaRaw) {
      const capaId = Number(capaRaw);
      if (!Number.isInteger(capaId) || capaId <= 0) {
        msg.replaceChildren(alertBox("error", "CAPA ID must be a positive whole number."));
        return;
      }
      body.capa_id = capaId;
    }

    try {
      const updated = await api(`/complaints/${c.complaint_id}/evaluate`, { method: "POST", body });
      await renderComplaintDetail(
        container,
        c.complaint_id,
        `Decision recorded: ${updated.mdr_decision}. The evaluation history below now includes this run.`
      );
    } catch (err) {
      msg.replaceChildren(alertBox("error", err.message));
    }
  }

  const field = (labelText, control, help) =>
    el(
      "div",
      { class: "form-row" },
      el("label", { for: control.id, text: labelText }),
      control,
      help ? el("p", { class: "help-text", text: help }) : null
    );

  return el(
    "section",
    { class: "card evaluate-card" },
    el("h2", { class: "card-title", text: "Update fields & re-run decision" }),
    el("p", { class: "help-text", text: "Update any decision inputs as new information arrives, then re-run the engine. This appends to the evaluation history — it does not create a new complaint. Leave a field on “(no change)” to keep its current value." }),
    el(
      "form",
      { onsubmit: onSubmit },
      el(
        "div",
        { class: "form-grid" },
        field("Injury occurred", selects.injury_occurred),
        field("Device malfunctioned", selects.device_malfunctioned),
        field("Device causality", selects.device_causality),
        field("Recurrence would be dangerous", selects.recurrence_would_be_dangerous),
        el(
          "div",
          { class: "form-row" },
          el("label", { for: "eval-injury_severity", text: "Injury severity" }),
          selects.injury_severity,
          seriousInjuryDefinitionPanel()
        ),
        field("Remedial action taken", remedialSelect),
        field("Link to CAPA (optional)", capaInput, "CAPA ID to link to this complaint. Leave blank to keep the current link.")
      ),
      msg,
      el("button", { class: "btn btn-primary", type: "submit", text: "Run decision engine" })
    )
  );
}
