import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { get, qs } from "../api/client";
import { addDays, iso } from "./format";
import { dailyAt, scheduleReminders } from "./notifications";

/** Keeps device reminders in sync with task reminders and the morning/evening routine. */
export function useReminderSync() {
  const { data: settings } = useQuery({ queryKey: ["/users/me/settings"], queryFn: () => get("/users/me/settings") });
  const { data: tasks } = useQuery({
    queryKey: ["/tasks/calendar", "reminders"],
    queryFn: () => get(`/tasks/calendar${qs({ from: iso(new Date()), to: iso(addDays(new Date(), 14)) })}`),
    refetchInterval: 10 * 60 * 1000,
  });
  useEffect(() => {
    if (!settings || !tasks) return;
    const p = settings.preferences;
    const items = (tasks as any[])
      .filter((t) => t.reminder_at && t.status !== "done")
      .map((t) => ({ key: `task-${t.id}`, title: t.title, body: t.due_date ? `Due ${t.due_date}` : "Reminder", at: new Date(t.reminder_at) }));
    for (const off of [0, 1]) {
      items.push({ key: `morning-${off}`, title: "Morning briefing", body: "Your plan for today is ready in AAROH.", at: dailyAt(p.morning_briefing_time, off) });
      items.push({ key: `evening-${off}`, title: "Evening review", body: "Take 3 minutes to close the day.", at: dailyAt(p.evening_review_time, off) });
    }
    scheduleReminders(items).catch(() => undefined);
  }, [settings, tasks]);
}
