/* ORBIT — Screens: Clientes Críticos, 11 Titulares, Alertas, Vendedores */

function ScreenClientes({ data }){
  const stateMap = {
    caida_compra:    {label:"Caída de compra",      kind:"bad"},
    sin_compra_mes:  {label:"Sin compra del mes",   kind:"bad"},
    sin_cobertura:   {label:"Sin cobertura válida", kind:"warn"},
    compra_baja:     {label:"Volumen bajo",         kind:"warn"},
  };
  return React.createElement(React.Fragment,null,
    React.createElement("div",{className:"row between",style:{marginBottom:16}},
      React.createElement("div",{className:"row",style:{gap:8}},
        React.createElement("div",{style:{position:"relative"}},
          React.createElement(Ic.search,{size:14}),
          React.createElement("input",{className:"input",placeholder:"Buscar cliente...",style:{paddingLeft:36,minWidth:280}})
        ),
        React.createElement("button",{className:"btn btn-sm btn-ghost"},
          React.createElement(Ic.filter,{size:14}), "Segmento"),
        React.createElement("button",{className:"btn btn-sm btn-ghost"},
          React.createElement(Ic.filter,{size:14}), "Vendedor"),
        React.createElement("button",{className:"btn btn-sm btn-ghost"},
          React.createElement(Ic.filter,{size:14}), "Estado"),
      ),
      React.createElement("div",{className:"row",style:{gap:8}},
        React.createElement("span",{className:"chip"}, data.clientesCriticos.length+" clientes críticos"),
        React.createElement("button",{className:"btn btn-sm btn-ghost"},
          React.createElement(Ic.download,{size:14}), "Exportar")
      )
    ),

    React.createElement("div",{className:"grid cols-4",style:{gap:14,marginBottom:18}},
      [
        {l:"SIN COMPRA DEL MES", v:96, k:"bad"},
        {l:"CAÍDA DE COMPRA", v:38, k:"bad"},
        {l:"SIN COBERTURA VÁLIDA", v:124, k:"warn"},
        {l:"OPORTUNIDAD VENTA", v:67, k:"info"},
      ].map((m,i)=>React.createElement(KpiCard,{
        key:i, label:m.l, value:m.v, kind:m.k,
        icon: React.createElement(Ic.store,{size:14}), hint:"Click para ver lista"
      }))
    ),

    React.createElement("div",{className:"card"},
      React.createElement("div",{style:{overflow:"auto"}},
        React.createElement("table",{className:"tbl"},
          React.createElement("thead",null,
            React.createElement("tr",null,
              ["Cliente","Segmento","Vendedor","Última compra","Brecha","Estado","Acción recomendada","11T",""].map((h,i)=>
                React.createElement("th",{key:i,className: i===4?"right":""},h))
            )
          ),
          React.createElement("tbody",null,
            data.clientesCriticos.map(c=>{
              const v = data.vendedores.find(x=>x.id===c.vendedor);
              const s = stateMap[c.estado] || {label:c.estado,kind:""};
              return React.createElement("tr",{key:c.id},
                React.createElement("td",null,
                  React.createElement("div",{style:{fontWeight:600,fontSize:13}}, c.nombre),
                  React.createElement("div",{className:"muted",style:{fontSize:11,marginTop:2}}, "ID "+c.id)
                ),
                React.createElement("td",null, React.createElement("span",{className:"chip"}, c.segmento)),
                React.createElement("td",null,
                  v && React.createElement("span",{className:"v-pill"},
                    React.createElement(VDot,{v,size:22}),
                    React.createElement("span",{style:{fontSize:12}}, v.nombre.split(" ")[0]))
                ),
                React.createElement("td",{className:"muted",style:{fontSize:12}}, c.ultima),
                React.createElement("td",{className:"right tnum",style:{fontWeight:600}}, "$"+c.brecha.toLocaleString("es-AR")),
                React.createElement("td",null, React.createElement("span",{className:"chip "+s.kind}, s.label)),
                React.createElement("td",{className:"muted",style:{fontSize:12.5,maxWidth:340}}, c.accion),
                React.createElement("td",null,
                  React.createElement("span",{className:"chip "+(c.t11>=10?"bad":"warn")}, "Faltan "+c.t11)
                ),
                React.createElement("td",null,
                  React.createElement("button",{className:"btn btn-sm btn-ghost"},
                    React.createElement(Ic.arrowRight,{size:14}))
                )
              );
            })
          )
        )
      )
    )
  );
}

function Screen11T({ data }){
  return React.createElement(React.Fragment,null,
    React.createElement("div",{className:"row between",style:{marginBottom:16}},
      React.createElement("div",{className:"row",style:{gap:8}},
        ["Total empresa","Por vendedor","Por segmento","Por día"].map((t,i)=>
          React.createElement("button",{key:i,className:"btn btn-sm"+(i===0?" btn-primary":" btn-ghost")},t))
      ),
      React.createElement("span",{className:"chip warn"}, "Cumplimiento promedio 47.2%")
    ),

    React.createElement("div",{className:"card"},
      React.createElement("div",{className:"card-head"},
        React.createElement("div",null,
          React.createElement("h3",{className:"card-title"}, "11 Titulares — Cobertura por marca"),
          React.createElement("div",{className:"card-sub"}, "Clientes con la marca activa en el mes")
        )
      ),
      React.createElement("div",{className:"card-body"},
        React.createElement(HBars,{
          valueFmt: v => v+" clientes",
          max: Math.max(...data.titulares11.map(t=>t.objetivo)),
          rows: data.titulares11.map(t=>{
            const pct = t.cubiertos/t.objetivo*100;
            const color = pct>=70?"#5BC23A":pct>=45?"#F2B544":"#FF5D5D";
            const kind = pct>=70?"ok":pct>=45?"warn":"bad";
            return {
              label: t.marca + " — " + t.producto,
              dot: color, value: t.cubiertos, target: t.objetivo, color,
              tag: pct.toFixed(0)+"% · "+t.responsable,
              tagKind: kind
            };
          })
        })
      )
    ),

    React.createElement("div",{className:"grid cols-2",style:{gap:14,marginTop:14}},
      React.createElement("div",{className:"card"},
        React.createElement("div",{className:"card-head"},
          React.createElement("h3",{className:"card-title"}, "Brecha por marca")),
        React.createElement("div",{className:"card-body"},
          React.createElement("table",{className:"tbl"},
            React.createElement("thead",null,
              React.createElement("tr",null,["Marca","Objetivo","Cubiertos","Brecha","Responsable"].map((h,i)=>
                React.createElement("th",{key:i,className:i>0?"right":""},h)))),
            React.createElement("tbody",null,
              data.titulares11.slice(0,7).map((t,i)=>{
                const brecha = t.objetivo - t.cubiertos;
                return React.createElement("tr",{key:i},
                  React.createElement("td",null,
                    React.createElement("div",{style:{fontWeight:600,fontSize:13}}, t.marca),
                    React.createElement("div",{className:"muted",style:{fontSize:11}}, t.segmento)),
                  React.createElement("td",{className:"right tnum"}, t.objetivo),
                  React.createElement("td",{className:"right tnum"}, t.cubiertos),
                  React.createElement("td",{className:"right tnum",style:{color:"var(--bad)",fontWeight:600}}, "-"+brecha),
                  React.createElement("td",{className:"right muted",style:{fontSize:12}}, t.responsable)
                );
              })
            )
          )
        )
      ),
      React.createElement("div",{className:"card"},
        React.createElement("div",{className:"card-head"},
          React.createElement("h3",{className:"card-title"}, "11T por segmento")),
        React.createElement("div",{className:"card-body"},
          React.createElement(StackedBars,{
            segments:[
              {name:"Cubiertos", color:"#5BC23A"},
              {name:"En curso", color:"#F2B544"},
              {name:"Sin cobertura", color:"#FF5D5D"},
            ],
            rows:[
              {label:"Tradicional", values:[163, 48, 68]},
              {label:"Autoservicio", values:[18, 12, 13]},
              {label:"On Premise / Vinoteca", values:[9, 6, 6]},
            ]
          })
        )
      ),
    )
  );
}

function ScreenAlertas({ data }){
  const grouped = {
    alta: data.alertas.filter(a=>a.prioridad==="alta"),
    media: data.alertas.filter(a=>a.prioridad==="media"),
    baja: data.alertas.filter(a=>a.prioridad==="baja"),
  };
  const meta = {
    alta:{label:"Prioridad ALTA", kind:"bad", ico:Ic.alert},
    media:{label:"Prioridad MEDIA", kind:"warn", ico:Ic.bell},
    baja:{label:"Oportunidades", kind:"info", ico:Ic.zap},
  };

  return React.createElement(React.Fragment,null,
    React.createElement("div",{className:"grid cols-3",style:{gap:14,marginBottom:18}},
      Object.entries(grouped).map(([k,arr])=>{
        const m = meta[k];
        const total = arr.reduce((s,a)=>s+(a.impacto||0),0);
        return React.createElement(KpiCard,{
          key:k, label:m.label, value:arr.length, kind:m.kind,
          icon: React.createElement(m.ico,{size:14}),
          hint: total? "Impacto: "+fmtMoney(total) : "Sin impacto monetario"
        });
      })
    ),

    React.createElement("div",{className:"card"},
      React.createElement("div",{className:"alist"},
        data.alertas.map(a=>{
          const m = meta[a.prioridad];
          return React.createElement("div",{key:a.id, className:"arow "+m.kind},
            React.createElement("div",{className:"pri"}),
            React.createElement("div",null,
              React.createElement("div",{className:"row",style:{gap:10,marginBottom:5}},
                React.createElement("span",{className:"chip "+m.kind, style:{textTransform:"uppercase"}}, a.prioridad),
                React.createElement("span",{className:"chip"}, a.tipo),
                React.createElement("b",{style:{fontSize:14}}, a.titulo),
              ),
              React.createElement("div",{className:"text-2",style:{fontSize:13,marginBottom:6}}, a.detalle),
              React.createElement("div",{className:"row",style:{gap:14,fontSize:12,color:"var(--text-3)"}},
                React.createElement("span",{className:"row",style:{gap:5}},
                  React.createElement(Ic.target,{size:12}), "Acción: ", React.createElement("b",{style:{color:"var(--text-2)"}}, a.accion)),
                React.createElement("span",{className:"row",style:{gap:5}},
                  React.createElement(Ic.users,{size:12}), "Responsable: ", a.responsable),
                a.impacto>0 && React.createElement("span",{className:"row",style:{gap:5,color:"var(--bad)"}},
                  React.createElement(Ic.flame,{size:12}), "Impacto: "+fmtMoney(a.impacto))
              )
            ),
            React.createElement("div",{className:"row",style:{gap:6}},
              React.createElement("button",{className:"btn btn-sm btn-ghost"},"Atender"),
              React.createElement("button",{className:"btn btn-sm btn-ghost btn-icon"},
                React.createElement(Ic.more,{size:14}))
            )
          );
        })
      )
    )
  );
}

function ScreenVendedores({ data }){
  return React.createElement(React.Fragment,null,
    React.createElement("div",{className:"grid cols-3",style:{gap:14}},
      data.vendedores.map(v=>{
        const proy = (v.acumulado/19)*30;
        const proyPct = (proy/v.objetivo)*100;
        const kind = v.avance>=100?"ok":v.avance>=60?"info":v.avance>=30?"warn":"bad";
        return React.createElement("div",{key:v.id, className:"card"},
          React.createElement("div",{className:"card-head"},
            React.createElement("div",{className:"row",style:{gap:12}},
              React.createElement(VDot,{v,size:38}),
              React.createElement("div",null,
                React.createElement("div",{style:{fontWeight:600}}, v.nombre),
                React.createElement("div",{className:"card-sub"}, v.id+" · "+v.zona)
              )
            ),
            React.createElement("span",{className:"chip "+kind}, v.avance.toFixed(0)+"%")
          ),
          React.createElement("div",{className:"card-body"},
            React.createElement("div",{className:"row between",style:{marginBottom:8}},
              React.createElement("span",{className:"muted",style:{fontSize:11}}, "OBJETIVO MENSUAL"),
              React.createElement("b",{className:"tnum"}, fmtMoney(v.objetivo))
            ),
            React.createElement("div",{className:"bar"+(kind==="bad"?" bad":kind==="warn"?" warn":"")},
              React.createElement("i",{style:{width:Math.min(v.avance,100)+"%"}})
            ),
            React.createElement("div",{className:"row between",style:{marginTop:6,fontSize:12}},
              React.createElement("span",{className:"muted"}, "Logrado " + fmtMoney(v.acumulado)),
              React.createElement("span",{className:"muted"}, "Proy. "+proyPct.toFixed(0)+"%")
            ),
            React.createElement("div",{style:{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:8,marginTop:14}},
              [
                {l:"CLIENTES", v:v.clientes},
                {l:"ALERTAS", v:v.alertas, k:"bad"},
                {l:"FOCO", v: v.id==="V10"?75:v.id==="V7"?54:v.id==="V8"?52:39, k:"info"},
              ].map((m,i)=>React.createElement("div",{key:i, style:{textAlign:"center",padding:"8px 4px",background:"#0B0E13",borderRadius:8,boxShadow:"inset 0 0 0 1px var(--hairline)"}},
                React.createElement("div",{className:"f-display tnum",style:{fontSize:18,fontWeight:700, color: m.k==="bad"?"var(--bad)":m.k==="info"?"var(--info)":"var(--text)"}}, m.v),
                React.createElement("div",{className:"muted",style:{fontSize:10,letterSpacing:1.2,marginTop:2}}, m.l)
              ))
            ),
            v.id==="V3" && React.createElement("div",{style:{
              marginTop:12,padding:"8px 12px",background:"rgba(155,123,255,.08)",
              borderLeft:"2px solid var(--violet)",borderRadius:"0 8px 8px 0",fontSize:12,color:"var(--text-2)"
            }}, "⚠ Nadia no opera Autoservicio"),
            React.createElement("div",{className:"row",style:{gap:8,marginTop:14}},
              React.createElement("button",{className:"btn btn-sm btn-ghost",style:{flex:1}},
                React.createElement(Ic.plan,{size:13})," Ver plan"),
              React.createElement("button",{className:"btn btn-sm btn-ghost",style:{flex:1}},
                React.createElement(Ic.arrowRight,{size:13})," Detalle"),
            )
          )
        );
      })
    )
  );
}

function ScreenSegmentos({ data }){
  return React.createElement(React.Fragment,null,
    React.createElement("div",{className:"grid cols-3",style:{gap:14,marginBottom:18}},
      data.segmentos.map(s=>{
        const pct = s.cubiertos/s.clientes*100;
        const kind = pct>=70?"ok":pct>=50?"warn":"bad";
        return React.createElement("div",{key:s.id,className:"card"},
          React.createElement("div",{className:"card-body",style:{display:"flex",gap:18,alignItems:"center"}},
            React.createElement(Donut,{value:pct,size:130,stroke:11,color:s.color, label:pct.toFixed(0)+"%", subLabel:"Cobertura"}),
            React.createElement("div",{style:{flex:1}},
              React.createElement("div",{className:"h-eyebrow"}, s.id.replace("_"," ")),
              React.createElement("h3",{style:{margin:"4px 0 6px",fontSize:18}}, s.nombre),
              React.createElement("div",{className:"muted",style:{fontSize:12.5,marginBottom:14}}, "Cobertura válida = mín. ", React.createElement("b",{style:{color:"var(--text)"}}, s.req+" botellas")),
              React.createElement("div",{className:"row between",style:{fontSize:12}},
                React.createElement("span",null,"Clientes ",React.createElement("b",{className:"tnum"}, s.clientes)),
                React.createElement("span",null,"Cubiertos ",React.createElement("b",{className:"tnum",style:{color:"var(--ok)"}}, s.cubiertos)),
                React.createElement("span",null,"Faltan ",React.createElement("b",{className:"tnum",style:{color:"var(--bad)"}}, s.clientes-s.cubiertos)),
              )
            )
          )
        );
      })
    ),
    React.createElement("div",{className:"card"},
      React.createElement("div",{className:"card-head"},
        React.createElement("div",null,
          React.createElement("h3",{className:"card-title"}, "Cobertura por vendedor x segmento"),
          React.createElement("div",{className:"card-sub"}, "V3 no opera Autoservicio"))),
      React.createElement("div",{className:"card-body"},
        React.createElement(StackedBars,{
          segments:[
            {name:"Tradicional", color:"#5BC23A"},
            {name:"Autoservicio", color:"#4DA3FF"},
            {name:"On Premise/Vino", color:"#9B7BFF"},
          ],
          rows: data.vendedores.map(v=>({
            label: v.nombre,
            values: v.id==="V3"? [v.clientes, 0, 0] :
                    v.id==="V9"? [3, 4, v.clientes-7] :
                    v.id==="V8"? [v.clientes-12, 12, 0] :
                    [v.clientes-Math.round(v.clientes*.15), Math.round(v.clientes*.15), 0]
          }))
        })
      )
    )
  );
}

window.ScreenClientes = ScreenClientes;
window.Screen11T = Screen11T;
window.ScreenAlertas = ScreenAlertas;
window.ScreenVendedores = ScreenVendedores;
window.ScreenSegmentos = ScreenSegmentos;
