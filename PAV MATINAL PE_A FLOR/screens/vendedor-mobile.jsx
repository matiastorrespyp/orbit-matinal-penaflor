/* ORBIT — Screen Vendedor (mobile mockup) */
function ScreenVendedorMobile({ data }){
  const v = data.vendedores.find(x=>x.id==="V10"); // Demo: Milagros
  const plan = data.planes.find(p=>p.vendedor===v.id);
  const proy = (v.acumulado/19)*30;
  const proyPct = (proy/v.objetivo)*100;
  const falta = v.objetivo - v.acumulado;

  return React.createElement("div",{className:"phone-stage"},
    React.createElement("div",{className:"row",style:{gap:30,alignItems:"flex-start"}},

      // Phone 1: Home
      React.createElement("div",{className:"phone"},
        React.createElement("div",{className:"phone-notch"}),
        React.createElement("div",{className:"phone-screen"},
          React.createElement("div",{className:"phone-bar"},
            React.createElement("span",null,"7:14"),
            React.createElement("span",{className:"row",style:{gap:6,fontSize:11}},
              React.createElement("span",null,"5G"),
              React.createElement("span",null,"●●●"))
          ),
          React.createElement("div",{style:{padding:"8px 22px 12px",display:"flex",flexDirection:"column",gap:14,overflow:"auto"}},
            // Header
            React.createElement("div",{className:"row between"},
              React.createElement("div",null,
                React.createElement("div",{className:"muted",style:{fontSize:11,letterSpacing:1.2,textTransform:"uppercase"}}, "Hola "+v.nombre.split(" ")[0]),
                React.createElement("div",{className:"f-display",style:{fontSize:20,fontWeight:700,marginTop:2}}, "Buen día ☀")
              ),
              React.createElement("div",{className:"row",style:{gap:8}},
                React.createElement("div",{className:"btn-icon btn btn-ghost",style:{position:"relative"}},
                  React.createElement(Ic.bell,{size:14}),
                  React.createElement("span",{style:{position:"absolute",top:5,right:5,width:7,height:7,borderRadius:4,background:"var(--bad)"}})),
                React.createElement(VDot,{v,size:34})
              )
            ),
            // Mensaje gerencia
            plan?.obs_gerencia && React.createElement("div",{style:{
              padding:"12px 14px",borderRadius:14,
              background:"linear-gradient(135deg,rgba(155,123,255,.18),rgba(155,123,255,.06))",
              border:"1px solid rgba(155,123,255,.3)"
            }},
              React.createElement("div",{className:"row",style:{gap:6,marginBottom:5}},
                React.createElement(Ic.zap,{size:13}),
                React.createElement("b",{style:{fontSize:11,letterSpacing:1.2,textTransform:"uppercase",color:"var(--violet)"}}, "Mensaje de gerencia")),
              React.createElement("div",{style:{fontSize:13,lineHeight:1.5}}, plan.obs_gerencia)
            ),
            // Donut grande objetivo
            React.createElement("div",{style:{
              padding:18,borderRadius:18,
              background:"linear-gradient(135deg,rgba(91,194,58,.14),rgba(91,194,58,.02))",
              border:"1px solid rgba(91,194,58,.25)",
              display:"flex",gap:16,alignItems:"center"
            }},
              React.createElement(Donut,{value:v.avance,size:118,stroke:11,label:v.avance.toFixed(0)+"%",subLabel:"Mes"}),
              React.createElement("div",{style:{flex:1}},
                React.createElement("div",{className:"muted",style:{fontSize:10,letterSpacing:1.2,textTransform:"uppercase"}}, "Te falta para el objetivo"),
                React.createElement("div",{className:"f-display tnum",style:{fontSize:22,fontWeight:700,marginTop:4}}, fmtMoney(falta)),
                React.createElement("div",{className:"row",style:{gap:6,marginTop:8,fontSize:11}},
                  React.createElement("span",{className:"chip warn"}, "Proy. "+proyPct.toFixed(0)+"%")),
                React.createElement("div",{className:"muted",style:{fontSize:11,marginTop:8,lineHeight:1.4}}, "Si seguís este ritmo cerrás en "+fmtMoney(proy))
              )
            ),

            // Plan del día
            React.createElement("div",null,
              React.createElement("div",{className:"row between",style:{marginBottom:8}},
                React.createElement("b",{style:{fontSize:13}}, "Plan de hoy · MA"),
                React.createElement(StatusPill,{status:plan.estado})
              ),
              React.createElement("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}},
                [
                  {l:"VENTA OBJ", v: fmtMoney(plan.venta_obj)},
                  {l:"CCC TRAD", v: plan.ccc_trad},
                  {l:"CCC AS", v: plan.ccc_as},
                  {l:"11T", v: plan.t11},
                ].map((m,i)=>React.createElement("div",{key:i,style:{
                  padding:"10px 12px",background:"#0B0E13",borderRadius:10,
                  boxShadow:"inset 0 0 0 1px var(--hairline)"
                }},
                  React.createElement("div",{className:"muted",style:{fontSize:9,letterSpacing:1.2,textTransform:"uppercase"}}, m.l),
                  React.createElement("div",{className:"f-display tnum",style:{fontSize:17,fontWeight:700,marginTop:3}}, m.v)
                ))
              )
            ),

            // Tip de acción
            React.createElement("div",{style:{
              padding:"12px 14px",borderRadius:14,
              background:"rgba(91,194,58,.08)",border:"1px solid rgba(91,194,58,.25)"
            }},
              React.createElement("div",{className:"row",style:{gap:6,marginBottom:5}},
                React.createElement(Ic.target,{size:13}),
                React.createElement("b",{style:{fontSize:11,letterSpacing:1.2,textTransform:"uppercase",color:"var(--ok)"}}, "Foco del día")),
              React.createElement("div",{style:{fontSize:13,lineHeight:1.5}}, "Recuperá a Hector Hernandez y Zheng Huijuan: cayeron de compra. Sumá Alma Mora + Trapiche Reserva al combo de visita.")
            ),

            // Acciones
            React.createElement("div",{className:"row",style:{gap:8}},
              React.createElement("button",{className:"btn btn-primary",style:{flex:1,justifyContent:"center"}},
                React.createElement(Ic.plan,{size:14})," Mi planificación"),
              React.createElement("button",{className:"btn",style:{flex:1,justifyContent:"center"}},
                React.createElement(Ic.users,{size:14})," Clientes")
            )
          )
        )
      ),

      // Phone 2: Planificación form
      React.createElement("div",{className:"phone"},
        React.createElement("div",{className:"phone-notch"}),
        React.createElement("div",{className:"phone-screen"},
          React.createElement("div",{className:"phone-bar"},
            React.createElement("span",null,"7:18"),
            React.createElement("span",{style:{fontSize:11}},"●●●")
          ),
          React.createElement("div",{style:{padding:"8px 22px 12px",display:"flex",flexDirection:"column",gap:12,overflow:"auto"}},
            React.createElement("div",{className:"row between"},
              React.createElement("div",null,
                React.createElement("div",{className:"muted",style:{fontSize:11,letterSpacing:1.2,textTransform:"uppercase"}}, "Mi plan · Lunes"),
                React.createElement("div",{className:"f-display",style:{fontSize:18,fontWeight:700,marginTop:2}}, "Planificación")),
              React.createElement(StatusPill,{status:"modificada"})
            ),

            // Diff banner
            React.createElement("div",{style:{
              padding:"10px 12px",borderRadius:12,
              background:"rgba(155,123,255,.10)",border:"1px solid rgba(155,123,255,.3)",
              fontSize:12,lineHeight:1.4
            }},
              React.createElement("b",{style:{color:"var(--violet)"}}, "Gerencia ajustó tu plan: "),
              "subió CCC AS a 5 y agregó Finca Las Moras."),

            // Form fields
            React.createElement("div",{className:"field"},
              React.createElement("label",null, "Día de visita"),
              React.createElement("div",{className:"day-selector",style:{width:"100%",justifyContent:"space-between"}},
                ["LU","MA","MI","JU","VI","SA"].map(d=>React.createElement("button",{key:d,className:d==="LU"?"active":""},d))
              )
            ),
            React.createElement("div",{className:"field"},
              React.createElement("label",null, "Venta objetivo del día"),
              React.createElement("input",{className:"input tnum",defaultValue:"$3.100.000"})
            ),
            React.createElement("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}},
              React.createElement("div",{className:"field"},
                React.createElement("label",null, "CCC Tradic."),
                React.createElement("input",{className:"input tnum",defaultValue:"7"})),
              React.createElement("div",{className:"field"},
                React.createElement("label",null, "CCC AS"),
                React.createElement("input",{className:"input tnum",defaultValue:"5",style:{borderColor:"rgba(155,123,255,.4)"}})),
            ),
            React.createElement("div",{className:"field"},
              React.createElement("label",null, "11 Titulares comprometidos"),
              React.createElement("input",{className:"input tnum",defaultValue:"11"})
            ),
            React.createElement("div",{className:"field"},
              React.createElement("label",null, "Marcas prioritarias"),
              React.createElement("div",{className:"row",style:{gap:6,flexWrap:"wrap"}},
                ["Alma Mora","Trapiche Reserva","Finca Las Moras"].map((m,i)=>
                  React.createElement("span",{key:i,className:"chip"+(m==="Finca Las Moras"?" violet":"")}, m,
                    React.createElement(Ic.x,{size:11}))),
                React.createElement("button",{className:"chip",style:{cursor:"pointer"}}, "+ Agregar"))
            ),
            React.createElement("div",{className:"field"},
              React.createElement("label",null, "Observaciones"),
              React.createElement("textarea",{className:"input",defaultValue:"Recupero Hector y Zheng (caída de compra)."})
            ),
            React.createElement("button",{className:"btn btn-primary",style:{justifyContent:"center"}},
              React.createElement(Ic.send,{size:14})," Enviar a la matinal")
          )
        )
      ),

      // Phone 3: Clientes prioritarios
      React.createElement("div",{className:"phone"},
        React.createElement("div",{className:"phone-notch"}),
        React.createElement("div",{className:"phone-screen"},
          React.createElement("div",{className:"phone-bar"},
            React.createElement("span",null,"7:22"),
            React.createElement("span",{style:{fontSize:11}},"●●●")),
          React.createElement("div",{style:{padding:"8px 22px 12px",display:"flex",flexDirection:"column",gap:10,overflow:"auto"}},
            React.createElement("div",null,
              React.createElement("div",{className:"muted",style:{fontSize:11,letterSpacing:1.2,textTransform:"uppercase"}}, "Para empujar hoy"),
              React.createElement("div",{className:"f-display",style:{fontSize:18,fontWeight:700,marginTop:2}}, "Clientes prioritarios")),

            data.clientesCriticos.filter(c=>c.vendedor==="V10").slice(0,4).map(c=>
              React.createElement("div",{key:c.id,style:{
                padding:14,borderRadius:14,background:"#0F141B",
                border:"1px solid var(--hairline-bright)"
              }},
                React.createElement("div",{className:"row between",style:{marginBottom:6}},
                  React.createElement("b",{style:{fontSize:13.5}}, c.nombre),
                  React.createElement("span",{className:"chip "+(c.prioridad==="alta"?"bad":"warn")}, c.prioridad.toUpperCase())
                ),
                React.createElement("div",{className:"row",style:{gap:6,marginBottom:8,fontSize:11,color:"var(--text-3)"}},
                  React.createElement("span",null, c.segmento),
                  React.createElement("span",null,"·"),
                  React.createElement("span",null, c.ultima)
                ),
                React.createElement("div",{style:{fontSize:12,lineHeight:1.5,color:"var(--text-2)",padding:"8px 10px",background:"#0B0E13",borderRadius:8,marginBottom:8}}, c.accion),
                React.createElement("div",{className:"row between"},
                  React.createElement("span",{className:"chip bad"}, "Brecha $"+c.brecha.toLocaleString("es-AR")),
                  React.createElement("button",{className:"btn btn-sm btn-primary"},
                    React.createElement(Ic.check,{size:12})," Visitar"))
              )),

            React.createElement("button",{className:"btn",style:{justifyContent:"center"}},
              "Ver los 40 clientes")
          )
        )
      )
    )
  );
}
window.ScreenVendedorMobile = ScreenVendedorMobile;
