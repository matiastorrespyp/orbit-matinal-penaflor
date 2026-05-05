/* ORBIT — icon set (inline SVG, stroked) */
const I = ({d, size=16, fill=false, stroke=2}) =>
  React.createElement("svg",{
    className:"ico", width:size, height:size, viewBox:"0 0 24 24",
    fill:fill?"currentColor":"none", stroke:"currentColor",
    strokeWidth:stroke, strokeLinecap:"round", strokeLinejoin:"round"
  }, d.map((p,i)=>React.createElement(p[0],Object.assign({key:i},p[1]))));

const Ic = {
  dashboard: (p)=>React.createElement(I,Object.assign({d:[
    ["rect",{x:3,y:3,width:7,height:9,rx:1.5}],
    ["rect",{x:14,y:3,width:7,height:5,rx:1.5}],
    ["rect",{x:14,y:12,width:7,height:9,rx:1.5}],
    ["rect",{x:3,y:16,width:7,height:5,rx:1.5}],
  ]},p)),
  target: (p)=>React.createElement(I,Object.assign({d:[
    ["circle",{cx:12,cy:12,r:9}],
    ["circle",{cx:12,cy:12,r:5}],
    ["circle",{cx:12,cy:12,r:1.5,fill:"currentColor"}],
  ]},p)),
  plan: (p)=>React.createElement(I,Object.assign({d:[
    ["rect",{x:3,y:4,width:18,height:17,rx:2}],
    ["path",{d:"M3 9h18"}],
    ["path",{d:"M8 3v4M16 3v4"}],
    ["path",{d:"M8 14l2 2 4-4"}],
  ]},p)),
  users: (p)=>React.createElement(I,Object.assign({d:[
    ["circle",{cx:9,cy:8,r:4}],
    ["path",{d:"M2 21c0-3.9 3.1-7 7-7s7 3.1 7 7"}],
    ["circle",{cx:17,cy:6,r:3}],
    ["path",{d:"M22 19c0-2.8-2-5-4.5-5.5"}],
  ]},p)),
  alert: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M12 3 1 21h22L12 3z"}],
    ["path",{d:"M12 10v5"}],
    ["circle",{cx:12,cy:18,r:.6,fill:"currentColor"}],
  ]},p)),
  bottle: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M10 2h4v4l1.5 2.5A4 4 0 0 1 16 11v8a3 3 0 0 1-3 3h-2a3 3 0 0 1-3-3v-8a4 4 0 0 1 .5-2.5L10 6V2z"}],
    ["path",{d:"M9 13h6"}],
  ]},p)),
  chart: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M3 21h18"}],
    ["rect",{x:5,y:13,width:3,height:6,rx:.5}],
    ["rect",{x:11,y:8,width:3,height:11,rx:.5}],
    ["rect",{x:17,y:4,width:3,height:15,rx:.5}],
  ]},p)),
  flame: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M12 22c-4 0-7-2.5-7-6.5 0-3 2-5 3-7 0 1 1 2 2 2 0-3 1-6 4-8 0 3 1 4 2 5 2 1.5 3 3.5 3 6 0 5-3 8.5-7 8.5z"}],
  ]},p)),
  refresh: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M21 12a9 9 0 0 1-15 6.7L3 16"}],
    ["path",{d:"M3 12a9 9 0 0 1 15-6.7L21 8"}],
    ["path",{d:"M21 3v5h-5M3 21v-5h5"}],
  ]},p)),
  download: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M12 3v13"}],
    ["path",{d:"M7 11l5 5 5-5"}],
    ["path",{d:"M5 21h14"}],
  ]},p)),
  send: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M22 2 11 13"}],
    ["path",{d:"M22 2l-7 20-4-9-9-4 20-7z"}],
  ]},p)),
  edit: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M4 20h4l10-10-4-4L4 16v4z"}],
    ["path",{d:"M14 6l4 4"}],
  ]},p)),
  check: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M4 12l5 5L20 6"}],
  ]},p)),
  x: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M6 6l12 12M18 6L6 18"}],
  ]},p)),
  arrowUp: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M12 19V5"}],
    ["path",{d:"M5 12l7-7 7 7"}],
  ]},p)),
  arrowDown: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M12 5v14"}],
    ["path",{d:"M5 12l7 7 7-7"}],
  ]},p)),
  arrowRight: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M5 12h14"}],
    ["path",{d:"M13 5l7 7-7 7"}],
  ]},p)),
  search: (p)=>React.createElement(I,Object.assign({d:[
    ["circle",{cx:11,cy:11,r:7}],
    ["path",{d:"M21 21l-4.5-4.5"}],
  ]},p)),
  filter: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M3 5h18"}],
    ["path",{d:"M6 12h12"}],
    ["path",{d:"M10 19h4"}],
  ]},p)),
  store: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M3 9l1.5-5h15L21 9"}],
    ["path",{d:"M3 9v11h18V9"}],
    ["path",{d:"M3 9c0 2 1.5 3 3 3s3-1 3-3 1.5 3 3 3 3-1 3-3 1.5 3 3 3 3-1 3-3"}],
  ]},p)),
  bell: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9z"}],
    ["path",{d:"M10 21a2 2 0 0 0 4 0"}],
  ]},p)),
  trend: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M3 17l6-6 4 4 8-8"}],
    ["path",{d:"M14 7h7v7"}],
  ]},p)),
  pin: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M12 22s7-7 7-12a7 7 0 1 0-14 0c0 5 7 12 7 12z"}],
    ["circle",{cx:12,cy:10,r:2.5}],
  ]},p)),
  clock: (p)=>React.createElement(I,Object.assign({d:[
    ["circle",{cx:12,cy:12,r:9}],
    ["path",{d:"M12 7v5l3 2"}],
  ]},p)),
  more: (p)=>React.createElement(I,Object.assign({d:[
    ["circle",{cx:5,cy:12,r:1,fill:"currentColor"}],
    ["circle",{cx:12,cy:12,r:1,fill:"currentColor"}],
    ["circle",{cx:19,cy:12,r:1,fill:"currentColor"}],
  ]},p)),
  history: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M3 12a9 9 0 1 0 3-6.7L3 8"}],
    ["path",{d:"M3 3v5h5"}],
    ["path",{d:"M12 7v5l3 2"}],
  ]},p)),
  flag: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M5 21V4"}],
    ["path",{d:"M5 4h12l-2 4 2 4H5"}],
  ]},p)),
  building: (p)=>React.createElement(I,Object.assign({d:[
    ["rect",{x:4,y:2,width:16,height:20,rx:1.5}],
    ["path",{d:"M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2"}],
    ["path",{d:"M10 22v-4h4v4"}],
  ]},p)),
  zap: (p)=>React.createElement(I,Object.assign({d:[
    ["path",{d:"M13 2 4 14h7l-1 8 9-12h-7l1-8z"}],
  ]},p)),
};
window.Ic = Ic;
