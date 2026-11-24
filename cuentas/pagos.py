"""Suscripción mensual con Mercado Pago.

Con la variable CUENTAS_MP_TOKEN (Access Token de producción de tu cuenta de Mercado Pago) la app crea
la suscripción de cada persona y se entera sola de cada pago por el webhook /api/mp/webhook.
Opcional: CUENTAS_MP_WEBHOOK_SECRET (la «clave secreta» de Webhooks) para verificar que el aviso viene de Mercado Pago.

Sin token, la app muestra el link de suscripción y/o el alias que cargues en el panel, y vos marcás
los pagos a mano desde Administración.
"""
import hashlib
import hmac
import logging
import os
from datetime import date, timedelta

import requests

from . import core
from .db import get_setting
from .push import notify

log = logging.getLogger(__name__)
API = "https://api.mercadopago.com"


def token():
    return os.environ.get("CUENTAS_MP_TOKEN", "").strip()


def configurado():
    return bool(token())


def _h():
    return {"Authorization": f"Bearer {token()}", "Content-Type": "application/json"}


def precio(con):
    try:
        return float(get_setting(con, "precio_mensual", "4000"))
    except ValueError:
        return 4000.0


def crear_suscripcion(con, u, base_url):
    """Devuelve el link de Mercado Pago donde la persona carga su tarjeta y confirma la suscripción."""
    body = {
        "reason": "Cuentas Claras · suscripción mensual",
        "external_reference": str(u["id"]),
        "payer_email": u["email"],
        "auto_recurring": {"frequency": 1, "frequency_type": "months", "transaction_amount": precio(con), "currency_id": "ARS"},
        "back_url": base_url.rstrip("/") + "/#cuenta",
        "status": "pending",
    }
    r = requests.post(f"{API}/preapproval", json=body, headers=_h(), timeout=20)
    if r.status_code >= 300:
        log.warning("Mercado Pago no creó la suscripción (%s): %s", r.status_code, r.text[:300])
        return None
    data = r.json()
    con.execute("UPDATE users SET mp_preapproval_id=?, mp_status=? WHERE id=?", (data.get("id"), data.get("status", "pending"), u["id"]))
    return data.get("init_point")


def cancelar_suscripcion(con, u):
    if not (configurado() and u["mp_preapproval_id"]):
        return False
    r = requests.put(f"{API}/preapproval/{u['mp_preapproval_id']}", json={"status": "cancelled"}, headers=_h(), timeout=20)
    if r.status_code < 300:
        con.execute("UPDATE users SET mp_status='cancelled' WHERE id=?", (u["id"],))
        return True
    return False


def firma_valida(headers, data_id):
    """Verifica la firma x-signature de Mercado Pago (si configuraste la clave secreta)."""
    secret = os.environ.get("CUENTAS_MP_WEBHOOK_SECRET", "").strip()
    if not secret:
        return True
    partes = dict(p.split("=", 1) for p in (headers.get("x-signature") or "").split(",") if "=" in p)
    ts, v1 = partes.get("ts", "").strip(), partes.get("v1", "").strip()
    if not ts or not v1:
        return False
    did = str(data_id).lower() if str(data_id).isalnum() else str(data_id)
    manifest = f"id:{did};request-id:{headers.get('x-request-id', '')};ts:{ts};"
    calc = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calc, v1)


def _usuario_de(con, preapproval_id, external_reference=None):
    r = con.execute("SELECT * FROM users WHERE mp_preapproval_id=?", (preapproval_id,)).fetchone()
    if not r and external_reference and str(external_reference).isdigit():
        r = con.execute("SELECT * FROM users WHERE id=?", (int(external_reference),)).fetchone()
    return r


def procesar_aviso(con, tipo, data_id):
    """Procesa un aviso de Mercado Pago. Nunca confía en el contenido: vuelve a consultar a la API."""
    if not configurado() or not data_id:
        return "ignorado"
    if tipo in ("subscription_preapproval", "preapproval"):
        r = requests.get(f"{API}/preapproval/{data_id}", headers=_h(), timeout=20)
        if r.status_code >= 300:
            return "error"
        p = r.json()
        u = _usuario_de(con, p.get("id"), p.get("external_reference"))
        if not u:
            return "sin usuario"
        con.execute("UPDATE users SET mp_preapproval_id=?, mp_status=? WHERE id=?", (p.get("id"), p.get("status"), u["id"]))
        if p.get("status") == "authorized":
            # mientras llega el primer cobro, unos días de gracia para que no se corte el acceso
            gracia = (core.hoy() + timedelta(days=3)).isoformat()
            if not u["paid_until"] or u["paid_until"] < gracia:
                con.execute("UPDATE users SET paid_until=? WHERE id=?", (gracia, u["id"]))
            if u["mp_status"] != "authorized":
                notify(con, u["id"], "¡Suscripción activa!", "Gracias por sumarte a Cuentas Claras. Ya podés seguir usando todo.", "#cuenta", "pago")
        return p.get("status") or "ok"
    if tipo in ("subscription_authorized_payment", "authorized_payment"):
        r = requests.get(f"{API}/authorized_payments/{data_id}", headers=_h(), timeout=20)
        if r.status_code >= 300:
            return "error"
        a = r.json()
        aprobado = a.get("status") == "processed" and (a.get("payment") or {}).get("status") == "approved"
        if not aprobado:
            return a.get("status") or "pendiente"
        u = _usuario_de(con, a.get("preapproval_id"), a.get("external_reference"))
        if not u:
            return "sin usuario"
        ref = f"mp-ap-{a.get('id') or data_id}"
        if con.execute("SELECT 1 FROM pagos WHERE ref=?", (ref,)).fetchone():
            return "repetido"
        # el pago cubre un mes desde hoy o desde donde terminaba lo pagado (sin contar la gracia)
        if u["paid_until"] and u["mp_status"] == "authorized" and not con.execute("SELECT 1 FROM pagos WHERE user_id=?", (u["id"],)).fetchone():
            con.execute("UPDATE users SET paid_until=NULL WHERE id=?", (u["id"],))
        hasta = core.extender_pago(con, u["id"])
        con.execute("INSERT INTO pagos(user_id, monto, fuente, ref, hasta, created_at) VALUES(?,?,?,?,?,?)",
                    (u["id"], a.get("transaction_amount"), "mercadopago", ref, hasta, core.stamp()))
        notify(con, u["id"], "Pago recibido", f"Tu suscripción está al día hasta el {date.fromisoformat(hasta).strftime('%d/%m/%Y')}.", "#cuenta", "pago")
        return "acreditado"
    return "ignorado"


def marcar_pago_manual(con, uid, meses=1, monto=None):
    hasta = core.extender_pago(con, uid, meses=meses)
    con.execute("INSERT INTO pagos(user_id, monto, fuente, ref, hasta, created_at) VALUES(?,?,?,?,?,?)",
                (uid, monto, "manual", None, hasta, core.stamp()))
    notify(con, uid, "Pago registrado", f"Tu suscripción está al día hasta el {date.fromisoformat(hasta).strftime('%d/%m/%Y')}. ¡Gracias!", "#cuenta", "pago")
    return hasta
