const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
export const money = (n: number | string | null | undefined, currency = "INR") => {
  const v = Number(n || 0);
  if (currency === "INR") return inr.format(v);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 2 }).format(v);
};
export const num = (n: number | null | undefined, d = 0) => (n === null || n === undefined ? "—" : Number(n).toLocaleString("en-IN", { maximumFractionDigits: d }));
export const pct = (n: number | null | undefined) => (n === null || n === undefined ? "—" : `${Math.round(n * 100)}%`);

const pad = (n: number) => String(n).padStart(2, "0");
/** Local YYYY-MM-DD (not UTC). */
export const iso = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const todayIso = () => iso(new Date());
export const addDays = (d: Date, n: number) => {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
};
export const parseIso = (s: string) => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
};
export const fmtDate = (s?: string | null, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" }) => (s ? parseIso(s.slice(0, 10)).toLocaleDateString("en-IN", opts) : "");
export const fmtTime = (s?: string | null) => (s ? new Date(s).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" }) : "");
export const relDay = (s?: string | null) => {
  if (!s) return "";
  const diff = Math.round((parseIso(s).getTime() - parseIso(todayIso()).getTime()) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  if (diff === -1) return "Yesterday";
  if (diff < 0) return `${-diff}d overdue`;
  if (diff < 7) return parseIso(s).toLocaleDateString("en-IN", { weekday: "short" });
  return fmtDate(s);
};
export const monthIso = (d = new Date()) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
export const greeting = () => {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
};

/** Indian short form for large amounts: ₹4.6L, ₹1.25Cr. */
export const moneyShort = (n: number | string | null | undefined) => {
  const v = Number(n || 0);
  const a = Math.abs(v);
  const sign = v < 0 ? "−" : "";
  if (a >= 1e7) return `${sign}₹${(a / 1e7).toFixed(2).replace(/\.?0+$/, "")}Cr`;
  if (a >= 1e5) return `${sign}₹${(a / 1e5).toFixed(2).replace(/\.?0+$/, "")}L`;
  return money(v);
};
