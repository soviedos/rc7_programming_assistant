"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  changePassword,
  fetchProfile,
  PASSWORD_RULES,
  updateProfile,
  type PreferredLanguage,
  type UserProfile,
  validatePasswordRules,
} from "@/lib/profile";
import { fetchSession } from "@/lib/auth";

const LANGUAGE_OPTIONS: Array<{ value: PreferredLanguage; label: string }> = [
  { value: "es", label: "Español" },
  { value: "en", label: "Inglés" },
];

type FlashMessage = {
  kind: "success" | "error";
  text: string;
} | null;

const EMPTY_PASSWORD_STATE = {
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
};

export function ProfileSettingsPanel() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [profileMessage, setProfileMessage] = useState<FlashMessage>(null);
  const [passwordMessage, setPasswordMessage] = useState<FlashMessage>(null);
  const [passwordState, setPasswordState] = useState(EMPTY_PASSWORD_STATE);
  const [returnPath, setReturnPath] = useState("/app");

  useEffect(() => {
    let isMounted = true;

    async function loadProfile() {
      try {
        const currentProfile = await fetchProfile();
        if (isMounted) {
          setProfile(currentProfile);
        }
      } catch (error) {
        if (isMounted) {
          setProfileMessage({
            kind: "error",
            text:
              error instanceof Error
                ? error.message
                : "No fue posible cargar el perfil del usuario.",
          });
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }

      try {
        const currentSession = await fetchSession();
        if (isMounted) {
          if (currentSession?.redirectPath) {
            setReturnPath(currentSession.redirectPath);
          }
        }
      } catch {
        // Si no se puede cargar la sesión, mantenemos la ruta por defecto.
      }
    }

    loadProfile();

    return () => {
      isMounted = false;
    };
  }, []);

  const profileReady = useMemo(() => profile !== null, [profile]);

  function updateProfileField<K extends keyof UserProfile>(key: K, value: UserProfile[K]) {
    setProfile((currentProfile) => {
      if (!currentProfile) {
        return currentProfile;
      }

      return {
        ...currentProfile,
        [key]: value,
      };
    });
  }

  function updateSettingsField<K extends keyof UserProfile["settings"]>(
    key: K,
    value: UserProfile["settings"][K],
  ) {
    setProfile((currentProfile) => {
      if (!currentProfile) {
        return currentProfile;
      }

      return {
        ...currentProfile,
        settings: {
          ...currentProfile.settings,
          [key]: value,
        },
      };
    });
  }

  async function handleSaveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) {
      return;
    }

    const normalizedName = profile.displayName.trim();
    if (normalizedName.length < 2) {
      setProfileMessage({
        kind: "error",
        text: "Ingresa un nombre visible válido.",
      });
      return;
    }

    setIsSavingProfile(true);
    setProfileMessage(null);

    try {
      const updatedProfile = await updateProfile({
        ...profile,
        displayName: normalizedName,
      });
      setProfile(updatedProfile);
      setProfileMessage({
        kind: "success",
        text: "Tu perfil se actualizó correctamente.",
      });
    } catch (error) {
      setProfileMessage({
        kind: "error",
        text: error instanceof Error ? error.message : "No fue posible actualizar el perfil.",
      });
    } finally {
      setIsSavingProfile(false);
    }
  }

  async function handleChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordMessage(null);

    if (!passwordState.currentPassword || !passwordState.newPassword || !passwordState.confirmPassword) {
      setPasswordMessage({
        kind: "error",
        text: "Completa todos los campos de contraseña.",
      });
      return;
    }

    if (passwordState.newPassword !== passwordState.confirmPassword) {
      setPasswordState(EMPTY_PASSWORD_STATE);
      setPasswordMessage({
        kind: "error",
        text: "La confirmación de la nueva contraseña no coincide.",
      });
      return;
    }

    const passwordRulesError = validatePasswordRules(passwordState.newPassword);
    if (passwordRulesError) {
      setPasswordState(EMPTY_PASSWORD_STATE);
      setPasswordMessage({
        kind: "error",
        text: passwordRulesError,
      });
      return;
    }

    setIsChangingPassword(true);

    try {
      const message = await changePassword(passwordState.currentPassword, passwordState.newPassword);
      setPasswordState(EMPTY_PASSWORD_STATE);
      setPasswordMessage({
        kind: "success",
        text: message,
      });
    } catch (error) {
      setPasswordState(EMPTY_PASSWORD_STATE);
      setPasswordMessage({
        kind: "error",
        text:
          error instanceof Error
            ? error.message
            : "No fue posible actualizar la contraseña.",
      });
    } finally {
      setIsChangingPassword(false);
    }
  }

  if (isLoading) {
    return (
      <section className="workspace-panel profile-panel">
        <div className="panel-header">
          <div className="conversation-heading">
            <p className="eyebrow">Perfil</p>
            <h2 className="panel-title">Cargando preferencias del usuario</h2>
            <p className="card-copy">
              Estamos preparando la información de tu cuenta.
            </p>
          </div>
        </div>
      </section>
    );
  }

  if (!profileReady || !profile) {
    return (
      <section className="workspace-panel profile-panel">
        <div className="panel-header">
          <div className="conversation-heading">
            <p className="eyebrow">Perfil</p>
            <h2 className="panel-title">No fue posible cargar el perfil</h2>
            <p className="card-copy">
              Revisa tu sesión e intenta nuevamente desde este mismo espacio.
            </p>
          </div>
        </div>
        {profileMessage ? (
          <p className={`profile-flash profile-flash-${profileMessage.kind}`}>
            {profileMessage.text}
          </p>
        ) : null}
      </section>
    );
  }

  return (
    <section className="workspace-panel profile-panel">
      <div className="panel-header">
        <div className="conversation-heading">
          <p className="eyebrow">Perfil</p>
          <h2 className="panel-title">Perfil de usuario</h2>
          <p className="card-copy">
            Administra tu nombre visible, tu idioma preferido y tu contraseña.
          </p>
        </div>
        <button className="button button-secondary" type="button" onClick={() => router.push(returnPath)}>
          Volver al panel principal
        </button>
      </div>

      <div className="profile-grid">
        <form className="profile-card" onSubmit={handleSaveProfile}>
          <div className="card-toolbar">
            <div>
              <p className="sidebar-label">Cuenta</p>
              <h3>Información y preferencias</h3>
            </div>
          </div>

          <div className="profile-form-grid">
            <label className="control-field">
              <span className="control-label">Correo autorizado</span>
              <input className="profile-input profile-input-readonly" value={profile.email} readOnly />
            </label>

            <label className="control-field">
              <span className="control-label">Nombre visible</span>
              <input
                className="profile-input"
                value={profile.displayName}
                onChange={(event) => updateProfileField("displayName", event.target.value)}
              />
            </label>

            <label className="control-field">
              <span className="control-label">Idioma preferido</span>
              <select
                className="control-select"
                value={profile.settings.preferredLanguage}
                onChange={(event) =>
                  updateSettingsField(
                    "preferredLanguage",
                    event.target.value as PreferredLanguage,
                  )
                }
              >
                {LANGUAGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

          </div>

          {profileMessage ? (
            <p className={`profile-flash profile-flash-${profileMessage.kind}`}>
              {profileMessage.text}
            </p>
          ) : null}

          <div className="profile-actions">
            <button className="button button-secondary" type="submit" disabled={isSavingProfile}>
              {isSavingProfile ? "Guardando..." : "Guardar perfil"}
            </button>
          </div>
        </form>

        <form className="profile-card" onSubmit={handleChangePassword}>
          <div className="card-toolbar">
            <div>
              <p className="sidebar-label">Seguridad</p>
              <h3>Cambiar contraseña</h3>
            </div>
          </div>

          <div className="profile-form-grid">
            <label className="control-field">
              <span className="control-label">Contraseña actual</span>
              <input
                className="profile-input"
                type="password"
                value={passwordState.currentPassword}
                onChange={(event) =>
                  setPasswordState((current) => ({
                    ...current,
                    currentPassword: event.target.value,
                  }))
                }
              />
            </label>

            <label className="control-field">
              <span className="control-label">Nueva contraseña</span>
              <input
                className="profile-input"
                type="password"
                value={passwordState.newPassword}
                onChange={(event) =>
                  setPasswordState((current) => ({
                    ...current,
                    newPassword: event.target.value,
                  }))
                }
              />
            </label>

            <label className="control-field">
              <span className="control-label">Confirmar nueva contraseña</span>
              <input
                className="profile-input"
                type="password"
                value={passwordState.confirmPassword}
                onChange={(event) =>
                  setPasswordState((current) => ({
                    ...current,
                    confirmPassword: event.target.value,
                  }))
                }
              />
            </label>
          </div>

          <ul className="profile-password-hint-list">
            {PASSWORD_RULES.map((rule) => (
              <li key={rule} className="profile-password-hint">
                {rule}
              </li>
            ))}
          </ul>

          {passwordMessage ? (
            <p className={`profile-flash profile-flash-${passwordMessage.kind}`}>
              {passwordMessage.text}
            </p>
          ) : null}

          <div className="profile-actions">
            <button
              className="button button-primary"
              type="submit"
              disabled={isChangingPassword}
            >
              {isChangingPassword ? "Actualizando..." : "Actualizar contraseña"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
