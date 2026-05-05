/* ORBIT — Screen: Avance de Objetivos */
function ScreenAvance({ data }){
  const vends = data.vendedores;
  const heatRows = vends.map(v=>({
    v,
    cells: [
      { label:"Avance", value: v.avance, fmt:v=>v.toFixed(0)+"%", level: v.avance>=100?4:v.avance>=70?3:v.avance>=40?2:v.avance>=15?2:1 },
      { label:"CCC", value: v.id==="V3"?34:v.id==="V4"?12:v.id==="V6"?56:v.id==="V7"?22:v.id==="V8"?28:v.id==="V9"?38:18, fmt:v=>v, level: 3 },
      { label:"11T", value: v.id==="V6"?89:v.id==="V9"?91:v.id==="V8"?34:42, fmt:v=>v+"%", level: 2 },
      { label:"Trad", value: v.id==="V6"?72:v.id==="V9"?12:50, fmt:v=>v+"%", level: 2 },
      { label:"AS", value: v.id==="V3"?null:v.id==="V8"?68:30, fmt:v=>v==null?"—":v+"%", level: v.id==="V3"?0:2 },
      { label:"OP", value: v.id==="V9"?92:8, fmt:v=>v+"%", level: 1 },
    ]
  }));

  return React.createElement(React.Fragment,null,
    React.createElement("div",{className:"grid cols-12",style:{gap:14, marginBottom:14}},
      React.createElement("div",{className:"card",style:{gridColumn:"span 8"}},
        React.createElement("div",{className:"card-head"},
          React.createElement("div",null,
            React.createElement("h3",{className:"card-title"}, "Objetivo vs Logrado por vendedor"),
            React.createElement("div",{className:"card-sub"}, "Línea punteada = objetivo mensual")
          )
        ),
        React.createElement("div",{className:"card-body"},
          React.createElement(HBars,{
            valueFmt: v => fmtMoney(v),
            max: Math.max(...vends.map(v=>v.objetivo)),
            rows: vends.map(v=>{
              const color = v.avance>=100? "#5BC23A" : v.avance>=60? "#4DA3FF" : v.avance>=30? "#F2B544" : "#FF5D5D";
              return {
                label: v.nombre,
                dot: v.color,
                value: v.acumulado, target: v.objetivo,
                color,
                tag: v.avance.toFixed(0)+"% / "+fmtMoney(v.objetivo),
                tagKind: v.avance>=70?"ok":v.avance>=30?"warn":"bad",
              };
            })
          })
        )
      ),

      React.createElement("div",{className:"card",style:{gridColumn:"span 4"}},
        React.createElement("div",{className:"card-head"},
          React.createElement("div",null,
            React.createElement("h3",{className:"card-title"}, "Tendencia proyectada"),
            React.createElement("div",{className:"card-sub"}, "Cierre estimado vs objetivo")
          )
        ),
        React.createElement("div",{className:"card-body",style:{display:"flex",flexDirection:"column",gap:14}},
          vends.map(v=>{
            const proy = (v.acumulado/19)*30;
            const proyPct = (proy/v.objetivo)*100;
            const kind = proyPct>=95?"ok":proyPct>=70?"warn":"bad";
            const color = kind==="ok"?"#5BC23A":kind==="warn"?"#F2B544":"#FF5D5D";
            return React.createElement("div",{key:v.id,className:"row between",style:{padding:"10px 0",borderBottom:"1px solid var(--hairline)"}},
              React.createElement("div",{className:"row",style:{gap:10}},
                React.createElement(VDot,{v,size:28}),
                React.createElement("div",null,
                  React.createElement("div",{style:{fontSize:13,fontWeight:600}}, v.nombre),
                  React.createElement("div",{className:"muted",style:{fontSize:11}}, "Proyectado: "+fmtMoney(proy))
                )
              ),
              React.createElement("div",{className:"chip "+kind, style:{minWidth:64,justifyContent:"center"}}, proyPct.toFixed(0)+"%")
            );
          })
        )
      ),
    ),

    React.createElement("div",{className:"card"},
      React.createElement("div",{className:"card-head"},
        React.createElement("div",null,
          React.createElement("h3",{className:"card-title"}, "Heatmap — Vendedor x Indicador"),
          React.createElement("div",{className:"card-sub"}, "V3 sin Autoservicio (no aplica)")
        ),
        React.createElement("div",{className:"row",style:{gap:6,fontSize:10,color:"var(--text-3)"}},
          ["bajo","medio","alto","excelente"].map((l,i)=>React.createElement("span",{key:i,className:"chip",style:{padding:"2px 8px"}},
            React.createElement("span",{style:{width:8,height:8,borderRadius:2,marginRight:4,background:["rgba(255,93,93,.5)","rgba(242,181,68,.55)","rgba(91,194,58,.55)","rgba(91,194,58,.85)"][i]}}),
            l))
        )
      ),
      React.createElement("div",{className:"card-body"},
        React.createElement("div",{style:{display:"grid",gridTemplateColumns:"180px repeat(6, 1fr)",gap:8,alignItems:"center"}},
          React.createElement("div",null),
          ["Avance","CCC","11T","Tradicional","Autoservicio","On Premise"].map((l,i)=>
            React.createElement("div",{key:i,className:"muted",style:{fontSize:10,letterSpacing:1.2,textTransform:"uppercase",textAlign:"center"}}, l)),
          heatRows.flatMap(r=>[
            React.createElement("div",{key:r.v.id+"_l", className:"row",style:{gap:10}},
              React.createElement(VDot,{v:r.v,size:24}),
              React.createElement("b",{style:{fontSize:13}}, r.v.nombre)
            ),
            ...r.cells.map((c,i)=>React.createElement("div",{key:r.v.id+i, className:"heat-cell heat-l"+c.level}, c.fmt(c.value)))
          ])
        )
      )
    )
  );
}
window.ScreenAvance = ScreenAvance;
