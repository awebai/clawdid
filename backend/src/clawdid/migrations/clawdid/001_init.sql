-- Initial clawdid schema

CREATE TABLE IF NOT EXISTS {{tables.did_claw_mappings}} (
  did_claw       TEXT PRIMARY KEY,
  current_did_key TEXT NOT NULL,
  server_url     TEXT NOT NULL,
  address        TEXT NOT NULL,
  handle         TEXT,
  created_at     TIMESTAMPTZ NOT NULL,
  updated_at     TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS {{tables.did_claw_log}} (
  did_claw        TEXT NOT NULL REFERENCES {{tables.did_claw_mappings}} (did_claw),
  seq             BIGINT NOT NULL,
  operation       TEXT NOT NULL,
  previous_did_key TEXT,
  new_did_key      TEXT NOT NULL,
  prev_entry_hash  TEXT,
  entry_hash       TEXT NOT NULL,
  state_hash       TEXT NOT NULL,
  authorized_by    TEXT NOT NULL,
  signature        TEXT NOT NULL,
  timestamp        TEXT NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (did_claw, seq)
);

CREATE INDEX IF NOT EXISTS did_claw_log_did_claw_seq_idx
  ON {{tables.did_claw_log}} (did_claw, seq);

