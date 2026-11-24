"""Cuentas del mes: saldo, gastos fijos, categorías, historial, racha y estado de la suscripción."""
import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Argentina/Buenos_Aires")

CATS = {
    "casa": "Casa", "super": "Alimentos", "servicios": "Servicios", "chicos": "Hijos y colegio",
    "salud": "Salud", "personal": "Cuidado personal", "transporte": "Transporte",
    "salidas": "Salidas y regalos", "otros": "Otros",
}
CATS_AHORRO = {"ahorro": "Ahorro", "inversion": "Inversión"}
TIPOS = ("egreso", "ingreso", "ahorro")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def ahora():
    """Fecha y hora de Argentina (el servidor puede estar en otro huso)."""
    return datetime.now(TZ).replace(tzinfo=None)


def hoy():
    return ahora().date()


def stamp():
    return ahora().isoformat(sep=" ", timespec="seconds")


def mes_key(d):
    return f"{d.year:04d}-{d.month:02d}"


def mes_nombre(key):
    return MESES[int(key[5:7]) - 1]


def mes_anterior(key):
    y, m = int(key[:4]), int(key[5:7])
    return f"{y - 1:04d}-12" if m == 1 else f"{y:04d}-{m - 1:02d}"


def dias_del_mes(d):
    return calendar.monthrange(d.year, d.month)[1]


def dia_real(dia, d):
    """Un vencimiento «día 31» en un mes de 30 días cae el último día."""
    return min(int(dia), dias_del_mes(d))


def sumar_mes(d):
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


# ------------------------------------------------------------------ suscripción
def estado_cuenta(u, d=None):
    d = d or hoy()
    if u["role"] == "admin" or u["email"].endswith("@cuentasclaras.app"):
        return {"estado": "activa", "dias": None, "hasta": None}
    if u["paid_until"] and date.fromisoformat(u["paid_until"]) >= d:
        return {"estado": "activa", "dias": (date.fromisoformat(u["paid_until"]) - d).days, "hasta": u["paid_until"]}
    fin = date.fromisoformat(u["trial_ends"])
    if fin >= d:
        return {"estado": "prueba", "dias": (fin - d).days + 1, "hasta": u["trial_ends"]}
    return {"estado": "vencida", "dias": 0, "hasta": u["paid_until"] or u["trial_ends"]}


def extender_pago(con, uid, d=None, meses=1):
    """Suma meses pagos desde lo que termine más tarde: hoy, lo ya pagado o la prueba gratis (no se pierden días)."""
    d = d or hoy()
    r = con.execute("SELECT paid_until, trial_ends FROM users WHERE id=?", (uid,)).fetchone()
    base = max([d - timedelta(days=1), date.fromisoformat(r["trial_ends"])] + ([date.fromisoformat(r["paid_until"])] if r["paid_until"] else []))
    for _ in range(meses):
        base = sumar_mes(base)
    con.execute("UPDATE users SET paid_until=? WHERE id=?", (base.isoformat(), uid))
    return base.isoformat()


# ------------------------------------------------------------------ tarjetas de crédito
def mes_mas(key, n):
    y, m = int(key[:4]), int(key[5:7]) - 1 + n
    return f"{y + m // 12:04d}-{m % 12 + 1:02d}"


def meses_entre(desde, hasta):
    return (int(hasta[:4]) - int(desde[:4])) * 12 + int(hasta[5:7]) - int(desde[5:7])


def primer_mes(fecha, cierre):
    """Mes en que se paga la primera cuota: lo comprado hasta el cierre entra en el resumen que se paga el mes que viene."""
    return mes_mas(mes_key(fecha), 1 if fecha.day <= dia_real(cierre, fecha) else 2)


def precio_final(precio, descuento=0, interes=0):
    return round(precio * (1 - descuento / 100) * (1 + interes / 100), 2)


def cuotas_mes(con, uid, key, tarjeta_id=None):
    """Cuotas de compras con tarjeta que se pagan en el mes `key`."""
    q = ("SELECT m.*, t.nombre AS tarjeta FROM movs m JOIN tarjetas t ON t.id=m.tarjeta_id "
         "WHERE m.user_id=? AND m.tipo='egreso' AND m.primer_mes<=?")
    args = [uid, key]
    if tarjeta_id:
        q += " AND m.tarjeta_id=?"
        args.append(tarjeta_id)
    out = []
    for r in con.execute(q, args):
        n = meses_entre(r["primer_mes"], key)
        if 0 <= n < r["cuotas"]:
            x = dict(r)
            x["cuota_n"], x["importe"] = n + 1, r["monto"] / r["cuotas"]
            x["ultimo_mes"] = mes_mas(r["primer_mes"], r["cuotas"] - 1)
            out.append(x)
    return out


def tarjetas_mes(con, uid, key, d=None):
    """Cada tarjeta con lo que hay que pagar en el mes `key` (o lo que se pagó, si ya se marcó)."""
    d = d or hoy()
    out = []
    for t in con.execute("SELECT * FROM tarjetas WHERE user_id=? ORDER BY nombre", (uid,)):
        x = dict(t)
        x["a_pagar"] = sum(c["importe"] for c in cuotas_mes(con, uid, key, t["id"]))
        p = con.execute("SELECT monto, pagado_el FROM tarjeta_pagos WHERE tarjeta_id=? AND mes=?", (t["id"], key)).fetchone()
        x["pagado"] = p is not None
        x["pagado_monto"] = p["monto"] if p else None
        x["vence_dia"] = dia_real(t["vence"], d) if key == mes_key(d) else t["vence"]
        x["vencido"] = not x["pagado"] and x["a_pagar"] > 0 and key == mes_key(d) and x["vence_dia"] < d.day
        x["total"] = x["pagado_monto"] if x["pagado"] else x["a_pagar"]
        out.append(x)
    return out


def compromisos(con, uid, d=None, meses=6):
    """Cuánto hay comprometido en cuotas en los próximos meses."""
    key = mes_key(d or hoy())
    return [{"mes": mes_mas(key, i), "total": sum(c["importe"] for c in cuotas_mes(con, uid, mes_mas(key, i)))} for i in range(meses)]


# ------------------------------------------------------------------ totales de un mes
def totales_mes(con, uid, key):
    """Ingresos, egresos (fijos + variables + tarjetas) y ahorro de un mes."""
    ing_fijos = con.execute(
        "SELECT COALESCE(SUM(COALESCE(c.monto, i.monto)),0) FROM ingresos i LEFT JOIN ingreso_cobros c ON c.ingreso_id=i.id AND c.mes=? "
        "WHERE i.user_id=?", (key, uid)).fetchone()[0]
    fijos = con.execute(
        "SELECT COALESCE(SUM(COALESCE(p.monto, f.monto)),0) FROM fijos f LEFT JOIN fijo_pagos p ON p.fijo_id=f.id AND p.mes=? WHERE f.user_id=?",
        (key, uid)).fetchone()[0]
    # lo comprado con tarjeta no cuenta el día de la compra: cuenta cada cuota en el mes en que se paga
    por_tipo = {r["tipo"]: r["t"] for r in con.execute(
        "SELECT tipo, SUM(monto) t FROM movs WHERE user_id=? AND substr(fecha,1,7)=? AND tarjeta_id IS NULL GROUP BY tipo", (uid, key))}
    tarjeta = sum(t["total"] for t in tarjetas_mes(con, uid, key))
    ing = ing_fijos + por_tipo.get("ingreso", 0)
    var = por_tipo.get("egreso", 0)
    ahorro = por_tipo.get("ahorro", 0)
    return {"ing": ing, "ing_fijos": ing_fijos, "ing_extra": por_tipo.get("ingreso", 0), "fij": fijos, "var": var, "tarjeta": tarjeta,
            "egr": fijos + var + tarjeta, "ahorro": ahorro, "saldo": ing - fijos - var - tarjeta - ahorro}


def cerrar_meses(con, uid, d=None):
    """Guarda la foto de cada mes terminado desde que se creó la cuenta. Devuelve los meses nuevos."""
    d = d or hoy()
    actual = mes_key(d)
    creado = con.execute("SELECT created_at FROM users WHERE id=?", (uid,)).fetchone()["created_at"][:7]
    primero = con.execute("SELECT MIN(substr(fecha,1,7)) FROM movs WHERE user_id=?", (uid,)).fetchone()[0]
    desde = min(creado, primero) if primero else creado
    hechos = {r[0] for r in con.execute("SELECT mes FROM cierres WHERE user_id=?", (uid,))}
    nuevos = []
    key = mes_anterior(actual)
    while key >= desde:
        if key not in hechos:
            t = totales_mes(con, uid, key)
            con.execute("INSERT INTO cierres(user_id, mes, ing, egr, ahorro) VALUES(?,?,?,?,?)", (uid, key, t["ing"], t["egr"], t["ahorro"]))
            nuevos.append(key)
        key = mes_anterior(key)
    return sorted(nuevos)


# ------------------------------------------------------------------ racha
def dias_activos(con, uid):
    q = ("SELECT fecha FROM movs WHERE user_id=? UNION SELECT fecha FROM checkins WHERE user_id=? "
         "UNION SELECT p.pagado_el FROM fijo_pagos p JOIN fijos f ON f.id=p.fijo_id WHERE f.user_id=?")
    return {r[0] for r in con.execute(q, (uid, uid, uid))}


def racha(con, uid, d=None):
    """Días seguidos anotando algo. Si hoy todavía no anotó, la racha sigue viva desde ayer."""
    d = d or hoy()
    activos = dias_activos(con, uid)
    hoy_ok = d.isoformat() in activos
    dia = d if hoy_ok else d - timedelta(days=1)
    n = 0
    while dia.isoformat() in activos:
        n += 1
        dia -= timedelta(days=1)
    ultimo = max(activos) if activos else None
    return {"dias": n, "hoy_ok": hoy_ok, "ultimo": ultimo}


# ------------------------------------------------------------------ todo lo de la pantalla de inicio
def fijos_del_mes(con, uid, d=None):
    d = d or hoy()
    key = mes_key(d)
    rows = con.execute(
        "SELECT f.*, p.monto AS pagado_monto, p.pagado_el FROM fijos f LEFT JOIN fijo_pagos p ON p.fijo_id=f.id AND p.mes=? "
        "WHERE f.user_id=? ORDER BY f.dia, f.nombre", (key, uid)).fetchall()
    out = []
    for r in rows:
        x = dict(r)
        x["pagado"] = r["pagado_monto"] is not None
        x["vence"] = dia_real(r["dia"], d)
        x["vencido"] = not x["pagado"] and x["vence"] < d.day
        out.append(x)
    return out


def resumen(con, uid, d=None):
    d = d or hoy()
    key = mes_key(d)
    cerrar_meses(con, uid, d)
    t = totales_mes(con, uid, key)
    dias_quedan = dias_del_mes(d) - d.day + 1
    fijos = fijos_del_mes(con, uid, d)
    cats = {}
    for f in fijos:
        cats[f["cat"]] = cats.get(f["cat"], 0) + (f["pagado_monto"] if f["pagado"] else f["monto"])
    for r in con.execute("SELECT cat, SUM(monto) t FROM movs WHERE user_id=? AND tipo='egreso' AND substr(fecha,1,7)=? AND tarjeta_id IS NULL "
                         "GROUP BY cat", (uid, key)):
        cats[r["cat"]] = cats.get(r["cat"], 0) + r["t"]
    for c in cuotas_mes(con, uid, key):
        cats[c["cat"]] = cats.get(c["cat"], 0) + c["importe"]
    hist = [dict(r) for r in con.execute("SELECT mes, ing, egr, ahorro FROM cierres WHERE user_id=? ORDER BY mes DESC LIMIT 5", (uid,))][::-1]
    hist.append({"mes": key, "ing": t["ing"], "egr": t["egr"], "ahorro": t["ahorro"], "actual": True})
    return {
        "mes": key, "mes_nombre": mes_nombre(key), "hoy": d.isoformat(), "dia": d.day, "dias_mes": dias_del_mes(d),
        "totales": t, "por_dia": t["saldo"] / dias_quedan if dias_quedan else t["saldo"],
        "fijos": fijos,
        "ingresos": [dict(r, cobrado=r["cobrado_monto"] is not None) for r in con.execute(
            "SELECT i.*, c.monto AS cobrado_monto FROM ingresos i LEFT JOIN ingreso_cobros c ON c.ingreso_id=i.id AND c.mes=? "
            "WHERE i.user_id=? ORDER BY i.dia, i.nombre", (key, uid))],
        "categorias": sorted(([k, v] for k, v in cats.items() if v > 0), key=lambda x: -x[1]),
        "tarjetas": tarjetas_mes(con, uid, key, d),
        "compromisos": compromisos(con, uid, d),
        "historial": hist,
        "racha": racha(con, uid, d),
    }


def frecuentes(con, uid, d=None, n=6):
    """Los gastos que más se repiten en los últimos 3 meses, con el último monto: para cargarlos de un toque."""
    desde = ((d or hoy()) - timedelta(days=90)).isoformat()
    rows = con.execute(
        "SELECT descr, cat, COUNT(*) veces, MAX(fecha) ultima FROM movs WHERE user_id=? AND tipo='egreso' AND fecha>=? AND descr<>'' "
        "AND cuotas=1 GROUP BY lower(descr), cat HAVING veces>=2 ORDER BY veces DESC, ultima DESC LIMIT ?", (uid, desde, n)).fetchall()
    out = []
    for r in rows:
        ult = con.execute("SELECT monto FROM movs WHERE user_id=? AND tipo='egreso' AND lower(descr)=lower(?) AND cat=? ORDER BY fecha DESC, id DESC LIMIT 1",
                          (uid, r["descr"], r["cat"])).fetchone()
        out.append({"descr": r["descr"], "cat": r["cat"], "monto": ult["monto"], "veces": r["veces"]})
    return out


def movimientos(con, uid, key=None, tipo=None, limit=400):
    q, args = "SELECT * FROM movs WHERE user_id=?", [uid]
    if key:
        q += " AND substr(fecha,1,7)=?"
        args.append(key)
    if tipo:
        q += " AND tipo=?"
        args.append(tipo)
    q += " ORDER BY fecha DESC, id DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in con.execute(q, args)]
