"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Loader2, Pencil, Plus, Shield, Trash2, UserCog, UserRound } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  createAdminUser,
  deleteAdminUser,
  fetchAdminUsers,
  updateAdminUser,
  type AdminUser,
  type UserRole,
} from "@/lib/admin-users";

type FlashMessage = { kind: "success" | "error"; text: string } | null;

type UserFormState = {
  email: string;
  displayName: string;
  role: UserRole;
  isActive: boolean;
  password: string;
};

const EMPTY_FORM: UserFormState = {
  email: "",
  displayName: "",
  role: "user",
  isActive: true,
  password: "",
};

function RoleBadge({ role }: { role: UserRole }) {
  if (role === "admin") {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full text-info bg-info/10">
        <Shield className="h-3 w-3" />
        Admin
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full text-muted bg-surface-hover">
      <UserRound className="h-3 w-3" />
      Usuario
    </span>
  );
}

function UserFormModal({
  isOpen,
  user,
  onClose,
  onSuccess,
}: {
  isOpen: boolean;
  user: AdminUser | null;
  onClose: () => void;
  onSuccess: (message: string) => void;
}) {
  const isEdit = Boolean(user);
  const [form, setForm] = useState<UserFormState>(EMPTY_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<FlashMessage>(null);

  useEffect(() => {
    if (!isOpen) return;

    if (user) {
      setForm({
        email: user.email,
        displayName: user.displayName,
        role: user.role,
        isActive: user.isActive,
        password: "",
      });
      return;
    }

    setForm(EMPTY_FORM);
    setMessage(null);
  }, [isOpen, user]);

  function updateField<K extends keyof UserFormState>(key: K, value: UserFormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setMessage(null);

    if (!form.displayName.trim()) {
      setMessage({ kind: "error", text: "El nombre para mostrar es obligatorio." });
      return;
    }

    if (!isEdit && !form.email.trim()) {
      setMessage({ kind: "error", text: "El correo del usuario es obligatorio." });
      return;
    }

    if (!isEdit && !form.password) {
      setMessage({ kind: "error", text: "La contraseña inicial es obligatoria." });
      return;
    }

    if (form.password && form.password.length < 8) {
      setMessage({ kind: "error", text: "La contraseña debe tener al menos 8 caracteres." });
      return;
    }

    setIsSubmitting(true);
    try {
      if (isEdit && user) {
        await updateAdminUser(user.id, {
          displayName: form.displayName,
          role: form.role,
          isActive: form.isActive,
          password: form.password || undefined,
        });
        onSuccess("Usuario actualizado correctamente.");
      } else {
        await createAdminUser({
          email: form.email,
          displayName: form.displayName,
          role: form.role,
          isActive: form.isActive,
          password: form.password,
        });
        onSuccess("Usuario creado correctamente.");
      }
      onClose();
    } catch (error) {
      setMessage({
        kind: "error",
        text: error instanceof Error ? error.message : "No fue posible guardar el usuario.",
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-bg-soft border border-border rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-ink">
            {isEdit ? "Editar usuario" : "Crear usuario"}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
          >
            <span className="sr-only">Cerrar</span>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-muted mb-1.5">Correo</label>
            <input
              value={form.email}
              onChange={(event) => updateField("email", event.target.value)}
              disabled={isEdit}
              placeholder="usuario@empresa.com"
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink placeholder:text-soft disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted mb-1.5">Nombre para mostrar</label>
            <input
              value={form.displayName}
              onChange={(event) => updateField("displayName", event.target.value)}
              placeholder="Nombre del usuario"
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted mb-1.5">Rol</label>
              <select
                value={form.role}
                onChange={(event) => updateField("role", event.target.value as UserRole)}
                className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
              >
                <option value="user">Usuario</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-muted mb-1.5">Estado</label>
              <select
                value={form.isActive ? "active" : "inactive"}
                onChange={(event) => updateField("isActive", event.target.value === "active")}
                className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
              >
                <option value="active">Activo</option>
                <option value="inactive">Inactivo</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-muted mb-1.5">
              {isEdit ? "Nueva contraseña (opcional)" : "Contraseña inicial"}
            </label>
            <input
              value={form.password}
              onChange={(event) => updateField("password", event.target.value)}
              type="password"
              placeholder={isEdit ? "Deja en blanco para mantener la actual" : "Mínimo 8 caracteres"}
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
            />
          </div>

          {message && (
            <p
              className={cn(
                "text-xs px-3 py-2 rounded-lg",
                message.kind === "error" ? "bg-danger/10 text-danger" : "bg-success/10 text-success",
              )}
            >
              {message.text}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-muted hover:text-ink hover:bg-surface-hover transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {isSubmitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {isSubmitting ? "Guardando..." : "Guardar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function UsersPanel() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<FlashMessage>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const stats = useMemo(() => {
    const admins = users.filter((user) => user.role === "admin").length;
    const active = users.filter((user) => user.isActive).length;
    return { total: users.length, admins, active };
  }, [users]);

  async function loadUsers() {
    try {
      const nextUsers = await fetchAdminUsers();
      setUsers(nextUsers);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "No fue posible cargar los usuarios.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  function openCreateModal() {
    setSelectedUser(null);
    setIsModalOpen(true);
  }

  function openEditModal(user: AdminUser) {
    setSelectedUser(user);
    setIsModalOpen(true);
  }

  async function handleDelete(user: AdminUser) {
    const confirmed = window.confirm(`¿Eliminar al usuario ${user.displayName}? Esta acción no se puede deshacer.`);
    if (!confirmed) return;

    setDeletingId(user.id);
    setMessage(null);
    try {
      await deleteAdminUser(user.id);
      await loadUsers();
      setMessage({ kind: "success", text: "Usuario eliminado correctamente." });
    } catch (nextError) {
      setMessage({
        kind: "error",
        text: nextError instanceof Error ? nextError.message : "No fue posible eliminar el usuario.",
      });
    } finally {
      setDeletingId(null);
    }
  }

  async function handleSaved(nextMessage: string) {
    await loadUsers();
    setMessage({ kind: "success", text: nextMessage });
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="px-6 py-5 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-ink">Usuarios</h2>
            <p className="text-sm text-muted mt-0.5">Administra cuentas, roles y estado de acceso</p>
          </div>
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors"
          >
            <Plus className="h-4 w-4" />
            Nuevo usuario
          </button>
        </div>

        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <UserCog className="h-4 w-4 text-muted" />
            <span className="text-muted">Total:</span>
            <span className="font-semibold text-ink">{stats.total}</span>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-info" />
            <span className="text-muted">Admins:</span>
            <span className="font-semibold text-ink">{stats.admins}</span>
          </div>
          <div className="flex items-center gap-2">
            <UserRound className="h-4 w-4 text-success" />
            <span className="text-muted">Activos:</span>
            <span className="font-semibold text-ink">{stats.active}</span>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-4">
        {message && (
          <p
            className={cn(
              "text-sm px-4 py-2 rounded-lg",
              message.kind === "error" ? "bg-danger/10 text-danger" : "bg-success/10 text-success",
            )}
          >
            {message.text}
          </p>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-16 text-muted">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            <span className="text-sm">Cargando usuarios...</span>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-16">
            <p className="text-sm text-danger bg-danger/10 px-4 py-2 rounded-lg">{error}</p>
          </div>
        ) : users.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted">
            <UserRound className="h-10 w-10 mb-3 opacity-40" />
            <p className="text-sm">No hay usuarios registrados</p>
          </div>
        ) : (
          <div className="space-y-2">
            {users.map((user) => (
              <article
                key={user.id}
                className="flex items-center gap-4 p-4 rounded-xl bg-surface border border-border hover:bg-surface-hover transition-colors"
              >
                <div className="w-10 h-10 rounded-full bg-accent/10 text-accent flex items-center justify-center text-sm font-semibold">
                  {user.displayName.slice(0, 1).toUpperCase()}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-medium text-ink truncate">{user.displayName}</h3>
                    <RoleBadge role={user.role} />
                    {!user.isActive && (
                      <span className="text-[11px] font-medium px-2 py-0.5 rounded-full text-warning bg-warning/10">
                        Inactivo
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted truncate">{user.email}</p>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => openEditModal(user)}
                    className="p-2 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
                    aria-label={`Editar ${user.displayName}`}
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(user)}
                    disabled={deletingId === user.id}
                    className="p-2 rounded-md text-muted hover:text-danger hover:bg-danger/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label={`Eliminar ${user.displayName}`}
                  >
                    {deletingId === user.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      <UserFormModal
        isOpen={isModalOpen}
        user={selectedUser}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleSaved}
      />
    </div>
  );
}
