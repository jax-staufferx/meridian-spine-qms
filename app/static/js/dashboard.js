// Dashboard: KPI cards + urgent MDR deadline banner.

import {
  api,
  daysUntil,
  dueChip,
  el,
  fmtDate,
  pageHeader,
} from "./core.js";

const URGENT_WINDOW_DAYS = 5;

function urgentComplaints(complaints) {
  return complaints.filter(
    (c) =>
      c.mdr_decision === "Reportable" &&
      c.mdr_due_date &&
      daysUntil(c.mdr_due_date) <= URGENT_WINDOW_DAYS
  );
}

function urgentBanner(urgent, reportableCount) {
  if (!urgent.length) {
    return el(
      "div",
      { class: "banner banner-neutral" },
      el("p", {}, reportableCount
        ? `${reportableCount} reportable complaint${reportableCount === 1 ? "" : "s"} on file — none due within the next ${URGENT_WINDOW_DAYS} days.`
        : `No reportable MDR deadlines due within the next ${URGENT_WINDOW_DAYS} days.`)
    );
  }
  return el(
    "div",
    { class: "banner banner-urgent", role: "alert" },
    el(
      "h2",
      { class: "banner-title" },
      `MDR deadline alert — ${urgent.length} reportable complaint${urgent.length === 1 ? "" : "s"} due soon or overdue`
    ),
    el(
      "ul",
      { class: "banner-list" },
      urgent.map((c) =>
        el(
          "li",
          {},
          el("a", { href: `#/complaints/${c.complaint_id}` }, `Complaint #${c.complaint_id}`),
          ` — due ${fmtDate(c.mdr_due_date)} — `,
          el("strong", {}, dueChip(c))
        )
      )
    )
  );
}

function kpiCard(href, value, label, hint) {
  return el(
    "a",
    { class: "kpi-card", href },
    el("span", { class: "kpi-value", "aria-hidden": "true", text: String(value) }),
    el("span", { class: "kpi-label" }, value, " ", label),
    el("span", { class: "kpi-hint", text: hint })
  );
}

export async function renderDashboard(container) {
  const [capas, complaints] = await Promise.all([api("/capas"), api("/complaints")]);

  const openCapas = capas.filter((c) => c.status !== "Closed");
  const awaiting = complaints.filter((c) => !c.mdr_decision);
  const needsReview = complaints.filter((c) => c.mdr_decision === "Needs Human Review");
  const reportable = complaints.filter((c) => c.mdr_decision === "Reportable");
  const urgent = urgentComplaints(complaints);

  container.replaceChildren(
    pageHeader(
      "Dashboard",
      "Quality system overview — implant traceability, CAPA workflow, and complaint / MDR status."
    ),
    urgentBanner(urgent, reportable.length),
    el(
      "section",
      { class: "kpi-grid", "aria-label": "Key metrics" },
      kpiCard("#/capas", openCapas.length, "open CAPAs", "CAPAs not yet Closed — view list"),
      kpiCard(
        "#/complaints?mdr_decision=Not+Yet+Evaluated",
        awaiting.length,
        "complaints awaiting evaluation",
        "No MDR decision recorded yet — view list"
      ),
      kpiCard(
        "#/complaints?mdr_decision=Needs+Human+Review",
        needsReview.length,
        "need human review",
        "Ambiguous complaints a reviewer must resolve — view list"
      )
    )
  );
}
