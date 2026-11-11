import type { ReactNode } from "react";
import { ResponsiveContainer, Tooltip } from "recharts";

export const C = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];
export const axis = { stroke: "var(--ink-3)", fontSize: 11, tickLine: false, axisLine: false } as const;
export const grid = { stroke: "var(--line)", strokeDasharray: "3 3", vertical: false } as const;

export function ChartBox({ height = 220, children }: { height?: number; children: ReactNode }) {
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">{children as any}</ResponsiveContainer>
    </div>
  );
}

export const tip = (
  <Tooltip
    cursor={{ fill: "var(--surface-2)", stroke: "var(--line)" }}
    contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 10, fontSize: 12, color: "var(--ink)" }}
    labelStyle={{ color: "var(--ink-2)" }}
  />
);
