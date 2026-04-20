"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSession } from "@/features/auth";
import { getRolePath } from "@/lib/auth";
import {
  changePassword,
  fetchProfile,
  PASSWORD_RULES,
  updateProfile,
  validatePasswordRules,
  type PreferredLanguage,
  type UserProfile,
} from "@/lib/profile";

type FlashMessage = { kind: "success" | "error"; text: string } | null;

const LANGUAGES: Array<{ value: PreferredLanguage; label: string }> = [
  { value: "es", label: "Español" },
  { value: "en", label: "Inglés" },
];

export function SettingsPanel() {
  const router = useRouter();
  const { session } = useSession();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isChangingPw, setIsChangingPw] = useState(false);
  const [profileMsg, setProfileMsg] = useState<FlashMessage>(null);
  const [pwMsg, setPwMsg] = useState<FlashMessage>(null);
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });

  useEffect(() => {
    fetchProfile()
      .then(setProfile)
      .catch((err) => {
        setProfileMsg({
          kind: "error",
          text: err instanceof Error ? err.message : "No fue posible cargar el perfil.",
        });
      })
      .finally(() => setIsLoading(false));
  }, []);

  async function handleSaveProfile(e: FormEvent) {
    e.preventDefault();
    if (!profile) return;

    const name = profile.displayName.trim();
    if (name.length < 2) {
      setProfileMsg({ kind: "error", text: "Ingresa un nombre válido." });
      return;
    }

    setIsSaving(true);
    setProfileMsg(null);
    try {
      const updated = await updateProfile({ ...profile, displayName: name });
      setProfile(updated);
      setProfileMsg({ kind: "success", text: "Perfil actualizado." });
    } catch (err) {
      setProfileMsg({
        kind: "error",
        text: err instanceof Error ? err.message : "Error al guardar.",
      });
    } finally {
      setIsSaving(false);
    }
  }

  async function handleChangePassword(e: FormEvent) {
    e.preventDefault();
    setPwMsg(null);

    if (!pw.current || !pw.next || !pw.confirm) {
      setPwMsg({ kind: "error", text: "Completa todos los campos." });
      return;
    }
    if (pw.next !== pw.confirm) {
      setPw({ current: "", next: "", confirm: "" });
      setPwMsg({ kind: "error", text: "Las contraseñas no coinciden." });
      return;
    }

    const ruleError = validatePasswordRules(pw.next);
    if (ruleError) {
      setPw({ current: "", next: "", confirm: "" });
      setPwMsg({ kind: "error", text: ruleError });
      return;
    }

    setIsChangingPw(true);
    try {
      const msg = await changePassword(pw.current, pw.next);
      setPw({ current: "", next: "", confirm: "" });
      setPwMsg({ kind: "success", text: msg });
    } catch (err) {
      setPw({ current: "", next: "", confirm: "" });
      setPwMsg({
        kind: "error",
        text: err instanceof Error ? err.message : "Error al cambiar contraseña.",
      });
    } finally {
      setIsChangingPw(false);
    }
  }

  const returnPath = session ? getRolePath(session.role) : "/chat";

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 text-muted">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        <span className="text-sm">Cargando perfil…</span>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-xl mx-auto px-6 py-8">
        {/* Back button */}
        <button
          onClick={() => router.push(returnPath)}
          className="flex items-center gap-1.5 text-sm text-muted hover:text-ink transition-colors mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          Volver
        </button>

        <h2 className="text-lg font-semibold text-ink mb-6">Configuración</h2>

        {/* Profile section */}
        {profile && (
          <form onSubmit={handleSaveProfile} className="space-y-4 mb-8">
            <h3 className="text-sm font-medium text-muted uppercase tracking-wider">Perfil</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-muted mb-1.5">Correo</label>
                <input
                  value={profile.email}
                  readOnly
                  className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-soft cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted mb-1.5">Nombre visible</label>
                <input
                  value={profile.displayName}
                  onChange={(e) => setProfile((p) => p ? { ...p, displayName: e.target.value } : p)}
                  className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted mb-1.5">Idioma preferido</label>
                <select
                  value={profile.settings.preferredLanguage}
                  onChange={(e) =>
                    setProfile((p) =>
                      p
                        ? { ...p, settings: { ...p.settings, preferredLanguage: e.target.value as PreferredLanguage } }
                        : p,
                    )
                  }
                  className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang.value} value={lang.value}>{lang.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {profileMsg && (
              <p className={cn(
                "text-xs px-3 py-2 rounded-lg",
                profileMsg.kind === "error" ? "bg-danger/10 text-danger" : "bg-success/10 text-success",
              )}>
                {profileMsg.kind === "success" && <Check className="inline h-3 w-3 mr-1" />}
                {profileMsg.text}
              </p>
            )}

            <button
              type="submit"
              disabled={isSaving}
              className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              {isSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {isSaving ? "Guardando…" : "Guardar perfil"}
            </button>
          </form>
        )}

        {/* Divider */}
        <div className="h-px bg-border mb-8" />

        {/* Password section */}
        <form onSubmit={handleChangePassword} className="space-y-4">
          <h3 className="text-sm font-medium text-muted uppercase tracking-wider">Contraseña</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-muted mb-1.5">Contraseña actual</label>
              <input
                type="password"
                value={pw.current}
                onChange={(e) => setPw((s) => ({ ...s, current: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted mb-1.5">Nueva contraseña</label>
              <input
                type="password"
                value={pw.next}
                onChange={(e) => setPw((s) => ({ ...s, next: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted mb-1.5">Confirmar contraseña</label>
              <input
                type="password"
                value={pw.confirm}
                onChange={(e) => setPw((s) => ({ ...s, confirm: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
              />
            </div>
          </div>

          <ul className="text-[11px] text-soft space-y-0.5 pl-4 list-disc">
            {PASSWORD_RULES.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>

          {pwMsg && (
            <p className={cn(
              "text-xs px-3 py-2 rounded-lg",
              pwMsg.kind === "error" ? "bg-danger/10 text-danger" : "bg-success/10 text-success",
            )}>
              {pwMsg.kind === "success" && <Check className="inline h-3 w-3 mr-1" />}
              {pwMsg.text}
            </p>
          )}

          <button
            type="submit"
            disabled={isChangingPw}
            className="px-4 py-2 rounded-lg bg-surface border border-border text-sm font-medium text-ink hover:bg-surface-hover disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {isChangingPw && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {isChangingPw ? "Actualizando…" : "Cambiar contraseña"}
          </button>
        </form>
      </div>
    </div>
  );
}
