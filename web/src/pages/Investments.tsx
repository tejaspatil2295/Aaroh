import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, XAxis, YAxis } from "recharts";
import { CalendarClock, Landmark, Plus, TrendingUp, Wallet } from "lucide-react";
import { get } from "../api/client";
import { InsightCard } from "../components/AI";
import { C, ChartBox, axis, grid, tip } from "../components/charts";
import { EntityForm, human, type FieldDef } from "../components/EntityForm";
import { Badge, Button, Card, Empty, Loading, Modal, PageHeader, Stat, Tabs, cx } from "../components/ui";
import { fmtDate, money, moneyShort, todayIso } from "../lib/format";
import { useCrud, useList } from "../lib/hooks";

type Tab = "overview" | "holdings" | "loans";
const RELATED = ["/investments/summary", "/dashboard"];
const PALETTE = C;

const ASSET_OPTIONS = [
  ["mutual_fund", "Mutual fund"], ["stock", "Stock"], ["etf", "ETF"], ["fd", "Fixed deposit"], ["rd", "Recurring deposit"],
  ["ppf", "PPF"], ["epf", "EPF / PF"], ["nps", "NPS"], ["gold", "Gold"], ["sgb", "Sovereign gold bond"], ["bonds", "Bonds"],
  ["real_estate", "Real estate"], ["crypto", "Crypto"], ["savings", "Savings / cash"], ["insurance_ulip", "ULIP / endowment"], ["other", "Other"],
].map(([value, label]) => ({ value, label }));
const assetLabel = (v: string) => ASSET_OPTIONS.find((o) => o.value === v)?.label || human(v);
const signed = (n: number) => `${n >= 0 ? "+" : "−"}${moneyShort(Math.abs(n))}`;
const pctSigned = (n: number | null) => (n === null || n === undefined ? "" : `${n >= 0 ? "+" : "−"}${Math.abs(n * 100).toFixed(1)}%`);

export default function Investments() {
  const [tab, setTab] = useState<Tab>("overview");
  const [editHolding, setEditHolding] = useState<any | null>(null);
  const [editLoan, setEditLoan] = useState<any | null>(null);
  const goals = useList("/finance/goals");
  const holdings = useCrud("/investments/holdings", RELATED);
  const loans = useCrud("/investments/liabilities", RELATED);

  const holdingFields: FieldDef[] = [
    { name: "name", label: "Name", required: true, placeholder: "e.g. Nifty 50 index fund, SBI FD, PPF" },
    { name: "asset_class", label: "Type", type: "select", options: ASSET_OPTIONS, required: true, half: true },
    { name: "platform", label: "Where it's held", placeholder: "Groww, Zerodha, SBI…", half: true },
    { name: "invested_amount", label: "Total invested (₹)", type: "number", step: "0.01", min: 0, required: true, half: true },
    { name: "current_value", label: "Current value (₹)", type: "number", step: "0.01", min: 0, required: true, half: true },
    { name: "sip_amount", label: "Monthly SIP (₹)", type: "number", step: "0.01", min: 0, half: true },
    { name: "sip_day", label: "SIP day of month", type: "number", min: 1, max: 28, half: true },
    { name: "interest_rate", label: "Interest rate (% p.a.)", type: "number", step: "0.01", min: 0, half: true, hint: "For FD, RD, PPF, EPF, bonds" },
    { name: "units", label: "Units / quantity", type: "number", step: "0.000001", min: 0, half: true },
    { name: "start_date", label: "Started on", type: "date", half: true },
    { name: "maturity_date", label: "Matures on", type: "date", half: true },
    { name: "risk", label: "Risk", type: "select", options: ["low", "medium", "high"], required: true, half: true },
    { name: "liquidity", label: "Can you withdraw quickly?", type: "select", options: [{ value: "high", label: "Yes, within days" }, { value: "medium", label: "With some cost/delay" }, { value: "locked", label: "Locked in" }], required: true, half: true },
    { name: "financial_goal_id", label: "Linked savings goal", type: "select", options: (goals.data || []).map((g: any) => ({ value: g.id, label: g.name })) },
    { name: "value_updated_on", label: "Value as of", type: "date", half: true, hint: "Updates automatically when you change the value" },
    { name: "active", label: "Still holding", type: "checkbox", half: true },
    { name: "notes", label: "Notes", type: "textarea" },
  ];
  const loanFields: FieldDef[] = [
    { name: "name", label: "Name", required: true, placeholder: "e.g. Home loan, Credit card" },
    { name: "kind", label: "Type", type: "select", options: ["home_loan", "car_loan", "personal_loan", "education_loan", "credit_card", "gold_loan", "borrowed_family", "other"], required: true, half: true },
    { name: "lender", label: "Lender", half: true },
    { name: "outstanding", label: "Outstanding (₹)", type: "number", step: "0.01", min: 0, required: true, half: true },
    { name: "principal", label: "Original amount (₹)", type: "number", step: "0.01", min: 0, half: true },
    { name: "interest_rate", label: "Interest rate (% p.a.)", type: "number", step: "0.01", min: 0, half: true },
    { name: "emi", label: "EMI (₹)", type: "number", step: "0.01", min: 0, half: true },
    { name: "emi_day", label: "EMI day of month", type: "number", min: 1, max: 28, half: true },
    { name: "end_date", label: "Ends on", type: "date", half: true },
    { name: "active", label: "Still open", type: "checkbox", half: true },
    { name: "notes", label: "Notes", type: "textarea" },
  ];

  return (
    <div className="fade-in">
      <PageHeader
        title="Investments"
        subtitle="Net worth, holdings, SIPs and loans"
        actions={
          <>
            <Button icon={<Landmark className="size-4" />} onClick={() => setEditLoan({ kind: "personal_loan", active: true })}>Loan</Button>
            <Button variant="primary" icon={<Plus className="size-4" />} onClick={() => setEditHolding({ asset_class: "mutual_fund", risk: "medium", liquidity: "medium", active: true, start_date: todayIso() })}>Investment</Button>
          </>
        }
      />
      <div className="mb-4">
        <Tabs<Tab> value={tab} onChange={setTab} tabs={[{ id: "overview", label: "Overview" }, { id: "holdings", label: "Holdings" }, { id: "loans", label: "Loans" }]} />
      </div>
      {tab === "overview" && <Overview onAdd={() => setEditHolding({ asset_class: "mutual_fund", risk: "medium", liquidity: "medium", active: true })} />}
      {tab === "holdings" && <Holdings onEdit={setEditHolding} />}
      {tab === "loans" && <Loans onEdit={setEditLoan} />}

      <Modal open={!!editHolding} onClose={() => setEditHolding(null)} title={editHolding?.id ? "Edit investment" : "Add investment"} wide>
        {editHolding && (
          <EntityForm
            fields={holdingFields}
            initial={editHolding}
            submitLabel={editHolding.id ? "Save" : "Add"}
            onSubmit={async (d) => { editHolding.id ? await holdings.update.mutateAsync({ id: editHolding.id, data: d }) : await holdings.create.mutateAsync(d); setEditHolding(null); }}
            onDelete={editHolding.id ? async () => { await holdings.remove.mutateAsync(editHolding.id); setEditHolding(null); } : undefined}
          />
        )}
      </Modal>
      <Modal open={!!editLoan} onClose={() => setEditLoan(null)} title={editLoan?.id ? "Edit loan" : "Add loan"} wide>
        {editLoan && (
          <EntityForm
            fields={loanFields}
            initial={editLoan}
            submitLabel={editLoan.id ? "Save" : "Add"}
            onSubmit={async (d) => { editLoan.id ? await loans.update.mutateAsync({ id: editLoan.id, data: d }) : await loans.create.mutateAsync(d); setEditLoan(null); }}
            onDelete={editLoan.id ? async () => { await loans.remove.mutateAsync(editLoan.id); setEditLoan(null); } : undefined}
          />
        )}
      </Modal>
    </div>
  );
}

function useSummary() {
  return useQuery<any>({ queryKey: ["/investments/summary"], queryFn: () => get("/investments/summary") });
}

function Overview({ onAdd }: { onAdd: () => void }) {
  const s = useSummary();
  if (s.isLoading || !s.data) return <Loading />;
  const d = s.data;
  if (!d.holdings.length && !d.liabilities.length) {
    return <Card><Empty title="No investments yet" hint="Add your mutual funds, PPF, EPF, FDs, stocks or gold. AAROH works out your net worth, allocation and returns." action={<Button variant="primary" icon={<Plus className="size-4" />} onClick={onAdd}>Add first investment</Button>} /></Card>;
  }
  // Top 4 classes plus "Other" so every slice gets a distinct colour
  const slices = Object.entries(d.allocation).map(([k, v]) => ({ name: assetLabel(k), value: v as number }));
  const pie = slices.length > 5 ? [...slices.slice(0, 4), { name: "Other", value: slices.slice(4).reduce((a, x) => a + x.value, 0) }] : slices;
  const history = d.history.map((h: any) => ({ ...h, label: fmtDate(h.date, { month: "short", day: "numeric" }) }));
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat icon={<Wallet className="size-3.5" />} label="Net worth" value={<span className={d.net_worth < 0 ? "text-bad" : ""}>{moneyShort(d.net_worth)}</span>} sub={`${moneyShort(d.total_assets)} assets − ${moneyShort(d.total_liabilities)} loans`} />
        <Stat icon={<TrendingUp className="size-3.5" />} label="Investments" value={moneyShort(d.total_assets)} sub={<span className={d.total_gain >= 0 ? "text-good" : "text-bad"}>{signed(d.total_gain)} {pctSigned(d.total_return_pct)} on {moneyShort(d.total_invested)}</span>} />
        <Stat icon={<CalendarClock className="size-3.5" />} label="Monthly SIPs" value={money(d.monthly_sip)} sub={d.monthly_emi ? `EMIs ${money(d.monthly_emi)}` : "No EMIs"} />
        <Stat label="Emergency buffer" value={d.emergency_fund_months === null ? "—" : `${d.emergency_fund_months} mo`} sub="Easily withdrawable money ÷ monthly spend" />
      </div>
      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3" title="Net worth over time">
          {history.length < 2 ? <Empty title="Trend builds up over time" hint="AAROH records your net worth each day you open this page." /> : (
            <ChartBox>
              <AreaChart data={history} margin={{ left: -4, right: 8 }}>
                <defs><linearGradient id="nw" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--chart-2)" stopOpacity={0.3} /><stop offset="100%" stopColor="var(--chart-2)" stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid {...grid} />
                <XAxis dataKey="label" {...axis} />
                <YAxis {...axis} width={56} tickFormatter={(v) => moneyShort(v)} />
                {tip}
                <Area type="monotone" dataKey="net_worth" name="Net worth" stroke="var(--chart-2)" strokeWidth={2} fill="url(#nw)" />
              </AreaChart>
            </ChartBox>
          )}
        </Card>
        <Card className="lg:col-span-2" title="Allocation">
          {pie.length === 0 ? <Empty title="No holdings" /> : (
            <>
              <ChartBox height={170}>
                <PieChart>
                  <Pie data={pie} dataKey="value" nameKey="name" innerRadius={50} outerRadius={78} paddingAngle={2} stroke="none">
                    {pie.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                  </Pie>
                  {tip}
                </PieChart>
              </ChartBox>
              <div className="mt-2 space-y-1">
                {pie.map((p, i) => (
                  <div key={p.name} className="flex items-center gap-2 text-xs">
                    <span className="size-2 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} />
                    <span className="flex-1 text-ink-2">{p.name}</span>
                    <span className="tabular-nums text-ink-3">{Math.round((p.value / d.total_assets) * 100)}%</span>
                    <span className="w-16 text-right tabular-nums">{moneyShort(p.value)}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Coming up (30 days)">
          {d.upcoming.length === 0 ? <p className="text-sm text-ink-3">No SIPs, EMIs or maturities in the next 30 days.</p> : (
            <div className="divide-y divide-line">
              {d.upcoming.map((u: any, i: number) => (
                <div key={i} className="flex items-center gap-3 py-2 text-sm">
                  <span className="w-14 text-xs text-ink-3">{fmtDate(u.date, { day: "numeric", month: "short" })}</span>
                  <span className="min-w-0 flex-1 truncate">{u.name}</span>
                  <Badge tone={u.kind === "emi" ? "warn" : u.kind === "maturity" ? "good" : "accent"}>{u.kind === "sip" ? "SIP" : u.kind === "emi" ? "EMI" : "Matures"}</Badge>
                  <span className="w-20 text-right tabular-nums">{moneyShort(u.amount)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
        <Card title="Observations">
          {d.observations.length === 0 ? <p className="text-sm text-ink-3">Nothing needs attention.</p> : (
            <ul className="space-y-2 text-sm text-ink-2">{d.observations.map((o: string) => <li key={o} className="flex gap-2"><span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-warn" />{o}</li>)}</ul>
          )}
          <p className="mt-3 text-[11px] text-ink-3">Values are what you enter; AAROH does not fetch market prices. General information, not investment advice.</p>
        </Card>
      </div>
      <InsightCard kind="investment_review" title="Investment review" cta="Review my portfolio" />
    </div>
  );
}

function Holdings({ onEdit }: { onEdit: (h: any) => void }) {
  const list = useList("/investments/holdings");
  const s = useSummary();
  const perf = Object.fromEntries((s.data?.holdings || []).map((h: any) => [h.id, h]));
  const rows = (list.data || []) as any[];
  return (
    <Card title={`${rows.length} holding${rows.length === 1 ? "" : "s"}`}>
      {list.isLoading ? <Loading /> : rows.length === 0 ? <Empty title="No investments yet" /> : (
        <div className="divide-y divide-line">
          {rows.map((h) => {
            const gain = Number(h.current_value) - Number(h.invested_amount);
            const p = perf[h.id];
            const stale = !h.value_updated_on || (Date.now() - new Date(h.value_updated_on).getTime()) / 864e5 > 45;
            return (
              <button key={h.id} onClick={() => onEdit(h)} className="flex w-full items-center gap-3 py-2.5 text-left">
                <div className="min-w-0 flex-1">
                  <div className={cx("truncate text-sm", !h.active && "text-ink-3 line-through")}>{h.name}</div>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-ink-3">
                    <span>{assetLabel(h.asset_class)}</span>
                    {h.platform && <span>· {h.platform}</span>}
                    {h.sip_amount && <span>· SIP {money(h.sip_amount)}{h.sip_day ? ` on ${h.sip_day}` : ""}</span>}
                    {h.interest_rate && <span>· {Number(h.interest_rate)}%</span>}
                    {stale && h.asset_class !== "savings" && <Badge tone="warn">update value</Badge>}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium tabular-nums">{moneyShort(h.current_value)}</div>
                  <div className={cx("text-[11px] tabular-nums", gain >= 0 ? "text-good" : "text-bad")}>{signed(gain)} {p?.return_pct != null ? pctSigned(p.return_pct) : ""}</div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function Loans({ onEdit }: { onEdit: (l: any) => void }) {
  const list = useList("/investments/liabilities");
  const rows = (list.data || []) as any[];
  const total = rows.filter((l) => l.active).reduce((a, l) => a + Number(l.outstanding), 0);
  return (
    <Card title={`Loans · ${moneyShort(total)} outstanding`}>
      {list.isLoading ? <Loading /> : rows.length === 0 ? <Empty title="No loans" hint="Add home, vehicle, personal or education loans and credit-card balances so net worth is accurate." /> : (
        <div className="divide-y divide-line">
          {rows.map((l) => (
            <button key={l.id} onClick={() => onEdit(l)} className="flex w-full items-center gap-3 py-2.5 text-left">
              <div className="min-w-0 flex-1">
                <div className={cx("truncate text-sm", !l.active && "text-ink-3 line-through")}>{l.name}</div>
                <div className="flex flex-wrap items-center gap-x-2 text-[11px] text-ink-3">
                  <span>{human(l.kind)}</span>
                  {l.lender && <span>· {l.lender}</span>}
                  {l.emi && <span>· EMI {money(l.emi)}{l.emi_day ? ` on ${l.emi_day}` : ""}</span>}
                  {l.interest_rate && <Badge tone={Number(l.interest_rate) >= 12 ? "bad" : "neutral"}>{Number(l.interest_rate)}%</Badge>}
                </div>
              </div>
              <div className="text-sm font-medium tabular-nums">{moneyShort(l.outstanding)}</div>
            </button>
          ))}
        </div>
      )}
    </Card>
  );
}
