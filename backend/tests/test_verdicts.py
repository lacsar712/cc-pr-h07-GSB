"""两类结论的核对：套准与套不准，在规则、判定入口、送审字段、队列、详情各层都吃真实数。"""

import pytest
from fastapi.testclient import TestClient

import api
import worker
from rules import judge

IN_ROW = {
    "id": 1,
    "sheet": "插页-02",
    "cyan_mm": 0.08,
    "magenta_mm": 0.02,
    "status": "done",
    "verdict": "套准",
    "reason": "青品两色偏差都在允差内",
    "created_by": "printer",
}
OUT_ROW = {
    "id": 2,
    "sheet": "内页-09",
    "cyan_mm": 0.40,
    "magenta_mm": 0.02,
    "status": "done",
    "verdict": "套不准",
    "reason": "至少一色偏差超出允差",
    "created_by": "printer",
}


class FakeResult:
    def __init__(self, one=None, many=None):
        self._one = one
        self._many = many

    def fetchone(self):
        return self._one

    def fetchall(self):
        return list(self._many or [])


class FakeConn:
    def __init__(self, state):
        self.state = state

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        norm = " ".join(str(sql).split()).upper()
        if norm.startswith("CREATE TABLE"):
            return FakeResult()
        if "COUNT(*)" in norm:
            return FakeResult(one={"n": 1})
        if norm.startswith("INSERT INTO JOBS"):
            self.state["inserted"].append(params)
            return FakeResult(one={"id": 900, "sheet": params[0], "status": "pending", "verdict": ""})
        if "FROM JOBS" in norm and "WHERE ID = %S" in norm:
            return FakeResult(one=self.state["detail_rows"].get(params[0]))
        if "FROM JOBS" in norm:
            return FakeResult(many=self.state["list_rows"])
        raise AssertionError(f"未预期的 SQL: {sql}")

    def commit(self):
        pass


@pytest.fixture
def db_state():
    return {"list_rows": [], "detail_rows": {}, "inserted": []}


@pytest.fixture
def client(db_state, monkeypatch):
    monkeypatch.setattr(api, "connect", lambda: FakeConn(db_state))
    with TestClient(api.app) as c:
        yield c


def login(client, username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def printer_auth(client):
    return login(client, "printer", "print123456")


@pytest.fixture
def checker_auth(client):
    return login(client, "checker", "check123456")


class TestInTolerance:
    """套准类：青 0.08、品 0.02 且印张合法，各层都要看见真实青毫米与套准结论。"""

    def test_rule_in_tolerance(self):
        assert judge(0.08, 0.02) == ("套准", "青品两色偏差都在允差内")

    def test_rule_boundary_still_in(self):
        assert judge(0.15, -0.15)[0] == "套准"

    def test_worker_entry_in_tolerance(self):
        assert worker.verdict_for(0.08, 0.02)[0] == "套准"

    def test_enqueue_keeps_real_fields(self, client, db_state, printer_auth):
        res = client.post(
            "/api/jobs",
            json={"sheet": "插页-02", "cyan_mm": 0.08, "magenta_mm": 0.02},
            headers=printer_auth,
        )
        assert res.status_code == 202
        sheet, cyan, magenta, *_ = db_state["inserted"][0]
        assert (sheet, cyan, magenta) == ("插页-02", 0.08, 0.02)

    def test_list_shows_real_cyan_and_verdict(self, client, db_state, printer_auth):
        db_state["list_rows"] = [dict(IN_ROW), dict(OUT_ROW)]
        data = client.get("/api/jobs", headers=printer_auth).json()
        assert [r["id"] for r in data] == [1, 2]
        first = data[0]
        assert first["cyan_mm"] == 0.08
        assert first["verdict"] == "套准"
        assert first["reason"] == "青品两色偏差都在允差内"

    def test_detail_shows_real_cyan(self, client, db_state, printer_auth):
        db_state["detail_rows"] = {1: dict(IN_ROW)}
        res = client.get("/api/jobs/1", headers=printer_auth)
        assert res.status_code == 200
        body = res.json()
        assert body["cyan_mm"] == 0.08
        assert body["verdict"] == "套准"


class TestOutOfTolerance:
    """套不准类：超差样张继续判套不准，队列与详情里的青毫米不得被压成空。"""

    def test_rule_out_of_tolerance(self):
        assert judge(0.40, 0.02)[0] == "套不准"
        assert judge(0.5, 0.0)[0] == "套不准"

    def test_worker_entry_out_of_tolerance(self):
        assert worker.verdict_for(0.5, 0.02)[0] == "套不准"

    def test_list_keeps_out_row_visible(self, client, db_state, printer_auth):
        db_state["list_rows"] = [dict(IN_ROW), dict(OUT_ROW)]
        data = client.get("/api/jobs", headers=printer_auth).json()
        out = data[1]
        assert out["cyan_mm"] == 0.40
        assert out["verdict"] == "套不准"
        assert out["reason"] == "至少一色偏差超出允差"

    def test_detail_keeps_out_row_visible(self, client, db_state, printer_auth):
        db_state["detail_rows"] = {2: dict(OUT_ROW)}
        res = client.get("/api/jobs/2", headers=printer_auth)
        assert res.status_code == 200
        body = res.json()
        assert body["cyan_mm"] == 0.40
        assert body["verdict"] == "套不准"


class TestGuards:
    def test_blank_sheet_rejected(self, client, db_state, printer_auth):
        res = client.post(
            "/api/jobs",
            json={"sheet": "   ", "cyan_mm": 0.08, "magenta_mm": 0.02},
            headers=printer_auth,
        )
        assert res.status_code == 422
        assert db_state["inserted"] == []

    def test_reader_cannot_submit(self, client, checker_auth):
        res = client.post(
            "/api/jobs",
            json={"sheet": "插页-02", "cyan_mm": 0.08, "magenta_mm": 0.02},
            headers=checker_auth,
        )
        assert res.status_code == 403

    def test_reader_can_list(self, client, db_state, checker_auth):
        db_state["list_rows"] = [dict(IN_ROW)]
        res = client.get("/api/jobs", headers=checker_auth)
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_detail_missing_returns_404(self, client, printer_auth):
        assert client.get("/api/jobs/404", headers=printer_auth).status_code == 404

    def test_anonymous_rejected(self, client):
        assert client.get("/api/jobs").status_code == 401
