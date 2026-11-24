"""Reconocimientos: se ganan anotando seguido, cerrando meses en verde, ahorrando e invirtiendo.

Solo registran lo que la persona hizo; la app nunca recomienda en qué invertir.
"""
from collections import defaultdict

from . import core

LOGROS = [
    {"id": "primer_paso", "icono": "🌱", "titulo": "Primer paso", "desc": "Cargaste tu primer movimiento."},
    {"id": "cuentas_ordenadas", "icono": "🗂️", "titulo": "Cuentas ordenadas", "desc": "Cargaste tus ingresos y al menos 3 gastos fijos."},
    {"id": "racha_3", "icono": "🔥", "titulo": "Tres días seguidos", "desc": "Anotaste algo 3 días seguidos.", "meta": 3},
    {"id": "racha_7", "icono": "🔥", "titulo": "Una semana entera", "desc": "Anotaste algo 7 días seguidos.", "meta": 7},
    {"id": "racha_30", "icono": "🏆", "titulo": "Un mes sin fallar", "desc": "Anotaste algo 30 días seguidos.", "meta": 30},
    {"id": "al_dia", "icono": "✅", "titulo": "Todo al día", "desc": "Pagaste todos tus gastos fijos del mes."},
    {"id": "constancia", "icono": "📅", "titulo": "Mes completo", "desc": "Anotaste en al menos 20 días distintos de un mes.", "meta": 20},
    {"id": "primer_ahorro", "icono": "🐷", "titulo": "Primer ahorro", "desc": "Apartaste plata para ahorrar por primera vez."},
    {"id": "ahorro_10", "icono": "⭐", "titulo": "Ahorro del 10%", "desc": "En un mes ahorraste al menos el 10% de tus ingresos."},
    {"id": "ahorro_20", "icono": "🌟", "titulo": "Ahorro del 20%", "desc": "En un mes ahorraste al menos el 20% de tus ingresos."},
    {"id": "meta_cumplida", "icono": "🎯", "titulo": "Meta cumplida", "desc": "Llegaste a tu meta de ahorro del mes."},
    {"id": "inversora", "icono": "📈", "titulo": "Primera inversión", "desc": "Registraste tu primera inversión."},
    {"id": "mes_verde", "icono": "💚", "titulo": "Mes en verde", "desc": "Cerraste un mes con saldo a favor."},
    {"id": "tres_verdes", "icono": "🌳", "titulo": "Tres meses en verde", "desc": "Cerraste 3 meses con saldo a favor.", "meta": 3},
    {"id": "ahorro_constante", "icono": "💎", "titulo": "Ahorro constante", "desc": "Ahorraste en 3 meses distintos.", "meta": 3},
]
POR_ID = {x["id"]: x for x in LOGROS}
NIVELES = [(0, "Arrancando"), (2, "En camino"), (5, "Ordenada"), (9, "Experta"), (13, "Maestra de las cuentas")]


def nivel(n):
    actual, sig = NIVELES[0], None
    for i, (desde, nombre) in enumerate(NIVELES):
        if n >= desde:
            actual = (desde, nombre)
            sig = NIVELES[i + 1] if i + 1 < len(NIVELES) else None
    return {"numero": NIVELES.index(actual) + 1, "nombre": actual[1],
            "siguiente": sig[1] if sig else None, "faltan": (sig[0] - n) if sig else 0}


def _contexto(con, uid, d):
    key = core.mes_key(d)
    r = core.racha(con, uid, d)
    ing_fijos = con.execute("SELECT COALESCE(SUM(monto),0) FROM ingresos WHERE user_id=?", (uid,)).fetchone()[0]
    por_mes = defaultdict(lambda: {"ingreso": 0, "ahorro": 0})
    inversion = False
    for m in con.execute("SELECT tipo, cat, monto, substr(fecha,1,7) mes FROM movs WHERE user_id=? AND tipo IN ('ingreso','ahorro')", (uid,)):
        por_mes[m["mes"]][m["tipo"]] += m["monto"]
        inversion = inversion or (m["tipo"] == "ahorro" and m["cat"] == "inversion")
    pct_ahorro = []
    for mes, v in por_mes.items():
        ingreso = ing_fijos + v["ingreso"]
        if v["ahorro"] > 0 and ingreso > 0:
            pct_ahorro.append(v["ahorro"] / ingreso)
    fijos = core.fijos_del_mes(con, uid, d)
    dias_mes = defaultdict(int)
    for x in core.dias_activos(con, uid):
        dias_mes[x[:7]] += 1
    verdes = con.execute("SELECT COUNT(*) FROM cierres WHERE user_id=? AND ing>0 AND ing-egr-ahorro>=0", (uid,)).fetchone()[0]
    meta = con.execute("SELECT meta_ahorro FROM users WHERE id=?", (uid,)).fetchone()["meta_ahorro"]
    return {
        "movs": con.execute("SELECT COUNT(*) FROM movs WHERE user_id=?", (uid,)).fetchone()[0]
        + con.execute("SELECT COUNT(*) FROM fijo_pagos p JOIN fijos f ON f.id=p.fijo_id WHERE f.user_id=?", (uid,)).fetchone()[0],
        "n_ingresos": con.execute("SELECT COUNT(*) FROM ingresos WHERE user_id=?", (uid,)).fetchone()[0],
        "n_fijos": len(fijos), "fijos_pagados": sum(f["pagado"] for f in fijos),
        "racha": r["dias"], "max_dias_mes": max(dias_mes.values(), default=0),
        "ahorros": sum(1 for v in por_mes.values() if v["ahorro"] > 0),
        "max_pct_ahorro": max(pct_ahorro, default=0), "inversion": inversion,
        "verdes": verdes, "meta": meta, "ahorro_mes": por_mes[key]["ahorro"] if key in por_mes else 0,
    }


def _cumple(lid, c):
    return {
        "primer_paso": c["movs"] >= 1,
        "cuentas_ordenadas": c["n_ingresos"] >= 1 and c["n_fijos"] >= 3,
        "racha_3": c["racha"] >= 3, "racha_7": c["racha"] >= 7, "racha_30": c["racha"] >= 30,
        "al_dia": c["n_fijos"] >= 3 and c["fijos_pagados"] == c["n_fijos"],
        "constancia": c["max_dias_mes"] >= 20,
        "primer_ahorro": c["ahorros"] >= 1,
        "ahorro_10": c["max_pct_ahorro"] >= 0.10, "ahorro_20": c["max_pct_ahorro"] >= 0.20,
        "meta_cumplida": bool(c["meta"]) and c["ahorro_mes"] >= c["meta"],
        "inversora": c["inversion"],
        "mes_verde": c["verdes"] >= 1, "tres_verdes": c["verdes"] >= 3,
        "ahorro_constante": c["ahorros"] >= 3,
    }[lid]


def _progreso(lid, c):
    return {"racha_3": c["racha"], "racha_7": c["racha"], "racha_30": c["racha"], "constancia": c["max_dias_mes"],
            "tres_verdes": c["verdes"], "ahorro_constante": c["ahorros"]}.get(lid)


def evaluar(con, uid, d=None, avisar=True):
    """Revisa qué logros nuevos ganó. Devuelve la lista de los nuevos (y avisa al celular)."""
    from .push import notify
    d = d or core.hoy()
    tiene = {r[0] for r in con.execute("SELECT logro_id FROM logros WHERE user_id=?", (uid,))}
    c = _contexto(con, uid, d)
    nuevos = []
    for x in LOGROS:
        if x["id"] not in tiene and _cumple(x["id"], c):
            con.execute("INSERT INTO logros(user_id, logro_id, fecha) VALUES(?,?,?)", (uid, x["id"], d.isoformat()))
            nuevos.append(x)
    if avisar and nuevos:
        x = nuevos[0]
        titulo = f"{x['icono']} ¡Nuevo logro: {x['titulo']}!" if len(nuevos) == 1 else f"🏅 ¡Ganaste {len(nuevos)} logros nuevos!"
        notify(con, uid, titulo, x["desc"] if len(nuevos) == 1 else ", ".join(n["titulo"] for n in nuevos), "#logros", "logro")
    return nuevos


def listado(con, uid, d=None):
    d = d or core.hoy()
    tiene = {r["logro_id"]: r["fecha"] for r in con.execute("SELECT logro_id, fecha FROM logros WHERE user_id=?", (uid,))}
    c = _contexto(con, uid, d)
    items = []
    for x in LOGROS:
        it = dict(x, ganado=x["id"] in tiene, fecha=tiene.get(x["id"]))
        p = _progreso(x["id"], c)
        if p is not None and not it["ganado"]:
            it["progreso"] = min(p, x["meta"])
        items.append(it)
    return {"items": items, "ganados": len(tiene), "total": len(LOGROS), "nivel": nivel(len(tiene)), "racha": c["racha"]}
