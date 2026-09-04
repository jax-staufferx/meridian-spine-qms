// Hash-based router: #/dashboard, #/traceability, #/capas[...], #/complaints[...]

import { alertBox, el } from "./core.js";
import { renderDashboard } from "./dashboard.js";
import { renderTraceability } from "./traceability.js";
import { renderCapaList, renderCapaNew, renderCapaDetail } from "./capa.js";
import {
  renderComplaintList,
  renderComplaintNew,
  renderComplaintDetail,
} from "./complaints.js";

function parseHash() {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const [path, query] = raw.split("?");
  const parts = path.split("/").filter(Boolean);
  return { parts, params: new URLSearchParams(query || "") };
}

function setActiveNav(section) {
  document.querySelectorAll(".nav-list a").forEach((a) => {
    if (a.dataset.nav === section) {
      a.setAttribute("aria-current", "page");
      a.classList.add("active");
    } else {
      a.removeAttribute("aria-current");
      a.classList.remove("active");
    }
  });
}

async function render() {
  const main = document.getElementById("main");
  const { parts, params } = parseHash();
  const section = parts[0] || "dashboard";
  setActiveNav(section);
  main.replaceChildren(el("p", { class: "loading", text: "Loading…" }));
  window.scrollTo(0, 0);
  try {
    if (section === "dashboard") {
      await renderDashboard(main);
    } else if (section === "traceability") {
      await renderTraceability(main, params);
    } else if (section === "capas") {
      if (parts[1] === "new") {
        await renderCapaNew(main);
      } else if (parts[1] && Number.isInteger(Number(parts[1]))) {
        await renderCapaDetail(main, Number(parts[1]));
      } else {
        await renderCapaList(main, params.get("status"));
      }
    } else if (section === "complaints") {
      if (parts[1] === "new") {
        await renderComplaintNew(main);
      } else if (parts[1] && Number.isInteger(Number(parts[1]))) {
        await renderComplaintDetail(main, Number(parts[1]));
      } else {
        await renderComplaintList(main, params.get("mdr_decision"));
      }
    } else {
      main.replaceChildren(alertBox("error", `Page not found: /${parts.join("/")}`));
    }
  } catch (err) {
    main.replaceChildren(alertBox("error", err.message || "Something went wrong."));
  }
}

window.addEventListener("hashchange", render);
render();
