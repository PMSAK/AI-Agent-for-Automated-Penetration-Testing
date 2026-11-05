"""Repository functions for assessments (scan records), findings and evidence.

All SQL lives here; UI and other layers must call these functions only.
Every query is parameterised.
"""
import sqlite3
import uuid

from src.database.connection import (
    ASSESSMENT_STATUSES, FINDING_STATUSES, SCANNERS, SEVERITIES,
    VERIFICATION_STATUSES, DatabaseError, NotFoundError, transaction, utc_now,
)


def _new_id() -> str:
    return str(uuid.uuid4())


def _require(value, field: str) -> None:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise DatabaseError(f"'{field}' is required")


def _check_enum(value, allowed, field: str) -> None:
    if value not in allowed:
        raise DatabaseError(f"Invalid {field} '{value}'; allowed: {', '.join(allowed)}")


def _one(conn, sql: str, params: tuple, what: str) -> dict:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        raise NotFoundError(f"{what} not found: {params[0]}")
    return dict(row)


# ---------------------------------------------------------------- assessments
def create_assessment(conn: sqlite3.Connection, name: str, target: str, target_type: str,
                      description: str | None = None, status: str = "Draft") -> str:
    for field, value in (("name", name), ("target", target), ("target_type", target_type)):
        _require(value, field)
    _check_enum(status, ASSESSMENT_STATUSES, "status")
    assessment_id, now = _new_id(), utc_now()
    with transaction(conn):
        conn.execute(
            "INSERT INTO assessments (assessment_id, name, description, target, target_type,"
            " status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (assessment_id, name, description, target, target_type, status, now, now),
        )
    return assessment_id


def get_assessment(conn: sqlite3.Connection, assessment_id: str) -> dict:
    return _one(conn, "SELECT * FROM assessments WHERE assessment_id = ?",
                (assessment_id,), "Assessment")


def list_assessments(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM assessments ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------- findings
def _insert_evidence(conn, finding_id, evidence_type, source, content, raw_output_reference):
    for field, value in (("evidence_type", evidence_type), ("source", source), ("content", content)):
        _require(value, field)
    evidence_id = _new_id()
    conn.execute(
        "INSERT INTO finding_evidence (evidence_id, finding_id, evidence_type, source,"
        " content, raw_output_reference, collected_at) VALUES (?,?,?,?,?,?,?)",
        (evidence_id, finding_id, evidence_type, source, content, raw_output_reference, utc_now()),
    )
    return evidence_id


def create_finding(conn: sqlite3.Connection, assessment_id: str, scanner: str, title: str,
                   description: str, target: str,
                   verification_status: str = "Unverified", status: str = "Open",
                   evidence: list[dict] | None = None, **optional) -> str:
    """Insert a finding (and optional evidence dicts) in ONE transaction.

    `optional` accepts: execution_id, scanner_finding_id, affected_url, affected_service,
    severity, original_severity, severity_source, agent_priority, confidence, cve_id,
    cvss_score, cvss_version, remediation, remediation_source, last_seen_at.
    Nothing is defaulted for CVE/CVSS/severity (no fabrication).
    """
    allowed_optional = {
        "execution_id", "scanner_finding_id", "affected_url", "affected_service", "severity",
        "original_severity", "severity_source", "agent_priority", "confidence", "cve_id",
        "cvss_score", "cvss_version", "remediation", "remediation_source", "last_seen_at",
    }
    unknown = set(optional) - allowed_optional
    if unknown:
        raise DatabaseError(f"Unknown finding fields: {', '.join(sorted(unknown))}")
    for field, value in (("title", title), ("description", description), ("target", target)):
        _require(value, field)
    _check_enum(scanner, SCANNERS, "scanner")
    _check_enum(verification_status, VERIFICATION_STATUSES, "verification_status")
    _check_enum(status, FINDING_STATUSES, "status")
    if optional.get("severity") is not None:
        _check_enum(optional["severity"], SEVERITIES, "severity")

    finding_id = _new_id()
    columns = {"finding_id": finding_id, "assessment_id": assessment_id, "scanner": scanner,
               "title": title, "description": description, "target": target,
               "verification_status": verification_status, "status": status,
               "detected_at": utc_now(), **optional}
    sql = (f"INSERT INTO findings ({', '.join(columns)}) "
           f"VALUES ({', '.join('?' * len(columns))})")  # column names are code-controlled
    with transaction(conn):
        conn.execute(sql, tuple(columns.values()))
        for ev in evidence or []:
            _insert_evidence(conn, finding_id, ev.get("evidence_type"), ev.get("source"),
                             ev.get("content"), ev.get("raw_output_reference"))
    return finding_id


def get_finding(conn: sqlite3.Connection, finding_id: str) -> dict:
    return _one(conn, "SELECT * FROM findings WHERE finding_id = ?", (finding_id,), "Finding")


def list_findings(conn: sqlite3.Connection, assessment_id: str) -> list[dict]:
    rows = conn.execute("SELECT * FROM findings WHERE assessment_id = ? ORDER BY detected_at",
                        (assessment_id,)).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------- evidence
def add_evidence(conn: sqlite3.Connection, finding_id: str, evidence_type: str, source: str,
                 content: str, raw_output_reference: str | None = None) -> str:
    with transaction(conn):
        return _insert_evidence(conn, finding_id, evidence_type, source, content,
                                raw_output_reference)


def get_evidence(conn: sqlite3.Connection, evidence_id: str) -> dict:
    return _one(conn, "SELECT * FROM finding_evidence WHERE evidence_id = ?",
                (evidence_id,), "Evidence")


def list_evidence(conn: sqlite3.Connection, finding_id: str) -> list[dict]:
    rows = conn.execute("SELECT * FROM finding_evidence WHERE finding_id = ? ORDER BY collected_at",
                        (finding_id,)).fetchall()
    return [dict(r) for r in rows]



# --------------------------------------------------------------------- scopes
def save_scope(conn: sqlite3.Connection, assessment_id: str, authorized_targets: list,
               allowed_operations: list, restrictions: list, validated: bool,
               validation_details: dict | None = None) -> str:
    """Insert or replace the single scope record of an assessment (lists stored as JSON)."""
    import json
    scope_id = _new_id()
    with transaction(conn):
        existing = conn.execute("SELECT scope_id FROM assessment_scopes WHERE assessment_id = ?",
                                (assessment_id,)).fetchone()
        if existing:
            scope_id = existing["scope_id"]
        conn.execute(
            "INSERT INTO assessment_scopes (scope_id, assessment_id, authorized_targets,"
            " allowed_operations, restrictions, validated, validated_at, validation_details)"
            " VALUES (?,?,?,?,?,?,?,?)"
            " ON CONFLICT(assessment_id) DO UPDATE SET authorized_targets=excluded.authorized_targets,"
            " allowed_operations=excluded.allowed_operations, restrictions=excluded.restrictions,"
            " validated=excluded.validated, validated_at=excluded.validated_at,"
            " validation_details=excluded.validation_details",
            (scope_id, assessment_id, json.dumps(authorized_targets), json.dumps(allowed_operations),
             json.dumps(restrictions), int(bool(validated)), utc_now() if validated else None,
             json.dumps(validation_details) if validation_details is not None else None),
        )
    return scope_id


def get_scope(conn: sqlite3.Connection, assessment_id: str) -> dict:
    import json
    row = _one(conn, "SELECT * FROM assessment_scopes WHERE assessment_id = ?",
               (assessment_id,), "Scope")
    for key in ("authorized_targets", "allowed_operations", "restrictions", "validation_details"):
        if row[key] is not None:
            row[key] = json.loads(row[key])
    row["validated"] = bool(row["validated"])
    return row
