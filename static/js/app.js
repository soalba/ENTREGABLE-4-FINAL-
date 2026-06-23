/* ===========================================================
   PLANO — app.js
   Lógica de frontend: navegación entre módulos, consumo de la
   API Django REST (filtros, predicción, estadísticas, carga CSV).
   Sin frameworks ni build step — JS vainilla.
   =========================================================== */

const API_BASE = "/api";

/* ---------------- Navegación entre módulos ---------------- */
const navButtons = document.querySelectorAll(".module-nav button");
const panels = document.querySelectorAll(".panel");

navButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    navButtons.forEach((b) => { b.classList.remove("active"); b.setAttribute("aria-selected", "false"); });
    panels.forEach((p) => p.classList.remove("active"));

    btn.classList.add("active");
    btn.setAttribute("aria-selected", "true");
    document.getElementById(`panel-${btn.dataset.panel}`).classList.add("active");

    if (btn.dataset.panel === "dashboard" && !dashboardCargado) cargarDashboard();
  });
});

/* ---------------- Utilidades ---------------- */
function fmtUSD(valor) {
  if (valor === null || valor === undefined || isNaN(valor)) return "—";
  return new Intl.NumberFormat("es-AR", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(valor);
}

function fmtNum(valor, decimales = 0) {
  if (valor === null || valor === undefined || isNaN(valor)) return "—";
  return new Intl.NumberFormat("es-AR", { maximumFractionDigits: decimales }).format(valor);
}

async function apiGet(path, params = {}) {
  const url = new URL(API_BASE + path, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (Array.isArray(v)) {
      v.forEach((val) => url.searchParams.append(k, val));
    } else if (v !== "" && v !== null && v !== undefined) {
      url.searchParams.append(k, v);
    }
  });
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Error ${resp.status} al consultar ${path}`);
  return resp.json();
}

async function apiPost(path, body) {
  const resp = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  if (!resp.ok) {
    const msg = data.error || JSON.stringify(data);
    throw new Error(msg);
  }
  return data;
}

/* ---------------- Carga inicial: lista de barrios ---------------- */
let barriosCache = [];

async function cargarBarrios() {
  try {
    const data = await apiGet("/barrios/");
    barriosCache = data;

    const selectores = [document.getElementById("f-barrio"), document.getElementById("e-barrio")];
    selectores.forEach((sel) => {
      data.forEach((b) => {
        const opt = document.createElement("option");
        opt.value = b.barrio;
        opt.textContent = `${b.barrio} (${b.cantidad})`;
        sel.appendChild(opt);
      });
    });

    const total = data.reduce((acc, b) => acc + b.cantidad, 0);
    document.getElementById("total-propiedades").textContent = `${fmtNum(total)}`;
  } catch (e) {
    console.error("No se pudieron cargar los barrios:", e);
  }
}

/* =================================================================
   MÓDULO 1 — BUSCADOR
   ================================================================= */
let paginaActual = 1;

function leerFiltros() {
  return {
    barrio: document.getElementById("f-barrio").value,
    precio_min: document.getElementById("f-precio-min").value,
    precio_max: document.getElementById("f-precio-max").value,
    ambientes_min: document.getElementById("f-amb-min").value,
    ambientes_max: document.getElementById("f-amb-max").value,
    banios_min: document.getElementById("f-banios").value,
    superficie_min: document.getElementById("f-sup-min").value,
    superficie_max: document.getElementById("f-sup-max").value,
    garage: document.getElementById("f-garage").checked || "",
    pileta: document.getElementById("f-pileta").checked || "",
    seguridad: document.getElementById("f-seguridad").checked || "",
    luminoso: document.getElementById("f-luminoso").checked || "",
    cerca_transporte: document.getElementById("f-transporte").checked || "",
    a_estrenar: document.getElementById("f-estrenar").checked || "",
    reciclado: document.getElementById("f-reciclado").checked || "",
    ordenar: document.getElementById("f-orden").value,
  };
}

function tarjetaPropiedad(p) {
  const amenities = [
    { on: p.amenity_garage, label: "Cochera" },
    { on: p.amenity_pool, label: "Pileta" },
    { on: p.amenity_security, label: "Seguridad" },
    { on: p.is_luminous, label: "Luminoso" },
    { on: p.near_transport, label: "Transporte" },
    { on: p.is_a_estrenar, label: "A estrenar" },
    { on: p.is_reciclado, label: "Reciclado" },
  ].filter((a) => a.on);

  const div = document.createElement("div");
  div.className = "card prop-card";
  div.innerHTML = `
    <span class="barrio-tag">${p.barrio || "Sin barrio"}</span>
    <div>
      <div class="precio">${fmtUSD(p.price)}</div>
      <div class="precio-m2">${p.price_m2 ? fmtNum(p.price_m2) + " USD/m²" : "Precio/m² no disponible"}</div>
    </div>
    <div class="prop-specs">
      <span>⌂ ${p.surface_total ?? "—"} m²</span>
      <span>${p.rooms ?? "—"} amb.</span>
      <span>${p.bathrooms ?? "—"} baño(s)</span>
    </div>
    ${amenities.length ? `<div class="prop-amenities">${amenities.map((a) => `<span class="chip on">${a.label}</span>`).join("")}</div>` : ""}
  `;
  return div;
}

async function buscarPropiedades(pagina = 1) {
  const lista = document.getElementById("lista-propiedades");
  const paginacion = document.getElementById("paginacion");
  lista.innerHTML = `<div class="estado-cargando">Buscando propiedades…</div>`;
  paginacion.innerHTML = "";

  try {
    const filtros = leerFiltros();
    const data = await apiGet("/propiedades/", { ...filtros, page: pagina });

    document.getElementById("resultados-num").textContent = fmtNum(data.count);

    if (data.results.length === 0) {
      lista.innerHTML = `<div class="estado-vacio">No encontramos propiedades con esos filtros.<br>Probá ampliar el rango de precio o sacar algún amenity.</div>`;
      return;
    }

    lista.innerHTML = "";
    data.results.forEach((p) => lista.appendChild(tarjetaPropiedad(p)));

    renderPaginacion(data, pagina);
    paginaActual = pagina;
  } catch (e) {
    lista.innerHTML = `<div class="estado-vacio">Ocurrió un error al buscar: ${e.message}</div>`;
  }
}

function renderPaginacion(data, pagina) {
  const cont = document.getElementById("paginacion");
  cont.innerHTML = "";

  if (!data.previous && !data.next) return;

  const btnPrev = document.createElement("button");
  btnPrev.className = "btn btn-secundario";
  btnPrev.textContent = "← Anterior";
  btnPrev.disabled = !data.previous;
  btnPrev.addEventListener("click", () => buscarPropiedades(pagina - 1));

  const btnNext = document.createElement("button");
  btnNext.className = "btn btn-secundario";
  btnNext.textContent = "Siguiente →";
  btnNext.disabled = !data.next;
  btnNext.addEventListener("click", () => buscarPropiedades(pagina + 1));

  cont.appendChild(btnPrev);
  cont.appendChild(btnNext);
}

document.getElementById("btn-aplicar-filtros").addEventListener("click", () => buscarPropiedades(1));
document.getElementById("f-orden").addEventListener("change", () => buscarPropiedades(1));

document.getElementById("btn-limpiar-filtros").addEventListener("click", () => {
  document.querySelectorAll("#panel-buscador input[type=number]").forEach((i) => (i.value = ""));
  document.querySelectorAll("#panel-buscador input[type=checkbox]").forEach((i) => (i.checked = false));
  document.getElementById("f-barrio").value = "";
  document.getElementById("f-banios").value = "";
  document.getElementById("f-orden").value = "";
  buscarPropiedades(1);
});

/* =================================================================
   MÓDULO 2 — ESTIMADOR DE PRECIO
   ================================================================= */
document.getElementById("form-estimador").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const cont = document.getElementById("resultado-prediccion");
  cont.innerHTML = `<p class="placeholder">Calculando estimación…</p>`;

  const payload = {
    barrio: document.getElementById("e-barrio").value,
    surface_total: parseFloat(document.getElementById("e-superficie").value),
    rooms: parseFloat(document.getElementById("e-ambientes").value),
    bathrooms: parseFloat(document.getElementById("e-banios").value),
    amenity_garage: document.getElementById("e-garage").checked,
    amenity_pool: document.getElementById("e-pileta").checked,
    amenity_security: document.getElementById("e-seguridad").checked,
    is_luminous: document.getElementById("e-luminoso").checked,
    near_transport: document.getElementById("e-transporte").checked,
    is_a_estrenar: document.getElementById("e-estrenar").checked,
    is_reciclado: document.getElementById("e-reciclado").checked,
  };

  if (!payload.barrio) {
    cont.innerHTML = `<p class="placeholder">Elegí un barrio para poder estimar el precio.</p>`;
    return;
  }

  try {
    const data = await apiPost("/predecir/", payload);
    cont.innerHTML = `
      <div class="resultado-numero">
        <div class="label">Precio estimado por m²</div>
        <div class="valor">${fmtNum(data.precio_estimado_m2)} <small>USD/m²</small></div>
      </div>
      <div class="resultado-detalle">
        <div>
          <div class="num">${fmtUSD(data.precio_total_estimado)}</div>
          <div class="lbl">Precio total est.</div>
        </div>
        <div>
          <div class="num">${payload.surface_total} m²</div>
          <div class="lbl">Superficie</div>
        </div>
        <div>
          <div class="num">${payload.barrio}</div>
          <div class="lbl">Barrio</div>
        </div>
      </div>
    `;
  } catch (e) {
    cont.innerHTML = `<p class="placeholder">No se pudo calcular la estimación.<br>${e.message}</p>`;
  }
});

/* =================================================================
   MÓDULO 3 — DASHBOARD / PANEL DE MERCADO
   ================================================================= */
let dashboardCargado = false;
let chartBarrios, chartImportancia, chartDistribucion;

const PALETA_GRAFICOS = {
  ink: "#10243E",
  inkSoft: "#34507A",
  brick: "#C1592A",
  ok: "#3E7A4D",
  line: "#C9BFA9",
};

async function cargarDashboard() {
  dashboardCargado = true;
  try {
    const data = await apiGet("/estadisticas/");

    document.getElementById("kpi-total").textContent = fmtNum(data.resumen_global.total_propiedades);
    document.getElementById("kpi-mediana").textContent = fmtNum(data.resumen_global.mediana_price_m2);
    document.getElementById("kpi-promedio").textContent = fmtNum(data.resumen_global.promedio_price_m2);
    document.getElementById("kpi-barrios").textContent = fmtNum(data.resumen_global.barrios_distintos);

    renderChartBarrios(data.precio_m2_por_barrio.slice(0, 15));
    renderChartImportancia(data.importancia_variables.slice(0, 10));
    renderChartDistribucion(data.distribucion_price_m2);
  } catch (e) {
    console.error("Error al cargar dashboard:", e);
  }
}

function renderChartBarrios(items) {
  const ctx = document.getElementById("chart-barrios");
  if (chartBarrios) chartBarrios.destroy();
  chartBarrios = new Chart(ctx, {
    type: "bar",
    data: {
      labels: items.map((i) => i.barrio),
      datasets: [{
        label: "USD/m² (mediana)",
        data: items.map((i) => i.mediana_usd_m2),
        backgroundColor: PALETA_GRAFICOS.ink,
        borderRadius: 2,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: PALETA_GRAFICOS.line } },
        y: { grid: { display: false } },
      },
    },
  });
}

function renderChartImportancia(items) {
  const ctx = document.getElementById("chart-importancia");
  if (chartImportancia) chartImportancia.destroy();
  const etiquetas = {
    barrio: "Barrio", surface_total: "Superficie", rooms: "Ambientes", bathrooms: "Baños",
    amenity_garage: "Cochera", amenity_pool: "Pileta", amenity_security: "Seguridad",
    is_luminous: "Luminoso", near_transport: "Cerca transporte", is_a_estrenar: "A estrenar",
    is_reciclado: "Reciclado",
  };
  chartImportancia = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: items.map((i) => etiquetas[i.variable] || i.variable),
      datasets: [{
        data: items.map((i) => i.importancia),
        backgroundColor: [
          PALETA_GRAFICOS.brick, PALETA_GRAFICOS.ink, PALETA_GRAFICOS.ok, PALETA_GRAFICOS.inkSoft,
          "#E0A87B", "#7C93B5", "#8FBF9B", "#D9CBAE", "#A8714B", "#5E7A9C",
        ],
        borderColor: "#FFFFFF",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } } },
    },
  });
}

function renderChartDistribucion(items) {
  const ctx = document.getElementById("chart-distribucion");
  if (chartDistribucion) chartDistribucion.destroy();
  chartDistribucion = new Chart(ctx, {
    type: "bar",
    data: {
      labels: items.map((i) => `${fmtNum(i.rango_min)}–${fmtNum(i.rango_max)}`),
      datasets: [{
        label: "Cantidad de propiedades",
        data: items.map((i) => i.frecuencia),
        backgroundColor: PALETA_GRAFICOS.brick,
        borderRadius: 2,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxRotation: 60, minRotation: 60, font: { size: 9 } }, grid: { display: false } },
        y: { grid: { color: PALETA_GRAFICOS.line } },
      },
    },
  });
}

/* =================================================================
   MÓDULO 4 — CARGA DE CSV
   ================================================================= */
const dropzone = document.getElementById("dropzone");
const inputCsv = document.getElementById("input-csv");
const archivoNombreEl = document.getElementById("archivo-nombre");
const btnSubirCsv = document.getElementById("btn-subir-csv");
let archivoSeleccionado = null;

dropzone.addEventListener("click", () => inputCsv.click());

dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files.length) seleccionarArchivo(e.dataTransfer.files[0]);
});

inputCsv.addEventListener("change", () => {
  if (inputCsv.files.length) seleccionarArchivo(inputCsv.files[0]);
});

function seleccionarArchivo(file) {
  if (!file.name.toLowerCase().endsWith(".csv")) {
    mostrarResultadoCarga("El archivo debe ser .csv", "error");
    return;
  }
  archivoSeleccionado = file;
  archivoNombreEl.textContent = file.name;
  btnSubirCsv.disabled = false;
}

function mostrarResultadoCarga(mensaje, tipo) {
  const el = document.getElementById("carga-resultado");
  el.className = `carga-resultado ${tipo}`;
  el.innerHTML = mensaje;
}

btnSubirCsv.addEventListener("click", async () => {
  if (!archivoSeleccionado) return;
  btnSubirCsv.disabled = true;
  btnSubirCsv.textContent = "Cargando…";

  const formData = new FormData();
  formData.append("archivo", archivoSeleccionado);

  try {
    const resp = await fetch(`${API_BASE}/cargar-csv/`, { method: "POST", body: formData });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Error desconocido al cargar el archivo.");

    let detalle = `✓ ${data.mensaje}`;
    if (data.filas_con_error > 0) {
      detalle += `<br>⚠ ${data.filas_con_error} filas con error (se omitieron).`;
    }
    mostrarResultadoCarga(detalle, "ok");

    // refrescar barrios/dashboard porque pueden sumarse propiedades/barrios nuevos
    await cargarBarrios();
    dashboardCargado = false;
  } catch (e) {
    mostrarResultadoCarga(`✗ ${e.message}`, "error");
  } finally {
    btnSubirCsv.disabled = false;
    btnSubirCsv.textContent = "Cargar archivo";
    archivoSeleccionado = null;
    archivoNombreEl.textContent = "";
    inputCsv.value = "";
  }
});

/* ---------------- Init ---------------- */
cargarBarrios();
buscarPropiedades(1);
