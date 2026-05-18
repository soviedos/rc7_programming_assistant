-- Migration: Add audit_log table
-- Run this against your PostgreSQL database if the table doesn't exist yet.

CREATE TABLE IF NOT EXISTS audit_log (
    id          VARCHAR(36)  PRIMARY KEY,
    event_type  VARCHAR(64)  NOT NULL,
    actor_id    INTEGER,
    actor_email VARCHAR(320),
    resource_type VARCHAR(64),
    resource_id VARCHAR(128),
    description TEXT         NOT NULL,
    event_metadata JSONB,
    ip_address  VARCHAR(45),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_audit_log_event_type ON audit_log (event_type);
CREATE INDEX IF NOT EXISTS ix_audit_log_created_at  ON audit_log (created_at);
CREATE INDEX IF NOT EXISTS ix_audit_log_actor_id    ON audit_log (actor_id);
