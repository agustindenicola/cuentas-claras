import hashlib
import hmac
from datetime import timedelta

from conftest import APP, H, nueva

from cuentas import core, pagos


class Resp:
    def __init__(self, data, code=200):
        self._d, self.status_code, self.text = data, code, str(data)

    def json(self):
        return self._d


def test_suscribir_sin_mercadopago_usa_link(client, con, monkeypatch):
    monkeypatch.delenv("CUENTAS_MP_TOKEN", raising=False)
    nueva(client)
    con.execute("UPDATE settings SET value='' WHERE key='mp_link'")
    con.commit()
    assert client.post("/api/cuenta/suscribir", headers=H).status_code == 400
    con.execute("UPDATE settings SET value='https://www.mercadopago.com.ar/subscriptions/checkout?x=1' WHERE key='mp_link'")
    con.commit()
    assert client.post("/api/cuenta/suscribir", headers=H).json["url"].startswith("https://www.mercadopago")


def test_flujo_mercadopago(client, con, monkeypatch):
    monkeypatch.setenv("CUENTAS_MP_TOKEN", "TEST-token")
    monkeypatch.delenv("CUENTAS_MP_WEBHOOK_SECRET", raising=False)
    uid, _ = nueva(client)
    con.execute("UPDATE users SET trial_ends=? WHERE id=?", ((core.hoy() - timedelta(days=1)).isoformat(), uid))
    con.commit()
    enviado = {}

    def post(url, json, headers, timeout):
        enviado.update(json)
        return Resp({"id": "PRE-1", "init_point": "https://mp/checkout/PRE-1", "status": "pending"}, 201)

    def get(url, headers, timeout):
        if "/preapproval/" in url:
            return Resp({"id": "PRE-1", "status": "authorized", "external_reference": str(uid)})
        return Resp({"id": 77, "preapproval_id": "PRE-1", "status": "processed", "payment": {"status": "approved"}, "transaction_amount": 4000})

    monkeypatch.setattr(pagos.requests, "post", post)
    monkeypatch.setattr(pagos.requests, "get", get)
    r = client.post("/api/cuenta/suscribir", headers=H).json
    assert r["url"] == "https://mp/checkout/PRE-1" and enviado["external_reference"] == str(uid)
    assert enviado["auto_recurring"]["transaction_amount"] == 4000
    mp = APP.test_client()      # Mercado Pago no manda nuestro encabezado ni cookies
    assert mp.post("/api/mp/webhook", json={"type": "subscription_preapproval", "data": {"id": "PRE-1"}}).json["resultado"] == "authorized"
    assert client.get("/api/me").json["user"]["cuenta"]["estado"] == "activa"     # días de gracia
    assert mp.post("/api/mp/webhook", json={"type": "subscription_authorized_payment", "data": {"id": "77"}}).json["resultado"] == "acreditado"
    assert mp.post("/api/mp/webhook", json={"type": "subscription_authorized_payment", "data": {"id": "77"}}).json["resultado"] == "repetido"
    hasta = client.get("/api/me").json["user"]["cuenta"]["hasta"]
    assert hasta == core.sumar_mes(core.hoy() - timedelta(days=1)).isoformat()


def test_firma_del_webhook(monkeypatch):
    monkeypatch.setenv("CUENTAS_MP_WEBHOOK_SECRET", "secreto")
    manifest = "id:123;request-id:req-1;ts:1700;"
    v1 = hmac.new(b"secreto", manifest.encode(), hashlib.sha256).hexdigest()
    assert pagos.firma_valida({"x-signature": f"ts=1700,v1={v1}", "x-request-id": "req-1"}, "123")
    assert not pagos.firma_valida({"x-signature": "ts=1700,v1=mal", "x-request-id": "req-1"}, "123")
    assert APP.test_client().post("/api/mp/webhook?data.id=123&type=payment", json={}).status_code == 401
