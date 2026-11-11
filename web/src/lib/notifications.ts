import { LocalNotifications } from "@capacitor/local-notifications";
import { isNative } from "../api/client";

/** Stable 31-bit id from a string so re-scheduling replaces rather than duplicates. */
const idFor = (s: string) => {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return Math.abs(h) % 2147483647;
};

export async function ensurePermission(): Promise<boolean> {
  if (!isNative) {
    if (!("Notification" in window)) return false;
    if (Notification.permission === "granted") return true;
    return (await Notification.requestPermission()) === "granted";
  }
  const p = await LocalNotifications.checkPermissions();
  if (p.display === "granted") return true;
  return (await LocalNotifications.requestPermissions()).display === "granted";
}

type Reminder = { key: string; title: string; body: string; at: Date };

/** Schedules local reminders on Android. On the web, reminders only fire while the tab is open. */
const webTimers = new Map<string, number>();
export async function scheduleReminders(items: Reminder[]) {
  const future = items.filter((r) => r.at.getTime() > Date.now() + 5000);
  if (isNative) {
    const pending = await LocalNotifications.getPending();
    const keep = new Set(future.map((r) => idFor(r.key)));
    const stale = pending.notifications.filter((n) => !keep.has(n.id));
    if (stale.length) await LocalNotifications.cancel({ notifications: stale.map((n) => ({ id: n.id })) });
    if (future.length)
      await LocalNotifications.schedule({
        notifications: future.slice(0, 60).map((r) => ({ id: idFor(r.key), title: r.title, body: r.body, schedule: { at: r.at, allowWhileIdle: true } })),
      });
    return;
  }
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  webTimers.forEach((t) => clearTimeout(t));
  webTimers.clear();
  future
    .filter((r) => r.at.getTime() - Date.now() < 24 * 3600 * 1000)
    .forEach((r) => webTimers.set(r.key, window.setTimeout(() => new Notification(r.title, { body: r.body }), r.at.getTime() - Date.now())));
}

export function dailyAt(hhmm: string, offsetDays = 0) {
  const [h, m] = hhmm.split(":").map(Number);
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  d.setHours(h, m, 0, 0);
  return d;
}
