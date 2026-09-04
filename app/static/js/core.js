// Shared helpers: DOM builder, API client, date formatting, and status badges.

export const CAPA_STATUSES = [
  "Open",
  "Investigation",
  "Root Cause",
  "Corrective Action",
  "Verification",
  "Closed",
];

export const SERIOUS_INJURY_DEFINITION =
  "A serious injury is one that is life-threatening, results in permanent impairment " +
  "of a body function or permanent damage to a body structure, or necessitates medical " +
  "or surgical intervention to preclude permanent impairment or damage.";

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else {
      node.setAttribute(key, value === true ? "" : String(value));
    }
  }
  append(node, children);
  return node;
}

function append(node, children) {
  for (const child of children) {
    if (child === null || child === undefined || child === false) continue;
    if (Array.isArray(child)) append(node, child);
    else if (child instanceof Node) node.appendChild(child);
    else node.appendChild(document.createTextNode(String(child)));
  }
}

// ---- API client ----

export async function api(path, { method = "GET", body } = {}) {
  const options = { method };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  const res = await fetch(path, options);
  let data = null;
  try {
    data = await res.json();
  } catch (_) {
    /* empty body */
  }
  if (!res.ok) {
    const detail = data && data.detail !== undefined ? data.detail : `Request failed (${res.status})`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

// ---- Formatting ----

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function fmtDate(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}

export function fmtDateTime(iso) {
  if (!iso) return "—";
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso;
  const pad = (n) => String(n).padStart(2, "0");
  return `${MONTHS[dt.getMonth()]} ${dt.getDate()}, ${dt.getFullYear()}, ${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
}

export function todayISO() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function daysUntil(dateIso) {
  const due = new Date(`${dateIso.slice(0, 10)}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((due - today) / 86400000);
}

// ---- Badges ----

const CAPA_STAGE_CLASS = {
  "Open": "stage-open",
  "Investigation": "stage-investigation",
  "Root Cause": "stage-rootcause",
  "Corrective Action": "stage-corrective",
  "Verification": "stage-verification",
  "Closed": "stage-closed",
};

/** CAPA status badge: color + stage number + status text (never color alone). */
export function capaBadge(status) {
  const stage = CAPA_STATUSES.indexOf(status) + 1;
  return el(
    "span",
    { class: `badge capa-badge ${CAPA_STAGE_CLASS[status] || ""}` },
    el("span", { class: "badge-num", "aria-hidden": "true", text: String(stage) }),
    status
  );
}

const MDR_BADGE_STYLE = {
  "Reportable": ["mdr-reportable", "⚠"],
  "Not Reportable": ["mdr-notreportable", "✓"],
  "Needs Human Review": ["mdr-review", "?"],
};

/** MDR decision badge: color + icon + decision text (never color alone). */
export function mdrBadge(decision) {
  if (!decision) {
    return el(
      "span",
      { class: "badge mdr-badge mdr-unevaluated" },
      el("span", { class: "badge-icon", "aria-hidden": "true", text: "–" }),
      "Not Yet Evaluated"
    );
  }
  const [cls, icon] = MDR_BADGE_STYLE[decision] || ["mdr-unevaluated", "•"];
  return el(
    "span",
    { class: `badge mdr-badge ${cls}` },
    el("span", { class: "badge-icon", "aria-hidden": "true", text: icon }),
    decision
  );
}

/** Days-remaining chip for Reportable complaints; urgent styling at <= 5 days. */
export function dueChip(complaint, { urgentWindowDays = 5 } = {}) {
  if (complaint.mdr_decision !== "Reportable" || !complaint.mdr_due_date) return null;
  const days = daysUntil(complaint.mdr_due_date);
  const urgent = days <= urgentWindowDays;
  const label =
    days < 0
      ? `Overdue by ${-days} day${days === -1 ? "" : "s"}`
      : days === 0
        ? "Due today"
        : `Due in ${days} day${days === 1 ? "" : "s"}`;
  return el("span", { class: `due-chip ${urgent ? "due-chip-urgent" : ""}`, text: label });
}

// ---- Shared UI pieces ----

export function alertBox(kind, message) {
  return el("div", { class: `alert alert-${kind}`, role: "alert" }, message);
}

export function emptyState(message) {
  return el("p", { class: "empty-state", text: message });
}

export function pageHeader(title, lede, ...actions) {
  return el(
    "div",
    { class: "page-header" },
    el(
      "div",
      {},
      el("h1", { class: "page-title", text: title }),
      lede ? el("p", { class: "page-lede", text: lede }) : null
    ),
    actions.length ? el("div", { class: "page-actions" }, actions) : null
  );
}

export function linkBtn(href, label, kind = "primary") {
  return el("a", { class: `btn btn-${kind}`, href, text: label });
}

export function tableWrap(headers, rows) {
  return el(
    "div",
    { class: "table-wrap" },
    el(
      "table",
      {},
      el("thead", {}, el("tr", {}, headers.map((h) => el("th", { scope: "col", text: h })))),
      el("tbody", {}, rows.map((cells) => el("tr", {}, cells.map((c) => el("td", {}, c)))))
    )
  );
}
