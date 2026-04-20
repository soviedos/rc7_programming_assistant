import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/auth/protected-route";

const sampleCode = `PROGRAM PICK_AND_PLACE
  TAKEARM 1
  MOTOR ON
  SPEED 35
  APPROACH P, P[11], 80
  MOVE L, P_PICK
  HAND ON
  DLY 0.3
  DEPART 80
  MOVE P, P_SAFE
  APPROACH P, P[21], 100
  MOVE L, P_PLACE
  HAND OFF
  DLY 0.2
  DEPART 100
  MOVE P, P_HOME
END`;

export default function WorkspacePage() {
  return (
    <ProtectedRoute allowedRoles={["admin", "user"]}>
      <AppShell
        leftSidebar={
          <div className="sidebar-stack">
            <section className="sidebar-group sidebar-group-strong">
              <p className="sidebar-label">Configuración</p>
              <h2>Perfil de trabajo</h2>
              <div className="control-stack">
                <label className="control-field">
                  <span className="control-label">Modelo de robot</span>
                  <select className="control-select" defaultValue="vp6242">
                    <option value="vp6242">VP-6242</option>
                    <option value="vs6556">VS-6556</option>
                    <option value="vm6083">VM-6083</option>
                  </select>
                </label>
                <label className="control-field">
                  <span className="control-label">Controlador</span>
                  <select className="control-select" defaultValue="rc7">
                    <option value="rc7">RC7</option>
                    <option value="rc8">RC8</option>
                  </select>
                </label>
                <label className="control-field">
                  <span className="control-label">IO configurada</span>
                  <select className="control-select" defaultValue="cell-a">
                    <option value="cell-a">Celda A</option>
                    <option value="cell-b">Celda B</option>
                    <option value="vacuum">Vacuum gripper</option>
                  </select>
                </label>
              </div>
            </section>

            <section className="sidebar-group">
              <p className="sidebar-label">Contexto técnico</p>
              <dl className="info-list info-list-compact">
                <div>
                  <dt>Eje activo</dt>
                  <dd>6-axis</dd>
                </div>
                <div>
                  <dt>Payload</dt>
                  <dd>Ligero</dd>
                </div>
                <div>
                  <dt>Seguridad</dt>
                  <dd>Fence interlock</dd>
                </div>
              </dl>
            </section>

            <section className="sidebar-group sidebar-group-success">
              <p className="sidebar-label">Knowledge base</p>
              <h2>Manuales listos</h2>
              <p className="card-copy">
                20 manuales indexados con filtros por modelo, controlador y tema PAC.
              </p>
            </section>

            <section className="sidebar-group">
              <p className="sidebar-label">Modo</p>
              <div className="tag-row">
                <span className="tag tag-highlight">Programador senior</span>
              </div>
            </section>
          </div>
        }
        main={
          <section className="workspace-panel">
            <div className="panel-header">
              <div className="conversation-heading">
                <p className="eyebrow">Chat y código</p>
                <h2 className="panel-title">Generación asistida de código PAC</h2>
                <p className="card-copy">
                  Describe la aplicación deseada y el asistente responderá con código
                  PAC, criterios técnicos y referencias del manual.
                </p>
              </div>
              <div className="workspace-language-switch">
                <button className="tab-pill tab-pill-active" type="button">
                  Español
                </button>
                <button className="tab-pill" type="button">
                  Inglés
                </button>
              </div>
            </div>

            <div className="conversation-thread">
              <article className="message-card message-card-user">
                <div className="message-avatar">Tú</div>
                <div className="message-body">
                  <p className="message-label">Consulta</p>
                  <p className="message-copy">
                    Genera una rutina PAC de Pick & Place con control de garra, approach
                    seguro y una secuencia lista para copiar en Wincaps III.
                  </p>
                </div>
              </article>

              <article className="message-card message-card-assistant">
                <div className="message-avatar message-avatar-assistant">AI</div>
                <div className="message-body">
                  <p className="message-label">Respuesta técnica</p>
                  <p className="message-copy">
                    Preparé una secuencia orientada a RC7 para pick and place con
                    `TAKEARM`, approach/depart, activación de mano y retorno a `HOME`.
                    Está pensada para un flujo de producción estable y fácil de adaptar.
                  </p>

                  <div className="code-panel">
                    <div className="card-toolbar">
                      <div>
                        <p className="sidebar-label">Código</p>
                        <h3>Salida PAC lista para copiar</h3>
                      </div>
                      <div className="toolbar-actions">
                        <button className="button button-secondary" type="button">
                          Copy code
                        </button>
                        <button className="button button-ghost" type="button">
                          Validar
                        </button>
                      </div>
                    </div>
                    <pre className="code-block code-block-framed">{sampleCode}</pre>
                  </div>

                  <div className="assistant-footnotes">
                    <span className="footnote-chip">Manual I · Motion flow</span>
                    <span className="footnote-chip">PAC Library · Hand control</span>
                    <span className="footnote-chip">RAG con filtro VP-6242</span>
                  </div>
                </div>
              </article>
            </div>

            <div className="composer-card composer-card-inline">
              <label className="input-label" htmlFor="prompt">
                Solicitud técnica
              </label>
              <div className="prompt-shell">
                <textarea
                  id="prompt"
                  className="prompt-input prompt-input-compact"
                  defaultValue="Genera una rutina de paletizado para VP-6242 con validación de I/O, approach seguro y comentarios listos para copiar en Wincaps III."
                />
                <button className="composer-send" type="button" aria-label="Enviar solicitud">
                  ▶
                </button>
              </div>
              <div className="composer-actions composer-actions-muted">
                <span className="composer-link">Adjuntar</span>
                <span className="composer-link">Comandos PAC</span>
                <span className="composer-link">Grabación de voz</span>
              </div>
            </div>
          </section>
        }
        rightSidebar={
          <div className="sidebar-stack">
            <section className="sidebar-group sidebar-group-strong">
              <p className="sidebar-label">Inspector RAG</p>
              <h2>Referencias</h2>
              <ul className="reference-list reference-list-rich">
                <li>
                  <strong>Programmer&apos;s Manual I</strong>
                  <span>Movimiento, approach/depart y secuencias base</span>
                </li>
                <li>
                  <strong>PAC Library</strong>
                  <span>Control de mano, macros y utilidades reutilizables</span>
                </li>
                <li>
                  <strong>Páginas citadas</strong>
                  <span>12-76, 12-81 y 4-9</span>
                </li>
              </ul>
            </section>

            <section className="sidebar-group">
              <p className="sidebar-label">Herramientas</p>
              <div className="tool-stack">
                <button className="tool-button tool-button-primary" type="button">
                  Validar sintaxis PAC
                </button>
                <button className="tool-button" type="button">
                  Generar plantilla Pick & Place
                </button>
              </div>
            </section>

            <section className="sidebar-group">
              <p className="sidebar-label">Historial</p>
              <ul className="reference-list reference-list-rich">
                <li>
                  <strong>Pick and place base</strong>
                  <span>hace 5 min</span>
                </li>
                <li>
                  <strong>Alarm recovery draft</strong>
                  <span>hace 18 min</span>
                </li>
                <li>
                  <strong>IO mapping review</strong>
                  <span>ayer</span>
                </li>
              </ul>
            </section>
          </div>
        }
      />
    </ProtectedRoute>
  );
}
