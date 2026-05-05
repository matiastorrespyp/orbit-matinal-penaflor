/* ORBIT — Screen: Planificación Matinal (gerencia view + edit) */
function ScreenPlanificacion({ data, openEdit }){
  return React.createElement(React.Fragment,null,
    React.createElement("div",{className:"row between",style:{marginBottom:16}},
      React.createElement("div",{className:"row",style:{gap:14}},
        ["Todas","Pendientes","Enviadas","Modificadas","Aprobadas"].map((t,i)=>
          React.createElement("button",{key:i, className:"btn btn-sm"+(i===0?" btn-primary":" btn-ghost")}, t))
      ),
      React.createElement("div",{className:"row",style:{gap:8}},
        React.createElement("button",{className:"btn btn-sm btn-ghost"},
          React.createElement(Ic.history,{size:14}), "Historial"),
        React.createElement("button",{className:"btn btn-sm btn-primary"},
          React.createElement(Ic.send,{size:14}), "Enviar matinal completa"),
      )
    ),

    React.createElement("div",{className:"grid cols-2",style:{gap:14}},
      data.planes.map(p=>{
        const v = data.vendedores.find(x=>x.id===p.vendedor);
        const hasOriginal = !!p.original;
        return React.createElement("div",{key:p.vendedor,className:"card"},
          React.createElement("div",{className:"card-head"},
            React.createElement("div",{className:"row",style:{gap:12}},
              v && React.createElement(VDot,{v, size:34}),
              React.createElement("div",null,
                React.createElement("div",{className:"row",style:{gap:8,alignItems:"center"}},
                  React.createElement("h3",{className:"card-title",style:{fontSize:15}}, v?v.nombre:p.vendedor),
                  React.createElement(StatusPill,{status:p.estado})
                ),
                React.createElement("div",{className:"card-sub"},
                  v?v.zona+" · ":"",
                  p.submitted? "Enviado "+p.submitted : "Sin envío")
              )
            ),
            React.createElement("button",{className:"btn btn-sm btn-ghost",onClick:()=>openEdit&&openEdit(p)},
              React.createElement(Ic.edit,{size:14}), "Editar")
          ),
          p.estado==="pendiente"
            ? React.createElement("div",{className:"card-body",style:{textAlign:"center",padding:"30px 18px"}},
                React.createElement("div",{className:"kpi-icon warn",style:{margin:"0 auto 10px",width:38,height:38,borderRadius:10}},
                  React.createElement(Ic.clock,{size:18})),
                React.createElement("div",{style:{fontWeight:600}}, "Planificación pendiente"),
                React.createElement("div",{className:"muted",style:{fontSize:12,marginTop:4}}, "El vendedor aún no envió su plan"),
                React.createElement("button",{className:"btn btn-primary btn-sm",style:{marginTop:14}},
                  React.createElement(Ic.send,{size:13}), "Recordar al vendedor"),
              )
            : React.createElement("div",{className:"card-body"},
                // 4-column micro KPIs of the plan
                React.createElement("div",{style:{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:14}},
                  [
                    {l:"VENTA OBJ", v: fmtMoney(p.venta_obj), orig: hasOriginal && p.original.venta_obj!=null && p.original.venta_obj!==p.venta_obj? fmtMoney(p.original.venta_obj):null},
                    {l:"CCC TRAD", v: p.ccc_trad, orig: hasOriginal && p.original.ccc_trad!=null && p.original.ccc_trad!==p.ccc_trad? p.original.ccc_trad:null},
                    {l:"CCC AS",   v: v && v.id==="V3"? "—" : p.ccc_as, orig: hasOriginal && p.original.ccc_as!=null && p.original.ccc_as!==p.ccc_as? p.original.ccc_as:null, dim:v && v.id==="V3"},
                    {l:"11T",      v: p.t11, orig: hasOriginal && p.original.t11!=null && p.original.t11!==p.t11? p.original.t11:null},
                  ].map((m,i)=>React.createElement("div",{key:i,style:{
                    background:"#0B0E13",borderRadius:10,padding:"10px 12px",
                    boxShadow:"inset 0 0 0 1px var(--hairline)"
                  }},
                    React.createElement("div",{className:"muted",style:{fontSize:10,letterSpacing:1.2,textTransform:"uppercase"}}, m.l),
                    React.createElement("div",{style:{display:"flex",alignItems:"baseline",gap:6,marginTop:5}},
                      m.orig!=null && React.createElement("span",{className:"diff-orig tnum",style:{fontSize:13}}, m.orig),
                      React.createElement("span",{
                        className:"f-display tnum",
                        style:{fontWeight:700,fontSize:m.orig!=null?16:18, color: m.dim?"var(--text-3)": (m.orig!=null?"var(--ok)":"var(--text)")}
                      }, m.v)
                    )
                  ))
                ),
                // marcas + clientes
                React.createElement("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:12}},
                  React.createElement("div",null,
                    React.createElement("div",{className:"h-eyebrow"}, "Marcas prioritarias"),
                    React.createElement("div",{className:"row",style:{gap:6,flexWrap:"wrap"}},
                      p.marcas.map((m,i)=>{
                        const wasNew = hasOriginal && p.original.marcas && !p.original.marcas.includes(m);
                        return React.createElement("span",{key:i,className:"chip "+(wasNew?"violet":"")}, m,
                          wasNew && React.createElement("span",{className:"diff-tag gerencia",style:{marginLeft:6,padding:"1px 4px",fontSize:9}}, "Ger."));
                      })
                    )
                  ),
                  React.createElement("div",null,
                    React.createElement("div",{className:"h-eyebrow"}, "Clientes clave"),
                    React.createElement("div",{className:"muted",style:{fontSize:12.5,lineHeight:1.5}},
                      p.clientes_clave.length? p.clientes_clave.join(" · ") : "—")
                  )
                ),
                // observaciones
                p.obs_vendedor && React.createElement("div",{style:{
                  background:"rgba(77,163,255,.06)",borderLeft:"2px solid var(--info)",
                  padding:"8px 12px",borderRadius:"0 8px 8px 0",fontSize:12.5,marginBottom:8
                }},
                  React.createElement("span",{className:"diff-tag vendedor",style:{marginRight:8}}, "Vendedor"),
                  p.obs_vendedor),
                p.obs_gerencia && React.createElement("div",{style:{
                  background:"rgba(155,123,255,.06)",borderLeft:"2px solid var(--violet)",
                  padding:"8px 12px",borderRadius:"0 8px 8px 0",fontSize:12.5
                }},
                  React.createElement("span",{className:"diff-tag gerencia",style:{marginRight:8}}, "Gerencia"),
                  p.obs_gerencia),

                React.createElement("div",{className:"row",style:{gap:8,marginTop:14, justifyContent:"flex-end"}},
                  p.estado!=="aprobada" && React.createElement("button",{className:"btn btn-sm btn-ghost"},
                    React.createElement(Ic.send,{size:13}), "Enviar al vendedor"),
                  p.estado!=="aprobada" && React.createElement("button",{className:"btn btn-sm btn-primary"},
                    React.createElement(Ic.check,{size:13}), "Aprobar"),
                  p.estado==="aprobada" && React.createElement("span",{className:"chip ok"},
                    React.createElement(Ic.check,{size:12,stroke:3}), " Aprobada")
                )
              )
        );
      })
    )
  );
}

/* Edit overlay */
function PlanEditModal({ plan, data, onClose }){
  if(!plan) return null;
  const v = data.vendedores.find(x=>x.id===plan.vendedor);
  return React.createElement("div",{
    style:{position:"fixed",inset:0,background:"rgba(7,9,12,.78)",backdropFilter:"blur(8px)",zIndex:100,display:"grid",placeItems:"center",padding:24}
  },
    React.createElement("div",{
      className:"card", style:{width:"100%",maxWidth:780,maxHeight:"92vh",overflow:"auto"}
    },
      React.createElement("div",{className:"card-head"},
        React.createElement("div",{className:"row",style:{gap:12}},
          v && React.createElement(VDot,{v,size:34}),
          React.createElement("div",null,
            React.createElement("h3",{className:"card-title",style:{fontSize:16}}, "Editar planificación · "+(v?v.nombre:plan.vendedor)),
            React.createElement("div",{className:"card-sub"}, "Cualquier cambio se guardará como ajuste de gerencia (visible para el vendedor)")
          )
        ),
        React.createElement("button",{className:"btn-icon btn btn-ghost",onClick:onClose},
          React.createElement(Ic.x,{size:16}))
      ),
      React.createElement("div",{className:"card-body",style:{display:"grid",gap:14}},
        React.createElement("div",{className:"grid cols-3",style:{gap:12}},
          React.createElement("div",{className:"field"},
            React.createElement("label",null,"Venta objetivo del día"),
            React.createElement("input",{className:"input tnum",defaultValue:plan.venta_obj}),
          ),
          React.createElement("div",{className:"field"},
            React.createElement("label",null,"CCC Tradicional"),
            React.createElement("input",{className:"input tnum",defaultValue:plan.ccc_trad}),
          ),
          React.createElement("div",{className:"field"},
            React.createElement("label",null,"CCC Autoservicio"),
            React.createElement("input",{className:"input tnum",defaultValue:plan.ccc_as ?? "", disabled: v?.id==="V3", placeholder: v?.id==="V3"?"No aplica":""}),
          ),
          React.createElement("div",{className:"field"},
            React.createElement("label",null,"CCC On Premise / Vinoteca"),
            React.createElement("input",{className:"input tnum",defaultValue:plan.ccc_op}),
          ),
          React.createElement("div",{className:"field"},
            React.createElement("label",null,"11 Titulares comprometidos"),
            React.createElement("input",{className:"input tnum",defaultValue:plan.t11}),
          ),
          React.createElement("div",{className:"field"},
            React.createElement("label",null,"Día de visita"),
            React.createElement("select",{className:"input",defaultValue:"MA"},
              ["LU","MA","MI","JU","VI","SA"].map(d=>React.createElement("option",{key:d,value:d},d))
            ),
          ),
        ),
        React.createElement("div",{className:"field"},
          React.createElement("label",null,"Marcas prioritarias"),
          React.createElement("input",{className:"input",defaultValue:plan.marcas.join(", ")}),
        ),
        React.createElement("div",{className:"field"},
          React.createElement("label",null,"Clientes clave"),
          React.createElement("input",{className:"input",defaultValue:plan.clientes_clave.join(", ")}),
        ),
        React.createElement("div",{className:"field"},
          React.createElement("label",null,"Comentario de gerencia"),
          React.createElement("textarea",{className:"input",defaultValue:plan.obs_gerencia,placeholder:"Mensaje al vendedor..."}),
        ),
        React.createElement("div",{className:"row",style:{justifyContent:"space-between",marginTop:6}},
          React.createElement("div",{className:"row",style:{gap:8,fontSize:12,color:"var(--text-3)"}},
            React.createElement(Ic.history,{size:14}),
            "Última modificación: gerencia · 06:58"
          ),
          React.createElement("div",{className:"row",style:{gap:8}},
            React.createElement("button",{className:"btn btn-ghost",onClick:onClose}, "Cancelar"),
            React.createElement("button",{className:"btn"},
              React.createElement(Ic.send,{size:14})," Guardar y enviar"),
            React.createElement("button",{className:"btn btn-primary"},
              React.createElement(Ic.check,{size:14})," Guardar y aprobar"),
          )
        )
      )
    )
  );
}
window.ScreenPlanificacion = ScreenPlanificacion;
window.PlanEditModal = PlanEditModal;
