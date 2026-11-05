import sqlite3
import pytest

from src.database import (
    DatabaseError, NotFoundError, add_evidence, create_assessment, create_finding,
    get_assessment, get_connection, get_evidence, get_finding, init_db, list_evidence,
    list_findings,
)


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"  # temporary, never the production DB


@pytest.fixture
def conn(db_path):
    c = init_db(db_path)
    yield c
    c.close()


def _assessment(conn):
    return create_assessment(conn, "Test", "http://localhost:8080", "url")


def _finding(conn, aid, **kw):
    return create_finding(conn, aid, "zap", "XSS", "desc", "http://localhost:8080", **kw)


def test_init_creates_tables_and_fk(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"assessments", "findings", "finding_evidence", "schema_version", "assessment_scopes"} <= tables
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 2


def test_init_is_idempotent(db_path, conn):
    aid = _assessment(conn)
    init_db(db_path).close()
    assert get_assessment(conn, aid)["name"] == "Test"
    assert conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 1


def test_create_and_get_assessment(conn):
    a = get_assessment(conn, _assessment(conn))
    assert a["status"] == "Draft" and a["target"] == "http://localhost:8080"


def test_get_missing_assessment(conn):
    with pytest.raises(NotFoundError):
        get_assessment(conn, "nope")


def test_invalid_assessment_values(conn):
    with pytest.raises(DatabaseError):
        create_assessment(conn, "", "t", "url")
    with pytest.raises(DatabaseError):
        create_assessment(conn, "n", "t", "url", status="Bogus")


def test_finding_with_evidence_and_relations(conn):
    aid = _assessment(conn)
    fid = _finding(conn, aid, severity="High", evidence=[
        {"evidence_type": "Scanner Alert", "source": "zap", "content": "alert text"}])
    f = get_finding(conn, fid)
    assert f["assessment_id"] == aid and f["severity"] == "High"
    assert f["cve_id"] is None and f["cvss_score"] is None  # nothing fabricated
    assert [x["finding_id"] for x in list_findings(conn, aid)] == [fid]
    ev = list_evidence(conn, fid)
    assert len(ev) == 1 and ev[0]["finding_id"] == fid


def test_add_and_get_evidence(conn):
    fid = _finding(conn, _assessment(conn))
    eid = add_evidence(conn, fid, "Header", "zap", "X-Frame-Options missing", "out/1.xml")
    e = get_evidence(conn, eid)
    assert e["raw_output_reference"] == "out/1.xml" and e["source"] == "zap"


def test_finding_requires_existing_assessment(conn):
    with pytest.raises(DatabaseError):
        _finding(conn, "missing-assessment")


def test_evidence_requires_existing_finding(conn):
    with pytest.raises(DatabaseError):
        add_evidence(conn, "missing-finding", "Other", "zap", "x")


def test_invalid_finding_values(conn):
    aid = _assessment(conn)
    with pytest.raises(DatabaseError):
        create_finding(conn, aid, "metasploit", "t", "d", "x")
    with pytest.raises(DatabaseError):
        _finding(conn, aid, severity="Extreme")
    with pytest.raises(DatabaseError):
        _finding(conn, aid, verification_status="Maybe")
    with pytest.raises(DatabaseError):
        _finding(conn, aid, bogus_field=1)


def test_failed_evidence_rolls_back_finding(conn):
    aid = _assessment(conn)
    with pytest.raises(DatabaseError):
        _finding(conn, aid, evidence=[{"evidence_type": "Other", "source": "zap"}])  # no content
    assert list_findings(conn, aid) == []


def test_duplicate_primary_key_rejected(conn):
    aid = _assessment(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO assessments (assessment_id,name,target,target_type,status,"
                     "created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                     (aid, "dup", "t", "url", "Draft", "x", "x"))


def test_data_persists_after_reopen(db_path):
    c1 = init_db(db_path)
    aid = _assessment(c1)
    fid = _finding(c1, aid, evidence=[{"evidence_type": "Other", "source": "zap", "content": "c"}])
    c1.close()
    c2 = get_connection(db_path)
    assert get_assessment(c2, aid)["name"] == "Test"
    assert get_finding(c2, fid)["title"] == "XSS"
    assert len(list_evidence(c2, fid)) == 1
    c2.close()


# ---- Phase 3: scope persistence and v1 -> v2 upgrade
def test_save_and_get_scope(conn):
    from src.database import get_scope, save_scope
    aid = _assessment(conn)
    save_scope(conn, aid, ["127.0.0.1:8080"], ["zap.passive_scan"], ["excluded: x.test"], False)
    s = get_scope(conn, aid)
    assert s["authorized_targets"] == ["127.0.0.1:8080"] and s["validated"] is False
    sid = save_scope(conn, aid, ["127.0.0.1:8080"], [], [], True, {"code": "OK"})  # upsert
    s = get_scope(conn, aid)
    assert s["scope_id"] == sid and s["validated"] is True and s["validation_details"] == {"code": "OK"}
    assert conn.execute("SELECT COUNT(*) FROM assessment_scopes").fetchone()[0] == 1


def test_scope_requires_existing_assessment(conn):
    from src.database import save_scope
    with pytest.raises(DatabaseError):
        save_scope(conn, "missing", [], [], [], False)


def test_upgrade_from_v1_preserves_data(db_path):
    c = init_db(db_path)
    aid = _assessment(c)
    c.execute("DROP TABLE assessment_scopes")
    c.execute("DELETE FROM schema_version")
    c.execute("INSERT INTO schema_version VALUES (1, 'x')")
    c.commit()
    c.close()
    c2 = init_db(db_path)
    assert get_assessment(c2, aid)["name"] == "Test"
    assert c2.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 2
    c2.execute("SELECT * FROM assessment_scopes").fetchall()
    c2.close()
