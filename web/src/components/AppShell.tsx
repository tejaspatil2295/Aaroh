import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { BookOpen, Briefcase, CheckSquare, Dumbbell, GraduationCap, LayoutDashboard, Lightbulb, MoreHorizontal, Settings, Sparkles, Wallet, X } from "lucide-react";
import { cx } from "./ui";
import { useAuth } from "../auth/AuthContext";
import { useReminderSync } from "../lib/useReminderSync";

export const NAV = [
  { to: "/", label: "Today", icon: LayoutDashboard },
  { to: "/tasks", label: "Plan", icon: CheckSquare },
  { to: "/companion", label: "Aaroh AI", icon: Sparkles },
  { to: "/finance", label: "Money", icon: Wallet },
  { to: "/fitness", label: "Fitness", icon: Dumbbell },
  { to: "/learning", label: "Learning", icon: GraduationCap },
  { to: "/work", label: "Work", icon: Briefcase },
  { to: "/journal", label: "Journal", icon: BookOpen },
  { to: "/side-income", label: "Side income", icon: Lightbulb },
  { to: "/settings", label: "Settings", icon: Settings },
];
const MOBILE_PRIMARY = ["/", "/tasks", "/companion", "/finance"];

export function AppShell() {
  const { user } = useAuth();
  const [more, setMore] = useState(false);
  const loc = useLocation();
  useEffect(() => setMore(false), [loc.pathname]);
  useReminderSync();

  return (
    <div className="flex min-h-full">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line bg-surface px-3 py-5 lg:flex">
        <div className="mb-6 flex items-center gap-2 px-2">
          <img src="/icon.svg" alt="" className="size-7" />
          <div>
            <div className="text-[15px] font-semibold leading-tight tracking-tight">AAROH</div>
            <div className="text-[11px] text-ink-3">Personal Life OS</div>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => cx("flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-sm transition-colors", isActive ? "bg-surface-2 font-medium text-ink" : "text-ink-2 hover:bg-surface-2 hover:text-ink")}>
              <Icon className="size-4" strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="truncate px-2 text-xs text-ink-3">{user?.email}</div>
      </aside>

      <main className="min-w-0 flex-1 pb-24 lg:pb-10">
        <div className="mx-auto w-full max-w-6xl px-4 pt-5 sm:px-6 lg:px-8 lg:pt-8 safe-top">
          <Outlet />
        </div>
      </main>

      {/* mobile bottom nav */}
      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface/95 backdrop-blur lg:hidden safe-bottom" aria-label="Primary">
        <div className="grid grid-cols-5">
          {NAV.filter((n) => MOBILE_PRIMARY.includes(n.to)).map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => cx("flex flex-col items-center gap-0.5 py-2 text-[11px]", isActive ? "text-accent" : "text-ink-3")}>
              <Icon className="size-5" strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
          <button onClick={() => setMore(true)} className="flex flex-col items-center gap-0.5 py-2 text-[11px] text-ink-3">
            <MoreHorizontal className="size-5" />
            More
          </button>
        </div>
      </nav>
      {more && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMore(false)} />
          <div className="fade-in absolute inset-x-0 bottom-0 rounded-t-2xl border-t border-line bg-surface p-4 safe-bottom">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-sm font-semibold">All modules</span>
              <button onClick={() => setMore(false)} aria-label="Close" className="p-1 text-ink-3">
                <X className="size-5" />
              </button>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {NAV.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => cx("flex flex-col items-center gap-1.5 rounded-xl border border-line p-3 text-xs", isActive ? "bg-accent-soft text-accent" : "text-ink-2")}>
                  <Icon className="size-5" strokeWidth={1.8} />
                  {label}
                </NavLink>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
