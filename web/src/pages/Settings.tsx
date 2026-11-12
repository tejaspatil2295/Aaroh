import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, del, get, patch, post } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Badge, Button, Card, ErrorNote, Field, Input, Loading, Modal, PageHeader, Select, Textarea, cx } from "../components/ui";
import { human } from "../components/EntityForm";
import { applyTheme, getTheme, type Theme } from "../lib/theme";
import { ensurePermission } from "../lib/notifications";

const PREF_FIELDS: { key: string; label: string; type: "number" | "time" | "text"; step?: string }[] = [
  { key: "day_start", label: "Day starts", type: "time" },
  { key: "day_end", label: "Day ends", type: "time" },
  { key: "focus_block_minutes", label: "Focus block (min)", type: "number" },
  { key: "break_minutes", label: "Break between blocks (min)", type: "number" },
  { key: "daily_learning_minutes", label: "Daily learning (min)", type: "number" },
  { key: "weekly_learning_hours", label: "Weekly learning (h)", type: "number", step: "0.5" },
  { key: "daily_protein_g", label: "Daily protein (g)", type: "number" },
  { key: "daily_calories", label: "Daily calories", type: "number" },
  { key: "daily_water_ml", label: "Daily water (ml)", type: "number" },
  { key: "daily_steps", label: "Daily steps", type: "number" },
  { key: "weekly_gym_sessions", label: "Gym sessions / week", type: "number" },
  { key: "monthly_budget", label: "Default monthly budget (₹)", type: "number" },
  { key: "morning_briefing_time", label: "Morning briefing reminder", type: "time" },
  { key: "evening_review_time", label: "Evening review reminder", type: "time" },
  { key: "timezone", label: "Time zone", type: "text" },
];

const MODULE_LABELS: Record<string, string> = { profile: "Profile & background", tasks: "Tasks", goals: "Goals & habits", finance: "Finance", investments: "Investments & loans", journal: "Personal journal", learning: "Learning", fitness: "Fitness & health", work: "Work journal", side_income: "Side income" };

export default function SettingsPage() {
  const qc = useQueryClient();
  const { user, setUser, logout } = useAuth();
  const s = useQuery({ queryKey: ["/users/me/settings"], queryFn: () => get("/users/me/settings") });
  const save = useMutation({ mutationFn: (data: any) => patch("/users/me/settings", data), onSuccess: (d) => { qc.setQueryData(["/users/me/settings"], d); qc.invalidateQueries(); } });
  const [profile, setProfile] = useState({ full_name: user?.full_name || "", about: user?.about || "" });
  const [prefs, setPrefs] = useState<Record<string, any> | null>(null);
  const [ai, setAi] = useState<any>(null);
  const [theme, setTheme] = useState<Theme>(getTheme());
  const [del0, setDel0] = useState(false);
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [msg, setMsg] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  if (!s.data) return <Loading />;
  const P = prefs ?? s.data.preferences;
  const A = ai ?? { ai_provider: s.data.ai_provider, ai_model: s.data.ai_model || "", ai_base_url: s.data.ai_base_url || "", ai_api_key: "" };
  const flash = (m: string) => { setMsg(m); setTimeout(() => setMsg(""), 2500); };

  return (
    <div className="fade-in space-y-4">
      <PageHeader title="Settings" subtitle={user?.email} actions={msg && <Badge tone="good">{msg}</Badge>} />

      <Card title="Profile">
        <div className="grid gap-3">
          <Field label="Name"><Input value={profile.full_name} onChange={(e) => setProfile({ ...profile, full_name: e.target.value })} /></Field>
          <Field label="About you" hint="Background, goals and constraints. Aaroh AI uses this as context (if Profile access is on)."><Textarea rows={5} value={profile.about} onChange={(e) => setProfile({ ...profile, about: e.target.value })} /></Field>
          <div><Button variant="primary" onClick={async () => { setUser(await patch("/users/me", profile)); flash("Profile saved"); }}>Save profile</Button></div>
        </div>
      </Card>

      <Card title="Goals & routine preferences">
        <p className="mb-3 text-sm text-ink-3">AAROH makes no assumptions about your routine. These targets drive scores, planning and reminders.</p>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {PREF_FIELDS.map((f) => (
            <Field key={f.key} label={f.label}>
              <Input type={f.type} step={f.step} value={P[f.key] ?? ""} onChange={(e) => setPrefs({ ...P, [f.key]: f.type === "number" ? Number(e.target.value) : e.target.value })} />
            </Field>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="primary" loading={save.isPending} onClick={async () => { const { theme: _t, currency: _c, ...rest } = P; void _t; void _c; await save.mutateAsync({ preferences: rest }); setPrefs(null); flash("Preferences saved"); }}>Save preferences</Button>
          <Button onClick={async () => flash((await ensurePermission()) ? "Notifications enabled" : "Notifications blocked")}>Enable reminders</Button>
        </div>
      </Card>

      <Card title="Appearance">
        <div className="flex gap-2">{(["system", "light", "dark"] as Theme[]).map((t) => <Button key={t} variant={theme === t ? "primary" : "secondary"} size="sm" onClick={() => { applyTheme(t); setTheme(t); }}>{human(t)}</Button>)}</div>
      </Card>

      <Card title="Privacy: what Aaroh AI can read">
        <p className="mb-3 text-sm text-ink-3">Turn modules off to keep them out of every AI request. Individual journal entries can also be hidden. Data is only sent to the AI provider you configure below.</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {Object.entries(s.data.ai_permissions).map(([k, v]) => (
            <label key={k} className="flex items-center justify-between rounded-xl border border-line px-3 py-2.5 text-sm">
              <span>{MODULE_LABELS[k] || human(k)}</span>
              <button role="switch" aria-checked={!!v} aria-label={MODULE_LABELS[k]} onClick={() => save.mutate({ ai_permissions: { [k]: !v } })} className={cx("relative h-6 w-10 rounded-full transition-colors", v ? "bg-accent" : "bg-surface-2 border border-line")}>
                <span className={cx("absolute top-0.5 size-5 rounded-full bg-white shadow transition-all", v ? "left-[18px]" : "left-0.5")} />
              </button>
            </label>
          ))}
        </div>
        <Button className="mt-3" size="sm" variant="ghost" onClick={async () => setPreview((await get("/ai/context-preview")).context)}>Preview exactly what the AI sees</Button>
      </Card>

      <Card title="AI provider">
        <div className="mb-3 text-sm">
          Currently: {s.data.ai_effective.mode === "ai" ? <Badge tone="accent">{s.data.ai_effective.provider} · {s.data.ai_effective.model} ({s.data.ai_effective.source === "user" ? "your key" : "server key"})</Badge> : <Badge tone="warn">Offline mode (rule-based summaries only)</Badge>}
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Provider">
            <Select value={A.ai_provider} onChange={(e) => setAi({ ...A, ai_provider: e.target.value })}>
              <option value="default">Server default</option>
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="openai_compatible">OpenAI-compatible (OpenAI, Groq, OpenRouter, Ollama…)</option>
              <option value="none">Off (offline mode)</option>
            </Select>
          </Field>
          <Field label="Model" hint={A.ai_provider === "anthropic" ? "Default: claude-opus-5-5" : A.ai_provider === "openai_compatible" ? "e.g. gpt-4o-mini, llama-3.3-70b-versatile" : undefined}><Input value={A.ai_model} onChange={(e) => setAi({ ...A, ai_model: e.target.value })} /></Field>
          {A.ai_provider === "openai_compatible" && <Field label="Base URL" hint="https://api.openai.com/v1 · http://localhost:11434/v1 for Ollama"><Input value={A.ai_base_url} onChange={(e) => setAi({ ...A, ai_base_url: e.target.value })} /></Field>}
          <Field label={`API key ${s.data.ai_key_set ? "(a key is saved, encrypted)" : ""}`} hint="Stored encrypted on the server and never sent back to the app."><Input type="password" autoComplete="off" placeholder={s.data.ai_key_set ? "•••••••• (leave blank to keep)" : "Paste key"} value={A.ai_api_key} onChange={(e) => setAi({ ...A, ai_api_key: e.target.value })} /></Field>
        </div>
        <div className="mt-3 flex gap-2">
          <Button variant="primary" loading={save.isPending} onClick={async () => { const { ai_api_key, ...rest } = A; await save.mutateAsync({ ...rest, ...(ai_api_key ? { ai_api_key } : {}) }); setAi(null); flash("AI settings saved"); }}>Save AI settings</Button>
          {s.data.ai_key_set && <Button variant="ghost" onClick={async () => { await save.mutateAsync({ ai_api_key: "" }); flash("Key removed"); }}>Remove saved key</Button>}
        </div>
        <ErrorNote error={save.error} />
      </Card>

      <Card title="Security & data">
        <div className="grid gap-3 md:grid-cols-3">
          <Field label="Current password"><Input type="password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></Field>
          <Field label="New password"><Input type="password" minLength={8} value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
          <div className="flex items-end"><Button disabled={pw.new_password.length < 8} onClick={async () => { try { await post("/users/me/password", pw); setPw({ current_password: "", new_password: "" }); flash("Password changed"); } catch (e) { alert((e as Error).message); } }}>Change password</Button></div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
          <Button onClick={async () => { const r: Response = await api("/users/me/export", { raw: true }); const url = URL.createObjectURL(await r.blob()); const a = document.createElement("a"); a.href = url; a.download = "aaroh-export.json"; a.click(); URL.revokeObjectURL(url); }}>Export all my data (JSON)</Button>
          <Button onClick={logout}>Sign out</Button>
          <Button variant="danger" onClick={() => setDel0(true)}>Delete account</Button>
        </div>
      </Card>

      <Modal open={!!preview} onClose={() => setPreview(null)} title="AI context preview" wide>
        <pre className="max-h-[60vh] overflow-auto rounded-lg bg-surface-2 p-3 text-[11px] leading-relaxed whitespace-pre-wrap">{preview}</pre>
      </Modal>
      <DeleteModal open={del0} onClose={() => setDel0(false)} onDeleted={logout} />
    </div>
  );
}

function DeleteModal({ open, onClose, onDeleted }: { open: boolean; onClose: () => void; onDeleted: () => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState<unknown>(null);
  return (
    <Modal open={open} onClose={onClose} title="Delete account permanently">
      <p className="mb-3 text-sm text-ink-2">This deletes your account and every record, photo and AI conversation. It cannot be undone. Export your data first if you want a copy.</p>
      <div className="space-y-3">
        <Field label="Password"><Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
        <Field label='Type "DELETE" to confirm'><Input value={confirm} onChange={(e) => setConfirm(e.target.value)} /></Field>
        <ErrorNote error={err} />
        <Button variant="danger" className="w-full" disabled={confirm !== "DELETE" || !password} onClick={async () => { try { await del("/users/me", { password, confirm }); onDeleted(); } catch (e) { setErr(e); } }}>Delete everything</Button>
      </div>
    </Modal>
  );
}
