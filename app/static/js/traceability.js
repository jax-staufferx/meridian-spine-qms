// Traceability: backward trace (device → components → lots),
// forward trace (lot → components → devices → shipment), and browse lists.

import { alertBox, api, el, emptyState, fmtDate, pageHeader, tableWrap } from "./core.js";

export async function renderTraceability(container, params) {
  const [devices, lots] = await Promise.all([api("/devices"), api("/lots")]);

  // ---- Trace tools ----

  const backResults = el("div", { class: "trace-results" });
  const fwdResults = el("div", { class: "trace-results" });

  const serialInput = el("input", {
    id: "trace-serial",
    type: "text",
    list: "device-suggestions",
    autocomplete: "off",
    placeholder: "e.g. PS-2001",
  });
  const lotInput = el("input", {
    id: "trace-lot",
    type: "text",
    list: "lot-suggestions",
    autocomplete: "off",
    placeholder: "e.g. TI-2025-0101",
  });

  async function runTraceBack() {
    const serial = serialInput.value.trim();
    backResults.replaceChildren();
    if (!serial) {
      backResults.replaceChildren(el("p", { class: "help-text", text: "Enter a device serial number to trace." }));
      return;
    }
    try {
      const device = await api(`/devices/${encodeURIComponent(serial)}/trace-back`);
      backResults.replaceChildren(renderTraceBackTree(device));
    } catch (err) {
      backResults.replaceChildren(alertBox("error", err.message));
    }
  }

  async function runTraceForward() {
    const lotId = lotInput.value.trim();
    fwdResults.replaceChildren();
    if (!lotId) {
      fwdResults.replaceChildren(el("p", { class: "help-text", text: "Enter a raw material lot ID to trace." }));
      return;
    }
    try {
      const lot = await api(`/lots/${encodeURIComponent(lotId)}/trace-forward`);
      fwdResults.replaceChildren(renderTraceForwardTree(lot));
    } catch (err) {
      fwdResults.replaceChildren(alertBox("error", err.message));
    }
  }

  // ---- Browse lists ----

  const browseCache = { lots, devices };
  let currentTab = "lots";
  const browseBody = el("div", { class: "browse-body" });

  async function renderBrowseTable() {
    browseBody.replaceChildren(el("p", { class: "loading", text: "Loading…" }));
    if (!browseCache[currentTab]) {
      try {
        browseCache[currentTab] = await api(`/${currentTab}`);
      } catch (err) {
        browseBody.replaceChildren(alertBox("error", err.message));
        return;
      }
    }
    browseBody.replaceChildren(browseTable(currentTab, browseCache[currentTab]));
  }

  function selectTab(key) {
    currentTab = key;
    for (const [tabKey, btn] of tabButtons) {
      const active = tabKey === key;
      btn.setAttribute("aria-pressed", String(active));
    }
    renderBrowseTable();
  }

  const TABS = [
    { key: "lots", label: "Lots" },
    { key: "devices", label: "Devices" },
    { key: "components", label: "Components" },
    { key: "shipments", label: "Shipments" },
  ];
  const tabButtons = new Map();
  const tabGroup = el("div", { class: "tab-group", role: "group", "aria-label": "Browse record type" },
    TABS.map((tab) => {
      const btn = el("button", {
        class: "tab-btn",
        type: "button",
        "aria-pressed": String(tab.key === currentTab),
        onclick: () => selectTab(tab.key),
        text: tab.label,
      });
      tabButtons.set(tab.key, btn);
      return btn;
    })
  );

  container.replaceChildren(
    pageHeader("Traceability", "Raw materials → components → devices → shipments."),
    el(
      "div",
      { class: "trace-tools" },
      el(
        "section",
        { class: "card" },
        el("h2", { class: "card-title", text: "Trace a device (backward)" }),
        el("p", { class: "help-text", text: "Device serial number → its components → every raw material lot they draw from. Used to scope what went into a specific unit." }),
        el(
          "form",
          {
            class: "trace-inline-form",
            onsubmit: (e) => {
              e.preventDefault();
              runTraceBack();
            },
          },
          el("label", { for: "trace-serial" }, "Device serial number"),
          serialInput,
          el("button", { class: "btn btn-primary", type: "submit", text: "Trace back" })
        ),
        backResults
      ),
      el(
        "section",
        { class: "card" },
        el("h2", { class: "card-title", text: "Trace a lot (forward — recall blast radius)" }),
        el("p", { class: "help-text", text: "Raw material lot → every component made from it → each device → where it shipped. Used to scope a recall." }),
        el(
          "form",
          {
            class: "trace-inline-form",
            onsubmit: (e) => {
              e.preventDefault();
              runTraceForward();
            },
          },
          el("label", { for: "trace-lot" }, "Raw material lot ID"),
          lotInput,
          el("button", { class: "btn btn-primary", type: "submit", text: "Trace forward" })
        ),
        fwdResults
      )
    ),
    el(
      "section",
      {},
      el("h2", { class: "card-title", text: "Browse records" }),
      tabGroup,
      browseBody
    ),
    // Datalists for input suggestions
    el("datalist", { id: "device-suggestions" }, devices.map((d) => el("option", { value: d.serial_number }))),
    el("datalist", { id: "lot-suggestions" }, lots.map((l) => el("option", { value: l.lot_id })))
  );

  // Auto-run traces when navigated here from a linked record.
  const qSerial = params.get("serial");
  const qLot = params.get("lot");
  if (qSerial) {
    serialInput.value = qSerial;
    runTraceBack();
  }
  if (qLot) {
    lotInput.value = qLot;
    runTraceForward();
  }

  renderBrowseTable();
}

// ---- Backward trace tree: Device > Components > Lots ----

function renderTraceBackTree(device) {
  return el(
    "div",
    { class: "trace-tree" },
    el(
      "div",
      { class: "trace-node trace-node-device" },
      el(
        "div",
        { class: "trace-node-head" },
        el("span", { class: "trace-title", text: `Device ${device.serial_number}` }),
        el("span", { class: "chip", text: device.device_type }),
        el("span", { class: "chip", text: `DHR ${device.dhr_status}` })
      ),
      el(
        "p",
        { class: "trace-meta" },
        `Manufactured ${fmtDate(device.manufacture_date)} · `,
        device.shipment_id ? `Shipment ${device.shipment_id}` : "Not shipped"
      ),
      el(
        "div",
        { class: "trace-children" },
        device.components.map((comp) =>
          el(
            "div",
            { class: "trace-node trace-node-component" },
            el(
              "div",
              { class: "trace-node-head" },
              el("span", { class: "trace-subtitle", text: comp.component_id }),
              el("span", { class: "chip", text: comp.component_type }),
              el("span", { class: "trace-meta-inline", text: `Manufactured ${fmtDate(comp.manufactured_date)}` })
            ),
            el(
              "ul",
              { class: "chip-list" },
              comp.lots.map((lot) => lotChip(lot)),
              comp.lots.length === 0
                ? el("li", { class: "chip chip-muted", text: "No raw material lots recorded" })
                : null
            )
          )
        ),
        device.components.length === 0
          ? el("p", { class: "help-text", text: "No components recorded for this device." })
          : null
      )
    )
  );
}

function lotChip(lot) {
  return el(
    "li",
    {
      class: "chip chip-lot",
      title: `${lot.material_type} — ${lot.supplier_name}, received ${fmtDate(lot.received_date)}, cert ${lot.supplier_cert_number}`,
    },
    el("span", { class: "chip-strong", text: lot.lot_id }),
    lot.material_type
  );
}

// ---- Forward trace tree: Lot > Components > Devices > Shipment ----

function renderTraceForwardTree(lot) {
  const byDevice = new Map();
  const unassembled = [];
  for (const comp of lot.components) {
    if (comp.device) {
      if (!byDevice.has(comp.device.serial_number)) {
        byDevice.set(comp.device.serial_number, { device: comp.device, components: [] });
      }
      byDevice.get(comp.device.serial_number).components.push(comp);
    } else {
      unassembled.push(comp);
    }
  }

  const groups = [...byDevice.values()];
  const shippedCount = groups.filter((g) => g.device.shipment).length;

  const summary = el(
    "p",
    { class: "trace-summary" },
    el("strong", {}, `${groups.length} device${groups.length === 1 ? "" : "s"} affected`),
    ` (${shippedCount} shipped) from ${lot.components.length} component${lot.components.length === 1 ? "" : "s"}`,
    unassembled.length
      ? ` · ${unassembled.length} component${unassembled.length === 1 ? "" : "s"} not yet assembled into a device`
      : "",
    "."
  );

  return el(
    "div",
    { class: "trace-tree" },
    el(
      "div",
      { class: "trace-node trace-node-lot" },
      el(
        "div",
        { class: "trace-node-head" },
        el("span", { class: "trace-title", text: `Lot ${lot.lot_id}` }),
        el("span", { class: "chip", text: lot.material_type })
      ),
      el(
        "p",
        { class: "trace-meta" },
        `${lot.supplier_name} · Received ${fmtDate(lot.received_date)} · Cert ${lot.supplier_cert_number}`
      ),
      summary,
      el(
        "div",
        { class: "trace-children" },
        groups.map((group) => deviceCard(group)),
        unassembled.length
          ? el(
              "div",
              { class: "trace-node trace-node-component" },
              el(
                "div",
                { class: "trace-node-head" },
                el("span", { class: "trace-subtitle", text: "Unassembled components" }),
                el("span", { class: "trace-meta-inline", text: "not yet built into a device" })
              ),
              el(
                "ul",
                { class: "chip-list" },
                unassembled.map((comp) =>
                  el(
                    "li",
                    { class: "chip" },
                    el("span", { class: "chip-strong", text: comp.component_id }),
                    comp.component_type
                  )
                )
              )
            )
          : null,
        groups.length === 0 && unassembled.length === 0
          ? el("p", { class: "help-text", text: "No components recorded for this lot." })
          : null
      )
    )
  );
}

function deviceCard({ device, components }) {
  return el(
    "div",
    { class: "trace-node trace-node-device" },
    el(
      "div",
      { class: "trace-node-head" },
      el("span", { class: "trace-subtitle", text: `Device ${device.serial_number}` }),
      el("span", { class: "chip", text: device.device_type }),
      el("span", { class: "chip", text: `DHR ${device.dhr_status}` }),
      device.shipment
        ? el(
            "span",
            {
              class: "chip chip-ship",
              title: `Shipped ${fmtDate(device.shipment.ship_date)}`,
            },
            el("span", { class: "chip-strong", text: device.shipment.shipment_id }),
            ` → ${device.shipment.destination}`
          )
        : el("span", { class: "chip chip-muted", text: "Not shipped" })
    ),
    el(
      "ul",
      { class: "chip-list" },
      components.map((comp) =>
        el(
          "li",
          { class: "chip" },
          el("span", { class: "chip-strong", text: comp.component_id }),
          comp.component_type
        )
      )
    )
  );
}

// ---- Browse tables ----

function browseTable(tab, data) {
  if (!data.length) return emptyState(`No ${tab} records found.`);

  if (tab === "lots") {
    return tableWrap(
      ["Lot ID", "Material type", "Supplier", "Received", "Supplier cert #"],
      data.map((lot) => [
        el("a", { href: `#/traceability?lot=${encodeURIComponent(lot.lot_id)}`, text: lot.lot_id }),
        lot.material_type,
        lot.supplier_name,
        fmtDate(lot.received_date),
        lot.supplier_cert_number,
      ])
    );
  }
  if (tab === "devices") {
    return tableWrap(
      ["Serial number", "Device type", "Manufactured", "DHR status", "Shipment"],
      data.map((d) => [
        el("a", { href: `#/traceability?serial=${encodeURIComponent(d.serial_number)}`, text: d.serial_number }),
        d.device_type,
        fmtDate(d.manufacture_date),
        d.dhr_status,
        d.shipment_id || "—",
      ])
    );
  }
  if (tab === "components") {
    return tableWrap(
      ["Component ID", "Type", "Manufactured", "Built into device"],
      data.map((c) => [
        c.component_id,
        c.component_type,
        fmtDate(c.manufactured_date),
        c.device_id || "— (unassembled)",
      ])
    );
  }
  return tableWrap(
    ["Shipment ID", "Ship date", "Destination"],
    data.map((s) => [s.shipment_id, fmtDate(s.ship_date), s.destination])
  );
}
