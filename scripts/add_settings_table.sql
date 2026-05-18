-- Migration: add system_settings table
-- Run this script if Base.metadata.create_all() has already been executed
-- and the table is not yet present.

CREATE TABLE IF NOT EXISTS system_settings (
    id            SERIAL PRIMARY KEY,
    key           VARCHAR(120) NOT NULL UNIQUE,
    value         TEXT NOT NULL,
    description   VARCHAR(255) NOT NULL DEFAULT '',
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by    INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_system_settings_key ON system_settings (key);

-- Default values
INSERT INTO system_settings (key, value, description) VALUES
  ('gemini_temperature',       '0.7',   'Temperatura de generación de Gemini (0.0 – 1.0)'),
  ('gemini_max_tokens',        '2048',  'Límite de tokens de salida para Gemini'),
  ('gemini_timeout_seconds',   '300',   'Tiempo máximo de espera para llamadas a Gemini (segundos)'),
  ('rag_top_k_chunks',         '6',     'Número de fragmentos RAG recuperados por consulta'),
  ('rag_context_budget_chars', '12000', 'Presupuesto de caracteres para el contexto RAG'),
  ('history_max_entries',      '50',    'Máximo de entradas de historial de chat por usuario')
ON CONFLICT (key) DO NOTHING;
