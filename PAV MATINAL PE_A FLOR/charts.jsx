/* ORBIT — chart primitives + shared components */
const { useState, useEffect, useMemo, useRef } = React;

// ---------- Donut ----------
function Donut({ value, size=170, stroke=14, color="var(--orbit-green)", track="rgba(255,255,255,.06)", label, subLabel }){
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const v = Math.max(0, Math.min(100, value));
  const off = c * (1 - v/100);
  return React.createElement("div",{className:"donut-wrap"},
    React.createElement("div",{className:"donut",style:{width:size,height:size}},
      React.createElement("svg",{width:size,height:size},
        React.createElement("circle",{cx:size/2,cy:size/2,r,stroke:track,strokeWidth:stroke,fill:"none"}),
        React.createElement("circle",{
          cx:size/2,cy:size/2,r,stroke:color,strokeWidth:stroke,fill:"none",
          strokeDasharray:c, strokeDashoffset:off, strokeLinecap:"round",
          transform:`rotate(-90 ${size/2} ${size/2})`,
          style:{filter:"drop-shadow(0 0 8px "+color+")"}
        }),
      ),
      React.createElement("div",{className:"donut-center"},
        React.createElement("div",null,
          React.createElement("div",{className:"v"}, label || (v.toFixed(1)+"%")),
          subLabel && React.createElement("div",{className:"l"}, subLabel)
        )
      )
    )
  );
}

// ---------- Sparkline ----------
function Sparkline({ data, w=80, h=28, color="var(--orbit-green)", fill=true }){
  if(!data||!data.length) return null;
  const min = Math.min(...data), max = Math.max(...data);
  const span = max-min || 1;
  const step = w/(data.length-1);
  const pts = data.map((y,i)=>[i*step, h - ((y-min)/span)*h]);
  const path = pts.map((p,i)=>(i?"L":"M")+p[0].toFixed(1)+","+p[1].toFixed(1)).join(" ");
  const area = path + ` L ${w},${h} L 0,${h} Z`;
  return React.createElement("svg",{width:w,height:h,style:{display:"block"}},
    fill && React.createElement("path",{d:area, fill:color, opacity:.18}),
    React.createElement("path",{d:path, fill:"none", stroke:color, strokeWidth:1.6, strokeLinecap:"round", strokeLinejoin:"round"})
  );
}

// ---------- Horizontal bar list ----------
function HBars({ rows, max, valueFmt=(n)=>n }){
  const m = max || Math.max(...rows.map(r=>r.value));
  return React.createElement("div",{style:{display:"flex",flexDirection:"column",gap:14}},
    rows.map((r,i)=>{
      const pct = m? (r.value/m)*100 : 0;
      const tgtPct = r.target? (r.target/m)*100 : null;
      const color = r.color || "var(--orbit-green)";
      return React.createElement("div",{key:i},
        React.createElement("div",{className:"row between",style:{marginBottom:6}},
          React.createElement("div",{className:"row",style:{gap:8}},
            r.dot && React.createElement("span",{style:{width:8,height:8,borderRadius:4,background:r.dot}}),
            React.createElement("b",{style:{fontSize:13}}, r.label),
            r.tag && React.createElement("span",{className:"chip "+(r.tagKind||"")}, r.tag)
          ),
          React.createElement("div",{className:"tnum",style:{fontSize:13,fontWeight:600}},
            valueFmt(r.value),
            r.delta!=null && React.createElement("span",{
              className:"kpi-delta " + (r.delta>=0?"up":"down"),
              style:{marginLeft:8,fontSize:11,fontWeight:600}
            }, (r.delta>=0?"+":"")+r.delta.toFixed(1)+"%")
          )
        ),
        React.createElement("div",{
          className:"bar"+(r.target?" target":""),
          style:tgtPct!=null?{"--target":tgtPct+"%"}:{}
        },
          React.createElement("i",{style:{width:Math.min(pct,100)+"%", background:color, boxShadow:"0 0 10px "+color}})
        )
      );
    })
  );
}

// ---------- Cumulative line chart (real vs plan) ----------
function CumulativeChart({ data, h=240 }){
  const w = 760;
  const pad = {l:42,r:14,t:14,b:24};
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const xs = data.map(d=>d.d);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMax = Math.max(...data.map(d => Math.max(d.real||0, d.plan||0)));
  const x = v => pad.l + (v - xMin)/(xMax-xMin)*innerW;
  const y = v => pad.t + (1 - v/yMax)*innerH;

  const planPath = data.map((d,i)=>(i?"L":"M")+x(d.d)+","+y(d.plan)).join(" ");
  const realPts = data.filter(d=>d.real!=null);
  const realPath = realPts.map((d,i)=>(i?"L":"M")+x(d.d)+","+y(d.real)).join(" ");
  const realArea = realPath + ` L ${x(realPts[realPts.length-1].d)},${pad.t+innerH} L ${x(realPts[0].d)},${pad.t+innerH} Z`;
  const todayD = data.find(d=>d.hoy);

  // gridlines
  const gridYs = [0, .25, .5, .75, 1].map(p => yMax * p);

  return React.createElement("svg",{viewBox:`0 0 ${w} ${h}`, width:"100%", style:{display:"block"}},
    React.createElement("defs",null,
      React.createElement("linearGradient",{id:"areaG",x1:0,y1:0,x2:0,y2:1},
        React.createElement("stop",{offset:"0%",stopColor:"#5BC23A",stopOpacity:.45}),
        React.createElement("stop",{offset:"100%",stopColor:"#5BC23A",stopOpacity:0})
      )
    ),
    // grid
    gridYs.map((g,i)=>React.createElement("g",{key:i},
      React.createElement("line",{x1:pad.l,x2:w-pad.r,y1:y(g),y2:y(g),stroke:"rgba(255,255,255,.05)"}),
      React.createElement("text",{x:8,y:y(g)+4,fill:"#6B7686",fontSize:10}, "$"+(g/1e6).toFixed(0)+"M")
    )),
    // today line
    todayD && React.createElement("g",null,
      React.createElement("line",{x1:x(todayD.d),x2:x(todayD.d),y1:pad.t,y2:pad.t+innerH,stroke:"rgba(91,194,58,.4)",strokeDasharray:"3 3"}),
      React.createElement("text",{x:x(todayD.d)+6,y:pad.t+12,fill:"#5BC23A",fontSize:10,fontWeight:600}, "HOY · D"+todayD.d)
    ),
    // plan
    React.createElement("path",{d:planPath, fill:"none", stroke:"rgba(255,255,255,.35)", strokeWidth:1.6, strokeDasharray:"5 4"}),
    // real area + line
    React.createElement("path",{d:realArea, fill:"url(#areaG)"}),
    React.createElement("path",{d:realPath, fill:"none", stroke:"#5BC23A", strokeWidth:2.2, strokeLinejoin:"round", strokeLinecap:"round", style:{filter:"drop-shadow(0 0 6px rgba(91,194,58,.5))"}}),
    // x labels
    [1,5,10,15,19,25,30].map(d=>React.createElement("text",{key:d, x:x(d), y:h-6, fill:"#6B7686", fontSize:10, textAnchor:"middle"}, d))
  );
}

// ---------- Stacked bar (segmento por vendedor) ----------
function StackedBars({ rows, segments }){
  // rows: [{label, values:[v1,v2,v3]}], segments: [{name,color}]
  const maxTotal = Math.max(...rows.map(r=>r.values.reduce((a,b)=>a+b,0))) || 1;
  return React.createElement("div",{style:{display:"flex",flexDirection:"column",gap:12}},
    rows.map((r,i)=>{
      const total = r.values.reduce((a,b)=>a+b,0);
      return React.createElement("div",{key:i},
        React.createElement("div",{className:"row between",style:{marginBottom:5}},
          React.createElement("b",{style:{fontSize:12}}, r.label),
          React.createElement("span",{className:"muted tnum",style:{fontSize:11}}, total+" clientes")
        ),
        React.createElement("div",{style:{display:"flex",height:16,borderRadius:6,overflow:"hidden",background:"rgba(255,255,255,.04)"}},
          r.values.map((v,j)=>React.createElement("div",{key:j,style:{
            width:(v/maxTotal*100)+"%", background:segments[j].color, opacity:.85
          }, title: segments[j].name+": "+v}))
        )
      );
    })
  );
}

// ---------- Vendor avatar dot ----------
function VDot({ v, size=26 }){
  const initials = v.nombre.split(" ").map(s=>s[0]).slice(0,2).join("");
  return React.createElement("span",{className:"v-dot",style:{
    width:size,height:size, background:v.color, fontSize:Math.round(size*.42)
  }}, initials);
}

// ---------- Status pill ----------
function StatusPill({ status }){
  const map = {
    aprobada:{kind:"ok",label:"APROBADA"},
    enviada:{kind:"info",label:"ENVIADA"},
    modificada:{kind:"violet",label:"MODIFICADA"},
    pendiente:{kind:"warn",label:"PENDIENTE"},
  };
  const c = map[status] || {kind:"",label:status?.toUpperCase()};
  return React.createElement("span",{className:"chip chip-dot "+c.kind}, c.label);
}

// ---------- KPI card ----------
function KpiCard({ label, value, unit, kind, icon, delta, deltaLabel, hint, spark }){
  return React.createElement("div",{className:"kpi "+(kind||"")},
    React.createElement("div",{className:"kpi-head"},
      React.createElement("div",{className:"kpi-label"}, label),
      icon && React.createElement("div",{className:"kpi-icon "+(kind||"")}, icon)
    ),
    React.createElement("div",{className:"kpi-value"},
      value,
      unit && React.createElement("span",{className:"unit"}, unit)
    ),
    React.createElement("div",{className:"kpi-foot"},
      React.createElement("span",{className:"muted",style:{fontSize:11.5}}, hint || ""),
      delta!=null
        ? React.createElement("span",{className:"kpi-delta "+(delta>=0?"up":"down")},
            React.createElement(delta>=0?Ic.arrowUp:Ic.arrowDown,{size:11,stroke:3}),
            (delta>=0?"+":"")+delta.toFixed(1)+"%",
            deltaLabel && React.createElement("span",{className:"muted",style:{fontWeight:400,marginLeft:3}}, deltaLabel))
        : spark
          ? React.createElement("div",{className:"kpi-spark"}, spark)
          : null
    )
  );
}

window.Donut = Donut;
window.Sparkline = Sparkline;
window.HBars = HBars;
window.CumulativeChart = CumulativeChart;
window.StackedBars = StackedBars;
window.VDot = VDot;
window.StatusPill = StatusPill;
window.KpiCard = KpiCard;
