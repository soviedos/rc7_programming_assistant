import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/auth/protected-route";

export default function AdminPage() {
  return (
    <ProtectedRoute allowedRoles={["admin"]}>
      <AppShell
        leftSidebar={
          <div className="sidebar-stack">
            <section className="sidebar-group sidebar-group-strong">
              <p className="sidebar-label">Control</p>
              <h2>Consola administrativa</h2>
              <div className="admin-nav">
                <button className="admin-nav-item admin-nav-item-active" type="button">
                  Usuarios
                </button>
                <button className="admin-nav-item" type="button">
                  Gemini
                </button>
                <button className="admin-nav-item" type="button">
                  Manuales
                </button>
                <button className="admin-nav-item" type="button">
                  Auditoría
                </button>
              </div>
            </section>

            <section className="sidebar-group">
              <p className="sidebar-label">Resumen operativo</p>
              <dl className="info-list info-list-compact">
                <div>
                  <dt>Ambiente</dt>
                  <dd>Producción</dd>
                </div>
                <div>
                  <dt>Acceso SSO</dt>
                  <dd>Google ready</dd>
                </div>
                <div>
                  <dt>RAG</dt>
                  <dd>Indexado por robot</dd>
                </div>
              </dl>
            </section>

            <section className="sidebar-group sidebar-group-success">
              <p className="sidebar-label">Acción rápida</p>
              <h2>Estado estable</h2>
              <p className="card-copy">
                El entorno está listo para agregar usuarios, ajustar el modelo y cargar
                manuales PDF con trazabilidad.
              </p>
            </section>
          </div>
        }
        main={
          <section className="workspace-panel">
            <div className="panel-header">
              <div className="conversation-heading">
                <p className="eyebrow">Administracion</p>
                <h2 className="panel-title">Gobierno del asistente</h2>
                <p className="card-copy">
                  Administra el acceso, la configuración de Gemini y la base documental
                  que alimenta al asistente PAC para DENSO RC7.
                </p>
              </div>
              <span className="status-pill">Config editable</span>
            </div>

            <div className="admin-kpi-grid">
              <article className="admin-kpi-card">
                <p className="sidebar-label">Usuarios</p>
                <strong className="admin-kpi-value">18</strong>
                <span className="admin-kpi-copy">14 activos, 4 administradores</span>
              </article>
              <article className="admin-kpi-card">
                <p className="sidebar-label">Manuales</p>
                <strong className="admin-kpi-value">20</strong>
                <span className="admin-kpi-copy">Indexados con filtros por modelo</span>
              </article>
              <article className="admin-kpi-card">
                <p className="sidebar-label">Gemini</p>
                <strong className="admin-kpi-value">Pro</strong>
                <span className="admin-kpi-copy">Prompt base y límites configurables</span>
              </article>
            </div>

            <div className="admin-panel-stack">
              <section className="admin-feature-card admin-feature-card-wide">
                <div className="card-toolbar">
                  <div>
                    <p className="sidebar-label">Acceso</p>
                    <h3>Usuarios autorizados</h3>
                  </div>
                  <button className="button button-secondary" type="button">
                    Nuevo usuario
                  </button>
                </div>
                <p className="card-copy">
                  Gestiona el CRUD de acceso, roles y estado operativo de cada usuario.
                </p>
                <div className="admin-user-list">
                  <div className="admin-user-row">
                    <div>
                      <strong>soviedo@ucenfotec.ac.cr</strong>
                      <span>Administrador principal</span>
                    </div>
                    <span className="admin-badge admin-badge-primary">Administrador</span>
                  </div>
                  <div className="admin-user-row">
                    <div>
                      <strong>operador.celda@ucenfotec.ac.cr</strong>
                      <span>Programación PAC y troubleshooting</span>
                    </div>
                    <span className="admin-badge">Usuario</span>
                  </div>
                  <div className="admin-user-row">
                    <div>
                      <strong>investigacion.robotica@ucenfotec.ac.cr</strong>
                      <span>Acceso a documentos y validación técnica</span>
                    </div>
                    <span className="admin-badge">Usuario</span>
                  </div>
                </div>
              </section>

              <div className="admin-split-grid">
                <section className="admin-feature-card">
                  <div className="card-toolbar">
                    <div>
                      <p className="sidebar-label">Modelo</p>
                      <h3>Configuración Gemini</h3>
                    </div>
                    <span className="admin-inline-tag">Editable</span>
                  </div>
                  <div className="admin-config-list">
                    <div className="admin-config-row">
                      <span>Modelo activo</span>
                      <strong>Gemini Pro</strong>
                    </div>
                    <div className="admin-config-row">
                      <span>Temperatura</span>
                      <strong>0.2</strong>
                    </div>
                    <div className="admin-config-row">
                      <span>Modo de respuesta</span>
                      <strong>PAC listo para copiar</strong>
                    </div>
                    <div className="admin-config-row">
                      <span>Validación</span>
                      <strong>Obligatoria</strong>
                    </div>
                  </div>
                </section>

                <section className="admin-feature-card">
                  <div className="card-toolbar">
                    <div>
                      <p className="sidebar-label">Knowledge base</p>
                      <h3>Base documental</h3>
                    </div>
                    <button className="button button-ghost" type="button">
                      Cargar PDF
                    </button>
                  </div>
                  <p className="card-copy">
                    Los manuales se almacenan, versionan y se indexan por robot,
                    controlador, tema PAC y troubleshooting.
                  </p>
                  <div className="admin-doc-stats">
                    <div>
                      <strong>VP-6242</strong>
                      <span>8 manuales</span>
                    </div>
                    <div>
                      <strong>RC7 Core</strong>
                      <span>6 manuales</span>
                    </div>
                    <div>
                      <strong>PAC Library</strong>
                      <span>6 manuales</span>
                    </div>
                  </div>
                </section>
              </div>
            </div>
          </section>
        }
        rightSidebar={
          <div className="sidebar-stack">
            <section className="sidebar-group sidebar-group-strong">
              <p className="sidebar-label">Estado del sistema</p>
              <h2>Salud general</h2>
              <dl className="info-list">
                <div>
                  <dt>Manuales indexados</dt>
                  <dd>20</dd>
                </div>
                <div>
                  <dt>Usuarios activos</dt>
                  <dd>18</dd>
                </div>
                <div>
                  <dt>Trabajos pendientes</dt>
                  <dd>2</dd>
                </div>
              </dl>
            </section>

            <section className="sidebar-group">
              <p className="sidebar-label">Pendientes</p>
              <ul className="reference-list reference-list-rich">
                <li>
                  <strong>Actualizar prompt base</strong>
                  <span>Revisión de estilo PAC y reglas de citación</span>
                </li>
                <li>
                  <strong>Cargar manual RC7 alarms</strong>
                  <span>Documento de troubleshooting pendiente de indexar</span>
                </li>
              </ul>
            </section>

            <section className="sidebar-group">
              <p className="sidebar-label">Infraestructura</p>
              <div className="admin-health-stack">
                <div className="admin-health-pill">
                  <span>PostgreSQL + pgvector</span>
                  <strong>Operativo</strong>
                </div>
                <div className="admin-health-pill">
                  <span>MinIO manuals</span>
                  <strong>Sincronizado</strong>
                </div>
                <div className="admin-health-pill">
                  <span>Gemini API</span>
                  <strong>Configurado</strong>
                </div>
              </div>
            </section>
          </div>
        }
      />
    </ProtectedRoute>
  );
}
