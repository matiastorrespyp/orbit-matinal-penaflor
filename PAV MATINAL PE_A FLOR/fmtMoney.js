window.fmtMoney = n => {
  if (n==null) return "—";
  if (Math.abs(n) >= 1e6) return "$" + (n/1e6).toFixed(1) + "M";
  if (Math.abs(n) >= 1e3) return "$" + (n/1e3).toFixed(0) + "K";
  return "$" + Math.round(n).toLocaleString("es-AR");
};
window.fmtMoneyFull = n => n==null ? "—" : "$" + Math.round(n).toLocaleString("es-AR");
window.fmtPct = n => (n==null ? "—" : (n.toFixed(1).replace(".",",")) + "%");