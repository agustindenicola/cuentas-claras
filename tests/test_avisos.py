from datetime import datetime, timedelta

from conftest import H, nueva

from cuentas import core, scheduler
from cuentas.db import db


def _u(con, uid):
    return con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def _avisos(con, uid, kind):
    return con.execute("SELECT * FROM notifications WHERE user_id=? AND kind=?", (uid, kind)).fetchall()


def _hoy_a(hora):
    d = core.hoy()
    return datetime(d.year, d.month, d.day, hora, 0)


def test_recordatorio_diario_una_sola_vez(client, con):
    uid, _ = nueva(client)
    assert scheduler.recordatorio_diario(con, _u(con, uid), _hoy_a(21))
    assert not scheduler.recordatorio_diario(con, _u(con, uid), _hoy_a(21))
    assert len(_avisos(con, uid, "diario")) == 1


def test_sin_recordatorio_si_ya_anoto(client, con):
    uid, _ = nueva(client)
    client.post("/api/movs", json={"tipo": "egreso", "cat": "super", "monto": 100}, headers=H)
    assert not scheduler.recordatorio_diario(con, _u(con, uid), _hoy_a(21))


def test_recordatorio_respeta_hora_y_preferencia(client, con):
    uid, _ = nueva(client)
    assert not scheduler.recordatorio_diario(con, _u(con, uid), _hoy_a(15))
    client.put("/api/me", json={"av_diario": False}, headers=H)
    assert not scheduler.recordatorio_diario(con, _u(con, uid), _hoy_a(21))


def test_vencimientos_hoy_y_manana(client, con, monkeypatch):
    uid, _ = nueva(client)
    now = datetime(2026, 11, 10, 9, 30)
    monkeypatch.setattr(core, "hoy", lambda: now.date())
    client.post("/api/fijos", json={"nombre": "Luz", "monto": 40000, "dia": 10, "cat": "servicios"}, headers=H)
    client.post("/api/fijos", json={"nombre": "Gas", "monto": 20000, "dia": 11, "cat": "servicios"}, headers=H)
    client.post("/api/fijos", json={"nombre": "Agua", "monto": 9000, "dia": 25, "cat": "servicios"}, headers=H)
    assert scheduler.vencimientos(con, _u(con, uid), now)
    assert not scheduler.vencimientos(con, _u(con, uid), now)    # no repite
    a = _avisos(con, uid, "vencimiento")
    assert len(a) == 1 and "Luz (hoy)" in a[0]["body"] and "Gas (mañana)" in a[0]["body"] and "Agua" not in a[0]["body"]


def test_no_avisa_lo_pagado(client, con):
    uid, _ = nueva(client)
    d = core.hoy()
    client.post("/api/fijos", json={"nombre": "Luz", "monto": 40000, "dia": d.day, "cat": "servicios"}, headers=H)
    fid = client.get("/api/resumen").json["fijos"][0]["id"]
    client.post(f"/api/fijos/{fid}/pagar", json={}, headers=H)
    assert not scheduler.vencimientos(con, _u(con, uid), _hoy_a(10))


def test_aviso_de_cobro(client, con):
    uid, _ = nueva(client)
    client.post("/api/ingresos", json={"nombre": "Sueldo", "monto": 100, "dia": core.hoy().day}, headers=H)
    assert scheduler.cobros(con, _u(con, uid), _hoy_a(9))
    assert "Sueldo" in _avisos(con, uid, "cobro")[0]["title"]


def test_aviso_fin_de_prueba(client, con):
    uid, _ = nueva(client)
    con.execute("UPDATE users SET trial_ends=? WHERE id=?", ((core.hoy() + timedelta(days=2)).isoformat(), uid))
    assert scheduler.avisos_cuenta(con, _u(con, uid), _hoy_a(10))
    assert "3 días" in _avisos(con, uid, "prueba")[0]["title"]


def test_resumen_mensual_el_dia_1():
    with db() as c:
        uid = c.execute("INSERT INTO users(email, pass_hash, name, created_at, trial_ends) "
                        "VALUES('res@x.com','x','R','2026-10-02 10:00:00','2027-01-01')").lastrowid
        c.execute("INSERT INTO ingresos(user_id, nombre, monto, dia) VALUES(?, 'Sueldo', 1000, 1)", (uid,))
        c.execute("INSERT INTO movs(user_id, tipo, cat, monto, fecha) VALUES(?, 'egreso', 'super', 300, '2026-10-05')", (uid,))
        u = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        assert scheduler.resumen_mensual(c, u, datetime(2026, 11, 1, 10, 0))
        a = _avisos(c, uid, "resumen")[0]
        assert "Octubre cerró en verde" in a["title"] and "$ 700" in a["body"]


def test_tick_no_falla(client):
    nueva(client)
    scheduler.tick()
