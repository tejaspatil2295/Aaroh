import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, XAxis, YAxis } from "recharts";
import { Droplets, Plus, Trash2 } from "lucide-react";
import { del, get, post, put, qs } from "../api/client";
import { InsightCard } from "../components/AI";
import { ChartBox, axis, grid, tip } from "../components/charts";
import { EntityForm, human, type FieldDef } from "../components/EntityForm";
import { Badge, Button, Card, Empty, ErrorNote, Field, Input, Loading, Modal, PageHeader, Ring, Select, Stat, Tabs, Textarea } from "../components/ui";
import { fmtDate, num, todayIso } from "../lib/format";
import { useCrud, useInvalidate, useList } from "../lib/hooks";

type Tab = "today" | "workouts" | "food" | "body" | "progress";
const REL = ["/fitness/summary", "/fitness/series", "/fitness/exercises"];

export default function Fitness() {
  const [tab, setTab] = useState<Tab>("today");
  return (
    <div className="fade-in">
      <PageHeader title="Fitness & health" subtitle="Workouts, nutrition, activity and body metrics" />
      <div className="mb-4"><Tabs<Tab> value={tab} onChange={setTab} tabs={[{ id: "today", label: "Today" }, { id: "workouts", label: "Workouts" }, { id: "food", label: "Food diary" }, { id: "body", label: "Body" }, { id: "progress", label: "Progress" }]} /></div>
      {tab === "today" && <Today />}
      {tab === "workouts" && <Workouts />}
      {tab === "food" && <Food />}
      {tab === "body" && <Body />}
      {tab === "progress" && <ProgressCharts />}
    </div>
  );
}

function Today() {
  const s = useQuery({ queryKey: ["/fitness/summary"], queryFn: () => get("/fitness/summary") });
  const inv = useInvalidate();
  const [steps, setSteps] = useState("");
  const [sleep, setSleep] = useState("");
  if (!s.data) return <Loading />;
  const t = s.data.today;
  const w = s.data.week;
  const upd = async (data: any) => { await put(`/fitness/activity/${todayIso()}`, data); inv(...REL); };
  const rings = [
    { label: "Protein", v: t.protein_g, max: t.protein_target, unit: "g", color: "var(--chart-1)" },
    { label: "Calories", v: t.calories, max: t.calorie_target, unit: "kcal", color: "var(--chart-3)" },
    { label: "Water", v: t.water_ml, max: t.water_target, unit: "ml", color: "var(--chart-2)" },
    { label: "Steps", v: t.steps, max: t.steps_target, unit: "", color: "var(--chart-4)" },
  ];
  return (
    <div className="space-y-4">
      <Card>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {rings.map((r) => (
            <div key={r.label} className="flex flex-col items-center gap-2">
              <Ring value={r.v / (r.max || 1)} color={r.color} size={92}>
                <div><div className="text-base font-semibold tabular-nums">{num(r.v)}</div><div className="text-[10px] text-ink-3">/ {num(r.max)} {r.unit}</div></div>
              </Ring>
              <span className="text-xs font-medium text-ink-2">{r.label}</span>
            </div>
          ))}
        </div>
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Quick log">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Droplets className="size-4 text-ink-3" />
              {[250, 500].map((ml) => <Button key={ml} size="sm" onClick={() => upd({ add_water_ml: ml })}>+{ml} ml</Button>)}
              <Button size="sm" variant="ghost" onClick={() => upd({ add_water_ml: -250 })}>−250</Button>
            </div>
            <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); upd({ steps: Number(steps) }); setSteps(""); }}>
              <Input type="number" placeholder={`Steps (now ${t.steps})`} value={steps} onChange={(e) => setSteps(e.target.value)} />
              <Button type="submit" disabled={!steps}>Save</Button>
            </form>
            <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); upd({ sleep_hours: Number(sleep) }); setSleep(""); }}>
              <Input type="number" step="0.5" placeholder={`Sleep hours${t.sleep_hours ? ` (now ${t.sleep_hours})` : ""}`} value={sleep} onChange={(e) => setSleep(e.target.value)} />
              <Button type="submit" disabled={!sleep}>Save</Button>
            </form>
            <p className="text-xs text-ink-3">Manual tracking for now. The API already accepts Health Connect / Google Fit imports (POST /fitness/import).</p>
          </div>
        </Card>
        <Card title="This week">
          <div className="grid grid-cols-2 gap-3">
            <Stat label="Gym sessions" value={`${w.gym_sessions}/${w.gym_target}`} sub={w.workouts_skipped ? `${w.workouts_skipped} skipped` : undefined} />
            <Stat label="Avg protein" value={w.avg_protein_g ? `${w.avg_protein_g} g` : "—"} sub={`target hit ${w.protein_target_days_hit}/7 days`} />
            <Stat label="Avg steps" value={num(w.avg_steps)} />
            <Stat label="Weight" value={w.latest_weight ? `${w.latest_weight} kg` : "—"} sub={w.weight_change_30d != null ? `${w.weight_change_30d > 0 ? "+" : ""}${w.weight_change_30d} kg in 30d` : undefined} />
          </div>
        </Card>
      </div>
      <InsightCard kind="fitness_insights" title="Weekly fitness report" cta="Generate report" />
    </div>
  );
}

type SetRow = { exercise: string; set_number: number; reps: string; weight_kg: string };

function WorkoutForm({ initial, onDone }: { initial: any; onDone: () => void }) {
  const inv = useInvalidate();
  const [w, setW] = useState({ date: initial.date || todayIso(), title: initial.title || "", workout_type: initial.workout_type || "strength", duration_minutes: initial.duration_minutes ?? "", status: initial.status || "done", attended_gym: initial.attended_gym ?? true, notes: initial.notes || "" });
  const [sets, setSets] = useState<SetRow[]>((initial.sets || []).map((s: any) => ({ ...s, reps: s.reps ?? "", weight_kg: s.weight_kg ?? "" })));
  const [err, setErr] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const addSet = () => {
    const last = sets[sets.length - 1];
    setSets([...sets, last ? { ...last, set_number: sets.filter((s) => s.exercise === last.exercise).length + 1 } : { exercise: "", set_number: 1, reps: "", weight_kg: "" }]);
  };
  const save = async () => {
    setBusy(true);
    setErr(null);
    const body = { ...w, duration_minutes: w.duration_minutes === "" ? null : Number(w.duration_minutes), sets: sets.filter((s) => s.exercise).map((s) => ({ exercise: s.exercise, set_number: Number(s.set_number) || 1, reps: s.reps === "" ? null : Number(s.reps), weight_kg: s.weight_kg === "" ? null : Number(s.weight_kg) })) };
    try {
      initial.id ? await put(`/fitness/workouts/${initial.id}`, body) : await post("/fitness/workouts", body);
      inv("/fitness/workouts", ...REL);
      onDone();
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Workout" className="col-span-2"><Input value={w.title} onChange={(e) => setW({ ...w, title: e.target.value })} placeholder="Push day" /></Field>
        <Field label="Date"><Input type="date" value={w.date} onChange={(e) => setW({ ...w, date: e.target.value })} /></Field>
        <Field label="Duration (min)"><Input type="number" value={w.duration_minutes} onChange={(e) => setW({ ...w, duration_minutes: e.target.value })} /></Field>
        <Field label="Type"><Select value={w.workout_type} onChange={(e) => setW({ ...w, workout_type: e.target.value })}>{["strength", "cardio", "mobility", "sport", "rest"].map((x) => <option key={x}>{x}</option>)}</Select></Field>
        <Field label="Status"><Select value={w.status} onChange={(e) => setW({ ...w, status: e.target.value })}>{["planned", "done", "skipped"].map((x) => <option key={x}>{x}</option>)}</Select></Field>
        <label className="col-span-2 flex items-center gap-2 text-sm text-ink-2"><input type="checkbox" checked={w.attended_gym} onChange={(e) => setW({ ...w, attended_gym: e.target.checked })} className="size-4 accent-[var(--accent)]" />Went to the gym</label>
      </div>
      <div>
        <div className="mb-1 text-[13px] font-medium text-ink-2">Sets</div>
        <div className="space-y-1.5">
          {sets.map((s, i) => (
            <div key={i} className="grid grid-cols-[1fr_44px_60px_64px_28px] items-center gap-1.5">
              <Input className="h-9" placeholder="Exercise" value={s.exercise} onChange={(e) => setSets(sets.map((x, j) => (j === i ? { ...x, exercise: e.target.value } : x)))} />
              <Input className="h-9 px-1 text-center" aria-label="Set" value={s.set_number} onChange={(e) => setSets(sets.map((x, j) => (j === i ? { ...x, set_number: Number(e.target.value) } : x)))} />
              <Input className="h-9 px-1 text-center" placeholder="reps" type="number" value={s.reps} onChange={(e) => setSets(sets.map((x, j) => (j === i ? { ...x, reps: e.target.value } : x)))} />
              <Input className="h-9 px-1 text-center" placeholder="kg" type="number" step="0.5" value={s.weight_kg} onChange={(e) => setSets(sets.map((x, j) => (j === i ? { ...x, weight_kg: e.target.value } : x)))} />
              <button aria-label="Remove set" onClick={() => setSets(sets.filter((_, j) => j !== i))} className="text-ink-3 hover:text-bad"><Trash2 className="size-4" /></button>
            </div>
          ))}
        </div>
        <Button size="sm" variant="ghost" className="mt-1" icon={<Plus className="size-3.5" />} onClick={addSet}>Add set</Button>
      </div>
      <Field label="Notes"><Textarea value={w.notes} onChange={(e) => setW({ ...w, notes: e.target.value })} /></Field>
      <ErrorNote error={err} />
      <div className="flex justify-between">
        {initial.id ? <Button variant="ghost" className="text-bad" onClick={async () => { if (confirm("Delete workout?")) { await del(`/fitness/workouts/${initial.id}`); inv("/fitness/workouts", ...REL); onDone(); } }}>Delete</Button> : <span />}
        <Button variant="primary" onClick={save} loading={busy} disabled={!w.title}>Save workout</Button>
      </div>
    </div>
  );
}

function Workouts() {
  const list = useQuery<any[]>({ queryKey: ["/fitness/workouts"], queryFn: () => get("/fitness/workouts?limit=60") });
  const [edit, setEdit] = useState<any | null>(null);
  return (
    <>
      <div className="mb-3 flex justify-end"><Button variant="primary" icon={<Plus className="size-4" />} onClick={() => setEdit({})}>Workout</Button></div>
      {list.isLoading ? <Loading /> : (list.data || []).length === 0 ? <Empty title="No workouts logged" /> : (
        <div className="space-y-2">
          {(list.data || []).map((w) => {
            const ex = Array.from(new Set(w.sets.map((s: any) => s.exercise)));
            return (
              <Card key={w.id} className="cursor-pointer hover:border-ink-3">
                <button className="block w-full text-left" onClick={() => setEdit(w)}>
                  <div className="flex items-center gap-2"><span className="flex-1 font-medium">{w.title}</span><span className="text-xs text-ink-3">{fmtDate(w.date, { weekday: "short", day: "numeric", month: "short" })}</span><Badge tone={w.status === "done" ? "good" : w.status === "skipped" ? "bad" : "neutral"}>{w.status}</Badge></div>
                  <div className="mt-1 text-xs text-ink-3">{w.duration_minutes ? `${w.duration_minutes} min · ` : ""}{w.sets.length} sets{ex.length > 0 && ` · ${ex.join(", ")}`}</div>
                </button>
              </Card>
            );
          })}
        </div>
      )}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit workout" : "Log workout"} wide>{edit && <WorkoutForm initial={edit} onDone={() => setEdit(null)} />}</Modal>
    </>
  );
}

function Food() {
  const [date, setDate] = useState(todayIso());
  const list = useList("/fitness/food", qs({ from: date, to: date }));
  const crud = useCrud("/fitness/food", REL);
  const [edit, setEdit] = useState<any | null>(null);
  const totals = (list.data || []).reduce((a: any, f: any) => ({ cal: a.cal + f.calories, p: a.p + Number(f.protein_g), c: a.c + Number(f.carbs_g), fat: a.fat + Number(f.fat_g) }), { cal: 0, p: 0, c: 0, fat: 0 });
  const fields: FieldDef[] = [
    { name: "food", label: "Food", required: true },
    { name: "meal", label: "Meal", type: "select", options: ["breakfast", "lunch", "dinner", "snack", "pre_workout", "post_workout"], required: true, half: true },
    { name: "quantity", label: "Quantity", placeholder: "1 bowl, 200 g…", half: true },
    { name: "calories", label: "Calories", type: "number", half: true },
    { name: "protein_g", label: "Protein (g)", type: "number", step: "0.1", half: true },
    { name: "carbs_g", label: "Carbs (g)", type: "number", step: "0.1", half: true },
    { name: "fat_g", label: "Fat (g)", type: "number", step: "0.1", half: true },
    { name: "date", label: "Date", type: "date", required: true },
  ];
  return (
    <Card title="Food diary" action={<div className="flex gap-2"><Input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="h-8 w-36" /><Button size="sm" variant="primary" icon={<Plus className="size-3.5" />} onClick={() => setEdit({ date, meal: "snack" })}>Food</Button></div>}>
      <div className="mb-3 grid grid-cols-4 gap-2 text-center text-xs">
        {[["Calories", totals.cal, ""], ["Protein", totals.p, "g"], ["Carbs", totals.c, "g"], ["Fat", totals.fat, "g"]].map(([l, v, u]) => <div key={l as string} className="rounded-lg bg-surface-2 py-2"><div className="text-base font-semibold tabular-nums">{num(v as number)}{u}</div><div className="text-ink-3">{l}</div></div>)}
      </div>
      {list.isLoading ? <Loading /> : (list.data || []).length === 0 ? <Empty title="Nothing logged for this day" /> : (
        <div className="divide-y divide-line">
          {(list.data || []).map((f: any) => (
            <button key={f.id} onClick={() => setEdit(f)} className="flex w-full items-center gap-3 py-2 text-left text-sm">
              <Badge>{human(f.meal)}</Badge>
              <span className="min-w-0 flex-1 truncate">{f.food}{f.quantity && <span className="text-ink-3"> · {f.quantity}</span>}</span>
              <span className="text-xs tabular-nums text-ink-3">{f.calories} kcal · {Number(f.protein_g)} g P</span>
            </button>
          ))}
        </div>
      )}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit food" : "Log food"}>
        {edit && <EntityForm fields={fields} initial={edit} onSubmit={async (d) => { edit.id ? await crud.update.mutateAsync({ id: edit.id, data: d }) : await crud.create.mutateAsync(d); setEdit(null); }} onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); setEdit(null); } : undefined} />}
      </Modal>
    </Card>
  );
}

function Body() {
  const list = useList("/fitness/body");
  const crud = useCrud("/fitness/body", REL);
  const [edit, setEdit] = useState<any | null>(null);
  const fields: FieldDef[] = [
    { name: "date", label: "Date", type: "date", required: true },
    { name: "weight_kg", label: "Weight (kg)", type: "number", step: "0.1", half: true },
    { name: "body_fat_pct", label: "Body fat %", type: "number", step: "0.1", half: true },
    { name: "waist_cm", label: "Waist (cm)", type: "number", step: "0.1", half: true },
    { name: "chest_cm", label: "Chest (cm)", type: "number", step: "0.1", half: true },
    { name: "arm_cm", label: "Arm (cm)", type: "number", step: "0.1", half: true },
    { name: "notes", label: "Notes", type: "textarea" },
  ];
  return (
    <Card title="Body measurements" action={<Button size="sm" variant="primary" icon={<Plus className="size-3.5" />} onClick={() => setEdit({ date: todayIso() })}>Measurement</Button>}>
      {(list.data || []).length === 0 ? <Empty title="No measurements yet" /> : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-[11px] text-ink-3"><th className="py-2 font-medium">Date</th><th className="font-medium">Weight</th><th className="font-medium">Body fat</th><th className="font-medium">Waist</th><th className="font-medium">Chest</th><th className="font-medium">Arm</th></tr></thead>
            <tbody>{(list.data || []).map((m: any) => (
              <tr key={m.id} onClick={() => setEdit(m)} className="cursor-pointer border-t border-line hover:bg-surface-2">
                <td className="py-2">{fmtDate(m.date)}</td><td className="tabular-nums">{m.weight_kg ?? "—"}</td><td className="tabular-nums">{m.body_fat_pct ? `${m.body_fat_pct}%` : "—"}</td><td className="tabular-nums">{m.waist_cm ?? "—"}</td><td className="tabular-nums">{m.chest_cm ?? "—"}</td><td className="tabular-nums">{m.arm_cm ?? "—"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit measurement" : "New measurement"}>
        {edit && <EntityForm fields={fields} initial={edit} onSubmit={async (d) => { edit.id ? await crud.update.mutateAsync({ id: edit.id, data: d }) : await crud.create.mutateAsync(d); setEdit(null); }} onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); setEdit(null); } : undefined} />}
      </Modal>
    </Card>
  );
}

function ProgressCharts() {
  const series = useQuery<any[]>({ queryKey: ["/fitness/series"], queryFn: () => get("/fitness/series?days=60") });
  const ex = useQuery<any[]>({ queryKey: ["/fitness/exercises"], queryFn: () => get("/fitness/exercises") });
  const settings = useQuery({ queryKey: ["/users/me/settings"], queryFn: () => get("/users/me/settings") });
  const [exercise, setExercise] = useState("");
  if (!series.data) return <Loading />;
  const weights = series.data.filter((d) => d.weight !== null);
  const p = settings.data?.preferences || {};
  const exSel = (ex.data || []).find((e) => e.exercise === exercise) || (ex.data || [])[0];
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Weight (kg)">
        {weights.length < 2 ? <Empty title="Log weight a few times to see a trend" /> : (
          <ChartBox><LineChart data={weights} margin={{ left: -20, right: 8 }}><CartesianGrid {...grid} /><XAxis dataKey="date" {...axis} tickFormatter={(s) => fmtDate(s)} minTickGap={24} /><YAxis {...axis} domain={["dataMin - 1", "dataMax + 1"]} />{tip}<Line type="monotone" dataKey="weight" stroke="var(--chart-1)" strokeWidth={2} dot={false} /></LineChart></ChartBox>
        )}
      </Card>
      <Card title="Protein per day (g)">
        <ChartBox><BarChart data={series.data.slice(-30)} margin={{ left: -20 }}><CartesianGrid {...grid} /><XAxis dataKey="date" {...axis} tickFormatter={(s) => fmtDate(s)} minTickGap={24} /><YAxis {...axis} />{tip}{p.daily_protein_g && <ReferenceLine y={p.daily_protein_g} stroke="var(--good)" strokeDasharray="4 4" />}<Bar dataKey="protein" fill="var(--chart-1)" radius={[3, 3, 0, 0]} /></BarChart></ChartBox>
      </Card>
      <Card title="Steps">
        <ChartBox><BarChart data={series.data.slice(-30)} margin={{ left: -10 }}><CartesianGrid {...grid} /><XAxis dataKey="date" {...axis} tickFormatter={(s) => fmtDate(s)} minTickGap={24} /><YAxis {...axis} />{tip}{p.daily_steps && <ReferenceLine y={p.daily_steps} stroke="var(--good)" strokeDasharray="4 4" />}<Bar dataKey="steps" fill="var(--chart-4)" radius={[3, 3, 0, 0]} /></BarChart></ChartBox>
      </Card>
      <Card title="Strength progress" action={(ex.data || []).length > 0 && <Select className="h-8 w-44 text-xs" value={exSel?.exercise} onChange={(e) => setExercise(e.target.value)}>{(ex.data || []).map((e) => <option key={e.exercise}>{e.exercise}</option>)}</Select>}>
        {!exSel ? <Empty title="Log sets to track strength" /> : (
          <>
            <div className="mb-1 text-xs text-ink-3">Best {exSel.best_weight} kg · {exSel.sets} sets logged</div>
            <ChartBox height={190}><LineChart data={exSel.history} margin={{ left: -20, right: 8 }}><CartesianGrid {...grid} /><XAxis dataKey="date" {...axis} tickFormatter={(s) => fmtDate(s)} /><YAxis {...axis} domain={["dataMin - 5", "dataMax + 5"]} />{tip}<Line type="monotone" dataKey="weight" stroke="var(--chart-2)" strokeWidth={2} /></LineChart></ChartBox>
          </>
        )}
      </Card>
    </div>
  );
}
