"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Eye, EyeOff, Loader2, Mail, Lock } from "lucide-react";

import { getRolePath, loginWithPassword } from "@/lib/auth";
import { useSession } from "@/features/auth/session-provider";
import { RobotOutline } from "@/components/shared/robot-outline";

function GoogleIcon() {
  return (
    <svg aria-hidden="true" className="h-4 w-4" viewBox="0 0 24 24">
      <path fill="#EA4335" d="M12.24 10.285v3.821h5.445c-.23 1.229-.92 2.27-1.96 2.966l3.17 2.458c1.85-1.705 2.915-4.216 2.915-7.19 0-.696-.063-1.365-.18-2.015z" />
      <path fill="#34A853" d="M12 22c2.645 0 4.865-.876 6.487-2.37l-3.17-2.458c-.88.59-2.006.94-3.317.94-2.548 0-4.706-1.72-5.476-4.033H3.248v2.534A9.793 9.793 0 0 0 12 22z" />
      <path fill="#4A90E2" d="M6.524 14.079A5.88 5.88 0 0 1 6.218 12c0-.722.124-1.422.306-2.079V7.387H3.248A9.996 9.996 0 0 0 2 12c0 1.614.386 3.141 1.248 4.613z" />
      <path fill="#FBBC05" d="M12 5.888c1.438 0 2.73.495 3.75 1.467l2.813-2.813C16.86 2.96 14.64 2 12 2a9.793 9.793 0 0 0-8.752 5.387l3.276 2.534C7.294 7.608 9.452 5.888 12 5.888z" />
    </svg>
  );
}

export function LoginForm() {
  const router = useRouter();
  const { session, isLoading, refresh } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<{
    kind: "error" | "info";
    text: string;
  } | null>(null);

  useEffect(() => {
    if (!isLoading && session) {
      router.replace(getRolePath(session.role));
    }
  }, [session, isLoading, router]);

  function validate(e: string, p: string): string | null {
    const em = e.trim();
    const pw = p.trim();
    if (!em && !pw) return "Ingresa tu correo y contraseña.";
    if (!em) return "Ingresa tu correo autorizado.";
    if (!em.includes("@")) return "Ingresa un correo válido.";
    if (!pw) return "Ingresa tu contraseña.";
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const error = validate(email, password);
    if (error) {
      setEmail("");
      setPassword("");
      setMessage({ kind: "error", text: error });
      return;
    }

    setIsSubmitting(true);
    setMessage(null);

    try {
      const session = await loginWithPassword(email.trim(), password);
      await refresh();
      router.replace(getRolePath(session.role));
    } catch (err) {
      setEmail("");
      setPassword("");
      setMessage({
        kind: "error",
        text: err instanceof Error ? err.message : "No se pudo conectar con el servidor.",
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-bg">
      {/* Robot illustration — fills left side of screen */}
      <div className="absolute -left-[5%] top-0 bottom-0 pointer-events-none w-[50vw] flex items-center justify-center opacity-[0.35]">
        <RobotOutline className="h-[90vh] w-auto text-white" />
      </div>

      <div className="relative z-10 w-full max-w-100 mx-4">
        {/* Brand */}
        <div className="text-center mb-8">
          <div className="mb-3">
            <p className="text-5xl font-bold text-accent tracking-wide">RobLab</p>
            <div className="flex items-center justify-center gap-3 my-2">
              <span className="h-px w-12 bg-white/40" />
              <span className="text-sm font-medium tracking-widest uppercase text-accent/70">Universidad</span>
              <span className="h-px w-12 bg-white/40" />
            </div>
            <p className="text-4xl font-bold text-accent tracking-wider">CENFOTEC</p>
          </div>
          <h1 className="text-xl font-semibold text-ink font-display mt-4">
            Asistente de Programación
          </h1>
          <p className="text-sm text-muted mt-1">DENSO RC7</p>
        </div>

        {/* Card */}
        <div className="bg-bg-soft/80 backdrop-blur-sm rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.4)] border border-border p-8">
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-xs font-medium text-muted mb-1.5">
                Correo autorizado
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-soft" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="username"
                  placeholder="correo@ejemplo.com"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-surface border border-border text-ink text-sm placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-medium text-muted mb-1.5">
                Contraseña
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-soft" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="w-full pl-10 pr-10 py-2.5 rounded-lg bg-surface border border-border text-ink text-sm placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-soft hover:text-muted transition-colors"
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {isSubmitting ? "Validando…" : "Iniciar sesión"}
            </button>
          </form>

          {/* Message */}
          {message && (
            <p className={`mt-3 text-xs text-center px-2 py-2 rounded-lg ${
              message.kind === "error"
                ? "bg-danger/10 text-danger"
                : "bg-info/10 text-info"
            }`}>
              {message.text}
            </p>
          )}

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <span className="flex-1 h-px bg-border" />
            <span className="text-xs text-soft">o</span>
            <span className="flex-1 h-px bg-border" />
          </div>

          {/* Google SSO */}
          <button
            type="button"
            onClick={() =>
              setMessage({
                kind: "info",
                text: "El SSO con Google está reservado para la siguiente iteración.",
              })
            }
            className="w-full py-2.5 rounded-lg border border-border bg-surface text-ink text-sm font-medium hover:bg-surface-hover transition-colors flex items-center justify-center gap-2.5"
          >
            <GoogleIcon />
            Continuar con Google
          </button>
        </div>

        {/* Footer */}
        <p className="text-center text-[11px] text-soft mt-6">
          Desarrollado por Universidad CENFOTEC — Laboratorio de robótica
        </p>
      </div>
    </div>
  );
}
