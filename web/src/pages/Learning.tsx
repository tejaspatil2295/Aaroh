import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Clock, Plus } from "lucide-react";
import { get, qs } from "../api/client";
import { InsightCard } from "../components/AI";
import { ChartBox, axis, grid, tip } from "../components/charts";
import { EntityForm, human, type FieldDef } from "../components/EntityForm";
import { Badge, Button, Card, Empty, Input, Loading, Modal, PageHeader, Progress, Stat, Tabs, cx } from "../components/ui";
import { fmtDate, todayIso } from "../lib/format";
import { useCrud, useList } from "../lib/hooks";
import { Simple } from "./Finance";

type Tab = "overview" | "skills" | "notes" | "resources" | "courses" | "interview";
const REL = ["/learning/summary", "/learning/daily"];

export default function Learning() {
  const [tab, setTab] = useState<Tab>("overview");
  const [logOpen, setLogOpen] = useState(false);
  const skills = useList("/learning/skills");
  const logs = useCrud("/learning/logs", REL);
  const skillOpts = (skills.data || []).map((s: any) => ({ value: s.id, label: s.name }));
  return (
    <div className="fade-in">
      <PageHeader title="Learning hub" subtitle="Skills, roadmaps, notes and interview prep" actions={<Button variant="primary" icon={<Clock className="size-4" />} onClick={() => setLogOpen(true)}>Log study time</Button>} />
      <div className="mb-4"><Tabs<Tab> value={tab} onChange={setTab} tabs={[{ id: "overview", label: "Overview" }, { id: "skills", label: "Skills & roadmaps" }, { id: "notes", label: "Notes & snippets" }, { id: "resources", label: "Resources" }, { id: "courses", label: "Courses & projects" }, { id: "interview", label: "Interview prep" }]} /></div>
      {tab === "overview" && <Overview />}
      {tab === "skills" && <Skills />}
      {tab === "notes" && <Notes skillOpts={skillOpts} />}
      {tab === "resources" && <Simple path="/learning/resources" title="resource" fields={[
        { name: "title", label: "Title", required: true },
        { name: "url", label: "URL", placeholder: "https://" },
        { name: "kind", label: "Type", type: "select", options: ["article", "docs", "video", "course", "book", "repo", "other"], required: true, half: true },
        { name: "status", label: "Status", type: "select", options: ["to_read", "in_progress", "done"], required: true, half: true },
        { name: "skill_id", label: "Skill", type: "select", options: skillOpts },
        { name: "notes", label: "Notes", type: "textarea" },
      ]} defaults={{ kind: "article", status: "to_read" }} render={(r) => (
        <div className="flex items-center gap-3"><div className="min-w-0 flex-1"><div className="truncate text-sm">{r.title}</div>{r.url && <a href={r.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} className="truncate text-xs text-accent">{r.url}</a>}</div><Badge>{r.kind}</Badge><Badge tone={r.status === "done" ? "good" : r.status === "in_progress" ? "accent" : "neutral"}>{human(r.status)}</Badge></div>
      )} />}
      {tab === "courses" && <Simple path="/learning/items" title="course or project" related={REL} fields={[
        { name: "title", label: "Title", required: true },
        { name: "kind", label: "Type", type: "select", options: ["course", "project", "certification"], required: true, half: true },
        { name: "status", label: "Status", type: "select", options: ["planned", "in_progress", "completed", "dropped"], required: true, half: true },
        { name: "provider", label: "Provider", half: true },
        { name: "progress_pct", label: "Progress %", type: "number", min: 0, max: 100, half: true },
        { name: "url", label: "Link" },
        { name: "started_on", label: "Started", type: "date", half: true },
        { name: "completed_on", label: "Completed", type: "date", half: true },
        { name: "notes", label: "Notes / outcomes", type: "textarea" },
      ]} defaults={{ kind: "course", status: "planned", progress_pct: 0 }} render={(c) => (
        <div><div className="mb-1 flex items-center gap-2 text-sm"><span className="flex-1 truncate">{c.title}</span><Badge>{c.kind}</Badge><Badge tone={c.status === "completed" ? "good" : c.status === "in_progress" ? "accent" : "neutral"}>{human(c.status)}</Badge></div><Progress value={c.progress_pct / 100} /></div>
      )} />}
      {tab === "interview" && <Simple path="/learning/interview" title="interview topic" related={REL} fields={[
        { name: "topic", label: "Topic", required: true },
        { name: "category", label: "Category", type: "select", options: ["dsa", "system_design", "frontend", "backend", "database", "devops", "behavioral", "other"], required: true, half: true },
        { name: "status", label: "Status", type: "select", options: ["todo", "practicing", "confident"], required: true, half: true },
        { name: "confidence", label: "Confidence 1–5", type: "number", min: 1, max: 5, half: true },
        { name: "last_practiced", label: "Last practiced", type: "date", half: true },
        { name: "question", label: "Question", type: "textarea" },
        { name: "notes", label: "Answer notes", type: "textarea" },
      ]} defaults={{ category: "dsa", status: "todo", confidence: 1 }} render={(i) => (
        <div className="flex items-center gap-3"><div className="min-w-0 flex-1"><div className="truncate text-sm">{i.topic}</div><div className="text-xs text-ink-3">{human(i.category)}{i.last_practiced && ` · practiced ${fmtDate(i.last_practiced)}`}</div></div><div className="flex gap-0.5">{[1, 2, 3, 4, 5].map((n) => <span key={n} className={cx("h-2 w-3 rounded-sm", n <= i.confidence ? "bg-accent" : "bg-surface-2")} />)}</div><Badge tone={i.status === "confident" ? "good" : i.status === "practicing" ? "accent" : "neutral"}>{i.status}</Badge></div>
      )} />}
      <Modal open={logOpen} onClose={() => setLogOpen(false)} title="Log study time">
        <EntityForm fields={[
          { name: "date", label: "Date", type: "date", required: true, half: true },
          { name: "minutes", label: "Minutes", type: "number", min: 1, required: true, half: true },
          { name: "skill_id", label: "Skill", type: "select", options: skillOpts },
          { name: "topic", label: "Topic" },
          { name: "notes", label: "What did you learn?", type: "textarea" },
        ]} initial={{ date: todayIso(), minutes: 45 }} onSubmit={async (d) => { await logs.create.mutateAsync(d); setLogOpen(false); }} />
      </Modal>
    </div>
  );
}

function Overview() {
  const s = useQuery({ queryKey: ["/learning/summary"], queryFn: () => get("/learning/summary") });
  const daily = useQuery<any[]>({ queryKey: ["/learning/daily"], queryFn: () => get("/learning/daily?days=28") });
  if (!s.data) return <Loading />;
  const d = s.data;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Today" value={`${d.today_minutes} min`} sub={<Progress className="mt-1.5" value={d.today_minutes / (d.daily_target_minutes || 1)} />} />
        <Stat label="This week" value={`${(d.week_minutes / 60).toFixed(1)} h`} sub={<Progress className="mt-1.5" value={d.week_minutes / (d.week_target_minutes || 1)} tone={d.week_minutes >= d.week_target_minutes ? "good" : "accent"} />} />
        <Stat label="Active days (28d)" value={d.days_learned_28d} />
        <Stat label="Interview ready" value={`${d.interview.confident}/${d.interview.total}`} sub="topics confident" />
      </div>
      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3" title="Daily minutes · 4 weeks">
          <ChartBox>
            <BarChart data={daily.data || []} margin={{ left: -20 }}>
              <CartesianGrid {...grid} />
              <XAxis dataKey="date" {...axis} tickFormatter={(s) => fmtDate(s)} minTickGap={20} />
              <YAxis {...axis} />
              {tip}
              <Bar dataKey="minutes" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartBox>
        </Card>
        <Card className="lg:col-span-2" title="Skill gaps">
          {d.skill_gaps.length === 0 ? <Empty title="Add skills with target levels" /> : (
            <div className="space-y-3">{d.skill_gaps.map((g: any) => (
              <div key={g.skill}>
                <div className="mb-1 flex justify-between text-sm"><span>{g.skill}</span><span className="text-xs text-ink-3">L{g.current} → L{g.target}</span></div>
                <Progress value={g.current / 5} tone={g.priority === "high" ? "warn" : "accent"} />
              </div>
            ))}</div>
          )}
        </Card>
      </div>
      <InsightCard kind="learning_recommendation" title="Technical mentor · what to learn next" cta="Recommend my next steps" />
    </div>
  );
}

function Skills() {
  const skills = useList("/learning/skills");
  const roadmap = useList("/learning/roadmap");
  const crud = useCrud("/learning/skills", REL);
  const rm = useCrud("/learning/roadmap", REL);
  const [edit, setEdit] = useState<any | null>(null);
  const [newItem, setNewItem] = useState<Record<string, string>>({});
  const fields: FieldDef[] = [
    { name: "name", label: "Skill / technology", required: true },
    { name: "category", label: "Category", type: "select", options: ["frontend", "backend", "database", "devops", "cloud", "architecture", "cs_fundamentals", "ai", "mobile", "soft_skills", "other"], required: true, half: true },
    { name: "priority", label: "Priority", type: "select", options: ["low", "medium", "high"], required: true, half: true },
    { name: "current_level", label: "Current level (0–5)", type: "number", min: 0, max: 5, required: true, half: true },
    { name: "target_level", label: "Target level (0–5)", type: "number", min: 0, max: 5, required: true, half: true },
    { name: "status", label: "Status", type: "select", options: ["planned", "learning", "paused", "strong"], required: true },
    { name: "notes", label: "Notes", type: "textarea" },
  ];
  return (
    <>
      <div className="mb-3 flex justify-end"><Button variant="primary" icon={<Plus className="size-4" />} onClick={() => setEdit({})}>Skill</Button></div>
      {skills.isLoading ? <Loading /> : (skills.data || []).length === 0 ? <Empty title="No skills yet" hint="Add the technologies you want to learn, then a roadmap for each." /> : (
        <div className="grid gap-3 md:grid-cols-2">
          {(skills.data || []).map((s: any) => {
            const items = (roadmap.data || []).filter((r: any) => r.skill_id === s.id);
            const done = items.filter((r: any) => r.done).length;
            return (
              <Card key={s.id}>
                <button className="mb-2 block w-full text-left" onClick={() => setEdit(s)}>
                  <div className="flex items-center gap-2"><span className="flex-1 font-medium">{s.name}</span><Badge tone={s.priority === "high" ? "warn" : "neutral"}>{s.priority}</Badge><Badge tone="accent">{s.status}</Badge></div>
                  <div className="mt-1 text-xs text-ink-3">{human(s.category)} · level {s.current_level} → {s.target_level}{items.length > 0 && ` · roadmap ${done}/${items.length}`}</div>
                </button>
                {items.length > 0 && <Progress value={done / items.length} className="mb-2" tone="good" />}
                <div className="space-y-1">
                  {items.map((r: any) => (
                    <label key={r.id} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={r.done} onChange={() => rm.update.mutate({ id: r.id, data: { done: !r.done } })} className="size-4 accent-[var(--accent)]" />
                      <span className={cx("flex-1", r.done && "text-ink-3 line-through")}>{r.title}</span>
                      <button className="text-xs text-ink-3 hover:text-bad" onClick={(e) => { e.preventDefault(); rm.remove.mutate(r.id); }} aria-label="Remove step">✕</button>
                    </label>
                  ))}
                </div>
                <form className="mt-2" onSubmit={(e) => { e.preventDefault(); if (newItem[s.id]) rm.create.mutate({ skill_id: s.id, title: newItem[s.id], order_index: items.length }, { onSuccess: () => setNewItem((x) => ({ ...x, [s.id]: "" })) }); }}>
                  <Input className="h-8 text-[13px]" placeholder="Add roadmap step" value={newItem[s.id] || ""} onChange={(e) => setNewItem((x) => ({ ...x, [s.id]: e.target.value }))} />
                </form>
              </Card>
            );
          })}
        </div>
      )}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit skill" : "New skill"} wide>
        {edit && <EntityForm fields={fields} initial={edit.id ? edit : { category: "backend", priority: "medium", current_level: 1, target_level: 4, status: "planned" }} onSubmit={async (d) => { edit.id ? await crud.update.mutateAsync({ id: edit.id, data: d }) : await crud.create.mutateAsync(d); setEdit(null); }} onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); setEdit(null); } : undefined} />}
      </Modal>
    </>
  );
}

function Notes({ skillOpts }: { skillOpts: { value: string; label: string }[] }) {
  const [q, setQ] = useState("");
  const list = useList("/learning/notes", qs({ q }));
  const crud = useCrud("/learning/notes");
  const [edit, setEdit] = useState<any | null>(null);
  const fields: FieldDef[] = [
    { name: "title", label: "Title", required: true },
    { name: "kind", label: "Type", type: "select", options: ["note", "snippet"], required: true, half: true },
    { name: "language", label: "Language", placeholder: "python, java, sql…", half: true },
    { name: "skill_id", label: "Skill", type: "select", options: skillOpts },
    { name: "content", label: "Content", type: "textarea" },
    { name: "tags", label: "Tags", type: "tags" },
  ];
  return (
    <>
      <div className="mb-3 flex gap-2"><Input placeholder="Search notes and code" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-xs" /><Button className="ml-auto" variant="primary" icon={<Plus className="size-4" />} onClick={() => setEdit({})}>Note</Button></div>
      {list.isLoading ? <Loading /> : (list.data || []).length === 0 ? <Empty title="No notes yet" /> : (
        <div className="grid gap-3 md:grid-cols-2">
          {(list.data || []).map((n: any) => (
            <Card key={n.id} className="cursor-pointer hover:border-ink-3">
              <button className="block w-full text-left" onClick={() => setEdit(n)}>
                <div className="mb-2 flex items-center gap-2"><span className="flex-1 truncate font-medium">{n.title}</span>{n.language && <Badge tone="accent">{n.language}</Badge>}<Badge>{n.kind}</Badge></div>
                {n.kind === "snippet" ? <pre className="max-h-40 overflow-hidden rounded-lg bg-surface-2 p-2.5 font-mono text-[12px] leading-relaxed text-ink-2">{n.content}</pre> : <p className="line-clamp-4 text-sm whitespace-pre-line text-ink-2">{n.content}</p>}
              </button>
            </Card>
          ))}
        </div>
      )}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit note" : "New note"} wide>
        {edit && <EntityForm fields={fields} initial={edit.id ? edit : { kind: "note" }} onSubmit={async (d) => { edit.id ? await crud.update.mutateAsync({ id: edit.id, data: d }) : await crud.create.mutateAsync(d); setEdit(null); }} onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); setEdit(null); } : undefined} />}
      </Modal>
    </>
  );
}
