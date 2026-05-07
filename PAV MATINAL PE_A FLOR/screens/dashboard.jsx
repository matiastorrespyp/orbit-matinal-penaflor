/* ORBIT — Screen 1: Dashboard Ejecutivo (datos reales, sin hardcode) */
function ScreenDashboard({ data, vendedorFiltro }){
  const k = data.kpisGerencia;
  const cal = data.calendario || {};
  const diasCorridos = cal.corridos || 1;
  const diasTotal = cal.total || 24;
  const diasRestantes = cal.restantes || (diasTotal - diasCorridos);
  const proyeccion = (k.acumulado_mes / Math.max(diasCorridos, 1)) * diasTotal;
  const diff = proyeccion - k.objetivo_mes;

  const realSpark = data.dailyEvolution && data.dailyEvolution.filter(d=>d.real!=null).map(d=>d.real) || [];
  const cccSpark = null;

  const cierreProyectado = (function(){ var d = new Date((data.fechaCorta||"")+"T12:00:00"); var last = new Date(d.getFullYear(),d.getMonth()+1,0); return "Cierre proyectado al "+String(last.getDate()).padStart(2,"0")+"/"+String(last.getMonth()+1).padStart(2,"0"); })();
  const vendsOrdenados = [...data.vendedores].sort((a,b)=>b.avance-a.avance);

  return React.createElement(React.Fragment,null,
    React.createElement("div",{className:"grid cols-6",style:{marginBottom:14}},
      React.createElement(KpiCard,{
        label:"VENTA ACUMULADA", kind:"ok",
        value: fmtMoney(k.acumulado_mes),
        icon: React.createElement(Ic.zap,{size:14}),
        hint: (data.calendario ? "Corte: " + data.calendario.fecha_corte : ""),
        spark: realSpark.length ? React.createElement(Sparkline,{data:realSpark, w:60, h:22}) : null
      }),
      React.createElement(KpiCard,{
        label:"VENTA DEL DÍA", kind:"warn",
        value: fmtMoney(k.venta_dia),
        icon: React.createElement(Ic.bottle,{size:14}),
        hint:"Objetivo día "+fmtMoney(k.objetivo_dia)
      }),
      React.createElement(KpiCard,{
        label:"OBJETIVO MENSUAL",
        value: fmtMoney(k.objetivo_mes),
        icon: React.createElement(Ic.target,{size:14}),
        hint: diasCorridos + " días hábiles transcurridos · " + diasRestantes + " días restantes"
      }),
      React.createElement(KpiCard,{
        label:"AVANCE %", kind: k.avance_pct >= 70 ? "ok" : k.avance_pct >= 40 ? "warn" : "bad",
        value: k.avance_pct.toFixed(1), unit:"%",
        icon: React.createElement(Ic.trend,{size:14})
      }),
      React.createElement(KpiCard,{
        label:"TENDENCIA PROYECTADA", kind: k.tendencia >= 95 ? "ok" : k.tendencia >= 70 ? "warn" : "bad",
        value: (k.tendencia || 0).toFixed(1), unit:"%",
        icon: React.createElement(Ic.flame,{size:14}),
        hint: cierreProyectado
      }),
      React.createElement(KpiCard,{
        label:"DIFERENCIA VS OBJ", kind:"bad",
        value: (k.diff_objetivo < 0 ? "-" : "") + fmtMoney(Math.abs(k.diff_objetivo)),
        icon: React.createElement(Ic.arrowDown,{size:14}),
        hint:"Brecha al cierre proyectado"
      }),
    ),

    React.createElement("div",{className:"grid cols-6",style:{marginBottom:22}},
      React.createElement(KpiCard,{
        label:"CCC ACUMULADOS",
        value: k.ccc_mes,
        icon: React.createElement(Ic.users,{size:14}),
        spark: null
      }),
      React.createElement(KpiCard,{
        label:"CCC DEL DÍA",
        value: k.ccc_dia, kind:"info",
        icon: React.createElement(Ic.users,{size:14})
      }),
      React.createElement(KpiCard,{
        label:"BOTELLAS DEL DÍA",
        value: (k.botellas_dia || 0).toLocaleString("es-AR"),
        icon: React.createElement(Ic.bottle,{size:14})
      }),
      React.createElement(KpiCard,{
        label:"CLIENTES C/COMPRA",
        value: k.clientes_compra,
        icon: React.createElement(Ic.store,{size:14}),
        hint:"de " + (k.clientes_compra + (data.vendedores.reduce((s,v)=>s+v.alertas,0) || 0)) + " visitados"
      }),
      React.createElement(KpiCard,{
        label:"COBERTURA GENERAL", kind: k.cobertura_general >= 70 ? "ok" : k.cobertura_general >= 50 ? "warn" : "bad",
        value: (k.cobertura_general || 0).toFixed(1), unit:"%",
        icon: React.createElement(Ic.flag,{size:14})
      }),
      React.createElement(KpiCard,{
        label:"CUMPLIMIENTO 11T", kind: k.cumplimiento_11t >= 70 ? "ok" : k.cumplimiento_11t >= 40 ? "warn" : "bad",
        value: (k.cumplimiento_11t || 0).toFixed(1), unit:"%",
        icon: React.createElement(Ic.flame,{size:14}),
        hint:"Empuje requerido"
      }),
    ),

    React.createElement("div",{className:"grid cols-12",style:{marginBottom:22, gap:14}},
      React.createElement("div",{className:"card", style:{gridColumn:"span 8"}},
        React.createElement("div",{className:"card-head"},
          React.createElement("div",null,
            React.createElement("h3",{className:"card-title"}, "Evolución mensual — Real vs Plan"),
            React.createElement("div",{className:"card-sub"}, "Acumulado diario · " + (data.fechaCorta || ""))
          ),
          React.createElement("div",{className:"row",style:{gap:14, fontSize:11}},
            React.createElement("span",{className:"row",style:{gap:6}},
              React.createElement("span",{style:{width:10,height:2,background:"#5BC23A",borderRadius:1,boxShadow:"0 0 6px #5BC23A"}}),
              "Real"),
            React.createElement("span",{className:"row",style:{gap:6}},
              React.createElement("span",{style:{width:10,height:2,background:"rgba(255,255,255,.4)",borderRadius:1,borderTop:"1px dashed #fff"}}),
              "Plan"),
          )
        ),
        React.createElement("div",{className:"card-body"},
          data.dailyEvolution && data.dailyEvolution.length > 0 ?
            React.createElement(CumulativeChart,{data: data.dailyEvolution}) :
            React.createElement("div",{className:"muted",style:{textAlign:"center",padding:40}},"Sin datos de evolución")
        )
      ),

      React.createElement("div",{className:"card", style:{gridColumn:"span 4"}},
        React.createElement("div",{className:"card-head"},
          React.createElement("div",null,
            React.createElement("h3",{className:"card-title"}, "Avance del mes"),
            React.createElement("div",{className:"card-sub"}, "Cumplimiento del objetivo")
          )
        ),
        React.createElement("div",{className:"card-body",style:{display:"flex",flexDirection:"column",alignItems:"center",gap:18}},
          React.createElement(Donut,{value: k.avance_pct, label: k.avance_pct.toFixed(1)+"%", subLabel:"Cumplido"}),
          React.createElement("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14,width:"100%",marginTop:6}},
            React.createElement("div",null,
              React.createElement("div",{className:"muted",style:{fontSize:11,letterSpacing:1.2,textTransform:"uppercase"}}, "Logrado"),
              React.createElement("div",{className:"f-display tnum",style:{fontSize:18,fontWeight:700,marginTop:3}}, fmtMoney(k.acumulado_mes))
            ),
            React.createElement("div",{style:{textAlign:"right"}},
              React.createElement("div",{className:"muted",style:{fontSize:11,letterSpacing:1.2,textTransform:"uppercase"}}, "Falta"),
              React.createElement("div",{className:"f-display tnum",style:{fontSize:18,fontWeight:700,marginTop:3,color:"var(--warn)"}}, fmtMoney(k.objetivo_mes - k.acumulado_mes))
            ),
          )
        )
      ),
    ),

    React.createElement("div",{className:"grid cols-12",style:{gap:14}},
      React.createElement("div",{className:"card",style:{gridColumn:"span 8"}},
        React.createElement("div",{className:"card-head"},
          React.createElement("div",null,
            React.createElement("h3",{className:"card-title"}, "Ranking de vendedores"),
            React.createElement("div",{className:"card-sub"}, "Avance vs objetivo mensual · Equipo Peñaflor")
          )
        ),
        React.createElement("div",{className:"card-body",style:{paddingTop:6}},
          React.createElement(HBars,{
            valueFmt: v => fmtMoney(v),
            max: Math.max(...data.vendedores.map(v=>v.objetivo)),
            rows: vendsOrdenados.map(v=>{
              const color = v.avance>=100? "#5BC23A" : v.avance>=60? "#4DA3FF" : v.avance>=30? "#F2B544" : "#FF5D5D";
              const kind = v.avance>=100? "ok" : v.avance>=60? "info" : v.avance>=30? "warn" : "bad";
              return {
                label: v.nombre + " · " + v.id,
                dot: v.color,
                value: v.acumulado, target: v.objetivo,
                color,
                tag: v.avance.toFixed(1)+"%",
                tagKind: kind,
              };
            })
          })
        )
      ),

      React.createElement("div",{className:"card",style:{gridColumn:"span 4"}},
        React.createElement("div",{className:"card-head"},
          React.createElement("div",null,
            React.createElement("h3",{className:"card-title"}, "Cobertura por segmento"),
            React.createElement("div",{className:"card-sub"}, "Clientes con cobertura válida")
          )
        ),
        React.createElement("div",{className:"card-body",style:{display:"flex",flexDirection:"column",gap:18}},
          data.segmentos.map(s=>{
            const pct = s.cubiertos/s.clientes*100;
            const kind = pct>=70? "" : pct>=50? "warn" : "bad";
            return React.createElement("div",{key:s.id},
              React.createElement("div",{className:"row between",style:{marginBottom:8}},
                React.createElement("div",null,
                  React.createElement("div",{style:{fontSize:13,fontWeight:600}}, s.nombre),
                  React.createElement("div",{className:"muted",style:{fontSize:11,marginTop:2}}, "Mín. "+s.req+" botellas · "+s.clientes+" clientes")
                ),
                React.createElement("div",{style:{textAlign:"right"}},
                  React.createElement("div",{className:"f-display tnum",style:{fontSize:20,fontWeight:700}}, pct.toFixed(0)+"%"),
                  React.createElement("div",{className:"muted",style:{fontSize:11,marginTop:1}}, s.cubiertos+"/"+s.clientes)
                )
              ),
              React.createElement("div",{className:"bar"+(kind?" "+kind:"")},
                React.createElement("i",{style:{width:pct+"%"}})
              )
            );
          })
        )
      )
    ),

    (function(){
      const ga = data.gastosAccion || {};
      const rs = ga.resumen || {};
      const topAcc  = ga.top_acciones   || [];
      const topVend = ga.top_vendedores || [];
      if (!rs.filas_con_exceso) return null;

      const rowStyle = {display:"flex",justifyContent:"space-between",alignItems:"center",
                        padding:"6px 0",borderBottom:"1px solid rgba(255,255,255,.06)",fontSize:12};
      const labelStyle = {color:"var(--text-2)",maxWidth:160,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"};
      const valStyle   = {color:"var(--bad)",fontVariantNumeric:"tabular-nums",fontWeight:600,whiteSpace:"nowrap"};

      return React.createElement("div",{className:"grid cols-12",style:{marginTop:14,gap:14}},

        React.createElement("div",{className:"card",style:{gridColumn:"span 4"}},
          React.createElement("div",{className:"card-head"},
            React.createElement("div",null,
              React.createElement("h3",{className:"card-title"}, "Gastos por acción"),
              React.createElement("div",{className:"card-sub"}, "Descuentos excedidos · período")
            )
          ),
          React.createElement("div",{className:"card-body",style:{display:"flex",flexDirection:"column",gap:14}},
            React.createElement("div",{style:{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}},
              React.createElement("div",null,
                React.createElement("div",{className:"muted",style:{fontSize:10,letterSpacing:1.2,textTransform:"uppercase"}}, "Exceso total"),
                React.createElement("div",{className:"f-display tnum",style:{fontSize:18,fontWeight:700,color:"var(--bad)",marginTop:3}},
                  fmtMoney(rs.exceso_pesos_total||0))
              ),
              React.createElement("div",null,
                React.createElement("div",{className:"muted",style:{fontSize:10,letterSpacing:1.2,textTransform:"uppercase"}}, "Gasto real"),
                React.createElement("div",{className:"f-display tnum",style:{fontSize:18,fontWeight:700,color:"var(--warn)",marginTop:3}},
                  fmtMoney(rs.gasto_real_total||0))
              ),
              React.createElement("div",null,
                React.createElement("div",{className:"muted",style:{fontSize:10,letterSpacing:1.2,textTransform:"uppercase"}}, "Vend. alertados"),
                React.createElement("div",{className:"f-display tnum",style:{fontSize:18,fontWeight:700,marginTop:3}},
                  rs.vendedores_alertados||0)
              ),
              React.createElement("div",null,
                React.createElement("div",{className:"muted",style:{fontSize:10,letterSpacing:1.2,textTransform:"uppercase"}}, "Clientes afect."),
                React.createElement("div",{className:"f-display tnum",style:{fontSize:18,fontWeight:700,marginTop:3}},
                  rs.clientes_afectados_total||0)
              )
            ),
            React.createElement("div",{className:"muted",style:{fontSize:11,marginTop:4}},
              (rs.acciones_csv||0)+" acciones CSV · "+(rs.acciones_fallback||0)+" fallback")
          )
        ),

        React.createElement("div",{className:"card",style:{gridColumn:"span 4"}},
          React.createElement("div",{className:"card-head"},
            React.createElement("div",null,
              React.createElement("h3",{className:"card-title"}, "Top acciones · exceso"),
              React.createElement("div",{className:"card-sub"}, "Por acción comercial")
            )
          ),
          React.createElement("div",{className:"card-body",style:{paddingTop:4}},
            topAcc.length === 0
              ? React.createElement("div",{className:"muted",style:{textAlign:"center",padding:20}}, "Sin datos")
              : topAcc.map((a,i)=>
                  React.createElement("div",{key:i,style:rowStyle},
                    React.createElement("div",{style:{display:"flex",alignItems:"center",gap:8,minWidth:0}},
                      React.createElement("span",{className:"muted",style:{fontSize:11,minWidth:14}}, (i+1)+"."),
                      React.createElement("div",{style:labelStyle},
                        React.createElement("div",{style:{fontWeight:600,fontSize:12}},
                          (a.accion_id||"").replace(/MAY26-GRAL-/,"").replace(/MAY26-/,"")),
                        React.createElement("div",{className:"muted",style:{fontSize:10,marginTop:1}},
                          (a.canal||"").split(" ")[0]+" · "+(a.categoria||"").split("/")[0])
                      )
                    ),
                    React.createElement("span",{style:valStyle}, fmtMoney(a.exceso_pesos_total||0))
                  )
                )
          )
        ),

        React.createElement("div",{className:"card",style:{gridColumn:"span 4"}},
          React.createElement("div",{className:"card-head"},
            React.createElement("div",null,
              React.createElement("h3",{className:"card-title"}, "Top vendedores · exceso"),
              React.createElement("div",{className:"card-sub"}, "Por vendedor")
            )
          ),
          React.createElement("div",{className:"card-body",style:{paddingTop:4}},
            topVend.length === 0
              ? React.createElement("div",{className:"muted",style:{textAlign:"center",padding:20}}, "Sin datos")
              : topVend.map((v,i)=>
                  React.createElement("div",{key:i,style:rowStyle},
                    React.createElement("div",{style:{display:"flex",alignItems:"center",gap:8,minWidth:0}},
                      React.createElement("span",{className:"muted",style:{fontSize:11,minWidth:14}}, (i+1)+"."),
                      React.createElement("div",{style:labelStyle},
                        React.createElement("div",{style:{fontWeight:600,fontSize:12}},
                          "V"+(v.vendedor_codigo||"")+" · "+((v.vendedor_nombre||"").split(" ")[0])),
                        React.createElement("div",{className:"muted",style:{fontSize:10,marginTop:1}},
                          (v.acciones_con_exceso||0)+" acciones con exceso")
                      )
                    ),
                    React.createElement("span",{style:valStyle}, fmtMoney(v.exceso_pesos_total||0))
                  )
                )
          )
        )
      );
    })()
  );
}
window.ScreenDashboard = ScreenDashboard;