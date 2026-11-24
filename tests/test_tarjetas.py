from datetime import date

from conftest import H, nueva

from cuentas import core
from cuentas.db import db


def test_primer_mes_segun_cierre():
    assert core.primer_mes(date(2026, 11, 20), 24) == "2026-12"      # antes del cierre: se paga el mes que viene
    assert core.primer_mes(date(2026, 11, 24), 24) == "2026-12"      # el día del cierre todavía entra
    assert core.primer_mes(date(2026, 11, 25), 24) == "2027-01"      # después del cierre: un mes más
    assert core.primer_mes(date(2026, 12, 28), 31) == "2027-01"      # cierre 31 en diciembre
    assert core.primer_mes(date(2027, 2, 28), 30) == "2027-03"       # cierre 30 en febrero = último día


def test_precio_final():
    assert core.precio_final(100000, descuento=20) == 80000
    assert core.precio_final(100000, interes=15) == 115000
    assert core.precio_final(100000, descuento=10, interes=10) == 99000


def test_meses():
    assert core.mes_mas("2026-11", 3) == "2027-02"
    assert core.meses_entre("2026-11", "2027-02") == 3


def _tarjeta(client, cierre=24, vence=5):
    r = client.post("/api/tarjetas", json={"nombre": "Visa", "cierre": cierre, "vence": vence}, headers=H)
    assert r.status_code == 200, r.json
    return r.json["id"]


def test_compra_en_cuotas_con_interes(client):
    nueva(client)
    tid = _tarjeta(client)
    d = core.hoy()
    r = client.post("/api/movs", json={"tipo": "egreso", "cat": "casa", "monto": 120000, "descr": "Heladera", "tarjeta_id": tid,
                                       "cuotas": 12, "interes": 10, "fecha": d.isoformat()}, headers=H)
    assert r.status_code == 200, r.json
    m = client.get("/api/movs").json["items"][0]
    assert m["monto"] == 132000 and m["precio"] == 120000 and m["cuotas"] == 12
    assert m["primer_mes"] == core.primer_mes(d, 24)
    # el mes de la compra no cuenta como egreso variable: se cuenta en cuotas
    t = client.get("/api/resumen").json["totales"]
    assert t["var"] == 0
    comp = client.get("/api/tarjetas").json["compromisos"]
    meses_con_cuota = [c for c in comp if c["total"]]
    assert all(abs(c["total"] - 11000) < 0.01 for c in meses_con_cuota) and len(meses_con_cuota) >= 4


def test_cuota_del_mes_entra_en_el_saldo():
    with db() as con:
        uid = con.execute("INSERT INTO users(email, pass_hash, name, created_at, trial_ends) VALUES('cuota@x.com','x','C','2026-09-01 10:00:00','2027-01-01')").lastrowid
        tid = con.execute("INSERT INTO tarjetas(user_id, nombre, cierre, vence) VALUES(?, 'Visa', 24, 5)", (uid,)).lastrowid
        con.execute("INSERT INTO ingresos(user_id, nombre, monto, dia) VALUES(?, 'Sueldo', 100000, 1)", (uid,))
        con.execute("INSERT INTO movs(user_id, tipo, cat, monto, fecha, tarjeta_id, cuotas, primer_mes) VALUES(?, 'egreso', 'casa', 30000, '2026-09-10', ?, 3, '2026-10')",
                    (uid, tid))
        assert core.totales_mes(con, uid, "2026-09")["tarjeta"] == 0
        for key in ("2026-10", "2026-11", "2026-12"):
            t = core.totales_mes(con, uid, key)
            assert t["tarjeta"] == 10000 and t["saldo"] == 90000
        assert core.totales_mes(con, uid, "2027-01")["tarjeta"] == 0
        # si se pagó el resumen con otro monto (impuestos), cuenta lo pagado
        con.execute("INSERT INTO tarjeta_pagos(tarjeta_id, mes, monto, pagado_el) VALUES(?, '2026-11', 12500, '2026-11-05')", (tid,))
        assert core.totales_mes(con, uid, "2026-11")["tarjeta"] == 12500
        r = core.resumen(con, uid, date(2026, 11, 16))
        assert dict(r["categorias"])["casa"] == 10000


def test_descuento_en_efectivo(client):
    nueva(client)
    client.post("/api/movs", json={"tipo": "egreso", "cat": "super", "monto": 50000, "descuento": 20}, headers=H)
    assert client.get("/api/resumen").json["totales"]["var"] == 40000


def test_pagar_resumen_y_no_borrar_tarjeta_con_compras(client):
    nueva(client)
    tid = _tarjeta(client)
    client.post("/api/movs", json={"tipo": "egreso", "cat": "casa", "monto": 1000, "tarjeta_id": tid, "cuotas": 1}, headers=H)
    assert client.delete(f"/api/tarjetas/{tid}", headers=H).status_code == 400
    assert client.post(f"/api/tarjetas/{tid}/pagar", json={"monto": 5000}, headers=H).status_code == 200
    t = client.get("/api/tarjetas").json["items"][0]
    assert t["pagado"] and t["total"] == 5000
    client.delete(f"/api/tarjetas/{tid}/pagar", headers=H)
    assert not client.get("/api/tarjetas").json["items"][0]["pagado"]


def test_tarjeta_ajena(client):
    nueva(client)
    tid = _tarjeta(client)
    from conftest import APP
    otro = APP.test_client()
    nueva(otro)
    r = otro.post("/api/movs", json={"tipo": "egreso", "cat": "casa", "monto": 1000, "tarjeta_id": tid}, headers=H)
    assert r.status_code == 400


def test_validaciones(client):
    nueva(client)
    assert client.post("/api/movs", json={"tipo": "egreso", "monto": 1000, "descuento": 150}, headers=H).status_code == 400
    assert client.post("/api/tarjetas", json={"nombre": "X", "cierre": 40, "vence": 5}, headers=H).status_code == 400
