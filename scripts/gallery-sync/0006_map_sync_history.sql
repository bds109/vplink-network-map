CREATE TABLE map_sync_history (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  original_filename TEXT,
  original_sha256 TEXT,
  source_proof TEXT,
  source_sha256 TEXT NOT NULL,
  data_version TEXT NOT NULL,
  release_revision TEXT,
  published_at TEXT,
  source_verified INTEGER NOT NULL DEFAULT 0 CHECK(source_verified IN (0,1)),
  result TEXT NOT NULL CHECK(result IN ('source','running','success','failed')),
  added_count INTEGER CHECK(added_count>=0),
  updated_count INTEGER CHECK(updated_count>=0),
  disabled_count INTEGER CHECK(disabled_count>=0),
  error_code TEXT
);
CREATE INDEX map_sync_history_recent ON map_sync_history(started_at DESC,id DESC);
