import "@fontsource-variable/inter";
import "./index.css";
import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { AppShell } from "./components/AppShell";
import { Loading } from "./components/ui";
import { applyTheme } from "./lib/theme";
import Login from "./pages/Login";

// Page chunks: loaded lazily, then prefetched in the background after sign-in so navigation is instant.
const pages = {
  Dashboard: () => import("./pages/Dashboard"),
  Tasks: () => import("./pages/Tasks"),
  Finance: () => import("./pages/Finance"),
  Investments: () => import("./pages/Investments"),
  Journal: () => import("./pages/Journal"),
  Learning: () => import("./pages/Learning"),
  Fitness: () => import("./pages/Fitness"),
  Work: () => import("./pages/Work"),
  SideIncome: () => import("./pages/SideIncome"),
  Companion: () => import("./pages/Companion"),
  SettingsPage: () => import("./pages/Settings"),
};
const Dashboard = lazy(pages.Dashboard);
const Tasks = lazy(pages.Tasks);
const Finance = lazy(pages.Finance);
const Investments = lazy(pages.Investments);
const Journal = lazy(pages.Journal);
const Learning = lazy(pages.Learning);
const Fitness = lazy(pages.Fitness);
const Work = lazy(pages.Work);
const SideIncome = lazy(pages.SideIncome);
const Companion = lazy(pages.Companion);
const SettingsPage = lazy(pages.SettingsPage);

applyTheme();
const qc = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000, // reuse data for a minute when moving between screens
      gcTime: 10 * 60_000,
      retry: 1,
      refetchOnWindowFocus: true,
      placeholderData: (prev: unknown) => prev, // keep showing the last data while a filter/month change loads
    },
  },
});

function prefetchPages() {
  const run = () => Object.values(pages).forEach((load) => load().catch(() => undefined));
  const ric = (window as any).requestIdleCallback as ((cb: () => void, o?: { timeout: number }) => void) | undefined;
  if (ric) ric(run, { timeout: 3000 });
  else setTimeout(run, 1200);
}

let prefetched = false;
function prefetchOnce() {
  if (prefetched) return;
  prefetched = true;
  prefetchPages();
}

function Gate() {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="grid h-full place-items-center">
        <Loading variant="inline" />
      </div>
    );
  if (!user) return <Login />;
  prefetchOnce();
  return (
    <Routes>
      <Route element={<AppShell />}>
        {[
          ["/", Dashboard],
          ["/tasks", Tasks],
          ["/finance", Finance],
          ["/investments", Investments],
          ["/journal", Journal],
          ["/learning", Learning],
          ["/fitness", Fitness],
          ["/work", Work],
          ["/side-income", SideIncome],
          ["/companion", Companion],
          ["/settings", SettingsPage],
        ].map(([path, C]: any) => (
          <Route key={path} path={path} element={<Suspense fallback={<Loading />}><C /></Suspense>} />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AuthProvider>
          <Gate />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
