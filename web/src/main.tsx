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

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Tasks = lazy(() => import("./pages/Tasks"));
const Finance = lazy(() => import("./pages/Finance"));
const Investments = lazy(() => import("./pages/Investments"));
const Journal = lazy(() => import("./pages/Journal"));
const Learning = lazy(() => import("./pages/Learning"));
const Fitness = lazy(() => import("./pages/Fitness"));
const Work = lazy(() => import("./pages/Work"));
const SideIncome = lazy(() => import("./pages/SideIncome"));
const Companion = lazy(() => import("./pages/Companion"));
const SettingsPage = lazy(() => import("./pages/Settings"));

applyTheme();
const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: true } } });

function Gate() {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="grid h-full place-items-center">
        <Loading />
      </div>
    );
  if (!user) return <Login />;
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
