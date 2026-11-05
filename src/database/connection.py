"""SQLite connection management, schema creation and versioning (spec 10)."""
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2  # v2 (Phase 3): adds assessment_scopes (purely additive)

ASSESSMENT_STATUSES = (
    "Draft", "Scope Validation", "Planning", "Awaiting Approval", "Running",
    "Analyzing", "Completed", "Failed", "Cancelled",
)
SCANNERS = ("nmap", "zap", "nikto")
VERIFICATION_STATUSES = ("Potential", "Unverified", "Confirmed", "False Positive", "Not Tested")
FINDING_STATUSES = ("Open", "In Review", "Accepted Risk", "Remediated", "Closed")
SEVERITIES = ("Critical", "High", "Medium", "Low", "Informational", "Unknown")


class DatabaseError(Exception):
    """Raised for any persistence failure (integrity, missing record, bad schema)."""


class NotFoundError(DatabaseError):
    """Raised when a requested record does not exist."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _in(values) -> str:
    return "(" + ",".join(f"'{v}'" for v in values) + ")"


# Enum lists above are module constants (not user input), so inlining them is safe.
_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessments (
    assessment_id TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    description   TEXT,
    target        TEXT NOT NULL,
    target_type   TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN {_in(ASSESSMENT_STATUSES)}),
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    completed_at  TEXT,
    error_message TEXT
);

-- execution_id has no FK yet: scanner_executions is created in a later phase.
CREATE TABLE IF NOT EXISTS findings (
    finding_id          TEXT PRIMARY KEY,
    assessment_id       TEXT NOT NULL REFERENCES assessments(assessment_id),
    execution_id        TEXT,
    scanner             TEXT NOT NULL CHECK (scanner IN {_in(SCANNERS)}),
    scanner_finding_id  TEXT,
    title               TEXT NOT NULL,
    description         TEXT NOT NULL,
    target              TEXT NOT NULL,
    affected_url        TEXT,
    affected_service    TEXT,
    severity            TEXT CHECK (severity IS NULL OR severity IN {_in(SEVERITIES)}),
    original_severity   TEXT,
    severity_source     TEXT,
    agent_priority      TEXT,
    confidence          TEXT,
    verification_status TEXT NOT NULL CHECK (verification_status IN {_in(VERIFICATION_STATUSES)}),
    cve_id              TEXT,
    cvss_score          REAL,
    cvss_version        TEXT,
    remediation         TEXT,
    remediation_source  TEXT,
    status              TEXT NOT NULL CHECK (status IN {_in(FINDING_STATUSES)}),
    detected_at         TEXT NOT NULL,
    last_seen_at        TEXT
);

CREATE TABLE IF NOT EXISTS finding_evidence (
    evidence_id          TEXT PRIMARY KEY,
    finding_id           TEXT NOT NULL REFERENCES findings(finding_id),
    evidence_type        TEXT NOT NULL,
    source               TEXT NOT NULL,
    content              TEXT NOT NULL,
    raw_output_reference TEXT,
    collected_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessment_scopes (
    scope_id           TEXT PRIMARY KEY,
    assessment_id      TEXT NOT NULL UNIQUE REFERENCES assessments(assessment_id),
    authorized_targets TEXT NOT NULL,
    allowed_operations TEXT NOT NULL,
    restrictions       TEXT NOT NULL,
    validated          INTEGER NOT NULL CHECK (validated IN (0, 1)),
    validated_at       TEXT,
    validation_details TEXT
);

CREATE INDEX IF NOT EXISTS idx_assessments_created_at ON assessments(created_at);
CREATE INDEX IF NOT EXISTS idx_assessments_status     ON assessments(status);
CREATE INDEX IF NOT EXISTS idx_findings_assessment    ON findings(assessment_id);
CREATE INDEX IF NOT EXISTS idx_findings_scanner       ON findings(scanner);
CREATE INDEX IF NOT EXISTS idx_findings_severity      ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_verification  ON findings(verification_status);
CREATE INDEX IF NOT EXISTS idx_findings_status        ON findings(status);
CREATE INDEX IF NOT EXISTS idx_evidence_finding       ON finding_evidence(finding_id);
"""


def get_connection(db_path: Path | str) -> sqlite3.Connection:
    """Open a connection with foreign keys enforced and row access by name."""
    try:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except (sqlite3.Error, OSError) as exc:
        raise DatabaseError(f"Cannot open database at {db_path}: {exc}") from exc


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Commit on success; roll back and raise DatabaseError on failure."""
    try:
        with conn:
            yield conn
    except sqlite3.Error as exc:
        raise DatabaseError(f"Database operation failed: {exc}") from exc


def init_db(db_path: Path | str) -> sqlite3.Connection:
    """Create the file/tables/indexes if needed and validate the schema version."""
    conn = get_connection(db_path)
    try:
        with transaction(conn):
            conn.executescript(_SCHEMA)
            row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
            current = row["v"]
            if current is not None and current > SCHEMA_VERSION:
                raise DatabaseError(
                    f"Database schema v{current} is newer than supported v{SCHEMA_VERSION}"
                )
            if current is None or current < SCHEMA_VERSION:
                # Tables are created idempotently above, so existing data is untouched.
                conn.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, utc_now()),
                )
    except Exception:
        conn.close()
        raise
    logger.info("Database initialised at %s", db_path)
    return conn

