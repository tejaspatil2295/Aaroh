import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Plus, Sparkles } from "lucide-react";
import { get, post } from "../api/client";
import { AIText } from "../components/AI";
import { EntityForm, human, type FieldDef } from "../components/EntityForm";
import { Badge, Button, Card, Empty, ErrorNote, Loading, Modal, PageHeader, Progress, Stat } from "../components/ui";
import { money } from "../lib/format";
import { useCrud, useInvalidate } from "../lib/hooks";

const CATS = ["upsc_mentorship", "content_creation", "current_affairs", "teaching", "online_course", "freelancing", "consulting", "blogging", "digital_product", "other"];
const STATUS_TONE: Record<string, string> = { idea: "neutral", validating: "accent", active: "good", paused: "warn", dropped: "bad" };

const fields: FieldDef[] = [
  { name: "title", label: "Opportunity", required: true },
  { name: "category", label: "Category", type: "select", options: CATS, required: true, half: true },
  { name: "status", label: "Status", type: "select", options: ["idea", "validating", "active", "paused", "dropped"], required: true, half: true },
  { name: "description", label: "Description", type: "textarea" },
  { name: "hours_per_week", label: "Hours / week you can give", type: "number", step: "0.5", half: true },
  { name: "estimated_investment", label: "Upfront investment (₹)", type: "number", half: true },
  { name: "est_monthly_low", label: "Monthly estimate: low (₹)", type: "number", half: true },
  { name: "est_monthly_high", label: "Monthly estimate: high (₹)", type: "number", half: true },
  { name: "skills_required", label: "Skills required", type: "tags" },
  { name: "validation_notes", label: "Validation notes (evidence of demand)", type: "textarea" },
  { name: "execution_plan", label: "Execution plan", type: "textarea" },
  { name: "next_action", label: "Next action", half: true },
  { name: "progress_pct", label: "Progress %", type: "number", min: 0, max: 100, half: true },
];

export default function SideIncome() {
  const list = useQuery<any[]>({ queryKey: ["/side-income/opportunities"], queryFn: () => get("/side-income/opportunities") });
  const summary = useQuery({ queryKey: ["/side-income/summary"], queryFn: () => get("/side-income/summary") });
  const templates = useQuery<any[]>({ queryKey: ["/side-income/templates"], queryFn: () => get("/side-income/templates"), staleTime: Infinity });
  const crud = useCrud("/side-income/opportunities", ["/side-income/summary"]);
  const inv = useInvalidate();
  const [edit, setEdit] = useState<any | null>(null);
  const [view, setView] = useState<any | null>(null);
  const [showIdeas, setShowIdeas] = useState(false);
  const evaluate = useMutation({ mutationFn: (id: string) => post(`/side-income/opportunities/${id}/evaluate`), onSuccess: (o) => { setView(o); inv("/side-income/opportunities"); } });
  const rev = Object.fromEntries((summary.data?.opportunities || []).map((o: any) => [o.id, o]));

  return (
    <div className="fade-in">
      <PageHeader title="Knowledge & side income" subtitle="Turn your UPSC years and engineering skills into realistic income streams" actions={<><Button onClick={() => setShowIdeas(true)}>Starter ideas</Button><Button variant="primary" icon={<Plus className="size-4" />} onClick={() => setEdit({ category: "other", status: "idea" })}>Opportunity</Button></>} />
      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Opportunities" value={list.data?.length ?? "—"} />
        <Stat label="Revenue to date" value={money(summary.data?.total_revenue)} />
        <Stat label="Costs to date" value={money(summary.data?.total_costs)} />
        <Stat label="Committed hours / week" value={summary.data?.active_hours_per_week ?? "—"} sub="active + validating" />
      </div>
      {list.isLoading ? <Loading /> : (list.data || []).length === 0 ? <Empty title="No opportunities yet" hint="Start from a template based on your background, then validate cheaply before investing." action={<Button onClick={() => setShowIdeas(true)}>Browse starter ideas</Button>} /> : (
        <div className="grid gap-3 md:grid-cols-2">
          {(list.data || []).map((o) => (
            <Card key={o.id}>
              <div className="mb-1 flex items-start gap-2"><button onClick={() => setView(o)} className="flex-1 text-left font-medium">{o.title}</button><Badge tone={STATUS_TONE[o.status]}>{o.status}</Badge></div>
              <div className="mb-2 text-xs text-ink-3">{human(o.category)}{o.hours_per_week && ` · ${Number(o.hours_per_week)} h/week`}{o.est_monthly_low && ` · est. ${money(o.est_monthly_low)}–${money(o.est_monthly_high)}/mo`}</div>
              <Progress value={o.progress_pct / 100} />
              <div className="mt-2 flex items-center justify-between text-xs"><span className="text-ink-3">Revenue {money(rev[o.id]?.revenue)} · costs {money(rev[o.id]?.costs)}</span><span className="text-ink-2">{o.next_action && `Next: ${o.next_action}`}</span></div>
              <div className="mt-3 flex gap-2"><Button size="sm" onClick={() => setEdit(o)}>Edit</Button><Button size="sm" icon={<Sparkles className="size-3.5" />} loading={evaluate.isPending && evaluate.variables === o.id} onClick={() => evaluate.mutate(o.id)}>{o.ai_evaluation ? "Re-evaluate" : "Evaluate realistically"}</Button></div>
            </Card>
          ))}
        </div>
      )}
      <div className="mt-2"><ErrorNote error={evaluate.error} /></div>
      <p className="mt-4 text-xs text-ink-3">Record revenue and costs as transactions in Money and link them to an opportunity. Estimates are yours; AI evaluations state assumptions and never promise income.</p>

      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit opportunity" : "New opportunity"} wide>
        {edit && <EntityForm fields={fields} initial={edit} onSubmit={async (d) => { edit.id ? await crud.update.mutateAsync({ id: edit.id, data: d }) : await crud.create.mutateAsync(d); setEdit(null); }} onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); setEdit(null); } : undefined} />}
      </Modal>
      <Modal open={!!view} onClose={() => setView(null)} title={view?.title || ""} wide>
        {view && (
          <div className="space-y-3 text-sm">
            {view.description && <p className="text-ink-2">{view.description}</p>}
            {view.skills_required?.length > 0 && <div className="flex flex-wrap gap-1">{view.skills_required.map((s: string) => <Badge key={s}>{s}</Badge>)}</div>}
            {view.validation_notes && <div><div className="font-medium">Validation</div><p className="text-ink-2 whitespace-pre-line">{view.validation_notes}</p></div>}
            {view.execution_plan && <div><div className="font-medium">Plan</div><p className="text-ink-2 whitespace-pre-line">{view.execution_plan}</p></div>}
            <div className="rounded-xl border border-line p-3"><div className="mb-1 flex items-center gap-1.5 font-medium"><Sparkles className="size-3.5 text-accent" /> AI evaluation</div>{view.ai_evaluation ? <AIText text={view.ai_evaluation} /> : <p className="text-ink-3">Not evaluated yet.</p>}</div>
          </div>
        )}
      </Modal>
      <Modal open={showIdeas} onClose={() => setShowIdeas(false)} title="Starter ideas for your background" wide>
        <div className="space-y-2">
          {(templates.data || []).map((t) => (
            <div key={t.title} className="rounded-xl border border-line p-3">
              <div className="flex items-start gap-2"><div className="flex-1"><div className="text-sm font-medium">{t.title}</div><p className="mt-0.5 text-xs text-ink-3">{t.description}</p></div><Button size="sm" onClick={async () => { await crud.create.mutateAsync({ ...t, status: "idea" }); setShowIdeas(false); }}>Add</Button></div>
            </div>
          ))}
        </div>
      </Modal>
    </div>
  );
}
