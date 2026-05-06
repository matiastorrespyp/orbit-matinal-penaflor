/* ORBIT — Main app shell */
const { useState } = React;

function Sidebar({ active, setActive, alertasCount }){
  const items = [
    {id:"dashboard", label:"Dashboard", icon: Ic.dashboard, group:"Gerencia"},
    {id:"avance", label:"Avance Objetivos", icon: Ic.trend},
    {id:"planificacion", label:"Planificación Matinal", icon: Ic.plan, badge: 1},
    {id:"vendedores", label:"Vendedores", icon: Ic.users},
    {id:"clientes", label:"Clientes Críticos", icon: Ic.store},
    {id:"titulares", label:"11 Titulares", icon: Ic.flame},
    {id:"segmentos", label:"Segmentos", icon: Ic.flag},
    {id:"alertas", label:"Alertas", icon: Ic.alert, badge: alertasCount},
    {id:"vendedor", label:"App del Vendedor", icon: Ic.zap, group:"Mobile"},
  ];
  let lastGroup = null;
  return React.createElement("aside",{className:"sidebar"},
    React.createElement("div",{className:"brand"},
      React.createElement("div",{className:"brand-mark"},
        React.createElement("img",{src:"assets/orbit-mark.png",alt:"Orbit"})),
      React.createElement("div",{className:"brand-text"},
        React.createElement("span",{className:"b1"}, "ORBIT"),
        React.createElement("span",{className:"b2"}, "Peñaflor · PAV"))
    ),
    items.map(it=>{
      const groupHeader = it.group && it.group!==lastGroup ? React.createElement("div",{key:"g_"+it.id,className:"nav-section-title"}, it.group) : null;
      lastGroup = it.group || lastGroup;
      return React.createElement(React.Fragment,{key:it.id},
        groupHeader,
        React.createElement("div",{
          className:"nav-item"+(active===it.id?" active":""),
          onClick:()=>setActive(it.id)
        },
          React.createElement(it.icon,null),
          React.createElement("span",null, it.label),
          it.badge ? React.createElement("span",{className:"badge"}, it.badge) : null
        )
      );
    }),
    React.createElement("div",{className:"sidebar-footer"},
      React.createElement("div",{className:"avatar"}, "SV"),
      React.createElement("div",{className:"user-meta"},
        React.createElement("b",null, "Supervisor"),
        React.createElement("span",null, "Supervisor PyP"))
    )
  );
}

function Topbar({ active, data, dia, setDia, vendedor, setVendedor, onSendMatinal }){
  const titles = {
    dashboard:["Dashboard Ejecutivo","Resumen general · matinal"],
    avance:["Avance de Objetivos","Cumplimiento mensual"],
    planificacion:["Planificación Matinal","Revisión y aprobación"],
    vendedores:["Vendedores Peñaflor","Equipo activo"],
    clientes:["Clientes Críticos","Foco operativo del día"],
    titulares:["11 Titulares","Cobertura por marca"],
    segmentos:["Segmentos","Cobertura Tradicional / AS / On Premise"],
    alertas:["Alertas Inteligentes","Copiloto comercial"],
    vendedor:["App del Vendedor","Vista mobile · vendedor"],
  };
  const [t, sub] = titles[active] || ["",""];
  return React.createElement("header",{className:"topbar"},
    React.createElement("div",{className:"topbar-title"},
      React.createElement("span",{className:"crumb"}, "ORBIT"),
      React.createElement("span",{style:{color:"var(--text-3)"}}, "/"),
      React.createElement("span",null, t),
      React.createElement("span",{className:"live"}, "EN VIVO · "+data.lastSync)
    ),
    React.createElement("div",{className:"topbar-spacer"}),
    React.createElement("div",{className:"topbar-actions"},
      React.createElement("div",{className:"day-selector"},
        data.diasVisita.map(d=>React.createElement("button",{
          key:d, className:dia===d?"active":"", onClick:()=>setDia(d)
        }, d))
      ),
      React.createElement("select",{className:"select",value:vendedor,onChange:e=>setVendedor(e.target.value)},
        React.createElement("option",{value:""},"Todos los vendedores"),
        data.vendedores.map(v=>React.createElement("option",{key:v.id,value:v.id}, v.nombre))
      ),
      React.createElement("button",{className:"btn btn-ghost btn-icon",title:"Actualizar datos"},
        React.createElement(Ic.refresh,{size:15})),
      React.createElement("button",{className:"btn btn-ghost"},
        React.createElement(Ic.download,{size:14}),"Exportar PDF"),
      React.createElement("button",{className:"btn btn-primary",onClick:onSendMatinal},
        React.createElement(Ic.send,{size:14}),"Enviar planificación")
    )
  );
}

function App(){
  const data = window.ORBIT_DATA;
  const [active, setActive] = useState("dashboard");
  const [dia, setDia] = useState(data.diaActivo);
  const [vendedor, setVendedor] = useState("");
  const [editPlan, setEditPlan] = useState(null);

  const screen = ()=>{
    switch(active){
      case "dashboard": return React.createElement(ScreenDashboard,{data, vendedorFiltro:vendedor});
      case "avance": return React.createElement(ScreenAvance,{data});
      case "planificacion": return React.createElement(ScreenPlanificacion,{data, openEdit:setEditPlan});
      case "vendedores": return React.createElement(ScreenVendedores,{data});
      case "clientes": return React.createElement(ScreenClientes,{data});
      case "titulares": return React.createElement(Screen11T,{data});
      case "segmentos": return React.createElement(ScreenSegmentos,{data});
      case "alertas": return React.createElement(ScreenAlertas,{data});
      case "vendedor": return React.createElement(ScreenVendedorMobile,{data});
      default: return null;
    }
  };

  if(active==="vendedor"){
    return React.createElement("div",{className:"app"},
      React.createElement(Sidebar,{active,setActive,alertasCount:data.alertas.filter(a=>a.prioridad==="alta").length}),
      React.createElement("main",{className:"main"},
        React.createElement(Topbar,{active,data,dia,setDia,vendedor,setVendedor}),
        React.createElement("div",{className:"page", style:{padding:0,background:"#06080B"}},
          screen()
        )
      )
    );
  }

  const diaNames = {LU:"Lunes",MA:"Martes",MI:"Miércoles",JU:"Jueves",VI:"Viernes",SA:"Sábado"};
  const fechaObj = (function(){
    var d = new Date((data.fechaCorta||"") + "T12:00:00");
    d.setDate(d.getDate() + 1);
    return String(d.getDate()).padStart(2,"0") + "/" + String(d.getMonth()+1).padStart(2,"0");
  })();
  const titles = {
    dashboard:["Reunión matinal · " + (diaNames[data.diaActivo]||data.diaActivo) + " " + fechaObj,"Equipo Peñaflor · 7 vendedores activos"],
    avance:["Avance contra objetivo","Cumplimiento mensual y proyección al cierre"],
    planificacion:["Planificación de la matinal","Revisar, ajustar y aprobar el plan de cada vendedor"],
    vendedores:["Vendedores Peñaflor","Vista 360° por vendedor"],
    clientes:["Clientes críticos del día","Acciones priorizadas para la jornada"],
    titulares:["11 Titulares · Peñaflor","Cobertura por marca y por segmento"],
    segmentos:["Cobertura por segmento","Tradicional · Autoservicio · On Premise"],
    alertas:["Alertas comerciales","Copiloto Orbit · prioridades del día"],
  };
  const [pt, ps] = titles[active] || ["",""];

  return React.createElement("div",{className:"app"},
    React.createElement(Sidebar,{active,setActive,alertasCount:data.alertas.filter(a=>a.prioridad==="alta").length}),
    React.createElement("main",{className:"main"},
      React.createElement(Topbar,{active,data,dia,setDia,vendedor,setVendedor}),
      React.createElement("div",{className:"page"},
        React.createElement("div",{className:"page-header"},
          React.createElement("div",null,
            React.createElement("h1",{className:"page-title"}, pt),
            React.createElement("p",{className:"page-sub"}, ps)
          ),
          React.createElement("div",{className:"row",style:{gap:10}},
            React.createElement("span",{className:"chip"}, data.fecha),
            React.createElement("span",{className:"chip ok"}, "Día "+dia)
          )
        ),
        screen()
      )
    ),
    editPlan && React.createElement(PlanEditModal,{plan:editPlan, data, onClose:()=>setEditPlan(null)})
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(App));
