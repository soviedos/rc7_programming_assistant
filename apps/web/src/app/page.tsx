import { LoginForm } from "@/components/auth/login-form";
import { RobotOutline } from "@/components/shared/robot-outline";

export default function LoginPage() {
  return (
    <main className="login-screen">
      <div className="login-backdrop" />
      <div className="login-grid-floor" />
      <div className="login-dots login-dots-right" />
      <div className="login-dots login-dots-center" />

      <div className="login-illustration login-illustration-left">
        <RobotOutline className="robot-outline" />
      </div>

      <section className="login-card-shell">
        <LoginForm />
      </section>

      <footer className="login-footer">
        <p>Desarrollado por Universidad CENFOTEC - Laboratorio de robótica</p>
      </footer>
    </main>
  );
}
