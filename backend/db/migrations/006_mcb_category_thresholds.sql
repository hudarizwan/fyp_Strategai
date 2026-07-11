CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS mcb_category_thresholds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL UNIQUE,
    approval_confidence_threshold NUMERIC(4,3) NOT NULL CHECK (
        approval_confidence_threshold >= 0
        AND approval_confidence_threshold <= 1
    ),
    changed_by TEXT NOT NULL DEFAULT 'system:threshold-script',
    change_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mcb_threshold_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    threshold_id UUID REFERENCES mcb_category_thresholds(id) ON DELETE SET NULL,
    category TEXT NOT NULL,
    old_approval_confidence_threshold NUMERIC(4,3),
    new_approval_confidence_threshold NUMERIC(4,3) NOT NULL CHECK (
        new_approval_confidence_threshold >= 0
        AND new_approval_confidence_threshold <= 1
    ),
    changed_by TEXT NOT NULL,
    change_reason TEXT,
    source_script TEXT NOT NULL DEFAULT 'set_mcb_category_threshold.py',
    action_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mcb_category_thresholds_created_at
    ON mcb_category_thresholds(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mcb_threshold_audit_events_category
    ON mcb_threshold_audit_events(category);
CREATE INDEX IF NOT EXISTS idx_mcb_threshold_audit_events_created_at
    ON mcb_threshold_audit_events(created_at DESC);
