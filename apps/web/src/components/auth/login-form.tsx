"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import {
  fetchSession,
  getRolePath,
  loginWithPassword,
} from "@/lib/auth";

function FieldIcon({ type }: { type: "email" | "password" }) {
  if (type === "email") {
    return (
      <svg
        aria-hidden="true"
        className="login-field-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M20 21a8 8 0 1 0-16 0" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    );
  }

  return (
    <svg
      aria-hidden="true"
      className="login-field-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V8a4 4 0 1 1 8 0v3" />
      <circle cx="12" cy="16" r="1.2" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg aria-hidden="true" className="google-icon" viewBox="0 0 24 24">
      <path
        fill="#EA4335"
        d="M12.24 10.285v3.821h5.445c-.23 1.229-.92 2.27-1.96 2.966l3.17 2.458c1.85-1.705 2.915-4.216 2.915-7.19 0-.696-.063-1.365-.18-2.015z"
      />
      <path
        fill="#34A853"
        d="M12 22c2.645 0 4.865-.876 6.487-2.37l-3.17-2.458c-.88.59-2.006.94-3.317.94-2.548 0-4.706-1.72-5.476-4.033H3.248v2.534A9.793 9.793 0 0 0 12 22z"
      />
      <path
        fill="#4A90E2"
        d="M6.524 14.079A5.88 5.88 0 0 1 6.218 12c0-.722.124-1.422.306-2.079V7.387H3.248A9.996 9.996 0 0 0 2 12c0 1.614.386 3.141 1.248 4.613z"
      />
      <path
        fill="#FBBC05"
        d="M12 5.888c1.438 0 2.73.495 3.75 1.467l2.813-2.813C16.86 2.96 14.64 2 12 2a9.793 9.793 0 0 0-8.752 5.387l3.276 2.534C7.294 7.608 9.452 5.888 12 5.888z"
      />
    </svg>
  );
}

function PasswordVisibilityIcon({ visible }: { visible: boolean }) {
  if (visible) {
    return (
      <svg
        aria-hidden="true"
        className="login-field-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    );
  }

  return (
    <svg
      aria-hidden="true"
      className="login-field-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path d="M3 3l18 18" />
      <path d="M10.6 6.3A10.4 10.4 0 0 1 12 6c5.5 0 9 6 9 6a16.4 16.4 0 0 1-3.2 3.8" />
      <path d="M6.6 6.7C4.2 8.3 3 12 3 12s3.5 6 9 6a8.8 8.8 0 0 0 2.8-.4" />
      <path d="M9.9 9.9A3 3 0 0 0 14.1 14.1" />
    </svg>
  );
}

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<{
    kind: "error" | "info";
    text: string;
  } | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function validateExistingSession() {
      try {
        const session = await fetchSession();
        if (session && isMounted) {
          router.replace(getRolePath(session.role));
        }
      } catch {
        // El usuario no tiene sesión todavía.
      }
    }

    validateExistingSession();

    return () => {
      isMounted = false;
    };
  }, [router]);

  function resetCredentials() {
    setEmail("");
    setPassword("");
    setShowPassword(false);
  }

  function validateCredentials(currentEmail: string, currentPassword: string): string | null {
    const normalizedEmail = currentEmail.trim();
    const normalizedPassword = currentPassword.trim();

    if (!normalizedEmail && !normalizedPassword) {
      return "Ingresa tu correo autorizado y tu contraseña.";
    }

    if (!normalizedEmail) {
      return "Ingresa tu correo autorizado.";
    }

    if (!normalizedEmail.includes("@")) {
      return "Ingresa un correo valido.";
    }

    if (!normalizedPassword) {
      return "Ingresa tu contraseña.";
    }

    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateCredentials(email, password);

    if (validationError) {
      resetCredentials();
      setMessage({
        kind: "error",
        text: validationError,
      });
      return;
    }

    setIsSubmitting(true);
    setMessage(null);

    try {
      const session = await loginWithPassword(email.trim(), password);
      router.replace(getRolePath(session.role));
    } catch (error) {
      resetCredentials();
      setMessage({
        kind: "error",
        text:
          error instanceof Error
            ? error.message
            : "No se pudo conectar con la API de autenticación en este momento.",
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="login-card">
      <div className="login-brand">
        <p className="login-brand-mark">RobLab</p>
        <div>
          <p className="login-brand-mini">Universidad CENFOTEC</p>
          <h1 className="login-brand-title">
            Asistente de programacion de robot Denso RC7
          </h1>
        </div>
      </div>

      <form className="login-form" onSubmit={handleSubmit} noValidate>
        <label className="login-field login-field-active">
          <FieldIcon type="email" />
          <input
          type="email"
          placeholder="Correo autorizado"
          value={email}
          required
          autoComplete="username"
          onChange={(event) => setEmail(event.target.value)}
        />
      </label>

        <label className="login-field login-field-password">
          <FieldIcon type="password" />
          <input
            type={showPassword ? "text" : "password"}
            placeholder="Contraseña"
            value={password}
            required
            autoComplete="current-password"
            onChange={(event) => setPassword(event.target.value)}
          />
          <button
            className="login-password-toggle"
            type="button"
            aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
            aria-pressed={showPassword}
            onClick={() => setShowPassword((current) => !current)}
          >
            <PasswordVisibilityIcon visible={showPassword} />
          </button>
        </label>

        <button className="login-primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Validando acceso..." : "Iniciar sesión"}
        </button>
      </form>

      {message ? (
        <p
          className={`login-message ${
            message.kind === "error" ? "login-message-error" : "login-message-info"
          }`}
        >
          {message.text}
        </p>
      ) : null}

      <div className="login-divider" aria-hidden="true">
        <span />
        <strong>o</strong>
        <span />
      </div>

      <button
        className="login-google-button"
        type="button"
        onClick={() =>
          setMessage({
            kind: "info",
            text: "El SSO con Google quedo reservado para la siguiente iteracion de integracion.",
          })
        }
      >
        <GoogleIcon />
        <span>Continuar con Google</span>
      </button>

      <div className="login-links">
        <Link href="/">¿Olvidó su contraseña?</Link>
      </div>
    </div>
  );
}
