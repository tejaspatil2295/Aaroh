import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Line, LineChart, XAxis, YAxis } from "recharts";
import { ImagePlus, Lock, Plus } from "lucide-react";
import { api, get, qs } from "../api/client";
import { InsightCard } from "../components/AI";
import { ChartBox, axis, tip } from "../components/charts";
import { EntityForm, human, type FieldDef } from "../components/EntityForm";
import { Badge, Button, Card, Empty, Input, Loading, Modal, PageHeader, Select } from "../components/ui";
import { fmtDate, todayIso } from "../lib/format";
import { useCrud, useList } from "../lib/hooks";

const KINDS = ["reflection", "experience", "event", "achievement", "travel", "lesson", "decision", "gratitude", "daily_review"];
const MOODS = ["", "😞", "😕", "😐", "🙂", "😄"];

const fields: FieldDef[] = [
  { name: "title", label: "Title" },
  { name: "kind", label: "Type", type: "select", options: KINDS, required: true, half: true },
  { name: "entry_date", label: "Date", type: "date", required: true, half: true },
  { name: "body", label: "What happened? What did you think or feel?", type: "textarea" },
  { name: "mood", label: "Mood (1–5)", type: "select", options: [1, 2, 3, 4, 5].map((n) => ({ value: String(n), label: `${n} ${MOODS[n]}` })), half: true },
  { name: "energy", label: "Energy (1–5)", type: "select", options: ["1", "2", "3", "4", "5"], half: true },
  { name: "decision_outcome", label: "Decision / outcome (for decisions & lessons)", type: "textarea" },
  { name: "location", label: "Location", half: true },
  { name: "tags", label: "Tags", type: "tags", half: true },
  { name: "hide_from_ai", label: "Keep this entry private from Aaroh AI", type: "checkbox" },
];

function Photos({ entryId }: { entryId: string }) {
  const list = useQuery<any[]>({ queryKey: ["/attachments", entryId], queryFn: () => get(`/attachments${qs({ entity_id: entryId })}`) });
  const [urls, setUrls] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    (list.data || []).forEach(async (a) => {
      if (urls[a.id]) return;
      const r: Response = await api(`/attachments/${a.id}/file`, { raw: true });
      const u = URL.createObjectURL(await r.blob());
      setUrls((s) => ({ ...s, [a.id]: u }));
    });
  }, [list.data]); // eslint-disable-line react-hooks/exhaustive-deps
  const upload = async (f: File) => {
    setBusy(true);
    const fd = new FormData();
    fd.append("file", f);
    try {
      await api(`/attachments${qs({ entity_type: "journal", entity_id: entryId })}`, { method: "POST", body: fd });
      list.refetch();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="mt-4 border-t border-line pt-4">
      <div className="mb-2 text-[13px] font-medium text-ink-2">Photos</div>
      <div className="flex flex-wrap gap-2">
        {(list.data || []).map((a) => (urls[a.id] ? <img key={a.id} src={urls[a.id]} alt={a.filename} className="size-20 rounded-lg object-cover" /> : <div key={a.id} className="size-20 rounded-lg bg-surface-2" />))}
        <label className="grid size-20 cursor-pointer place-items-center rounded-lg border border-dashed border-line text-ink-3 hover:border-accent">
          {busy ? "…" : <ImagePlus className="size-5" />}
          <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
        </label>
      </div>
    </div>
  );
}

export default function Journal() {
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("");
  const [tag, setTag] = useState("");
  const [edit, setEdit] = useState<any | null>(null);
  const list = useList(tag ? `/journal/by-tag/${encodeURIComponent(tag)}` : "/journal", tag ? "" : qs({ q, kind }));
  const tags = useQuery<Record<string, number>>({ queryKey: ["/journal/tags"], queryFn: () => get("/journal/tags") });
  const mood = useQuery({ queryKey: ["/journal/mood"], queryFn: () => get("/journal/mood?days=90") });
  const crud = useCrud("/journal", ["/journal/tags", "/journal/mood", "/journal/by-tag"]);
  const save = async (d: any) => {
    const data = { ...d, mood: d.mood ? Number(d.mood) : null, energy: d.energy ? Number(d.energy) : null };
    if (edit.id) await crud.update.mutateAsync({ id: edit.id, data });
    else {
      const created: any = await crud.create.mutateAsync(data);
      setEdit(created);
      return;
    }
    setEdit(null);
  };

  return (
    <div className="fade-in">
      <PageHeader title="Journal" subtitle="Experiences, reflections, decisions and lessons" actions={<Button variant="primary" icon={<Plus className="size-4" />} onClick={() => setEdit({ kind: "reflection", entry_date: todayIso() })}>Entry</Button>} />
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="flex flex-wrap gap-2">
            <Input placeholder="Search your journal" value={q} onChange={(e) => { setQ(e.target.value); setTag(""); }} className="max-w-xs" />
            <Select value={kind} onChange={(e) => { setKind(e.target.value); setTag(""); }} className="w-auto"><option value="">All types</option>{KINDS.map((k) => <option key={k} value={k}>{human(k)}</option>)}</Select>
            {tag && <Button size="sm" variant="ghost" onClick={() => setTag("")}>#{tag} ✕</Button>}
          </div>
          {list.isLoading ? <Loading /> : (list.data || []).length === 0 ? <Empty title="No entries" hint="Write two honest lines. Patterns appear after a week or two." /> : (
            (list.data || []).map((e: any) => (
              <Card key={e.id} className="cursor-pointer transition-colors hover:border-ink-3">
                <button className="block w-full text-left" onClick={() => setEdit({ ...e, mood: e.mood ? String(e.mood) : "", energy: e.energy ? String(e.energy) : "" })}>
                  <div className="mb-1 flex items-center gap-2 text-xs text-ink-3">
                    <span>{fmtDate(e.entry_date, { weekday: "short", day: "numeric", month: "short", year: "numeric" })}</span>
                    <Badge>{human(e.kind)}</Badge>
                    {e.mood && <span>{MOODS[e.mood]}</span>}
                    {e.hide_from_ai && <Lock className="size-3" aria-label="Hidden from AI" />}
                  </div>
                  {e.title && <div className="font-medium">{e.title}</div>}
                  <p className="mt-1 line-clamp-3 text-sm whitespace-pre-line text-ink-2">{e.body}</p>
                  {e.tags?.length > 0 && <div className="mt-2 flex flex-wrap gap-1">{e.tags.map((t: string) => <Badge key={t} tone="accent">#{t}</Badge>)}</div>}
                </button>
              </Card>
            ))
          )}
        </div>
        <div className="space-y-4">
          <Card title="Mood · 90 days">
            {mood.data?.mood_series?.length ? (
              <>
                <div className="mb-1 text-sm text-ink-2">Average {mood.data.avg_mood} / 5 across {mood.data.entries} entries</div>
                <ChartBox height={140}>
                  <LineChart data={mood.data.mood_series} margin={{ left: -30, right: 6 }}>
                    <XAxis dataKey="date" {...axis} tickFormatter={(s) => fmtDate(s)} minTickGap={24} />
                    <YAxis domain={[1, 5]} ticks={[1, 3, 5]} {...axis} />
                    {tip}
                    <Line type="monotone" dataKey="mood" stroke="var(--chart-1)" strokeWidth={2} dot={{ r: 2 }} />
                  </LineChart>
                </ChartBox>
              </>
            ) : <p className="text-sm text-ink-3">Add moods to entries to see trends.</p>}
          </Card>
          <Card title="Tags">
            <div className="flex flex-wrap gap-1.5">{Object.entries(tags.data || {}).map(([t, n]) => <button key={t} onClick={() => setTag(t)}><Badge tone={tag === t ? "accent" : "neutral"}>#{t} · {n}</Badge></button>)}</div>
          </Card>
          <InsightCard kind="journal_patterns" title="Reflection companion" cta="Find patterns" />
          <p className="px-1 text-xs text-ink-3">Aaroh AI reads your journal only if you allow it in Settings → Privacy. It is a reflection aid, not a therapist. If you are struggling, Tele-MANAS is free and 24×7 at 14416.</p>
        </div>
      </div>
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Journal entry" : "New entry"} wide>
        {edit && (
          <>
            <EntityForm key={edit.id || "new"} fields={fields} initial={edit} onSubmit={save} onDelete={edit.id ? async () => { await crud.remove.mutateAsync(edit.id); setEdit(null); } : undefined} submitLabel={edit.id ? "Save" : "Save & add photos"} />
            {edit.id && <Photos entryId={edit.id} />}
          </>
        )}
      </Modal>
    </div>
  );
}
