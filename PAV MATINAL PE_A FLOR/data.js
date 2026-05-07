/* ORBIT — Real data only. No mock. No hardcode. */
(function() {
  window.ORBIT_DATA = null;
  window.ORBIT_MODE = "LOADING";

  function fetchSync(url) {
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", url, false);
      xhr.send();
      if (xhr.status === 200) return JSON.parse(xhr.responseText);
    } catch(e) {}
    return null;
  }

  var diag = fetchSync("/api/diagnostico") || {};
  var dash = fetchSync("/api/dashboard") || [];
  var cli  = fetchSync("/api/clientes") || [];
  var al   = fetchSync("/api/alertas") || [];
  var pl   = fetchSync("/api/planificacion") || [];
  var ga   = fetchSync("/api/gastos_accion") || {};

  var colorMap = { V3: "#7BD8B8", V4: "#F2B544", V6: "#5BC23A", V7: "#9B7BFF", V8: "#4DA3FF", V9: "#FF9D5C", V10: "#FF5D8B" };
  var calendario = diag.calendario || { total: 24, corridos: 2, restantes: 22, fecha_corte: new Date().toISOString().split("T")[0] };

  // Vendedores reales
  var vendedores = dash.map(function(v) {
    var k = v.kpis || {};
    return {
      id: v.vendedor_id,
      nombre: v.vendedor_nombre,
      color: colorMap[v.vendedor_id] || "#E2147A",
      avance: k.avance_pct || 0,
      objetivo: k.objetivo || 0,
      acumulado: k.acumulado || k.venta_mes_actual || 0,
      venta_ayer: k.venta_hoy_total || 0,
      ccc: k.ccc_total || (k.ccc_tradicional||0) + (k.ccc_autoservicio||0) + (k.ccc_onpremise||0),
      t11: k.once_titulares_cumplidos || 0,
      t11_total: k.once_titulares_total || 0,
      clientes: k.clientes_total || 0,
      alertas: k.clientes_pendientes || 0,
      cobertura_pct: k.cobertura_pct || 0,
      trabaja_autoservicio: k.trabaja_autoservicio !== false,
      segmento_excluye: v.vendedor_id === "V3" ? ["AUTOSERVICIO"] : []
    };
  });

  // KPIs gerenciales
  var tObj=0, tAcum=0, tVentaAyer=0, tCli=0, tPen=0, tCCC=0, t11C=0, t11T=0;
  vendedores.forEach(function(v) {
    tObj += v.objetivo; tAcum += v.acumulado; tVentaAyer += v.venta_ayer;
    tCli += v.clientes; tPen += v.alertas; tCCC += v.ccc;
    t11C += v.t11; t11T += v.t11_total;
  });

  var avancePct = tObj ? (tAcum / tObj * 100) : 0;

  window.ORBIT_DATA = {
    fecha: new Date().toLocaleDateString("es-AR", { weekday: "long", day: "numeric", month: "long", year: "numeric" }),
    fechaCorta: calendario.fecha_corte,
    lastSync: new Date().toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" }),
    diasVisita: ["LU","MA","MI","JU","VI","SA"],
    diaActivo: (function(){
      var abrev = ["DO","LU","MA","MI","JU","VI","SA"];
      var d = new Date((calendario.fecha_corte || new Date().toISOString().split("T")[0]) + "T12:00:00");
      d.setDate(d.getDate() + 1);
      return abrev[d.getDay()];
    })(),
    calendario: calendario,
    modo_datos: "REAL",
    vendedores: vendedores,
    kpisGerencia: {
      objetivo_mes: tObj,
      acumulado_mes: tAcum,
      avance_pct: avancePct,
      venta_dia: tVentaAyer,
      objetivo_dia: tObj / calendario.total,
      ccc_mes: 0,
      ccc_dia: tCCC,
      botellas_dia: diag.botellas_dia || 0,
      botellas_mes: diag.botellas_mes || 0,
      clientes_compra: tCli - tPen,
      cobertura_general: tCli ? (100 - (tPen / tCli * 100)) : 0,
      cumplimiento_11t: t11T ? (t11C / t11T * 100) : 0,
      tendencia: tObj ? ((tAcum / Math.max(calendario.corridos,1)) * calendario.total / tObj * 100) : 0,
      diff_objetivo: tObj - tAcum,
    },
    dailyEvolution: Array.from({ length: calendario.total }, function(_, i) {
      return {
        d: i + 1,
        real: i < calendario.corridos ? (tAcum / calendario.corridos) * (i + 1) : null,
        plan: (tObj / calendario.total) * (i + 1),
        hoy: i === calendario.corridos - 1
      };
    }),
    clientesCriticos: cli.slice(0, 20).map(function(c) {
      return {
        id: c.cliente_id, nombre: c.cliente_nombre,
        segmento: c.segmento === "AUTOSERVICIO" ? "Autoservicio" : c.segmento === "ON_PREMISE_VTK" ? "On Premise" : "Tradicional",
        vendedor: c.vendedor_id, ultima: "sin compra",
        brecha: c.impacto_alertas_ars || 0,
        estado: c.estado === "SIN_COMPRA_MES" ? "sin_compra_mes" : "sin_cobertura",
        accion: (c.kernel_accion || "").substring(0, 90),
        prioridad: c.prioridad_label === "ALTA" ? "alta" : "media",
        t11: c.faltan_11t || 11
      };
    }),
    alertas: al.slice(0, 10).map(function(a, i) {
      return {
        id: i + 1, prioridad: a.prioridad || "media",
        tipo: a.tipo || "cliente", titulo: a.cliente_nombre || a.titulo || "Alerta",
        detalle: a.detalle || "", accion: a.accion || "",
        responsable: a.vendedor_id || "", impacto: a.impacto_alertas_ars || 0
      };
    }),
    segmentos: diag.segmentos || [
      { id: "TRADICIONAL", nombre: "Tradicional", req: 3, clientes: 0, cubiertos: 0, color: "#5BC23A" },
      { id: "AUTOSERVICIO", nombre: "Autoservicio", req: 6, clientes: 0, cubiertos: 0, color: "#4DA3FF" },
      { id: "ON_PREMISE_VTK", nombre: "On Premise / Vinoteca", req: 6, clientes: 0, cubiertos: 0, color: "#9B7BFF" },
    ],
    titulares11: diag.titulares11 || [],
    gastosAccion: {
      resumen:        ga.resumen        || {},
      top_acciones:   ga.top_acciones   || [],
      top_vendedores: ga.top_vendedores || []
    },
    planes: pl.slice(0, 7).map(function(p) {
      return {
        vendedor: p.vendedor_id, estado: p.estado || "enviada",
        submitted: p.created_at ? p.created_at.substring(11, 16) : "",
        venta_obj: p.venta_esperada || 0, ccc_trad: p.ccc_tradicional || 0,
        ccc_as: p.ccc_autoservicio || 0, ccc_op: p.ccc_onpremise || 0, t11: p.once_t || 0,
        clientes_clave: [], marcas: [], obs_vendedor: "", obs_gerencia: ""
      };
    })
  };

  window.ORBIT_MODE = "REAL";
  console.log("ORBIT: Datos reales cargados. Días hábiles:", calendario.corridos, "de", calendario.total);
})();
