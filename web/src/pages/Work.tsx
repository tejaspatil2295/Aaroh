import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { get, qs } from "../api/client";
import { InsightCard } from "../components/AI";
import { EntityForm, type FieldDef } from "../components/EntityForm";
import { Badge, Button, Card, Empty, Input, Loading, Modal, PageHeader, Select, Stat } from "../components/ui";
import { fmtDate, todayIso } from "../lib/format";
import { useCrud, useList } from "../lib/hooks";

const fields: FieldDef[] = [
  { name: "date", label: "Date", type: "date", required: true, half: true },
  { name: "project", label: "Project", half: true },
  { name: "summary", label: "Daily update", type: "textarea", placeholder: "What did you work on today?" },
  { name: "tasks_completed", label: "Completed", type: "textarea" },
  { name: "problems", label: "Problems encountered", type: "textarea", half: true },
  { name: "solutions", label: "Solutions implemented", type: "textarea", half: true },
  { name: "learnings", label: "Learned at work", type: "textarea", half: true },
  { name: "pending", label: "Pending / blockers", type: "textarea", half: true },
  { name: "hours", label: "Hours", type: "number", step: "0.5", half: true },
  { name: "tags", label: "Tags", type: "tags", half: true },
];

export default function Work() {
  const [q, setQ] = useState("");
  const [project, setProject] = useState("");
  const [edit, setEdit] = useState<any | null>(null);
  const list = useList("/work/logs", qs({ q, project }));
  const projects = useQuery<any[]>({ queryKey: ["/work/projects"], queryFn: () => get("/work/projects") });
  const week = useQuery({ queryKey: ["/work/weekly"], queryFn: () => get("/work/weekly") });
  const crud = useCrud("/work/logs", ["/work/projects", "/work/weekly"]);
  return (
    <div className="fade-in">
      <PageHeader title="Work journal" subtitle="Daily updates that become weekly reports, reviews and resume bullets" actions={<Button variant="primary" icon={<Plus className="size-4" />} onClick={() => setEdit({ date: todayIso() })}>Daily update</Button>} />
      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Days logged (7d)" value={week.data?.days_logged ?? "—"} />
        <Stat label="Hours (7d)" value={week.data?.hours ?? "—"} />
        <Stat label="Projects" value={projects.data?.length ?? "—"} />
        <Stat label="Entries" value={list.data?.length ?? "—"} />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          <div className="flex flex-wrap gap-2">
            <Input placeholder="Search problems, solutions, learnings…" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-sm" />
            <Select value={project} onChange={(e) => setProject(e.target.value)} className="w-auto"><option value="">All projects</option>{(projects.data || []).map((p) => <option key={p.project} value={p.project === "General" ? "" : p.project}>{p.project}</option>)}</Select>
          </div>
          {list.isLoading ? <Loading /> : (list.data || []).length === 0 ? <Empty title="No work updates yet" hint="Two or three lines a day are enough." /> : (list.data || []).map((w: any) => (
            <Card key={w.id} className="cursor-pointer hover:border-ink-3">
              <button className="block w-full text-left" onClick={() => setEdit(w)}>
                <div className="mb-1 flex items-center gap-2 text-xs text-ink-3"><span>{fmtDate(w.date, { weekday: "short", day: "numeric", month: "short" })}</span>{w.project && <Badge tone="accent">{w.project}</Badge>}{w.hours && <span>{Number(w.hours)} h</span>}</div>
                <p className="text-sm whitespace-pre-line">{w.summary}</p>
                {(w.problems || w.solutions) && <div className="mt-2 grid gap-2 text-xs sm:grid-cols-2">{w.problems && <div><span className="font-medium text-ink-2">Problem: </span><span className="text-ink-3">{w.problems}</span></div>}{w.solutions && <div><span className="font-medium text-ink-2">Solution: </span><span className="text-ink-3">{w.solutions}</span></div>}</div>}
                {w.pending && <div className="mt-1 text-xs text-warn">Pending: {w.pending}</div>}
              </button>
            </Card>
          ))}
        </div>
        <div className="space-y-4">
          <InsightCard kind="work_weekly_report" title="Weekly work report" cta="Write my weekly report" />
          <Card title="Projects">
            <div className="space-y-2">{(projects.data || []).map((p) => <div key={p.project} className="flex justify-between text-sm"><span>{p.project}</span><span className="text-xs text-ink-3">{p.entries} entries · {p.hours} h</span></div>)}</div>
          </Card>
        </div>
      </div>
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit update" : "Daily work update"} wide>
        {edit && <EntityForm fields={fields} initial={edit} onSubmit={async (d) => { edit.id ? await crud.update.mutateAsync({ id: edit.id, data: d }) : await crud.create.mutateAsync(d); setEdit(null); }} onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); setEdit(null); } : undefined} />}
      </Modal>
    </div>
  );
}
