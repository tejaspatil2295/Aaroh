import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { CalendarDays, ChevronLeft, ChevronRight, Plus, Sparkles, Wand2 } from "lucide-react";
import { get, post, qs } from "../api/client";
import { EntityForm, type FieldDef } from "../components/EntityForm";
import { Badge, Button, Card, Empty, ErrorNote, Field, Input, Loading, Modal, PageHeader, Progress, Select, Tabs, cx } from "../components/ui";
import { addDays, fmtDate, fmtTime, iso, parseIso, pct, todayIso } from "../lib/format";
import { useCrud, useInvalidate, useList } from "../lib/hooks";
import { TaskRow } from "./Dashboard";

const CATS = ["personal", "professional", "fitness", "learning", "finance", "side_income", "household"];
const AREAS = ["personal", "career", "finance", "fitness", "learning", "side_income", "work", "health", "relationships"];

export const taskFields = (goals: any[] = []): FieldDef[] => [
  { name: "title", label: "Title", required: true },
  { name: "category", label: "Category", type: "select", options: CATS, required: true, half: true },
  { name: "priority", label: "Priority", type: "select", options: ["low", "medium", "high", "urgent"], required: true, half: true },
  { name: "due_date", label: "Due date", type: "date", half: true },
  { name: "estimate_minutes", label: "Estimate (minutes)", type: "number", half: true, min: 1 },
  { name: "scheduled_start", label: "Scheduled start", type: "datetime", half: true },
  { name: "reminder_at", label: "Reminder", type: "datetime", half: true },
  { name: "recurrence", label: "Repeats", type: "select", options: ["none", "daily", "weekdays", "weekly", "monthly"], required: true, half: true },
  { name: "status", label: "Status", type: "select", options: ["todo", "in_progress", "done", "cancelled"], required: true, half: true },
  { name: "goal_id", label: "Linked goal", type: "select", options: goals.map((g) => ({ value: g.id, label: g.title })) },
  { name: "description", label: "Notes", type: "textarea" },
  { name: "tags", label: "Tags", type: "tags" },
];

type Tab = "list" | "calendar" | "goals" | "habits";

export default function Tasks() {
  const [sp, setSp] = useSearchParams();
  const tab = (sp.get("tab") as Tab) || "list";
  return (
    <div className="fade-in">
      <PageHeader title="Plan" subtitle="Tasks, calendar, goals and habits" />
      <div className="mb-4">
        <Tabs<Tab> value={tab} onChange={(t) => setSp({ tab: t })} tabs={[{ id: "list", label: "Tasks" }, { id: "calendar", label: "Calendar" }, { id: "goals", label: "Goals" }, { id: "habits", label: "Habits" }]} />
      </div>
      {tab === "list" && <TaskList />}
      {tab === "calendar" && <CalendarView />}
      {tab === "goals" && <Goals />}
      {tab === "habits" && <Habits />}
    </div>
  );
}

function TaskList() {
  const [status, setStatus] = useState("open");
  const [cat, setCat] = useState("");
  const [q, setQ] = useState("");
  const [edit, setEdit] = useState<any | null>(null);
  const [planOpen, setPlanOpen] = useState(false);
  const [breakOpen, setBreakOpen] = useState(false);
  const goals = useList("/goals", qs({ status: "active" }));
  const params = qs({ category: cat, q, status: status === "open" ? undefined : status, limit: 500 });
  const tasks = useList("/tasks", params);
  const crud = useCrud("/tasks", ["/tasks/calendar"]);
  const inv = useInvalidate();
  const list = useMemo(() => (tasks.data || []).filter((t: any) => (status === "open" ? ["todo", "in_progress"].includes(t.status) : true)), [tasks.data, status]);
  const groups = useMemo(() => {
    const today = todayIso();
    const g: Record<string, any[]> = { Overdue: [], Today: [], Upcoming: [], "No date": [], Done: [] };
    list.forEach((t: any) => {
      if (t.status === "done" || t.status === "cancelled") g.Done.push(t);
      else if (!t.due_date) g["No date"].push(t);
      else if (t.due_date < today) g.Overdue.push(t);
      else if (t.due_date === today) g.Today.push(t);
      else g.Upcoming.push(t);
    });
    return Object.entries(g).filter(([, v]) => v.length);
  }, [list]);

  const toggle = async (id: string) => {
    const t = list.find((x: any) => x.id === id);
    if (t?.status === "done") await crud.update.mutateAsync({ id, data: { status: "todo" } });
    else {
      await post(`/tasks/${id}/complete`);
      inv("/tasks", "/tasks/calendar");
    }
  };

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input placeholder="Search tasks" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-[220px]" />
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-auto">
          <option value="open">Open</option>
          <option value="done">Done</option>
          <option value="">All</option>
        </Select>
        <Select value={cat} onChange={(e) => setCat(e.target.value)} className="w-auto">
          <option value="">All categories</option>
          {CATS.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
        </Select>
        <div className="ml-auto flex gap-2">
          <Button icon={<Wand2 className="size-4" />} onClick={() => setBreakOpen(true)}>Break down</Button>
          <Button icon={<CalendarDays className="size-4" />} onClick={() => setPlanOpen(true)}>Plan my day</Button>
          <Button variant="primary" icon={<Plus className="size-4" />} onClick={() => setEdit({})}>Task</Button>
        </div>
      </div>
      <Card>
        {tasks.isLoading ? <Loading /> : groups.length === 0 ? <Empty title="No tasks here" hint="Add a task or change the filters." /> : groups.map(([name, items]) => (
          <div key={name} className="mb-3 last:mb-0">
            <div className={cx("mb-1 text-[11px] font-semibold tracking-wide uppercase", name === "Overdue" ? "text-bad" : "text-ink-3")}>{name} · {items.length}</div>
            <div className="divide-y divide-line">
              {items.map((t: any) => (
                <div key={t.id} className="cursor-pointer" onClick={(e) => { if (!(e.target as HTMLElement).closest("button")) setEdit(t); }}>
                  <TaskRow t={t} onDone={toggle} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </Card>
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit task" : "New task"} wide>
        {edit && (
          <EntityForm
            fields={taskFields(goals.data)}
            initial={edit.id ? edit : { category: "personal", priority: "medium", recurrence: "none", status: "todo", due_date: todayIso() }}
            onSubmit={async (data) => { edit.id ? await crud.update.mutateAsync({ id: edit.id, data }) : await crud.create.mutateAsync(data); setEdit(null); }}
            onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); setEdit(null); } : undefined}
          />
        )}
      </Modal>
      <PlanModal open={planOpen} onClose={() => setPlanOpen(false)} />
      <BreakdownModal open={breakOpen} onClose={() => setBreakOpen(false)} goals={goals.data || []} />
    </>
  );
}

function PlanModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [date, setDate] = useState(todayIso());
  const [plan, setPlan] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const inv = useInvalidate();
  const run = async (apply: boolean) => {
    setBusy(true);
    setErr(null);
    try {
      setPlan(await post("/tasks/plan", { date, apply }));
      if (apply) inv("/tasks", "/tasks/calendar");
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal open={open} onClose={onClose} title="Smart daily plan" wide>
      <p className="mb-3 text-sm text-ink-3">Fits your open tasks into your configured day window, ordering by overdue, due date, priority and how often a task has been postponed.</p>
      <div className="mb-3 flex items-end gap-2">
        <Field label="Day"><Input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        <Button onClick={() => run(false)} loading={busy && !plan}>Preview</Button>
      </div>
      <ErrorNote error={err} />
      {plan && (
        <>
          <div className="mb-2 text-xs text-ink-3">{plan.planned_minutes} of {plan.available_minutes} available minutes planned{plan.applied && " · saved to calendar"}</div>
          <div className="divide-y divide-line rounded-xl border border-line">
            {plan.plan.length === 0 && <div className="p-3 text-sm text-ink-3">No tasks fit this window.</div>}
            {plan.plan.map((p: any) => (
              <div key={p.task_id} className="flex items-center gap-3 px-3 py-2 text-sm">
                <span className="w-24 shrink-0 tabular-nums text-ink-3">{fmtTime(p.start)}–{fmtTime(p.end)}</span>
                <span className="min-w-0 flex-1 truncate">{p.title}</span>
                <Badge tone={p.fixed ? "neutral" : "accent"}>{p.reason}</Badge>
              </div>
            ))}
          </div>
          {plan.unscheduled.length > 0 && <p className="mt-2 text-xs text-ink-3">Didn't fit: {plan.unscheduled.map((u: any) => u.title).join(", ")}</p>}
          <div className="mt-4 flex justify-end"><Button variant="primary" onClick={() => run(true)} loading={busy} disabled={plan.applied}>Apply to calendar</Button></div>
        </>
      )}
    </Modal>
  );
}

function BreakdownModal({ open, onClose, goals }: { open: boolean; onClose: () => void; goals: any[] }) {
  const [title, setTitle] = useState("");
  const [goal, setGoal] = useState("");
  const [cat, setCat] = useState("learning");
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const inv = useInvalidate();
  const run = async (create: boolean) => {
    setBusy(true);
    setErr(null);
    try {
      const r = await post("/tasks/breakdown", { title, goal_id: goal || null, category: cat, create });
      setRes(r);
      if (create) { inv("/tasks"); onClose(); setRes(null); setTitle(""); }
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal open={open} onClose={onClose} title="Break a goal into tasks" wide>
      <div className="space-y-3">
        <Field label="What do you want to achieve?"><Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Learn Kubernetes basics and deploy my portfolio app" /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Category"><Select value={cat} onChange={(e) => setCat(e.target.value)}>{CATS.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}</Select></Field>
          <Field label="Goal (optional)"><Select value={goal} onChange={(e) => setGoal(e.target.value)}><option value="">—</option>{goals.map((g) => <option key={g.id} value={g.id}>{g.title}</option>)}</Select></Field>
        </div>
        <ErrorNote error={err} />
        {res && (
          <div className="divide-y divide-line rounded-xl border border-line">
            {res.items.map((it: any, i: number) => (
              <div key={i} className="flex items-center gap-2 px-3 py-2 text-sm"><span className="flex-1">{it.title}</span><span className="text-xs text-ink-3">{it.estimate_minutes}m · day +{it.day_offset}</span></div>
            ))}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button icon={<Sparkles className="size-4" />} onClick={() => run(false)} loading={busy && !res} disabled={title.length < 3}>Suggest steps</Button>
          {res && <Button variant="primary" onClick={() => run(true)} loading={busy}>Create these tasks</Button>}
        </div>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------- calendar
function CalendarView() {
  const [view, setView] = useState<"day" | "week" | "month">("week");
  const [anchor, setAnchor] = useState(new Date());
  const [edit, setEdit] = useState<any | null>(null);
  const crud = useCrud("/tasks", ["/tasks/calendar"]);
  const goals = useList("/goals", qs({ status: "active" }));
  const range = useMemo(() => {
    if (view === "day") return [anchor, anchor];
    if (view === "week") {
      const s = addDays(anchor, -((anchor.getDay() + 6) % 7));
      return [s, addDays(s, 6)];
    }
    const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
    const s = addDays(first, -((first.getDay() + 6) % 7));
    return [s, addDays(s, 41)];
  }, [view, anchor]);
  const { data = [], isLoading } = useQuery<any[]>({ queryKey: ["/tasks/calendar", iso(range[0]), iso(range[1])], queryFn: () => get(`/tasks/calendar${qs({ from: iso(range[0]), to: iso(range[1]) })}`) });
  const byDay = useMemo(() => {
    const m: Record<string, any[]> = {};
    data.forEach((t) => {
      const k = t.scheduled_start ? iso(new Date(t.scheduled_start)) : t.due_date;
      (m[k] ||= []).push(t);
    });
    return m;
  }, [data]);
  const step = (dir: number) => setAnchor((a) => (view === "day" ? addDays(a, dir) : view === "week" ? addDays(a, 7 * dir) : new Date(a.getFullYear(), a.getMonth() + dir, 1)));
  const days = Array.from({ length: Math.round((range[1].getTime() - range[0].getTime()) / 86400000) + 1 }, (_, i) => addDays(range[0], i));
  const label = view === "month" ? anchor.toLocaleDateString("en-IN", { month: "long", year: "numeric" }) : view === "week" ? `${fmtDate(iso(range[0]))} – ${fmtDate(iso(range[1]))}` : fmtDate(iso(anchor), { weekday: "long", day: "numeric", month: "long" });

  const chip = (t: any) => (
    <button key={t.id} onClick={() => setEdit(t)} className={cx("block w-full truncate rounded-md px-1.5 py-0.5 text-left text-[11px]", t.status === "done" ? "bg-surface-2 text-ink-3 line-through" : "bg-accent-soft text-accent")}>
      {t.scheduled_start && <span className="mr-1 opacity-70">{fmtTime(t.scheduled_start)}</span>}
      {t.title}
    </button>
  );

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1">
          <Button size="sm" variant="ghost" onClick={() => step(-1)} aria-label="Previous"><ChevronLeft className="size-4" /></Button>
          <Button size="sm" variant="ghost" onClick={() => setAnchor(new Date())}>Today</Button>
          <Button size="sm" variant="ghost" onClick={() => step(1)} aria-label="Next"><ChevronRight className="size-4" /></Button>
        </div>
        <div className="text-sm font-semibold">{label}</div>
        <div className="ml-auto"><Tabs value={view} onChange={setView} tabs={[{ id: "day", label: "Day" }, { id: "week", label: "Week" }, { id: "month", label: "Month" }]} /></div>
      </div>
      {isLoading ? <Loading /> : view === "day" ? (
        <div className="divide-y divide-line">
          {(byDay[iso(anchor)] || []).length === 0 && <Empty title="Nothing scheduled" />}
          {(byDay[iso(anchor)] || []).sort((a, b) => (a.scheduled_start || "z").localeCompare(b.scheduled_start || "z")).map((t) => (
            <button key={t.id} onClick={() => setEdit(t)} className="flex w-full items-center gap-3 py-2.5 text-left text-sm">
              <span className="w-16 shrink-0 tabular-nums text-ink-3">{t.scheduled_start ? fmtTime(t.scheduled_start) : "Any time"}</span>
              <span className={cx("flex-1", t.status === "done" && "text-ink-3 line-through")}>{t.title}</span>
              <Badge>{t.category}</Badge>
            </button>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-7 gap-px overflow-hidden rounded-xl border border-line bg-line text-xs">
          {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => <div key={d} className="bg-surface-2 px-2 py-1.5 font-medium text-ink-3">{d}</div>)}
          {days.map((d) => {
            const k = iso(d);
            const items = byDay[k] || [];
            const other = view === "month" && d.getMonth() !== anchor.getMonth();
            return (
              <div key={k} className={cx("bg-surface p-1.5", view === "week" ? "min-h-40" : "min-h-20", other && "opacity-40")} onDoubleClick={() => setEdit({ due_date: k })}>
                <button onClick={() => { setAnchor(d); setView("day"); }} className={cx("mb-1 grid size-6 place-items-center rounded-full text-[11px]", k === todayIso() ? "bg-accent text-white" : "text-ink-2")}>{d.getDate()}</button>
                <div className="space-y-0.5">{items.slice(0, view === "month" ? 3 : 8).map(chip)}{items.length > (view === "month" ? 3 : 8) && <div className="text-[10px] text-ink-3">+{items.length - 3} more</div>}</div>
              </div>
            );
          })}
        </div>
      )}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit task" : "New task"} wide>
        {edit && (
          <EntityForm
            fields={taskFields(goals.data)}
            initial={edit.id ? edit : { category: "personal", priority: "medium", recurrence: "none", status: "todo", ...edit }}
            onSubmit={async (data) => { edit.id ? await crud.update.mutateAsync({ id: edit.id, data }) : await crud.create.mutateAsync(data); setEdit(null); }}
            onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); setEdit(null); } : undefined}
          />
        )}
      </Modal>
    </Card>
  );
}

// ---------------------------------------------------------------- goals
function Goals() {
  const progress = useQuery<any[]>({ queryKey: ["/goals/progress"], queryFn: () => get("/goals/progress") });
  const goals = useList("/goals");
  const milestones = useList("/milestones");
  const crud = useCrud("/goals", ["/goals/progress"]);
  const ms = useCrud("/milestones", ["/goals/progress"]);
  const [edit, setEdit] = useState<any | null>(null);
  const [newMs, setNewMs] = useState<Record<string, string>>({});
  const prog = Object.fromEntries((progress.data || []).map((p) => [p.id, p]));
  const fields: FieldDef[] = [
    { name: "title", label: "Goal", required: true },
    { name: "area", label: "Area", type: "select", options: AREAS, required: true, half: true },
    { name: "status", label: "Status", type: "select", options: ["active", "completed", "paused", "abandoned"], required: true, half: true },
    { name: "target_date", label: "Target date", type: "date", half: true },
    { name: "metric_unit", label: "Metric unit", placeholder: "kg, ₹, % body fat…", half: true },
    { name: "start_value", label: "Start value", type: "number", step: "any", half: true },
    { name: "target_value", label: "Target value", type: "number", step: "any", half: true },
    { name: "current_value", label: "Current value", type: "number", step: "any", half: true },
    { name: "description", label: "Why it matters", type: "textarea" },
  ];
  return (
    <>
      <div className="mb-3 flex justify-end"><Button variant="primary" icon={<Plus className="size-4" />} onClick={() => setEdit({})}>Goal</Button></div>
      {goals.isLoading ? <Loading /> : (goals.data || []).length === 0 ? <Empty title="No goals yet" hint="Goals connect tasks, habits and milestones so progress is visible." /> : (
        <div className="grid gap-3 md:grid-cols-2">
          {(goals.data || []).map((g: any) => {
            const p = prog[g.id];
            const mine = (milestones.data || []).filter((m: any) => m.goal_id === g.id);
            return (
              <Card key={g.id}>
                <div className="mb-2 flex items-start justify-between gap-2">
                  <button className="text-left" onClick={() => setEdit(g)}>
                    <div className="font-medium">{g.title}</div>
                    <div className="mt-0.5 text-xs text-ink-3 capitalize">{g.area.replace("_", " ")}{g.target_date && ` · by ${fmtDate(g.target_date, { day: "numeric", month: "short", year: "numeric" })}`}</div>
                  </button>
                  <Badge tone={g.status === "active" ? "accent" : g.status === "completed" ? "good" : "neutral"}>{g.status}</Badge>
                </div>
                {p?.progress != null && <><Progress value={p.progress} /><div className="mt-1 text-xs text-ink-3">{pct(p.progress)}{g.target_value != null && ` · ${g.current_value ?? "?"} / ${g.target_value} ${g.metric_unit}`}</div></>}
                <div className="mt-3 space-y-1">
                  {mine.map((m: any) => (
                    <label key={m.id} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={m.done} onChange={() => ms.update.mutate({ id: m.id, data: { done: !m.done } })} className="size-4 accent-[var(--accent)]" />
                      <span className={cx(m.done && "text-ink-3 line-through")}>{m.title}</span>
                      {m.due_date && <span className="ml-auto text-[11px] text-ink-3">{fmtDate(m.due_date)}</span>}
                    </label>
                  ))}
                  <form className="flex gap-2 pt-1" onSubmit={(e) => { e.preventDefault(); if (newMs[g.id]) ms.create.mutate({ goal_id: g.id, title: newMs[g.id] }, { onSuccess: () => setNewMs((s) => ({ ...s, [g.id]: "" })) }); }}>
                    <Input className="h-8 text-[13px]" placeholder="Add milestone" value={newMs[g.id] || ""} onChange={(e) => setNewMs((s) => ({ ...s, [g.id]: e.target.value }))} />
                  </form>
                </div>
              </Card>
            );
          })}
        </div>
      )}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit goal" : "New goal"} wide>
        {edit && <EntityForm fields={fields} initial={edit.id ? edit : { area: "career", status: "active" }} onSubmit={async (d) => { edit.id ? await crud.update.mutateAsync({ id: edit.id, data: d }) : await crud.create.mutateAsync(d); setEdit(null); }} onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); setEdit(null); } : undefined} />}
      </Modal>
    </>
  );
}

// ---------------------------------------------------------------- habits
function Habits() {
  const status = useQuery<any[]>({ queryKey: ["/habits/status"], queryFn: () => get("/habits/status") });
  const crud = useCrud("/habits", ["/habits/status"]);
  const inv = useInvalidate();
  const [edit, setEdit] = useState<any | null>(null);
  const habits = useList("/habits");
  const fields: FieldDef[] = [
    { name: "name", label: "Habit", required: true },
    { name: "area", label: "Area", type: "select", options: AREAS, required: true, half: true },
    { name: "target_per_week", label: "Target days per week", type: "number", min: 1, max: 7, required: true, half: true },
    { name: "active", label: "Active", type: "checkbox" },
  ];
  const days = Array.from({ length: 7 }, (_, i) => addDays(new Date(), i - 6));
  const toggle = async (id: string, d: Date) => { await post(`/habits/${id}/toggle${qs({ date: iso(d) })}`); inv("/habits/status"); };
  return (
    <>
      <div className="mb-3 flex justify-end"><Button variant="primary" icon={<Plus className="size-4" />} onClick={() => setEdit({})}>Habit</Button></div>
      <Card pad={false}>
        {status.isLoading ? <Loading /> : (status.data || []).length === 0 ? <div className="p-4"><Empty title="No habits yet" hint="Start with one or two you can keep, like a 20-minute walk." /></div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[11px] text-ink-3">
                  <th className="px-4 py-2 text-left font-medium">Habit</th>
                  {days.map((d) => <th key={iso(d)} className="px-1 py-2 font-medium">{d.toLocaleDateString("en-IN", { weekday: "narrow" })}<div className="text-[10px]">{d.getDate()}</div></th>)}
                  <th className="px-3 py-2 font-medium">Streak</th>
                  <th className="px-3 py-2 font-medium">30d</th>
                </tr>
              </thead>
              <tbody>
                {(status.data || []).map((h) => (
                  <tr key={h.id} className="border-t border-line">
                    <td className="px-4 py-2"><button onClick={() => setEdit((habits.data || []).find((x: any) => x.id === h.id))} className="text-left">{h.name}<div className="text-[11px] text-ink-3">{h.this_week}/{h.target_per_week} this week</div></button></td>
                    {days.map((d, i) => (
                      <td key={i} className="px-1 py-2 text-center">
                        <button aria-label={`${h.name} ${iso(d)}`} onClick={() => toggle(h.id, d)} className={cx("size-6 rounded-md border transition-colors", h.last_7[i] ? "border-good bg-good" : "border-line hover:border-accent")} />
                      </td>
                    ))}
                    <td className="px-3 py-2 text-center tabular-nums">{h.streak}</td>
                    <td className="px-3 py-2 text-center tabular-nums text-ink-3">{pct(h.consistency_30d)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit habit" : "New habit"}>
        {edit && <EntityForm fields={fields} initial={edit.id ? edit : { area: "personal", target_per_week: 7, active: true }} onSubmit={async (d) => { edit.id ? await crud.update.mutateAsync({ id: edit.id, data: d }) : await crud.create.mutateAsync(d); setEdit(null); }} onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); setEdit(null); } : undefined} />}
      </Modal>
    </>
  );
}

export { parseIso };
