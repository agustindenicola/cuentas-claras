from datetime import date, timedelta

from conftest import APP, H, nueva
from werkzeug.security import generate_password_hash

from cuentas import core, logros
from cuentas.db import db


def test_registro_login_y_prueba(client):
    uid, email = nueva(client, "Ana")
    me = client.get("/api/me").json["user"]
    assert me["name"] == "Ana" and me["cuenta"]["estado"] == "prueba" and me["cuenta"]["dias"] == 14
    client.post("/api/logout", headers=H)
    assert client.get("/api/me").json["user"] is None
    assert client.post("/api/login", json={"email": email, "password": "mal"}, headers=H).status_code == 400
    assert client.post("/api/login", json={"email": email, "password": "clave-segura-1"}, headers=H).status_code == 200


def test_registro_valida(client):
    r = client.post("/api/register", json={"email": "x@y.com", "password": "corta", "name": "X", "accept_terms": True}, headers=H)
    assert r.status_code == 400
    r = client.post("/api/register", json={"email": "z@y.com", "password": "clave-segura-1", "name": "X"}, headers=H)
    assert "términos" in r.json["error"]


def test_escrituras_requieren_encabezado(client):
    nueva(client)
    assert client.post("/api/movs", json={"tipo": "egreso", "monto": 100}).status_code == 403


def test_resumen_y_totales(client):
    nueva(client)
    client.post("/api/ingresos", json={"nombre": "Sueldo", "monto": 1000000, "dia": 1}, headers=H)
    assert client.post("/api/fijos", json={"nombre": "Luz", "monto": 50000, "dia": 12, "cat": "servicios"}, headers=H).status_code == 200
    client.post("/api/movs", json={"tipo": "egreso", "cat": "super", "monto": "30.000", "descr": "Súper"}, headers=H)
    client.post("/api/movs", json={"tipo": "ahorro", "cat": "inversion", "monto": 100000}, headers=H)
    client.post("/api/movs", json={"tipo": "ingreso", "monto": 20000, "descr": "Venta"}, headers=H)
    t = client.get("/api/resumen").json["totales"]
    assert t["ing"] == 1020000 and t["fij"] == 50000 and t["var"] == 30000 and t["ahorro"] == 100000
    assert t["saldo"] == 1020000 - 50000 - 30000 - 100000


def test_pagar_fijo_con_otro_monto(client):
    nueva(client)
    client.post("/api/fijos", json={"nombre": "Gas", "monto": 20000, "dia": 15, "cat": "servicios"}, headers=H)
    f = client.get("/api/resumen").json["fijos"][0]
    assert not f["pagado"]
    client.post(f"/api/fijos/{f['id']}/pagar", json={"monto": 23500}, headers=H)
    r = client.get("/api/resumen").json
    assert r["fijos"][0]["pagado"] and r["totales"]["fij"] == 23500
    assert r["fijos"][0]["monto"] == 20000                # el habitual no cambia si no se pide
    client.delete(f"/api/fijos/{f['id']}/pagar", headers=H)
    assert not client.get("/api/resumen").json["fijos"][0]["pagado"]


def test_no_se_tocan_datos_ajenos(client):
    nueva(client)
    mid = client.post("/api/movs", json={"tipo": "egreso", "cat": "super", "monto": 100}, headers=H).json["id"]
    otro = APP.test_client()
    nueva(otro)
    assert otro.delete(f"/api/movs/{mid}", headers=H).status_code == 404
    assert otro.get("/api/movs").json["items"] == []


def test_logros_primer_paso_y_festejo(client):
    nueva(client)
    r = client.post("/api/movs", json={"tipo": "egreso", "cat": "super", "monto": 100}, headers=H).json
    assert [x["id"] for x in r["logros"]] == ["primer_paso"]
    r = client.post("/api/movs", json={"tipo": "ahorro", "cat": "inversion", "monto": 100}, headers=H).json
    assert {"primer_ahorro", "inversora"} <= {x["id"] for x in r["logros"]}
    assert client.get("/api/resumen").json["logros"]["sin_ver"]
    client.post("/api/logros/vistos", headers=H)
    assert client.get("/api/resumen").json["logros"]["sin_ver"] == []


def test_racha_con_hoy_no_gaste(client, con):
    uid, _ = nueva(client)
    d = core.hoy()
    for i in (1, 2):
        con.execute("INSERT INTO checkins(user_id, fecha) VALUES(?,?)", (uid, (d - timedelta(days=i)).isoformat()))
    con.commit()
    assert core.racha(con, uid) == {"dias": 2, "hoy_ok": False, "ultimo": (d - timedelta(days=1)).isoformat()}
    r = client.post("/api/checkin", headers=H).json
    assert "racha_3" in {x["id"] for x in r["logros"]}


def test_nivel():
    assert logros.nivel(0)["nombre"] == "Arrancando"
    assert logros.nivel(5) == {"numero": 3, "nombre": "Ordenada", "siguiente": "Experta", "faltan": 4}
    assert logros.nivel(15)["siguiente"] is None


def test_prueba_vencida_bloquea_carga_pero_no_lectura(client, con):
    uid, _ = nueva(client)
    con.execute("UPDATE users SET trial_ends=? WHERE id=?", ((core.hoy() - timedelta(days=1)).isoformat(), uid))
    con.commit()
    r = client.post("/api/movs", json={"tipo": "egreso", "cat": "super", "monto": 100}, headers=H)
    assert r.status_code == 402 and r.json["code"] == "pago"
    assert client.get("/api/resumen").status_code == 200
    assert client.get("/api/me/export").status_code == 200


def test_extender_pago_respeta_la_prueba():
    with db() as c:
        uid = c.execute("INSERT INTO users(email, pass_hash, name, created_at, trial_ends) VALUES('pago@x.com','x','P',?,?)",
                        (core.stamp(), "2026-11-20")).lastrowid
        assert core.extender_pago(c, uid, d=date(2026, 11, 10)) == "2026-12-20"
        assert core.extender_pago(c, uid, d=date(2026, 11, 10)) == "2027-01-20"
        c.execute("UPDATE users SET paid_until='2026-01-31', trial_ends='2026-01-01' WHERE id=?", (uid,))
        assert core.extender_pago(c, uid, d=date(2026, 1, 15)) == "2026-02-28"


def test_admin_marca_pago(client, con):
    uid, _ = nueva(client)
    con.execute("UPDATE users SET trial_ends=? WHERE id=?", ((core.hoy() - timedelta(days=1)).isoformat(), uid))
    con.execute("INSERT INTO users(email, pass_hash, name, role, created_at, trial_ends) VALUES('adm@x.com', ?, 'Adm', 'admin', ?, ?)",
                (generate_password_hash("clave-admin-1"), core.stamp(), core.hoy().isoformat()))
    con.commit()
    adm = APP.test_client()
    adm.post("/api/login", json={"email": "adm@x.com", "password": "clave-admin-1"}, headers=H)
    assert client.get("/api/me").json["user"]["cuenta"]["estado"] == "vencida"
    assert client.get("/api/admin").status_code == 403
    assert adm.post(f"/api/admin/users/{uid}/pago", json={"meses": 1}, headers=H).status_code == 200
    assert client.get("/api/me").json["user"]["cuenta"]["estado"] == "activa"
    panel = adm.get("/api/admin").json
    assert any(u["id"] == uid for u in panel["users"]) and panel["resumen"]["activa"] >= 1


def test_cerrar_meses_y_historial():
    with db() as c:
        uid = c.execute("INSERT INTO users(email, pass_hash, name, created_at, trial_ends) "
                        "VALUES('hist@x.com','x','H','2026-09-03 10:00:00','2026-09-16')").lastrowid
        c.execute("INSERT INTO ingresos(user_id, nombre, monto, dia) VALUES(?, 'Sueldo', 1000, 1)", (uid,))
        c.execute("INSERT INTO movs(user_id, tipo, cat, monto, fecha) VALUES(?, 'egreso', 'super', 300, '2026-10-05')", (uid,))
        assert core.cerrar_meses(c, uid, date(2026, 11, 16)) == ["2026-09", "2026-10"]
        assert core.cerrar_meses(c, uid, date(2026, 11, 16)) == []
        r = core.resumen(c, uid, date(2026, 11, 16))
        assert [h["mes"] for h in r["historial"]] == ["2026-09", "2026-10", "2026-11"]
        assert r["historial"][1]["egr"] == 300


def test_dia_31_en_mes_corto():
    assert core.dia_real(31, date(2026, 11, 5)) == 30
    assert core.dia_real(31, date(2027, 2, 5)) == 28


def test_recuperar_contrasena(client):
    _, email = nueva(client)
    client.post("/api/logout", headers=H)
    link = client.post("/api/password/forgot", json={"email": email}, headers=H).json["dev_link"]
    token = link.split("#reset/")[1]
    assert client.post("/api/password/reset", json={"token": token, "password": "nueva-clave-9"}, headers=H).status_code == 200
    assert client.post("/api/password/reset", json={"token": token, "password": "otra-clave-9"}, headers=H).status_code == 400
    client.post("/api/logout", headers=H)
    assert client.post("/api/login", json={"email": email, "password": "nueva-clave-9"}, headers=H).status_code == 200


def test_borrar_cuenta(client):
    _, email = nueva(client)
    assert client.delete("/api/me", json={"password": "mal"}, headers=H).status_code == 400
    assert client.delete("/api/me", json={"password": "clave-segura-1"}, headers=H).status_code == 200
    assert client.post("/api/login", json={"email": email, "password": "clave-segura-1"}, headers=H).status_code == 400


def test_demo(client):
    assert client.post("/api/demo-login", headers=H).status_code == 200
    r = client.get("/api/resumen").json
    assert len(r["historial"]) == 6 and r["logros"]["ganados"] >= 5
