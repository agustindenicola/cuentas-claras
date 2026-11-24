from datetime import datetime

from conftest import H, nueva

from cuentas import core, scheduler


def test_ingreso_variable_cobrado_con_otro_monto(client):
    nueva(client)
    client.post("/api/ingresos", json={"nombre": "Trabajo por mi cuenta", "monto": 400000, "dia": 15}, headers=H)
    i = client.get("/api/resumen").json["ingresos"][0]
    assert not i["cobrado"]
    client.post(f"/api/ingresos/{i['id']}/cobrar", json={"monto": 520000}, headers=H)
    r = client.get("/api/resumen").json
    assert r["ingresos"][0]["cobrado"] and r["totales"]["ing"] == 520000
    client.delete(f"/api/ingresos/{i['id']}/cobrar", headers=H)
    assert client.get("/api/resumen").json["totales"]["ing"] == 400000


def test_frecuentes(client):
    nueva(client)
    for monto in (40000, 45000):
        client.post("/api/movs", json={"tipo": "egreso", "cat": "super", "monto": monto, "descr": "Supermercado"}, headers=H)
    client.post("/api/movs", json={"tipo": "egreso", "cat": "salidas", "monto": 9000, "descr": "Cine"}, headers=H)
    items = client.get("/api/frecuentes").json["items"]
    assert items == [{"descr": "Supermercado", "cat": "super", "monto": 45000, "veces": 2}]


def test_recordatorio_trae_botones(client, con, monkeypatch):
    uid, _ = nueva(client)
    enviados = []
    monkeypatch.setattr(scheduler, "notify", lambda con, uid, t, b, url, kind, actions=None: enviados.append(actions))
    d = core.hoy()
    u = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    assert scheduler.recordatorio_diario(con, u, datetime(d.year, d.month, d.day, 21, 0))
    assert [a["action"] for a in enviados[0]] == ["nogaste", "anotar"]


def test_copia_por_mail(tmp_path, monkeypatch):
    from cuentas import mail
    ruta = tmp_path / "cuentas-2026-11-16.db"
    ruta.write_bytes(b"datos")
    mandados = []
    monkeypatch.setenv("CUENTAS_BACKUP_EMAIL", "yo@ejemplo.com")
    monkeypatch.setattr(mail, "configured", lambda: True)
    monkeypatch.setattr(mail, "send", lambda to, subj, text, adjunto=None: mandados.append((to, adjunto[0])) or True)
    assert scheduler.enviar_copia(str(ruta), core.hoy())
    assert not scheduler.enviar_copia(str(ruta), core.hoy())       # una sola vez por día
    assert mandados == [("yo@ejemplo.com", "cuentas-2026-11-16.db.gz")]


def test_sin_mail_no_manda_copia(tmp_path, monkeypatch):
    from cuentas import mail
    ruta = tmp_path / "x.db"
    ruta.write_bytes(b"x")
    monkeypatch.setattr(mail, "configured", lambda: False)
    assert not scheduler.enviar_copia(str(ruta), core.hoy())
