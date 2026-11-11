import { useState, type FormEvent } from "react";
import { Button, ErrorNote, Field, Input, Select, Textarea, cx } from "./ui";

export type FieldDef = {
  name: string;
  label: string;
  type?: "text" | "textarea" | "number" | "date" | "datetime" | "select" | "checkbox" | "tags" | "time";
  options?: (string | { value: string; label: string })[];
  required?: boolean;
  placeholder?: string;
  hint?: string;
  step?: string;
  half?: boolean;
  min?: number;
  max?: number;
};

export const human = (s: string) => s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

function toInput(v: any, f: FieldDef) {
  if (v === null || v === undefined) return f.type === "checkbox" ? false : "";
  if (f.type === "tags") return Array.isArray(v) ? v.join(", ") : v;
  if (f.type === "datetime" && typeof v === "string") {
    const d = new Date(v);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  return v;
}

function fromInput(v: any, f: FieldDef) {
  if (f.type === "checkbox") return !!v;
  if (f.type === "tags") return String(v || "").split(",").map((s) => s.trim()).filter(Boolean);
  if (v === "" || v === undefined) return f.type === "text" || f.type === "textarea" ? "" : null;
  if (f.type === "number") return Number(v);
  if (f.type === "datetime") return new Date(v).toISOString();
  return v;
}

export function EntityForm({ fields, initial, onSubmit, submitLabel = "Save", onDelete }: { fields: FieldDef[]; initial?: Record<string, any>; onSubmit: (data: Record<string, any>) => Promise<unknown>; submitLabel?: string; onDelete?: () => Promise<unknown> }) {
  const [vals, setVals] = useState<Record<string, any>>(() => Object.fromEntries(fields.map((f) => [f.name, toInput(initial?.[f.name], f)])));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const data: Record<string, any> = {};
      for (const f of fields) {
        const out = fromInput(vals[f.name], f);
        if (out === null && !initial?.id) continue; // let server defaults apply on create
        data[f.name] = out;
      }
      await onSubmit(data);
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="grid grid-cols-2 gap-3">
      {fields.map((f) => {
        const common = { id: f.name, name: f.name, required: f.required, placeholder: f.placeholder, value: vals[f.name], onChange: (e: any) => setVals((s) => ({ ...s, [f.name]: f.type === "checkbox" ? e.target.checked : e.target.value })) };
        let control;
        if (f.type === "textarea") control = <Textarea {...common} />;
        else if (f.type === "select")
          control = (
            <Select {...common}>
              {!f.required && <option value="">—</option>}
              {(f.options || []).map((o) => {
                const opt = typeof o === "string" ? { value: o, label: human(o) } : o;
                return (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                );
              })}
            </Select>
          );
        else if (f.type === "checkbox")
          return (
            <label key={f.name} className={cx("flex items-center gap-2 text-sm text-ink-2", f.half ? "col-span-1" : "col-span-2")}>
              <input type="checkbox" checked={!!vals[f.name]} onChange={common.onChange} className="size-4 accent-[var(--accent)]" />
              {f.label}
            </label>
          );
        else control = <Input {...common} type={f.type === "datetime" ? "datetime-local" : f.type === "tags" ? "text" : f.type || "text"} step={f.step} min={f.min} max={f.max} inputMode={f.type === "number" ? "decimal" : undefined} />;
        return (
          <Field key={f.name} label={f.label + (f.required ? " *" : "")} hint={f.hint ?? (f.type === "tags" ? "Comma separated" : undefined)} className={f.half ? "col-span-2 sm:col-span-1" : "col-span-2"}>
            {control}
          </Field>
        );
      })}
      <div className="col-span-2">
        <ErrorNote error={err} />
      </div>
      <div className="col-span-2 flex items-center justify-between gap-2 pt-1">
        {onDelete ? (
          <Button type="button" variant="ghost" className="text-bad" onClick={async () => { if (confirm("Delete this item?")) { setBusy(true); try { await onDelete(); } catch (e) { setErr(e); } finally { setBusy(false); } } }}>
            Delete
          </Button>
        ) : (
          <span />
        )}
        <Button type="submit" variant="primary" loading={busy}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
