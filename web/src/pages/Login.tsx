import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { getServer, isNative, setServer } from "../api/client";
import { Button, ErrorNote, Field, Input } from "../components/ui";

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [server, setSrv] = useState(getServer());
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      if (isNative) setServer(server);
      if (mode === "login") await login(email, password);
      else await register(email, password, name);
      navigate("/", { replace: true });
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-full place-items-center px-4 py-10 safe-top">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <img src="/icon.svg" alt="" className="mx-auto mb-4 size-12" />
          <h1 className="text-2xl font-semibold tracking-tight">AAROH</h1>
          <p className="mt-1 text-sm text-ink-3">Your personal life operating system</p>
        </div>
        <form onSubmit={submit} className="space-y-3 rounded-2xl border border-line bg-surface p-5">
          {mode === "register" && (
            <Field label="Name">
              <Input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
            </Field>
          )}
          <Field label="Email">
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          </Field>
          <Field label="Password" hint={mode === "register" ? "At least 8 characters" : undefined}>
            <Input type="password" required minLength={mode === "register" ? 8 : undefined} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} />
          </Field>
          {isNative && (
            <Field label="Server address" hint="Where your AAROH backend runs, e.g. https://aaroh.example.com">
              <Input type="url" required value={server} onChange={(e) => setSrv(e.target.value)} placeholder="https://" />
            </Field>
          )}
          <ErrorNote error={err} />
          <Button type="submit" variant="primary" className="w-full" loading={busy}>
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-ink-3">
          {mode === "login" ? "New here? " : "Already have an account? "}
          <button className="font-medium text-accent" onClick={() => setMode(mode === "login" ? "register" : "login")}>
            {mode === "login" ? "Create an account" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}
