import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowUp, MessageSquarePlus, Trash2 } from "lucide-react";
import { del, get, post } from "../api/client";
import { AIText, InsightCard, SourceBadge } from "../components/AI";
import { Badge, Button, Card, ErrorNote, Spinner, Tabs, Textarea, cx } from "../components/ui";

const STARTERS: Record<string, string[]> = {
  life_coach: ["What am I avoiding this week?", "Design a realistic morning routine from my settings", "Why do my tasks keep slipping?"],
  career_mentor: ["How should I position my UPSC years on my resume?", "What's my path to a senior full-stack role?", "Turn this week's work into resume bullets"],
  tech_teacher: ["Quiz me on system design, one question at a time", "Explain Kafka consumer groups simply", "Make a 2-week plan for my biggest skill gap"],
  finance_coach: ["Where can I cut ₹5,000 a month?", "Is my emergency fund on track?", "Which subscriptions should I review?"],
  fitness_companion: ["How do I hit my protein target on a vegetarian day?", "Adjust my week, I keep skipping Wednesday gym", "Am I losing fat at a healthy rate?"],
  journal_companion: ["Help me reflect on today", "What patterns do you see in my mood?", "Help me think through a decision"],
  side_hustle_advisor: ["Which of my opportunities should I test first?", "Design a cheap 2-week validation for UPSC mentorship", "What's realistic with 5 hours a week?"],
};

type Msg = { id: string; role: string; content: string; is_fallback: boolean; model: string };

export default function Companion() {
  const qc = useQueryClient();
  const status = useQuery({ queryKey: ["/ai/status"], queryFn: () => get("/ai/status") });
  const convs = useQuery<any[]>({ queryKey: ["/ai/conversations"], queryFn: () => get("/ai/conversations") });
  const [persona, setPersona] = useState("life_coach");
  const [convId, setConvId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [tab, setTab] = useState<"chat" | "reviews">("chat");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  const open = async (c: any) => {
    setConvId(c.id);
    setPersona(c.persona);
    setMsgs(await get(`/ai/conversations/${c.id}/messages`));
  };
  const send = useMutation({
    mutationFn: (message: string) => post("/ai/chat", { message, persona, conversation_id: convId }),
    onMutate: (message) => setMsgs((m) => [...m, { id: "tmp", role: "user", content: message, is_fallback: false, model: "" }]),
    onSuccess: (r) => {
      setConvId(r.conversation.id);
      setMsgs((m) => [...m.filter((x) => x.id !== "tmp"), r.user_message, r.message]);
      qc.invalidateQueries({ queryKey: ["/ai/conversations"] });
    },
    onError: () => setMsgs((m) => m.filter((x) => x.id !== "tmp")),
  });
  const submit = (m = text) => {
    if (!m.trim() || send.isPending) return;
    setText("");
    send.mutate(m.trim());
  };
  const personas = status.data?.personas || [];
  const current = personas.find((p: any) => p.id === persona);

  return (
    <div className="fade-in">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Aaroh AI</h1>
          <p className="mt-0.5 flex flex-wrap items-center gap-2 text-sm text-ink-3">
            {status.data?.mode === "ai" ? <Badge tone="accent">Connected · {status.data.model}</Badge> : <Badge tone="warn">Offline mode: no AI provider configured</Badge>}
            <Link to="/settings" className="text-xs text-accent">Privacy & provider settings</Link>
          </p>
        </div>
        <Tabs value={tab} onChange={setTab} tabs={[{ id: "chat", label: "Chat" }, { id: "reviews", label: "Reviews & insights" }]} />
      </div>

      {tab === "reviews" ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <InsightCard kind="weekly_review" title="Weekly life review" cta="Review my week" />
          <InsightCard kind="monthly_review" title="Monthly life review" cta="Review my month" />
          <InsightCard kind="task_suggestions" title="Suggested tasks" cta="Suggest tasks" />
          <InsightCard kind="habit_analysis" title="Habit consistency" cta="Analyse habits" />
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
          <div className="hidden space-y-1 lg:block">
            <Button className="mb-2 w-full" icon={<MessageSquarePlus className="size-4" />} onClick={() => { setConvId(null); setMsgs([]); }}>New chat</Button>
            {(convs.data || []).map((c) => (
              <div key={c.id} className={cx("group flex items-center rounded-lg px-2 py-1.5 text-sm", convId === c.id ? "bg-surface-2" : "hover:bg-surface-2")}>
                <button className="min-w-0 flex-1 truncate text-left" onClick={() => open(c)}>{c.title}</button>
                <button aria-label="Delete conversation" className="hidden text-ink-3 group-hover:block hover:text-bad" onClick={async () => { await del(`/ai/conversations/${c.id}`); if (convId === c.id) { setConvId(null); setMsgs([]); } qc.invalidateQueries({ queryKey: ["/ai/conversations"] }); }}><Trash2 className="size-3.5" /></button>
              </div>
            ))}
          </div>
          <Card className="flex min-h-[70vh] flex-col" pad={false}>
            <div className="flex gap-1 overflow-x-auto border-b border-line p-2">
              {personas.map((p: any) => (
                <button key={p.id} onClick={() => setPersona(p.id)} className={cx("h-8 shrink-0 rounded-lg px-3 text-[13px] font-medium", persona === p.id ? "bg-accent-soft text-accent" : "text-ink-2 hover:bg-surface-2")}>{p.title}</button>
              ))}
            </div>
            <div className="flex-1 space-y-4 overflow-y-auto p-4">
              {msgs.length === 0 && (
                <div className="mx-auto max-w-md py-8 text-center">
                  <div className="text-sm font-medium">{current?.title}</div>
                  <p className="mt-1 text-xs text-ink-3">{current?.description}</p>
                  <div className="mt-4 space-y-2">{(STARTERS[persona] || []).map((s) => <button key={s} onClick={() => submit(s)} className="block w-full rounded-xl border border-line px-3 py-2 text-left text-sm text-ink-2 hover:border-accent hover:text-ink">{s}</button>)}</div>
                </div>
              )}
              {msgs.map((m) => (
                <div key={m.id} className={cx("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                  <div className={cx("max-w-[85%] rounded-2xl px-3.5 py-2.5", m.role === "user" ? "bg-accent text-white" : "bg-surface-2")}>
                    {m.role === "user" ? <p className="text-sm whitespace-pre-line">{m.content}</p> : <><div className="mb-1"><SourceBadge fallback={m.is_fallback} model={m.model} /></div><AIText text={m.content} /></>}
                  </div>
                </div>
              ))}
              {send.isPending && <div className="flex items-center gap-2 text-sm text-ink-3"><Spinner className="size-4" /> Aaroh is thinking…</div>}
              <ErrorNote error={send.error} />
              <div ref={endRef} />
            </div>
            <form className="flex items-end gap-2 border-t border-line p-3" onSubmit={(e) => { e.preventDefault(); submit(); }}>
              <Textarea aria-label="Message" rows={1} className="min-h-[42px] resize-none" placeholder={`Ask your ${current?.title?.toLowerCase() || "companion"}…`} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }} />
              <Button type="submit" variant="primary" aria-label="Send" className="h-[42px] w-[42px] shrink-0 p-0" disabled={!text.trim()} loading={send.isPending}><ArrowUp className="size-4" /></Button>
            </form>
          </Card>
        </div>
      )}
      <p className="mt-3 text-xs text-ink-3">Aaroh AI gives general guidance, not professional medical, financial or mental-health advice. In a crisis in India, call Tele-MANAS 14416 or 112.</p>
    </div>
  );
}
