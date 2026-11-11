import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, XAxis, YAxis } from "recharts";
import { Plus, TrendingDown, TrendingUp } from "lucide-react";
import { get, qs } from "../api/client";
import { InsightCard } from "../components/AI";
import { C, ChartBox, axis, grid, tip } from "../components/charts";
import { EntityForm, human, type FieldDef } from "../components/EntityForm";
import { Badge, Button, Card, Empty, Input, Loading, Modal, PageHeader, Progress, Select, Stat, Tabs, cx } from "../components/ui";
import { fmtDate, money, monthIso, pct, todayIso } from "../lib/format";
import { useCrud, useList } from "../lib/hooks";

type Tab = "overview" | "transactions" | "budgets" | "subscriptions" | "goals";

export default function Finance() {
  const [tab, setTab] = useState<Tab>("overview");
  const [month, setMonth] = useState(monthIso());
  const [edit, setEdit] = useState<any | null>(null);
  const cats = useQuery({ queryKey: ["/finance/categories"], queryFn: () => get("/finance/categories"), staleTime: Infinity });
  const opps = useList("/side-income/opportunities");
  const tx = useCrud("/finance/transactions", ["/finance/summary", "/finance/trends", "/side-income/summary"]);

  const txFields = (kind: string): FieldDef[] => [
    { name: "kind", label: "Type", type: "select", options: ["expense", "income"], required: true, half: true },
    { name: "amount", label: "Amount (₹)", type: "number", step: "0.01", min: 0.01, required: true, half: true },
    { name: "category", label: "Category", type: "select", options: (kind === "income" ? cats.data?.income : cats.data?.expense) || [], required: true, half: true },
    { name: "date", label: "Date", type: "date", required: true, half: true },
    { name: "description", label: "Description" },
    { name: "payment_method", label: "Payment method", type: "select", options: ["upi", "card", "cash", "bank", "wallet"], half: true },
    { name: "opportunity_id", label: "Side-income project", type: "select", options: (opps.data || []).map((o: any) => ({ value: o.id, label: o.title })), half: true },
    { name: "tags", label: "Tags", type: "tags" },
  ];

  return (
    <div className="fade-in">
      <PageHeader
        title="Money"
        subtitle="Expenses, income, budgets and savings"
        actions={
          <>
            <Button icon={<TrendingUp className="size-4" />} onClick={() => setEdit({ kind: "income", category: "salary", date: todayIso() })}>Income</Button>
            <Button variant="primary" icon={<Plus className="size-4" />} onClick={() => setEdit({ kind: "expense", category: "groceries", date: todayIso(), payment_method: "upi" })}>Expense</Button>
          </>
        }
      />
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Tabs<Tab> value={tab} onChange={setTab} tabs={[{ id: "overview", label: "Overview" }, { id: "transactions", label: "Transactions" }, { id: "budgets", label: "Budgets" }, { id: "subscriptions", label: "Subscriptions" }, { id: "goals", label: "Savings goals" }]} />
        {(tab === "overview" || tab === "budgets" || tab === "transactions") && <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="ml-auto w-40" />}
      </div>
      {tab === "overview" && <Overview month={month} />}
      {tab === "transactions" && <Transactions month={month} onEdit={setEdit} />}
      {tab === "budgets" && <Budgets month={month} cats={cats.data?.expense || []} />}
      {tab === "subscriptions" && <Simple path="/finance/subscriptions" title="subscription" fields={[
        { name: "name", label: "Name", required: true },
        { name: "amount", label: "Amount (₹)", type: "number", step: "0.01", required: true, half: true },
        { name: "billing_cycle", label: "Billing cycle", type: "select", options: ["weekly", "monthly", "quarterly", "yearly"], required: true, half: true },
        { name: "next_due_date", label: "Next due", type: "date", half: true },
        { name: "category", label: "Category", type: "select", options: cats.data?.expense || [], required: true, half: true },
        { name: "active", label: "Active", type: "checkbox" },
        { name: "notes", label: "Notes", type: "textarea" },
      ]} defaults={{ billing_cycle: "monthly", category: "subscriptions", active: true }} render={(s) => (
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1"><div className={cx("text-sm", !s.active && "text-ink-3 line-through")}>{s.name}</div><div className="text-xs text-ink-3">{s.billing_cycle}{s.next_due_date && ` · next ${fmtDate(s.next_due_date)}`}</div></div>
          <div className="text-sm font-medium tabular-nums">{money(s.amount)}</div>
        </div>
      )} />}
      {tab === "goals" && <Simple path="/finance/goals" title="savings goal" fields={[
        { name: "name", label: "Goal", required: true },
        { name: "target_amount", label: "Target (₹)", type: "number", required: true, half: true },
        { name: "saved_amount", label: "Saved so far (₹)", type: "number", half: true },
        { name: "target_date", label: "Target date", type: "date", half: true },
        { name: "notes", label: "Notes", type: "textarea" },
      ]} render={(g) => (
        <div>
          <div className="mb-1 flex justify-between text-sm"><span>{g.name}</span><span className="tabular-nums text-ink-3">{money(g.saved_amount)} / {money(g.target_amount)}</span></div>
          <Progress value={Number(g.saved_amount) / Number(g.target_amount)} tone="good" />
          {g.target_date && <div className="mt-1 text-xs text-ink-3">by {fmtDate(g.target_date, { month: "short", year: "numeric" })}</div>}
        </div>
      )} />}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit transaction" : edit?.kind === "income" ? "Add income" : "Add expense"} wide>
        {edit && <TxForm edit={edit} fields={txFields} onDone={() => setEdit(null)} crud={tx} />}
      </Modal>
    </div>
  );
}

function TxForm({ edit, fields, onDone, crud }: { edit: any; fields: (k: string) => FieldDef[]; onDone: () => void; crud: ReturnType<typeof useCrud> }) {
  return (
    <EntityForm
      fields={fields(edit.kind)}
      initial={edit}
      onSubmit={async (d) => { edit.id ? await crud.update.mutateAsync({ id: edit.id, data: d }) : await crud.create.mutateAsync(d); onDone(); }}
      onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); onDone(); } : undefined}
      submitLabel={edit.id ? "Save" : "Add"}
    />
  );
}

function Overview({ month }: { month: string }) {
  const s = useQuery({ queryKey: ["/finance/summary", month], queryFn: () => get(`/finance/summary${qs({ month })}`) });
  const trends = useQuery<any[]>({ queryKey: ["/finance/trends"], queryFn: () => get("/finance/trends?months=6") });
  if (s.isLoading || !s.data) return <Loading />;
  const d = s.data;
  const pie = Object.entries(d.by_category).map(([name, value]) => ({ name: human(name), value }));
  const daily = Object.entries(d.daily).map(([date, v]) => ({ date: date.slice(8), spend: v }));
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat icon={<TrendingDown className="size-3.5" />} label="Spent" value={money(d.total_expense)} sub={d.budget ? <Progress className="mt-1.5" value={d.budget_used_pct} tone={d.budget_used_pct > 1 ? "bad" : d.budget_used_pct > 0.85 ? "warn" : "accent"} /> : "No budget set"} />
        <Stat icon={<TrendingUp className="size-3.5" />} label="Income" value={money(d.total_income)} sub={d.side_income ? `${money(d.side_income)} from side income` : undefined} />
        <Stat label="Net savings" value={<span className={d.net_savings < 0 ? "text-bad" : ""}>{money(d.net_savings)}</span>} sub={`Savings rate ${pct(d.savings_rate)}`} />
        <Stat label="Subscriptions" value={money(d.subscriptions.monthly_total)} sub={`${d.subscriptions.count} active / month`} />
      </div>
      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3" title="Daily spending">
          {daily.length === 0 ? <Empty title="No expenses this month" /> : (
            <ChartBox>
              <AreaChart data={daily} margin={{ left: -10, right: 8 }}>
                <defs><linearGradient id="sp" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.25} /><stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid {...grid} />
                <XAxis dataKey="date" {...axis} />
                <YAxis {...axis} tickFormatter={(v) => `₹${v >= 1000 ? `${Math.round(v / 1000)}k` : v}`} />
                {tip}
                <Area type="monotone" dataKey="spend" stroke="var(--chart-1)" strokeWidth={2} fill="url(#sp)" />
              </AreaChart>
            </ChartBox>
          )}
        </Card>
        <Card className="lg:col-span-2" title="Where it went">
          {pie.length === 0 ? <Empty title="No data" /> : (
            <>
              <ChartBox height={170}>
                <PieChart>
                  <Pie data={pie} dataKey="value" nameKey="name" innerRadius={50} outerRadius={78} paddingAngle={2} stroke="none">
                    {pie.map((_, i) => <Cell key={i} fill={i < 4 ? C[i] : "var(--chart-5)"} />)}
                  </Pie>
                  {tip}
                </PieChart>
              </ChartBox>
              <div className="mt-2 space-y-1">
                {pie.slice(0, 6).map((p, i) => (
                  <div key={p.name} className="flex items-center gap-2 text-xs"><span className="size-2 rounded-full" style={{ background: i < 4 ? C[i] : "var(--chart-5)" }} /><span className="flex-1 text-ink-2">{p.name}</span><span className="tabular-nums">{money(p.value as number)}</span>{d.category_budgets[Object.keys(d.by_category)[i]] && <Badge tone={d.over_budget_categories.includes(Object.keys(d.by_category)[i]) ? "bad" : "neutral"}>of {money(d.category_budgets[Object.keys(d.by_category)[i]])}</Badge>}</div>
                ))}
              </div>
            </>
          )}
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Last 6 months">
          <ChartBox>
            <BarChart data={trends.data || []} margin={{ left: -10 }}>
              <CartesianGrid {...grid} />
              <XAxis dataKey="month" {...axis} tickFormatter={(m) => new Date(`${m}-01`).toLocaleDateString("en-IN", { month: "short" })} />
              <YAxis {...axis} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
              {tip}
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="income" fill="var(--chart-2)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="expense" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartBox>
        </Card>
        <Card title="Observations">
          {d.observations.length === 0 ? <p className="text-sm text-ink-3">Nothing unusual this month.</p> : (
            <ul className="space-y-2 text-sm text-ink-2">{d.observations.map((o: string) => <li key={o} className="flex gap-2"><span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-warn" />{o}</li>)}</ul>
          )}
        </Card>
      </div>
      <InsightCard kind="finance_insights" title="Financial coach" cta="Analyse my spending" />
    </div>
  );
}

function Transactions({ month, onEdit }: { month: string; onEdit: (t: any) => void }) {
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("");
  const [y, m] = month.split("-").map(Number);
  const to = new Date(y, m, 0).getDate();
  const list = useList("/finance/transactions", qs({ from: `${month}-01`, to: `${month}-${to}`, q, kind, limit: 1000 }));
  const groups = useMemo(() => {
    const g: Record<string, any[]> = {};
    (list.data || []).forEach((t: any) => (g[t.date] ||= []).push(t));
    return Object.entries(g);
  }, [list.data]);
  return (
    <Card>
      <div className="mb-3 flex gap-2">
        <Input placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-xs" />
        <Select value={kind} onChange={(e) => setKind(e.target.value)} className="w-auto"><option value="">All</option><option value="expense">Expenses</option><option value="income">Income</option></Select>
      </div>
      {list.isLoading ? <Loading /> : groups.length === 0 ? <Empty title="No transactions" /> : groups.map(([date, items]) => (
        <div key={date} className="mb-3">
          <div className="mb-1 flex justify-between text-[11px] font-semibold tracking-wide text-ink-3 uppercase"><span>{fmtDate(date, { weekday: "short", day: "numeric", month: "short" })}</span><span>{money(items.filter((t) => t.kind === "expense").reduce((a, t) => a + Number(t.amount), 0))}</span></div>
          <div className="divide-y divide-line">
            {items.map((t) => (
              <button key={t.id} onClick={() => onEdit(t)} className="flex w-full items-center gap-3 py-2 text-left">
                <div className="min-w-0 flex-1"><div className="truncate text-sm">{t.description || human(t.category)}</div><div className="text-[11px] text-ink-3">{human(t.category)}{t.payment_method && ` · ${t.payment_method.toUpperCase()}`}</div></div>
                <div className={cx("text-sm font-medium tabular-nums", t.kind === "income" && "text-good")}>{t.kind === "income" ? "+" : "−"}{money(t.amount)}</div>
              </button>
            ))}
          </div>
        </div>
      ))}
    </Card>
  );
}

function Budgets({ month, cats }: { month: string; cats: string[] }) {
  const s = useQuery({ queryKey: ["/finance/summary", month], queryFn: () => get(`/finance/summary${qs({ month })}`) });
  const budgets = useList("/finance/budgets", qs({ month }));
  const crud = useCrud("/finance/budgets", ["/finance/summary"]);
  const [cat, setCat] = useState("__total__");
  const [amt, setAmt] = useState("");
  const save = async () => {
    const existing = (budgets.data || []).find((b: any) => b.category === cat);
    if (existing) await crud.update.mutateAsync({ id: existing.id, data: { amount: Number(amt) } });
    else await crud.create.mutateAsync({ month, category: cat, amount: Number(amt) });
    setAmt("");
  };
  const spent = s.data?.by_category || {};
  return (
    <Card title={`Budgets for ${new Date(`${month}-01`).toLocaleDateString("en-IN", { month: "long", year: "numeric" })}`}>
      <div className="mb-4 flex flex-wrap gap-2">
        <Select value={cat} onChange={(e) => setCat(e.target.value)} className="w-auto"><option value="__total__">Overall monthly budget</option>{cats.map((c) => <option key={c} value={c}>{human(c)}</option>)}</Select>
        <Input type="number" placeholder="Amount ₹" value={amt} onChange={(e) => setAmt(e.target.value)} className="w-36" />
        <Button variant="primary" onClick={save} disabled={!amt} loading={crud.create.isPending || crud.update.isPending}>Set budget</Button>
      </div>
      {(budgets.data || []).length === 0 ? <Empty title="No budgets this month" hint="Your default monthly budget from Settings is used for the overview until you set one." /> : (
        <div className="space-y-3">
          {(budgets.data || []).map((b: any) => {
            const used = b.category === "__total__" ? s.data?.total_expense || 0 : spent[b.category] || 0;
            const ratio = used / Number(b.amount || 1);
            return (
              <div key={b.id}>
                <div className="mb-1 flex items-center justify-between text-sm"><span>{b.category === "__total__" ? "Overall" : human(b.category)}</span><span className="tabular-nums text-ink-3">{money(used)} / {money(b.amount)} <button className="ml-2 text-xs text-bad" onClick={() => crud.remove.mutate(b.id)}>Remove</button></span></div>
                <Progress value={ratio} tone={ratio > 1 ? "bad" : ratio > 0.85 ? "warn" : "good"} />
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

export function Simple({ path, title, fields, render, defaults = {}, related = [] }: { path: string; title: string; fields: FieldDef[]; render: (x: any) => React.ReactNode; defaults?: Record<string, any>; related?: string[] }) {
  const list = useList(path);
  const crud = useCrud(path, related);
  const [edit, setEdit] = useState<any | null>(null);
  return (
    <Card action={<Button size="sm" variant="primary" icon={<Plus className="size-3.5" />} onClick={() => setEdit({})}>Add {title}</Button>} title={`${human(title)}s`}>
      {list.isLoading ? <Loading /> : (list.data || []).length === 0 ? <Empty title={`No ${title}s yet`} /> : (
        <div className="divide-y divide-line">{(list.data || []).map((x: any) => <button key={x.id} className="block w-full py-2.5 text-left" onClick={() => setEdit(x)}>{render(x)}</button>)}</div>
      )}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? `Edit ${title}` : `New ${title}`} wide>
        {edit && <EntityForm fields={fields} initial={edit.id ? edit : defaults} onSubmit={async (d) => { edit.id ? await crud.update.mutateAsync({ id: edit.id, data: d }) : await crud.create.mutateAsync(d); setEdit(null); }} onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); setEdit(null); } : undefined} />}
      </Modal>
    </Card>
  );
}
