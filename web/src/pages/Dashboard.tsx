import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Bar, BarChart, Cell, XAxis } from "recharts";
import { AlertCircle, Check, Droplets, Dumbbell, Flame, Footprints, GraduationCap, Wallet } from "lucide-react";
import { get, post, put } from "../api/client";
import { InsightCard } from "../components/AI";
import { ChartBox, axis, tip } from "../components/charts";
import { Badge, Card, Empty, Loading, PageHeader, Progress, Ring, Stat, cx } from "../components/ui";
import { fmtDate, fmtTime, greeting, money, num, pct, relDay, todayIso } from "../lib/format";
import { useInvalidate } from "../lib/hooks";

const PRIORITY_TONE: Record<string, string> = { urgent: "bad", high: "warn", medium: "accent", low: "neutral" };

export function TaskRow({ t, onDone }: { t: any; onDone: (id: string) => void }) {
  const overdue = t.due_date && t.due_date < todayIso() && t.status !== "done";
  return (
    <div className="flex items-center gap-3 py-2">
      <button aria-label={`Complete ${t.title}`} onClick={() => onDone(t.id)} className={cx("grid size-5 shrink-0 place-items-center rounded-full border transition-colors", t.status === "done" ? "border-good bg-good text-white" : "border-ink-3 hover:border-accent")}>
        {t.status === "done" && <Check className="size-3" strokeWidth={3} />}
      </button>
      <div className="min-w-0 flex-1">
        <div className={cx("truncate text-sm", t.status === "done" && "text-ink-3 line-through")}>{t.title}</div>
        <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-ink-3">
          <span className="capitalize">{t.category.replace("_", " ")}</span>
          {t.scheduled_start && <span>· {fmtTime(t.scheduled_start)}</span>}
          {t.estimate_minutes && <span>· {t.estimate_minutes}m</span>}
        </div>
      </div>
      {t.due_date && <span className={cx("text-[11px]", overdue ? "font-medium text-bad" : "text-ink-3")}>{relDay(t.due_date)}</span>}
      <Badge tone={PRIORITY_TONE[t.priority]}>{t.priority}</Badge>
    </div>
  );
}

export default function Dashboard() {
  const { data: d, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: () => get("/dashboard") });
  const inv = useInvalidate();
  if (isLoading || !d) return <Loading />;

  const complete = async (id: string) => {
    await post(`/tasks/${id}/complete`);
    inv("/tasks");
  };
  const toggleHabit = async (id: string) => {
    await post(`/habits/${id}/toggle`);
    inv("/habits/status");
  };
  const addWater = async () => {
    await put(`/fitness/activity/${d.date}`, { add_water_ml: 250 });
    inv("/fitness/summary");
  };

  const hour = new Date().getHours();
  const todayTasks = [...d.tasks.overdue, ...d.tasks.due_today];
  const f = d.fitness;
  const score = d.productivity.score;

  return (
    <div className="fade-in space-y-4">
      <PageHeader title={`${greeting()}${d.greeting_name ? `, ${d.greeting_name}` : ""}`} subtitle={fmtDate(d.date, { weekday: "long", day: "numeric", month: "long" })} />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1" title="Productivity">
          <div className="flex items-center gap-5">
            <Ring value={score / 100} size={104}>
              <div>
                <div className="text-2xl font-semibold tabular-nums">{score}</div>
                <div className="text-[10px] text-ink-3">of 100</div>
              </div>
            </Ring>
            <div className="flex-1 space-y-2">
              {Object.entries(d.productivity.components).map(([k, v]: any) => (
                <div key={k}>
                  <div className="mb-0.5 flex justify-between text-xs"><span className="capitalize text-ink-2">{k}</span><span className="tabular-nums text-ink-3">{v}%</span></div>
                  <Progress value={v / 100} />
                </div>
              ))}
            </div>
          </div>
          <ChartBox height={70}>
            <BarChart data={d.productivity_week} margin={{ top: 12, right: 0, left: 0, bottom: 0 }}>
              <XAxis dataKey="date" {...axis} tickFormatter={(s) => new Date(s).toLocaleDateString("en-IN", { weekday: "narrow" })} />
              {tip}
              <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                {d.productivity_week.map((x: any) => <Cell key={x.date} fill={x.date === d.date ? "var(--accent)" : "var(--accent-soft)"} />)}
              </Bar>
            </BarChart>
          </ChartBox>
        </Card>

        <InsightCard className="lg:col-span-2" kind={hour >= 17 ? "evening_review" : "morning_briefing"} title={hour >= 17 ? "Evening review" : "Morning briefing"} cta={hour >= 17 ? "Review my day" : "Brief me"} />
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat icon={<Wallet className="size-3.5" />} label="Spent today" value={money(d.finance.today_expense)} sub={d.finance.budget ? `${pct(d.finance.budget_used_pct)} of ${money(d.finance.budget)} this month` : `${money(d.finance.month_expense)} this month`} />
        <Stat icon={<Flame className="size-3.5" />} label="Protein" value={`${num(f.protein_g)} g`} sub={<Progress className="mt-1.5" value={f.protein_g / f.protein_target} tone={f.protein_g >= f.protein_target ? "good" : "accent"} />} />
        <Stat icon={<GraduationCap className="size-3.5" />} label="Learning" value={`${d.learning.today_minutes} min`} sub={`${Math.round(d.learning.week_minutes / 60 * 10) / 10} / ${d.learning.week_target_minutes / 60} h this week`} />
        <Stat icon={<Footprints className="size-3.5" />} label="Steps" value={num(f.steps)} sub={<Progress className="mt-1.5" value={f.steps / f.steps_target} />} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2" title={`Today's tasks · ${d.tasks.done_today.length} done`} action={<Link to="/tasks" className="text-xs font-medium text-accent">Open planner</Link>}>
          {d.tasks.overdue.length > 0 && (
            <div className="mb-2 flex items-center gap-1.5 rounded-lg bg-bad/8 px-2.5 py-1.5 text-xs text-bad">
              <AlertCircle className="size-3.5" /> {d.tasks.overdue.length} overdue
            </div>
          )}
          {todayTasks.length === 0 && d.tasks.done_today.length === 0 ? (
            <Empty title="Nothing due today" hint="Add tasks in the planner or let Aaroh suggest some." />
          ) : (
            <div className="divide-y divide-line">
              {[...todayTasks, ...d.tasks.done_today].map((t: any) => <TaskRow key={t.id} t={t} onDone={complete} />)}
            </div>
          )}
          {d.tasks.upcoming.length > 0 && (
            <>
              <div className="mt-4 mb-1 text-[11px] font-semibold tracking-wide text-ink-3 uppercase">Coming up</div>
              <div className="divide-y divide-line">{d.tasks.upcoming.slice(0, 4).map((t: any) => <TaskRow key={t.id} t={t} onDone={complete} />)}</div>
            </>
          )}
        </Card>

        <Card title="Habits">
          {d.habits.length === 0 ? (
            <Empty title="No habits yet" action={<Link className="text-sm text-accent" to="/tasks?tab=habits">Add a habit</Link>} />
          ) : (
            <div className="space-y-2.5">
              {d.habits.map((h: any) => (
                <div key={h.id} className="flex items-center gap-3">
                  <button aria-label={`Toggle ${h.name}`} onClick={() => toggleHabit(h.id)} className={cx("grid size-7 place-items-center rounded-lg border transition-colors", h.done_today ? "border-good bg-good text-white" : "border-line hover:border-accent")}>
                    {h.done_today && <Check className="size-4" strokeWidth={3} />}
                  </button>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm">{h.name}</div>
                    <div className="mt-1 flex gap-0.5">{h.last_7.map((x: boolean, i: number) => <span key={i} className={cx("h-1.5 w-3 rounded-full", x ? "bg-good" : "bg-surface-2")} />)}</div>
                  </div>
                  <span className="text-xs tabular-nums text-ink-3">🔥 {h.streak}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Fitness today" action={<Link to="/fitness" className="text-xs font-medium text-accent">Log</Link>}>
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-ink-2"><Dumbbell className="size-4" /> Workout</span>
              {f.workouts.length ? f.workouts.map((w: any) => <Badge key={w.title} tone={w.status === "done" ? "good" : w.status === "skipped" ? "bad" : "neutral"}>{w.title} · {w.status}</Badge>) : <span className="text-ink-3">Rest / not logged</span>}
            </div>
            <div>
              <div className="mb-1 flex justify-between"><span className="flex items-center gap-2 text-ink-2"><Droplets className="size-4" /> Water</span><button onClick={addWater} className="text-xs font-medium text-accent">+250 ml</button></div>
              <Progress value={f.water_ml / f.water_target} tone="accent" />
              <div className="mt-1 text-xs text-ink-3">{num(f.water_ml)} / {num(f.water_target)} ml</div>
            </div>
            <div className="text-xs text-ink-3">Calories {num(f.calories)} / {num(f.calorie_target)} · Gym this week {d.fitness_week.gym_sessions}/{d.fitness_week.gym_target}</div>
          </div>
        </Card>

        <Card title="Active goals" action={<Link to="/tasks?tab=goals" className="text-xs font-medium text-accent">All goals</Link>}>
          {d.goals.length === 0 ? <Empty title="No active goals" /> : (
            <div className="space-y-3">
              {d.goals.map((g: any) => (
                <div key={g.id}>
                  <div className="mb-1 flex items-center justify-between gap-2 text-sm"><span className="truncate">{g.title}</span><span className="text-xs tabular-nums text-ink-3">{g.progress !== null ? pct(g.progress) : `${g.milestones_done}/${g.milestones_total}`}</span></div>
                  <Progress value={g.progress ?? 0} />
                  {g.next_milestone && <div className="mt-1 truncate text-[11px] text-ink-3">Next: {g.next_milestone}</div>}
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Work today" action={<Link to="/work" className="text-xs font-medium text-accent">Log update</Link>}>
          {d.work_today.length === 0 ? <Empty title="No work update yet" hint="Two lines at the end of the day become your weekly report." /> : (
            <div className="space-y-2">{d.work_today.map((w: any, i: number) => <div key={i} className="text-sm"><Badge>{w.project || "General"}</Badge><p className="mt-1 text-ink-2">{w.summary}</p></div>)}</div>
          )}
          {d.learning.courses_in_progress.length > 0 && <div className="mt-4 text-xs text-ink-3">In progress: {d.learning.courses_in_progress.join(", ")}</div>}
        </Card>
      </div>
    </div>
  );
}
