
PRAGMA foreign_keys = ON;
CREATE TABLE meta (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL
);
CREATE TABLE objects (
    hash TEXT PRIMARY KEY NOT NULL CHECK (length(hash) = 64 AND hash NOT GLOB '*[^0-9a-f]*'),
    size INTEGER NOT NULL CHECK (typeof(size) = 'integer' AND size >= 0),
    stored_size INTEGER NOT NULL CHECK (typeof(stored_size) = 'integer' AND stored_size >= 0),
    encoding TEXT NOT NULL CHECK (encoding <> ''),
    created_at TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]+00:00'),
    UNIQUE (hash, size)
);
CREATE TABLE branches (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    commit_id TEXT REFERENCES commits(id),
    comment TEXT NOT NULL DEFAULT '',
    deleted INTEGER NOT NULL DEFAULT 0 CHECK (deleted IN (0, 1)),
    CHECK (deleted = 0 OR commit_id IS NULL)
);
CREATE UNIQUE INDEX idx_branches_live_name ON branches(name) WHERE deleted = 0;
CREATE TABLE commits (
    id TEXT PRIMARY KEY NOT NULL,
    seq INTEGER NOT NULL UNIQUE CHECK (typeof(seq) = 'integer' AND seq > 0),
    parent_id TEXT REFERENCES commits(id),
    branch_id TEXT NOT NULL REFERENCES branches(id),
    branch_name TEXT NOT NULL,
    created_at TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]+00:00'),
    message TEXT NOT NULL
);
CREATE TABLE repository_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    head_branch_id TEXT NOT NULL REFERENCES branches(id),
    current_commit_id TEXT REFERENCES commits(id)
);
CREATE TABLE commit_files (
    commit_id TEXT NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    object_hash TEXT NOT NULL,
    size INTEGER NOT NULL CHECK (typeof(size) = 'integer' AND size >= 0),
    mtime_ns INTEGER NOT NULL CHECK (typeof(mtime_ns) = 'integer'),
    PRIMARY KEY (commit_id, path),
    FOREIGN KEY (object_hash, size) REFERENCES objects(hash, size)
);
CREATE TABLE commit_attachments (
    id TEXT PRIMARY KEY NOT NULL,
    commit_id TEXT NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0 CHECK (typeof(position) = 'integer' AND position >= 0),
    original_name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    object_hash TEXT NOT NULL,
    size INTEGER NOT NULL CHECK (typeof(size) = 'integer' AND size >= 0),
    created_at TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]+00:00'),
    updated_at TEXT NOT NULL CHECK (updated_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]+00:00'),
    UNIQUE (commit_id, role, position),
    FOREIGN KEY (object_hash, size) REFERENCES objects(hash, size)
);
CREATE UNIQUE INDEX idx_single_thumbnail ON commit_attachments(commit_id)
    WHERE role = 'thumbnail';
CREATE TABLE commit_notes (
    commit_id TEXT PRIMARY KEY NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    note TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]+00:00')
);
CREATE TABLE commit_labels (
    commit_id TEXT NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    PRIMARY KEY (commit_id, label)
);
CREATE TABLE tags (
    name TEXT PRIMARY KEY NOT NULL,
    commit_id TEXT NOT NULL REFERENCES commits(id),
    comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]+00:00')
);
CREATE TABLE tracked_paths (
    path TEXT PRIMARY KEY NOT NULL
);
CREATE TABLE buds (
    id TEXT PRIMARY KEY NOT NULL,
    seq INTEGER NOT NULL UNIQUE CHECK (typeof(seq) = 'integer' AND seq > 0),
    base_commit_id TEXT REFERENCES commits(id),
    branch_id TEXT NOT NULL REFERENCES branches(id),
    branch_name TEXT NOT NULL,
    created_at TEXT NOT NULL CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]+00:00')
);
CREATE TABLE bud_files (
    bud_id TEXT NOT NULL REFERENCES buds(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    object_hash TEXT NOT NULL,
    size INTEGER NOT NULL CHECK (typeof(size) = 'integer' AND size >= 0),
    mtime_ns INTEGER NOT NULL CHECK (typeof(mtime_ns) = 'integer'),
    PRIMARY KEY (bud_id, path),
    FOREIGN KEY (object_hash, size) REFERENCES objects(hash, size)
);
CREATE INDEX idx_commits_parent ON commits(parent_id);
CREATE INDEX idx_commits_branch ON commits(branch_id);
CREATE INDEX idx_branches_commit ON branches(commit_id);
CREATE INDEX idx_tags_commit ON tags(commit_id);
CREATE INDEX idx_commit_files_object ON commit_files(object_hash, size);
CREATE INDEX idx_commit_attachments_object ON commit_attachments(object_hash, size);
CREATE INDEX idx_commit_labels_label ON commit_labels(label);
CREATE INDEX idx_buds_base ON buds(base_commit_id);
CREATE INDEX idx_buds_branch ON buds(branch_id);
CREATE INDEX idx_bud_files_object ON bud_files(object_hash, size);
