import { useEffect } from "react";
import Markdown from "react-markdown";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Sparkles } from "lucide-react";
import { get, post, qs } from "../api/client";
import { Badge, Button, Card, ErrorNote, Spinner } from "./ui";

export function AIText({ text }: { text: string }) {
  return (
    <div className="prose-ai text-sm leading-relaxed text-ink">
      <Markdown>{text}</Markdown>
    </div>
  );
}

export function SourceBadge({ fallback, model }: { fallback: boolean; model?: string }) {
  return fallback ? <Badge tone="warn">Offline mode · rule-based</Badge> : <Badge tone="accent">AI · {model}</Badge>;
}

type Insight = { id: string; kind: string; content: string; is_fallback: boolean; model: string; created_at: string };

/** Shows the latest insight of a kind, with generate / regenerate. */
export function InsightCard({ kind, title, cta = "Generate", className, autoLoad = false }: { kind: string; title: string; cta?: string; className?: string; autoLoad?: boolean }) {
  const qc = useQueryClient();
  const latest = useQuery<Insight[]>({ queryKey: ["/ai/insights", kind], queryFn: () => get(`/ai/insights${qs({ kind, limit: 1 })}`) });
  const gen = useMutation({
    mutationFn: (force: boolean) => post<Insight>("/ai/insights", { kind, force }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/ai/insights", kind] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
  const ins = latest.data?.[0];
  const shouldAuto = autoLoad && latest.isSuccess && !ins && gen.isIdle;
  useEffect(() => {
    if (shouldAuto) gen.mutate(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shouldAuto]);
  return (
    <Card
      className={className}
      title={
        <span className="flex items-center gap-1.5">
          <Sparkles className="size-3.5 text-accent" />
          {title}
        </span>
      }
      action={ins && <Button size="sm" variant="ghost" icon={<RefreshCw className="size-3.5" />} loading={gen.isPending} onClick={() => gen.mutate(true)}>Refresh</Button>}
    >
      {latest.isLoading || (gen.isPending && !ins) ? (
        <div className="flex items-center gap-2 text-sm text-ink-3"><Spinner className="size-4" /> Thinking…</div>
      ) : ins ? (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <SourceBadge fallback={ins.is_fallback} model={ins.model} />
            <span className="text-[11px] text-ink-3">{new Date(ins.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</span>
          </div>
          <AIText text={ins.content} />
        </div>
      ) : (
        <Button variant="primary" size="sm" icon={<Sparkles className="size-3.5" />} onClick={() => gen.mutate(false)} loading={gen.isPending}>{cta}</Button>
      )}
      <div className="mt-2"><ErrorNote error={gen.error} /></div>
    </Card>
  );
}
