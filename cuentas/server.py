"""Servidor web de Cuentas Claras: API + la app instalable (PWA)."""
import hashlib
import logging
import os
import re
import secrets
import time
from collections import defaultdict
from datetime import date, timedelta
from functools import wraps

from flask import Flask, abort, g, jsonify, request, send_from_directory, session
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from . import core, logros, mail, pagos, push
from .db import db, get_setting, init_db, set_setting

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
DEMO = os.environ.get("CUENTAS_DEMO", "1") == "1"
ONLINE = os.environ.get("CUENTAS_HTTPS") == "1"            # publicada en internet (detrás del https del hosting)
app = Flask(__name__, static_folder=None)
if ONLINE:
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", MAX_CONTENT_LENGTH=1024 * 1024,
                  PERMANENT_SESSION_LIFETIME=timedelta(days=90), SESSION_COOKIE_SECURE=ONLINE,
                  SESSION_COOKIE_NAME="cuentas")
log = logging.getLogger("cuentas")
_intentos = defaultdict(list)


# ------------------------------------------------------------------ utilidades
@app.errorhandler(HTTPException)
def http_error(e):
    if request.path.startswith("/api/"):
        return jsonify(error=e.description, code=getattr(e, "code_name", None)), e.code
    return e


@app.errorhandler(Exception)
def any_error(e):
    log.exception("Error en %s", request.path)
    return jsonify(error="Algo salió mal. Probá de nuevo en un momento."), 500


@app.before_request
def guard():
    # toda escritura viene de nuestra app con este encabezado (protege de pedidos armados por otros sitios).
    # el aviso de Mercado Pago es la excepción: no trae el encabezado y se verifica consultando a su API.
    if (request.path.startswith("/api/") and request.method not in ("GET", "HEAD")
            and request.path != "/api/mp/webhook" and request.headers.get("X-CC") != "1"):
        abort(403, "Pedido no permitido")


@app.before_request
def track_activity():
    d = core.hoy().isoformat()
    if "uid" in session and request.path.startswith("/api/") and session.get("act_day") != d:
        with db() as con:
            con.execute("INSERT OR IGNORE INTO activity(user_id, day) VALUES(?,?)", (session["uid"], d))
            con.execute("UPDATE users SET last_seen=? WHERE id=?", (core.stamp(), session["uid"]))
        session["act_day"] = d


@app.after_request
def headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


def body():
    return request.get_json(silent=True) or {}


def num(v, campo, lo=0, hi=1e11):
    if v in (None, ""):
        abort(400, f"Falta {campo}")
    try:
        x = float(str(v).replace(".", "").replace(",", ".")) if isinstance(v, str) and re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?|\d+,\d+", v.strip()) else float(v)
    except (TypeError, ValueError):
        abort(400, f"{campo.capitalize()}: no es un número válido")
    if not lo <= x <= hi:
        abort(400, f"{campo.capitalize()}: está fuera de rango")
    return x


def texto(v, campo, maxlen=60, requerido=True):
    t = re.sub(r"\s+", " ", str(v or "")).strip()[:maxlen]
    if requerido and not t:
        abort(400, f"Ingresá {campo}")
    return t


def fecha(v):
    if not v:
        return core.hoy()
    try:
        f = date.fromisoformat(str(v)[:10])
    except ValueError:
        abort(400, "Fecha inválida")
    if not date(2000, 1, 1) <= f <= core.hoy() + timedelta(days=62):
        abort(400, "La fecha está fuera de rango")
    return f


def current_user():
    if "uid" not in session:
        return None
    if "user" not in g:
        with db() as con:
            r = con.execute("SELECT * FROM users WHERE id=?", (session["uid"],)).fetchone()
        g.user = dict(r) if r else None
    return g.user


class PagoRequerido(HTTPException):
    code = 402
    code_name = "pago"
    description = "Tu prueba gratis terminó. Suscribite para seguir cargando movimientos; tus datos siguen guardados."


def login_required(role=None, escribe=False):
    def deco(fn):
        @wraps(fn)
        def inner(*a, **k):
            u = current_user()
            if not u:
                abort(401, "Iniciá sesión para seguir")
            if role and u["role"] != role:
                abort(403, "Esta sección es solo para administración")
            if escribe and core.estado_cuenta(u)["estado"] == "vencida":
                raise PagoRequerido()
            return fn(u, *a, **k)
        return inner
    return deco


def con_logros(con, uid, **extra):
    """Respuesta de una escritura: incluye los logros que se acaban de ganar."""
    nuevos = logros.evaluar(con, uid)
    return jsonify(ok=True, logros=[dict(x) for x in nuevos], **extra)


def propio(con, tabla, rid, uid):
    r = con.execute(f"SELECT * FROM {tabla} WHERE id=? AND user_id=?", (rid, uid)).fetchone()
    if not r:
        abort(404, "No se encontró")
    return r


# ------------------------------------------------------------------ app instalable
@app.get("/")
def index():
    resp = send_from_directory(STATIC, "index.html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/sw.js")
def sw():
    resp = send_from_directory(STATIC, "sw.js")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.get("/manifest.webmanifest")
def manifest():
    return send_from_directory(STATIC, "manifest.webmanifest", mimetype="application/manifest+json")


@app.get("/static/<path:p>")
def static_files(p):
    resp = send_from_directory(STATIC, p)
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/salud")
def salud():
    return jsonify(ok=True)


# ------------------------------------------------------------------ cuentas
def start_session(uid):
    session.clear()
    session.permanent = True
    session["uid"] = uid


def limitar(clave, maximo, segundos):
    now = time.time()
    _intentos[clave] = [t for t in _intentos[clave] if now - t < segundos]
    if len(_intentos[clave]) >= maximo:
        abort(429, "Demasiados intentos. Esperá unos minutos y probá de nuevo.")
    _intentos[clave].append(now)


@app.post("/api/register")
def register():
    b = body()
    limitar("reg-" + (request.remote_addr or "?"), 10, 3600)
    email = (b.get("email") or "").strip().lower()
    name = texto(b.get("name"), "tu nombre", 40)
    pw = b.get("password") or ""
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        abort(400, "Ese mail no parece válido. Revisalo.")
    if email.endswith("@cuentasclaras.app"):
        abort(400, "Ese mail no se puede usar")
    if len(pw) < 8:
        abort(400, "La contraseña tiene que tener al menos 8 caracteres")
    if not b.get("accept_terms"):
        abort(400, "Para crear la cuenta tenés que aceptar los términos y la política de privacidad")
    with db() as con:
        if con.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            abort(400, "Ya hay una cuenta con ese mail. Probá con «Ya tengo cuenta».")
        dias = int(get_setting(con, "dias_prueba", "14"))
        fin = (core.hoy() + timedelta(days=dias - 1)).isoformat()
        uid = con.execute("INSERT INTO users(email, pass_hash, name, created_at, accepted_terms, trial_ends) VALUES(?,?,?,?,?,?)",
                          (email, generate_password_hash(pw), name, core.stamp(), core.stamp(), fin)).lastrowid
        push.notify(con, uid, f"¡Bienvenida, {name}!", f"Tenés {dias} días para probar todo gratis.", "#inicio", "bienvenida", push=False)
    start_session(uid)
    return jsonify(ok=True)


@app.post("/api/login")
def login():
    b = body()
    limitar("login-" + (request.remote_addr or "?"), 10, 600)
    with db() as con:
        r = con.execute("SELECT id, pass_hash FROM users WHERE email=?", ((b.get("email") or "").strip().lower(),)).fetchone()
    if not r or not check_password_hash(r["pass_hash"], b.get("password") or ""):
        abort(400, "El mail o la contraseña no son correctos")
    _intentos.pop("login-" + (request.remote_addr or "?"), None)
    start_session(r["id"])
    return jsonify(ok=True)


@app.post("/api/demo-login")
def demo_login():
    if not DEMO:
        abort(404)
    from .seed import DEMO_EMAIL
    with db() as con:
        r = con.execute("SELECT id FROM users WHERE email=?", (DEMO_EMAIL,)).fetchone()
    if not r:
        abort(404, "No hay datos de ejemplo cargados")
    start_session(r["id"])
    return jsonify(ok=True)


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


def user_publico(con, u):
    return {
        "id": u["id"], "email": u["email"], "name": u["name"], "role": u["role"], "onboarded": u["onboarded"],
        "notify_hour": u["notify_hour"], "av_diario": u["av_diario"], "av_vencimientos": u["av_vencimientos"],
        "av_resumen": u["av_resumen"], "meta_ahorro": u["meta_ahorro"], "grande": u["grande"],
        "demo": u["email"].endswith("@cuentasclaras.app"), "cuenta": core.estado_cuenta(u),
    }


@app.get("/api/me")
def me():
    u = current_user()
    if not u:
        return jsonify(user=None, demo=DEMO, mail=mail.configured())
    with db() as con:
        unread = con.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND read=0", (u["id"],)).fetchone()[0]
        subs = con.execute("SELECT COUNT(*) FROM push_subs WHERE user_id=?", (u["id"],)).fetchone()[0]
        return jsonify(user=user_publico(con, u), unread=unread, vapid=push.vapid_public_key(con), push_devices=subs,
                       demo=DEMO, mail=mail.configured(), hoy=core.hoy().isoformat())


@app.put("/api/me")
@login_required()
def update_me(u):
    b = body()
    with db() as con:
        if "name" in b:
            con.execute("UPDATE users SET name=? WHERE id=?", (texto(b["name"], "tu nombre", 40), u["id"]))
        if "notify_hour" in b:
            con.execute("UPDATE users SET notify_hour=? WHERE id=?", (int(num(b["notify_hour"], "hora", 0, 23)), u["id"]))
        for k in ("av_diario", "av_vencimientos", "av_resumen", "grande"):
            if k in b:
                con.execute(f"UPDATE users SET {k}=? WHERE id=?", (int(bool(b[k])), u["id"]))
        if "meta_ahorro" in b:
            meta = None if b["meta_ahorro"] in (None, "", 0) else num(b["meta_ahorro"], "meta", 1)
            con.execute("UPDATE users SET meta_ahorro=? WHERE id=?", (meta, u["id"]))
        if b.get("onboarded"):
            con.execute("UPDATE users SET onboarded=1 WHERE id=?", (u["id"],))
        return con_logros(con, u["id"])


@app.post("/api/me/password")
@login_required()
def change_password(u):
    b = body()
    if len(b.get("new") or "") < 8:
        abort(400, "La contraseña nueva tiene que tener al menos 8 caracteres")
    with db() as con:
        r = con.execute("SELECT pass_hash FROM users WHERE id=?", (u["id"],)).fetchone()
        if not check_password_hash(r["pass_hash"], b.get("current") or ""):
            abort(400, "La contraseña actual no es correcta")
        con.execute("UPDATE users SET pass_hash=? WHERE id=?", (generate_password_hash(b["new"]), u["id"]))
    return jsonify(ok=True)


@app.get("/api/me/export")
@login_required()
def export_me(u):
    with db() as con:
        data = {t: [dict(r) for r in con.execute(f"SELECT * FROM {t} WHERE user_id=?", (u["id"],))]
                for t in ("ingresos", "fijos", "tarjetas", "movs", "checkins", "cierres", "logros", "pagos")}
        data["fijo_pagos"] = [dict(r) for r in con.execute(
            "SELECT p.* FROM fijo_pagos p JOIN fijos f ON f.id=p.fijo_id WHERE f.user_id=?", (u["id"],))]
    data["cuenta"] = {k: u[k] for k in ("email", "name", "created_at")}
    resp = jsonify(data)
    resp.headers["Content-Disposition"] = "attachment; filename=mis-datos-cuentas-claras.json"
    return resp


@app.delete("/api/me")
@login_required()
def delete_me(u):
    with db() as con:
        r = con.execute("SELECT pass_hash FROM users WHERE id=?", (u["id"],)).fetchone()
        if not check_password_hash(r["pass_hash"], body().get("password") or ""):
            abort(400, "La contraseña no es correcta")
        try:
            pagos.cancelar_suscripcion(con, u)
        except Exception:  # noqa: BLE001
            log.exception("Cancelar suscripción al borrar cuenta")
        con.execute("DELETE FROM users WHERE id=?", (u["id"],))
    session.clear()
    return jsonify(ok=True)


# ------------------------------------------------------------------ resumen
@app.get("/api/resumen")
@login_required()
def resumen(u):
    with db() as con:
        r = core.resumen(con, u["id"])
        nuevos = logros.evaluar(con, u["id"])
        r["logros"] = {"ganados": con.execute("SELECT COUNT(*) FROM logros WHERE user_id=?", (u["id"],)).fetchone()[0],
                       "total": len(logros.LOGROS),
                       "sin_ver": [dict(logros.POR_ID[x["logro_id"]]) for x in con.execute(
                           "SELECT logro_id FROM logros WHERE user_id=? AND visto=0", (u["id"],))]}
        r["logros_nuevos"] = [dict(x) for x in nuevos]
        r["meta_ahorro"] = u["meta_ahorro"]
    return jsonify(r)


# ------------------------------------------------------------------ ingresos fijos
def _ingreso_de(b):
    return texto(b.get("nombre"), "el concepto"), num(b.get("monto"), "monto", 1), int(num(b.get("dia", 1), "día", 1, 31))


@app.post("/api/ingresos")
@login_required(escribe=True)
def add_ingreso(u):
    nombre, monto, dia = _ingreso_de(body())
    with db() as con:
        con.execute("INSERT INTO ingresos(user_id, nombre, monto, dia, created_at) VALUES(?,?,?,?,?)", (u["id"], nombre, monto, dia, core.stamp()))
        return con_logros(con, u["id"])


@app.post("/api/ingresos/<int:iid>/cobrar")
@login_required(escribe=True)
def cobrar_ingreso(u, iid):
    b = body()
    d = core.hoy()
    with db() as con:
        i = propio(con, "ingresos", iid, u["id"])
        monto = num(b["monto"], "monto", 0) if b.get("monto") not in (None, "") else i["monto"]
        con.execute("INSERT INTO ingreso_cobros(ingreso_id, mes, monto, cobrado_el) VALUES(?,?,?,?) "
                    "ON CONFLICT(ingreso_id, mes) DO UPDATE SET monto=excluded.monto", (iid, core.mes_key(d), monto, d.isoformat()))
        return con_logros(con, u["id"])


@app.delete("/api/ingresos/<int:iid>/cobrar")
@login_required()
def descobrar_ingreso(u, iid):
    with db() as con:
        propio(con, "ingresos", iid, u["id"])
        con.execute("DELETE FROM ingreso_cobros WHERE ingreso_id=? AND mes=?", (iid, core.mes_key(core.hoy())))
    return jsonify(ok=True)


@app.put("/api/ingresos/<int:iid>")
@login_required(escribe=True)
def edit_ingreso(u, iid):
    nombre, monto, dia = _ingreso_de(body())
    with db() as con:
        propio(con, "ingresos", iid, u["id"])
        con.execute("UPDATE ingresos SET nombre=?, monto=?, dia=? WHERE id=?", (nombre, monto, dia, iid))
        return con_logros(con, u["id"])


@app.delete("/api/ingresos/<int:iid>")
@login_required()
def del_ingreso(u, iid):
    with db() as con:
        propio(con, "ingresos", iid, u["id"])
        con.execute("DELETE FROM ingresos WHERE id=?", (iid,))
    return jsonify(ok=True)


# ------------------------------------------------------------------ gastos fijos
def _fijo_de(b):
    cat = b.get("cat") if b.get("cat") in core.CATS else "otros"
    return texto(b.get("nombre"), "el concepto"), cat, num(b.get("monto"), "monto", 1), int(num(b.get("dia", 10), "día", 1, 31))


@app.post("/api/fijos")
@login_required(escribe=True)
def add_fijo(u):
    nombre, cat, monto, dia = _fijo_de(body())
    with db() as con:
        con.execute("INSERT INTO fijos(user_id, nombre, cat, monto, dia, created_at) VALUES(?,?,?,?,?,?)",
                    (u["id"], nombre, cat, monto, dia, core.stamp()))
        return con_logros(con, u["id"])


@app.put("/api/fijos/<int:fid>")
@login_required(escribe=True)
def edit_fijo(u, fid):
    nombre, cat, monto, dia = _fijo_de(body())
    with db() as con:
        propio(con, "fijos", fid, u["id"])
        con.execute("UPDATE fijos SET nombre=?, cat=?, monto=?, dia=? WHERE id=?", (nombre, cat, monto, dia, fid))
        return con_logros(con, u["id"])


@app.delete("/api/fijos/<int:fid>")
@login_required()
def del_fijo(u, fid):
    with db() as con:
        propio(con, "fijos", fid, u["id"])
        con.execute("DELETE FROM fijos WHERE id=?", (fid,))
    return jsonify(ok=True)


@app.post("/api/fijos/<int:fid>/pagar")
@login_required(escribe=True)
def pagar_fijo(u, fid):
    b = body()
    with db() as con:
        f = propio(con, "fijos", fid, u["id"])
        monto = num(b["monto"], "monto", 1) if b.get("monto") not in (None, "") else f["monto"]
        d = core.hoy()
        con.execute("INSERT INTO fijo_pagos(fijo_id, mes, monto, pagado_el) VALUES(?,?,?,?) "
                    "ON CONFLICT(fijo_id, mes) DO UPDATE SET monto=excluded.monto",
                    (fid, core.mes_key(d), monto, d.isoformat()))
        if b.get("actualizar") and monto != f["monto"]:
            con.execute("UPDATE fijos SET monto=? WHERE id=?", (monto, fid))
        return con_logros(con, u["id"])


@app.delete("/api/fijos/<int:fid>/pagar")
@login_required()
def despagar_fijo(u, fid):
    with db() as con:
        propio(con, "fijos", fid, u["id"])
        con.execute("DELETE FROM fijo_pagos WHERE fijo_id=? AND mes=?", (fid, core.mes_key(core.hoy())))
    return jsonify(ok=True)


# ------------------------------------------------------------------ movimientos (egresos, ingresos extra, ahorros)
def _mov_de(con, uid, b):
    """Valida un movimiento. Con tarjeta: cuotas, % de descuento y % de interés; el total se calcula acá."""
    tipo = b.get("tipo")
    if tipo not in core.TIPOS:
        abort(400, "Tipo de movimiento inválido")
    if tipo == "egreso":
        cat = b.get("cat") if b.get("cat") in core.CATS else "otros"
    elif tipo == "ahorro":
        cat = b.get("cat") if b.get("cat") in core.CATS_AHORRO else "ahorro"
    else:
        cat = "extra"
    precio = num(b.get("monto"), "monto", 1)
    f = fecha(b.get("fecha"))
    m = {"tipo": tipo, "cat": cat, "descr": texto(b.get("descr"), "", 80, requerido=False), "fecha": f.isoformat(),
         "tarjeta_id": None, "cuotas": 1, "primer_mes": None, "precio": None, "descuento": 0, "interes": 0}
    if tipo == "egreso":
        m["descuento"] = num(b.get("descuento") or 0, "descuento", 0, 100)
        m["interes"] = num(b.get("interes") or 0, "interés", 0, 500)
        if b.get("tarjeta_id"):
            t = con.execute("SELECT * FROM tarjetas WHERE id=? AND user_id=?", (int(b["tarjeta_id"]), uid)).fetchone()
            if not t:
                abort(400, "Esa tarjeta no existe")
            m["tarjeta_id"] = t["id"]
            m["cuotas"] = int(num(b.get("cuotas") or 1, "cuotas", 1, 72))
            m["primer_mes"] = core.primer_mes(f, t["cierre"])
    if m["descuento"] or m["interes"]:
        m["precio"] = precio
    m["monto"] = core.precio_final(precio, m["descuento"], m["interes"])
    return m


CAMPOS_MOV = ("tipo", "cat", "monto", "descr", "fecha", "tarjeta_id", "cuotas", "primer_mes", "precio", "descuento", "interes")


@app.get("/api/frecuentes")
@login_required()
def get_frecuentes(u):
    with db() as con:
        return jsonify(items=core.frecuentes(con, u["id"]))


@app.get("/api/movs")
@login_required()
def list_movs(u):
    mes = request.args.get("mes")
    if mes and not re.fullmatch(r"\d{4}-\d{2}", mes):
        abort(400, "Mes inválido")
    with db() as con:
        items = core.movimientos(con, u["id"], mes, request.args.get("tipo") or None)
        meses = [r[0] for r in con.execute("SELECT DISTINCT substr(fecha,1,7) m FROM movs WHERE user_id=? ORDER BY m DESC", (u["id"],))]
    return jsonify(items=items, meses=meses)


@app.post("/api/movs")
@login_required(escribe=True)
def add_mov(u):
    with db() as con:
        m = _mov_de(con, u["id"], body())
        mid = con.execute(f"INSERT INTO movs(user_id, created_at, {', '.join(CAMPOS_MOV)}) VALUES(?,?{',?' * len(CAMPOS_MOV)})",
                          (u["id"], core.stamp(), *[m[k] for k in CAMPOS_MOV])).lastrowid
        return con_logros(con, u["id"], id=mid)


@app.put("/api/movs/<int:mid>")
@login_required(escribe=True)
def edit_mov(u, mid):
    with db() as con:
        propio(con, "movs", mid, u["id"])
        m = _mov_de(con, u["id"], body())
        con.execute(f"UPDATE movs SET {', '.join(k + '=?' for k in CAMPOS_MOV)} WHERE id=?", (*[m[k] for k in CAMPOS_MOV], mid))
        return con_logros(con, u["id"])


@app.delete("/api/movs/<int:mid>")
@login_required()
def del_mov(u, mid):
    with db() as con:
        propio(con, "movs", mid, u["id"])
        con.execute("DELETE FROM movs WHERE id=?", (mid,))
    return jsonify(ok=True)


# ------------------------------------------------------------------ tarjetas de crédito
def _tarjeta_de(b):
    return (texto(b.get("nombre"), "el nombre de la tarjeta", 40), int(num(b.get("cierre"), "día de cierre", 1, 31)),
            int(num(b.get("vence"), "día de vencimiento", 1, 31)))


@app.get("/api/tarjetas")
@login_required()
def list_tarjetas(u):
    d = core.hoy()
    key = core.mes_key(d)
    with db() as con:
        en_curso = []
        for c in core.cuotas_mes(con, u["id"], key):
            en_curso.append({k: c[k] for k in ("id", "descr", "cat", "monto", "cuotas", "cuota_n", "importe", "ultimo_mes", "tarjeta_id", "tarjeta", "fecha")})
        # compras que todavía no empezaron a pagarse (entran en un resumen futuro)
        futuras = [dict(r) for r in con.execute(
            "SELECT m.id, m.descr, m.cat, m.monto, m.cuotas, m.primer_mes, m.tarjeta_id, t.nombre AS tarjeta, m.fecha FROM movs m "
            "JOIN tarjetas t ON t.id=m.tarjeta_id WHERE m.user_id=? AND m.primer_mes>? ORDER BY m.fecha DESC", (u["id"], key))]
        for f in futuras:
            f["importe"] = f["monto"] / f["cuotas"]
        return jsonify(items=core.tarjetas_mes(con, u["id"], key, d), compromisos=core.compromisos(con, u["id"], d),
                       en_curso=sorted(en_curso, key=lambda c: c["ultimo_mes"]), futuras=futuras, mes=key)


@app.post("/api/tarjetas")
@login_required(escribe=True)
def add_tarjeta(u):
    nombre, cierre, vence = _tarjeta_de(body())
    with db() as con:
        tid = con.execute("INSERT INTO tarjetas(user_id, nombre, cierre, vence, created_at) VALUES(?,?,?,?,?)",
                          (u["id"], nombre, cierre, vence, core.stamp())).lastrowid
    return jsonify(ok=True, id=tid)


@app.put("/api/tarjetas/<int:tid>")
@login_required(escribe=True)
def edit_tarjeta(u, tid):
    nombre, cierre, vence = _tarjeta_de(body())
    with db() as con:
        propio(con, "tarjetas", tid, u["id"])
        con.execute("UPDATE tarjetas SET nombre=?, cierre=?, vence=? WHERE id=?", (nombre, cierre, vence, tid))
    return jsonify(ok=True)


@app.delete("/api/tarjetas/<int:tid>")
@login_required()
def del_tarjeta(u, tid):
    with db() as con:
        propio(con, "tarjetas", tid, u["id"])
        if con.execute("SELECT 1 FROM movs WHERE tarjeta_id=?", (tid,)).fetchone():
            abort(400, "Esta tarjeta tiene compras cargadas. Borrá primero esas compras (o editalas para pasarlas a otra tarjeta).")
        con.execute("DELETE FROM tarjetas WHERE id=?", (tid,))
    return jsonify(ok=True)


@app.post("/api/tarjetas/<int:tid>/pagar")
@login_required(escribe=True)
def pagar_tarjeta(u, tid):
    b = body()
    d = core.hoy()
    key = core.mes_key(d)
    with db() as con:
        propio(con, "tarjetas", tid, u["id"])
        if b.get("monto") not in (None, ""):
            monto = num(b["monto"], "monto", 0)
        else:
            monto = sum(c["importe"] for c in core.cuotas_mes(con, u["id"], key, tid))
        con.execute("INSERT INTO tarjeta_pagos(tarjeta_id, mes, monto, pagado_el) VALUES(?,?,?,?) "
                    "ON CONFLICT(tarjeta_id, mes) DO UPDATE SET monto=excluded.monto", (tid, key, monto, d.isoformat()))
        return con_logros(con, u["id"])


@app.delete("/api/tarjetas/<int:tid>/pagar")
@login_required()
def despagar_tarjeta(u, tid):
    with db() as con:
        propio(con, "tarjetas", tid, u["id"])
        con.execute("DELETE FROM tarjeta_pagos WHERE tarjeta_id=? AND mes=?", (tid, core.mes_key(core.hoy())))
    return jsonify(ok=True)


@app.post("/api/checkin")
@login_required(escribe=True)
def checkin(u):
    with db() as con:
        con.execute("INSERT OR IGNORE INTO checkins(user_id, fecha) VALUES(?,?)", (u["id"], core.hoy().isoformat()))
        return con_logros(con, u["id"])


# ------------------------------------------------------------------ logros
@app.get("/api/logros")
@login_required()
def get_logros(u):
    with db() as con:
        logros.evaluar(con, u["id"])
        return jsonify(logros.listado(con, u["id"]))


@app.post("/api/logros/vistos")
@login_required()
def logros_vistos(u):
    with db() as con:
        con.execute("UPDATE logros SET visto=1 WHERE user_id=?", (u["id"],))
    return jsonify(ok=True)


# ------------------------------------------------------------------ avisos
@app.get("/api/notifications")
@login_required()
def notifications(u):
    with db() as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 40", (u["id"],))]
    return jsonify(items=rows)


@app.post("/api/notifications/read")
@login_required()
def notifications_read(u):
    with db() as con:
        con.execute("UPDATE notifications SET read=1 WHERE user_id=?", (u["id"],))
    return jsonify(ok=True)


@app.post("/api/push/subscribe")
@login_required()
def push_subscribe(u):
    s = body().get("subscription") or {}
    ep, keys = s.get("endpoint"), s.get("keys") or {}
    if not (ep and str(ep).startswith("https://") and keys.get("p256dh") and keys.get("auth")):
        abort(400, "Suscripción inválida")
    with db() as con:
        con.execute("INSERT INTO push_subs(user_id, endpoint, p256dh, auth, created_at) VALUES(?,?,?,?,?) "
                    "ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id, p256dh=excluded.p256dh, auth=excluded.auth",
                    (u["id"], ep, keys["p256dh"], keys["auth"], core.stamp()))
    return jsonify(ok=True)


@app.post("/api/push/unsubscribe")
@login_required()
def push_unsubscribe(u):
    with db() as con:
        con.execute("DELETE FROM push_subs WHERE user_id=? AND endpoint=?", (u["id"], body().get("endpoint")))
    return jsonify(ok=True)


@app.post("/api/push/test")
@login_required()
def push_test(u):
    with db() as con:
        sent = push.notify(con, u["id"], "¡Listo! 🔔", "Así te van a llegar los recordatorios de Cuentas Claras.", "#inicio", "prueba-aviso")
    return jsonify(sent=sent)


# ------------------------------------------------------------------ suscripción
@app.get("/api/cuenta")
@login_required()
def cuenta(u):
    with db() as con:
        return jsonify(
            estado=core.estado_cuenta(u), precio=pagos.precio(con), mp_auto=pagos.configurado(),
            mp_link=get_setting(con, "mp_link", ""), alias=get_setting(con, "alias_transferencia", ""),
            contacto=get_setting(con, "contact_email", ""), mp_status=u["mp_status"],
            pagos=[dict(r) for r in con.execute("SELECT monto, fuente, hasta, created_at FROM pagos WHERE user_id=? ORDER BY id DESC LIMIT 12", (u["id"],))])


@app.post("/api/cuenta/suscribir")
@login_required()
def suscribir(u):
    with db() as con:
        if pagos.configurado():
            link = pagos.crear_suscripcion(con, u, request.host_url)
            if not link:
                abort(502, "Mercado Pago no respondió. Probá de nuevo en un rato.")
            return jsonify(url=link)
        link = get_setting(con, "mp_link", "")
        if not link:
            abort(400, "Todavía no hay un medio de pago configurado. Escribinos y lo resolvemos.")
        return jsonify(url=link)


@app.post("/api/cuenta/cancelar")
@login_required()
def cancelar(u):
    with db() as con:
        if not pagos.cancelar_suscripcion(con, u):
            abort(400, "No se pudo cancelar desde acá. Podés hacerlo desde tu Mercado Pago, en «Suscripciones».")
    return jsonify(ok=True)


@app.post("/api/mp/webhook")
def mp_webhook():
    b = body()
    tipo = b.get("type") or b.get("topic") or request.args.get("type") or request.args.get("topic")
    data_id = (b.get("data") or {}).get("id") or request.args.get("data.id") or request.args.get("id")
    if not pagos.firma_valida(request.headers, request.args.get("data.id") or data_id):
        abort(401, "Firma inválida")
    with db() as con:
        res = pagos.procesar_aviso(con, tipo, data_id)
    log.info("Aviso de Mercado Pago %s %s: %s", tipo, data_id, res)
    return jsonify(ok=True, resultado=res)


# ------------------------------------------------------------------ recuperar contraseña
RESET_HORAS = 2


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def make_reset_link(con, uid):
    token = secrets.token_urlsafe(32)
    vence = (core.ahora() + timedelta(hours=RESET_HORAS)).isoformat(sep=" ", timespec="seconds")
    con.execute("INSERT INTO password_resets(token_hash, user_id, expires_at) VALUES(?,?,?)", (_hash(token), uid, vence))
    return f"{request.host_url.rstrip('/')}/#reset/{token}"


@app.post("/api/password/forgot")
def password_forgot():
    email = (body().get("email") or "").strip().lower()
    limitar("forgot-" + (request.remote_addr or "?"), 5, 3600)
    res = {"ok": True, "mail": mail.configured()}
    with db() as con:
        r = con.execute("SELECT id, name FROM users WHERE email=?", (email,)).fetchone()
        if r:
            link = make_reset_link(con, r["id"])
            sent = mail.send(email, "Recuperá tu contraseña de Cuentas Claras",
                             f"Hola, {r['name']}.\n\nPara elegir una contraseña nueva, entrá a este link (vale {RESET_HORAS} horas):\n\n{link}\n\n"
                             "Si no lo pediste vos, ignorá este mail: tu contraseña sigue igual.\n\nCuentas Claras")
            if not sent:
                log.info("Link para recuperar contraseña de %s: %s", email, link)
                if not ONLINE:
                    res["dev_link"] = link
    return jsonify(res)


@app.post("/api/password/reset")
def password_reset():
    b = body()
    pw = b.get("password") or ""
    if len(pw) < 8:
        abort(400, "La contraseña tiene que tener al menos 8 caracteres")
    with db() as con:
        r = con.execute("SELECT * FROM password_resets WHERE token_hash=? AND used=0 AND expires_at>?",
                        (_hash(str(b.get("token") or "")), core.stamp())).fetchone()
        if not r:
            abort(400, "El link venció o ya se usó. Pedí uno nuevo.")
        con.execute("UPDATE users SET pass_hash=? WHERE id=?", (generate_password_hash(pw), r["user_id"]))
        con.execute("UPDATE password_resets SET used=1 WHERE user_id=?", (r["user_id"],))
    start_session(r["user_id"])
    return jsonify(ok=True)


# ------------------------------------------------------------------ «Contanos qué mejorar»
@app.post("/api/feedback")
@login_required()
def send_feedback(u):
    b = body()
    text = (b.get("text") or "").strip()[:2000]
    if len(text) < 3:
        abort(400, "Contanos un poco más")
    kind = b.get("kind") if b.get("kind") in ("idea", "problema", "otro") else "otro"
    with db() as con:
        con.execute("INSERT INTO app_feedback(user_id, kind, text, created_at) VALUES(?,?,?,?)", (u["id"], kind, text, core.stamp()))
        for a in con.execute("SELECT id FROM users WHERE role='admin'").fetchall():
            push.notify(con, a["id"], "Alguien reportó un problema" if kind == "problema" else "Nuevo comentario", text[:120], "#admin", "feedback")
    return jsonify(ok=True)


# ------------------------------------------------------------------ administración
@app.get("/api/admin")
@login_required("admin")
def admin_panel(u):
    d = core.hoy()
    with db() as con:
        users = []
        for r in con.execute("SELECT * FROM users WHERE role='user' ORDER BY id DESC"):
            x = {k: r[k] for k in ("id", "email", "name", "created_at", "last_seen", "trial_ends", "paid_until", "mp_status")}
            x["cuenta"] = core.estado_cuenta(r, d)
            x["movs"] = con.execute("SELECT COUNT(*) FROM movs WHERE user_id=?", (r["id"],)).fetchone()[0]
            x["push"] = con.execute("SELECT COUNT(*) FROM push_subs WHERE user_id=?", (r["id"],)).fetchone()[0]
            users.append(x)
        hace7 = (d - timedelta(days=6)).isoformat()
        activos7 = con.execute("SELECT COUNT(DISTINCT user_id) FROM activity WHERE day>=?", (hace7,)).fetchone()[0]
        settings = {k: get_setting(con, k, "") for k in ("precio_mensual", "dias_prueba", "mp_link", "alias_transferencia", "contact_email")}
        feedback = [dict(r) for r in con.execute(
            "SELECT f.*, u.name AS user_name, u.email AS user_email FROM app_feedback f LEFT JOIN users u ON u.id=f.user_id "
            "ORDER BY (f.status='nuevo') DESC, f.id DESC LIMIT 50")]
        ingresos_mes = con.execute("SELECT COALESCE(SUM(monto),0) FROM pagos WHERE substr(created_at,1,7)=?", (core.mes_key(d),)).fetchone()[0]
    cuenta = defaultdict(int)
    for x in users:
        cuenta[x["cuenta"]["estado"]] += 1
    return jsonify(users=users, settings=settings, feedback=feedback, mp_auto=pagos.configurado(), mail=mail.configured(),
                   resumen={"total": len(users), "activos7": activos7, "prueba": cuenta["prueba"], "activa": cuenta["activa"],
                            "vencida": cuenta["vencida"], "cobrado_mes": ingresos_mes})


@app.post("/api/admin/users/<int:uid>/pago")
@login_required("admin")
def admin_pago(u, uid):
    b = body()
    with db() as con:
        if not con.execute("SELECT 1 FROM users WHERE id=?", (uid,)).fetchone():
            abort(404, "No existe esa cuenta")
        hasta = pagos.marcar_pago_manual(con, uid, int(num(b.get("meses", 1), "meses", 1, 24)),
                                         num(b["monto"], "monto", 0) if b.get("monto") not in (None, "") else None)
    return jsonify(ok=True, hasta=hasta)


@app.post("/api/admin/users/<int:uid>/prueba")
@login_required("admin")
def admin_prueba(u, uid):
    dias = int(num(body().get("dias", 7), "días", 1, 365))
    with db() as con:
        r = con.execute("SELECT trial_ends FROM users WHERE id=?", (uid,)).fetchone() or abort(404, "No existe esa cuenta")
        base = max(core.hoy() - timedelta(days=1), date.fromisoformat(r["trial_ends"]))
        con.execute("UPDATE users SET trial_ends=? WHERE id=?", ((base + timedelta(days=dias)).isoformat(), uid))
    return jsonify(ok=True)


@app.put("/api/admin/settings")
@login_required("admin")
def admin_settings(u):
    b = body()
    with db() as con:
        if "precio_mensual" in b:
            set_setting(con, "precio_mensual", str(int(num(b["precio_mensual"], "precio", 0, 1e8))))
        if "dias_prueba" in b:
            set_setting(con, "dias_prueba", str(int(num(b["dias_prueba"], "días de prueba", 1, 90))))
        if "mp_link" in b:
            link = str(b["mp_link"] or "").strip()
            if link and not link.startswith("https://"):
                abort(400, "El link de Mercado Pago tiene que empezar con https://")
            set_setting(con, "mp_link", link)
        for k in ("alias_transferencia", "contact_email"):
            if k in b:
                set_setting(con, k, str(b[k] or "").strip()[:120])
    return jsonify(ok=True)


@app.post("/api/admin/reset-link")
@login_required("admin")
def admin_reset_link(u):
    email = (body().get("email") or "").strip().lower()
    with db() as con:
        r = con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone() or abort(404, "No hay ninguna cuenta con ese mail")
        link = make_reset_link(con, r["id"])
    return jsonify(link=link, horas=RESET_HORAS)


@app.put("/api/admin/feedback/<int:fid>")
@login_required("admin")
def admin_feedback(u, fid):
    with db() as con:
        con.execute("UPDATE app_feedback SET status=? WHERE id=?", ("visto" if body().get("seen", True) else "nuevo", fid))
    return jsonify(ok=True)


# ------------------------------------------------------------------ armado
def create_app(seed_demo=None):
    init_db()
    with db() as con:
        app.secret_key = get_setting(con, "secret_key")
        push.vapid_public_key(con)
        if seed_demo if seed_demo is not None else DEMO:
            from .seed import seed_demo as _seed
            _seed(con)
        email = (os.environ.get("CUENTAS_ADMIN_EMAIL") or "").strip().lower()
        pw = os.environ.get("CUENTAS_ADMIN_PASSWORD") or ""
        if email and len(pw) >= 8:
            r = con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if r:
                con.execute("UPDATE users SET role='admin' WHERE id=?", (r["id"],))
            else:
                con.execute("INSERT INTO users(email, pass_hash, name, role, onboarded, created_at, trial_ends) VALUES(?,?,?,?,1,?,?)",
                            (email, generate_password_hash(pw), "Administración", "admin", core.stamp(), core.hoy().isoformat()))
    return app
