"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  Loader2,
  Pencil,
  Plus,
  Shield,
  Trash2,
  UserRound,
  Wrench,
  X,
} from "lucide-react";

import {
  createRolePermission,
  deleteRolePermission,
  fetchRolePermissions,
  updateRolePermission,
  type RolePermission,
} from "@/lib/roles";
import { cn } from "@/lib/utils";

type FlashMessage = { kind: "success" | "error"; text: string } | null;

type PermissionFormState = {
  key: string;
  name: string;
  description: string;
  admin: boolean;
  user: boolean;
};

const EMPTY_FORM: PermissionFormState = {
  key: "",
  name: "",
  description: "",
  admin: true,
  user: false,
};

function PermissionBadge({ allowed }: { allowed: boolean }) {
  return (
    <span
      className={
        allowed
          ? "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-success/10 text-success"
          : "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-surface-hover text-muted"
      }
    >
      {allowed ? "Permitido" : "No permitido"}
    </span>
  );
}

function PermissionFormModal({
  isOpen,
  form,
  isEdit,
  isSubmitting,
  onClose,
  onChange,
  onSubmit,
}: {
  isOpen: boolean;
  form: PermissionFormState;
  isEdit: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  onChange: <K extends keyof PermissionFormState>(
    key: K,
    value: PermissionFormState[K],
  ) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative bg-bg-soft border border-border rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-ink">
            {isEdit ? "Editar permiso" : "Crear permiso"}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-muted hover:text-ink hover:bg-surface-hover transition-colors"
            aria-label="Cerrar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={onSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-muted mb-1.5">
              Clave
            </label>
            <input
              value={form.key}
              onChange={(event) => onChange("key", event.target.value)}
              disabled={isEdit}
              placeholder="Ej: reports"
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink placeholder:text-soft disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted mb-1.5">
              Nombre
            </label>
            <input
              value={form.name}
              onChange={(event) => onChange("name", event.target.value)}
              placeholder="Ej: Reportes"
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink placeholder:text-soft focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted mb-1.5">
              Descripcion
            </label>
            <textarea
              value={form.description}
              onChange={(event) => onChange("description", event.target.value)}
              rows={3}
              placeholder="Describe que habilita este permiso"
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-sm text-ink placeholder:text-soft resize-none focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/40 transition-colors"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <label className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-surface text-sm text-ink cursor-pointer">
              <input
                type="checkbox"
                checked={form.admin}
                onChange={(event) => onChange("admin", event.target.checked)}
                className="h-4 w-4"
              />
              Admin habilitado
            </label>

            <label className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-surface text-sm text-ink cursor-pointer">
              <input
                type="checkbox"
                checked={form.user}
                onChange={(event) => onChange("user", event.target.checked)}
                className="h-4 w-4"
              />
              Usuario habilitado
            </label>
          </div>

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
              {isSubmitting && (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              )}
              {isSubmitting ? "Guardando..." : "Guardar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DeletePermissionModal({
  isOpen,
  permissionName,
  isDeleting,
  onClose,
  onConfirm,
}: {
  isOpen: boolean;
  permissionName: string;
  isDeleting: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative bg-bg-soft border border-border rounded-2xl shadow-2xl w-full max-w-md mx-4">
        <div className="px-6 py-5 space-y-2">
          <h2 className="text-base font-semibold text-ink">Eliminar permiso</h2>
          <p className="text-sm text-muted">
            Seguro que deseas eliminar{" "}
            <span className="font-medium text-ink">{permissionName}</span>? Esta
            accion no se puede deshacer.
          </p>
        </div>

        <div className="px-6 py-4 border-t border-border flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-muted hover:text-ink hover:bg-surface-hover transition-colors"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 rounded-lg bg-danger text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {isDeleting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {isDeleting ? "Eliminando..." : "Eliminar"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function RolesPanel() {
  const [permissions, setPermissions] = useState<RolePermission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<FlashMessage>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingPermission, setEditingPermission] =
    useState<RolePermission | null>(null);
  const [form, setForm] = useState<PermissionFormState>(EMPTY_FORM);
  const [isSubmittingForm, setIsSubmittingForm] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<RolePermission | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    loadPermissions();
  }, []);

  async function loadPermissions() {
    try {
      const nextPermissions = await fetchRolePermissions();
      setPermissions(nextPermissions);
      setError(null);
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "No fue posible cargar la matriz de permisos.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  function updateFormField<K extends keyof PermissionFormState>(
    key: K,
    value: PermissionFormState[K],
  ) {
    setForm((previous) => ({ ...previous, [key]: value }));
  }

  function openCreateForm() {
    setMessage(null);
    setEditingPermission(null);
    setForm(EMPTY_FORM);
    setIsFormOpen(true);
  }

  function openEditForm(permission: RolePermission) {
    setMessage(null);
    setEditingPermission(permission);
    setForm({
      key: permission.key,
      name: permission.name,
      description: permission.description,
      admin: permission.admin,
      user: permission.user,
    });
    setIsFormOpen(true);
  }

  async function handleSubmitForm(event: FormEvent) {
    event.preventDefault();
    setMessage(null);

    if (!form.key.trim() || !form.name.trim() || !form.description.trim()) {
      setMessage({ kind: "error", text: "Todos los campos son obligatorios." });
      return;
    }

    setIsSubmittingForm(true);
    try {
      if (editingPermission) {
        await updateRolePermission(editingPermission.id, {
          name: form.name,
          description: form.description,
          admin: form.admin,
          user: form.user,
        });
        setMessage({
          kind: "success",
          text: "Permiso actualizado correctamente.",
        });
      } else {
        await createRolePermission({
          key: form.key,
          name: form.name,
          description: form.description,
          admin: form.admin,
          user: form.user,
        });
        setMessage({ kind: "success", text: "Permiso creado correctamente." });
      }

      await loadPermissions();
      setIsFormOpen(false);
    } catch (nextError) {
      setMessage({
        kind: "error",
        text:
          nextError instanceof Error
            ? nextError.message
            : "No fue posible guardar el permiso.",
      });
    } finally {
      setIsSubmittingForm(false);
    }
  }

  function openDeleteModal(permission: RolePermission) {
    setMessage(null);
    setDeleteTarget(permission);
  }

  async function handleConfirmDelete() {
    if (!deleteTarget) return;

    setMessage(null);
    setIsDeleting(true);
    try {
      await deleteRolePermission(deleteTarget.id);
      await loadPermissions();
      setMessage({ kind: "success", text: "Permiso eliminado correctamente." });
      setDeleteTarget(null);
    } catch (nextError) {
      setMessage({
        kind: "error",
        text:
          nextError instanceof Error
            ? nextError.message
            : "No fue posible eliminar el permiso.",
      });
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="px-6 py-5 border-b border-border">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-accent/10 text-accent flex items-center justify-center shrink-0">
            <Wrench className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-ink">Roles y permisos</h2>
            <p className="text-sm text-muted mt-0.5">
              Matriz actual de acceso para roles user y admin.
            </p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-4">
        <div className="flex justify-end">
          <button
            onClick={openCreateForm}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Plus className="h-4 w-4" />
            Nuevo permiso
          </button>
        </div>

        {message && (
          <p
            className={cn(
              "text-sm px-4 py-2 rounded-lg",
              message.kind === "error"
                ? "text-danger bg-danger/10"
                : "text-success bg-success/10",
            )}
          >
            {message.text}
          </p>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <article className="rounded-xl border border-border bg-surface p-4">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="h-4 w-4 text-info" />
              <h3 className="text-sm font-semibold text-ink">Rol Admin</h3>
            </div>
            <p className="text-xs text-muted">
              Tiene permisos operativos y de configuracion, incluyendo gestion
              de manuales y usuarios.
            </p>
          </article>

          <article className="rounded-xl border border-border bg-surface p-4">
            <div className="flex items-center gap-2 mb-2">
              <UserRound className="h-4 w-4 text-muted" />
              <h3 className="text-sm font-semibold text-ink">Rol Usuario</h3>
            </div>
            <p className="text-xs text-muted">
              Enfocado en operacion del asistente: chat, perfil y preferencias
              personales.
            </p>
          </article>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-16 text-muted rounded-xl border border-border bg-surface">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            <span className="text-sm">Cargando permisos...</span>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-16 rounded-xl border border-border bg-surface">
            <p className="text-sm text-danger bg-danger/10 px-4 py-2 rounded-lg">
              {error}
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-surface overflow-hidden">
            <div className="grid grid-cols-12 text-xs font-medium text-muted bg-bg-soft border-b border-border">
              <div className="col-span-5 px-4 py-3">Modulo</div>
              <div className="col-span-3 px-4 py-3">Admin</div>
              <div className="col-span-3 px-4 py-3">Usuario</div>
              <div className="col-span-1 px-4 py-3 text-right">Acciones</div>
            </div>

            <div className="divide-y divide-border">
              {permissions.map((permission) => (
                <div key={permission.key} className="grid grid-cols-12 items-center">
                  <div className="col-span-5 px-4 py-3">
                    <p className="text-sm font-medium text-ink">{permission.name}</p>
                    <p className="text-xs text-muted mt-0.5">
                      {permission.description}
                    </p>
                    <p className="text-[11px] text-soft mt-1">{permission.key}</p>
                  </div>
                  <div className="col-span-3 px-4 py-3">
                    <PermissionBadge allowed={permission.admin} />
                  </div>
                  <div className="col-span-3 px-4 py-3">
                    <PermissionBadge allowed={permission.user} />
                  </div>
                  <div className="col-span-1 px-4 py-3 flex items-center justify-end gap-1">
                    <button
                      onClick={() => openEditForm(permission)}
                      disabled={isSubmittingForm || isDeleting}
                      className="p-1.5 rounded-md text-muted hover:text-ink hover:bg-surface-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label={`Editar ${permission.name}`}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => openDeleteModal(permission)}
                      disabled={isSubmittingForm || isDeleting}
                      className="p-1.5 rounded-md text-muted hover:text-danger hover:bg-danger/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label={`Eliminar ${permission.name}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <PermissionFormModal
        isOpen={isFormOpen}
        form={form}
        isEdit={Boolean(editingPermission)}
        isSubmitting={isSubmittingForm}
        onClose={() => setIsFormOpen(false)}
        onChange={updateFormField}
        onSubmit={handleSubmitForm}
      />

      <DeletePermissionModal
        isOpen={Boolean(deleteTarget)}
        permissionName={deleteTarget?.name ?? ""}
        isDeleting={isDeleting}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
