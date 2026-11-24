"""Cuenta de ejemplo «Carolina» con 6 meses de movimientos, para mostrar la app.

Entra con el botón «Ver un ejemplo» (demo@cuentasclaras.app). Se vuelve a armar todas las noches.
"""
import random
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from . import core, logros
from .db import get_setting, set_setting

DEMO_EMAIL = "demo@cuentasclaras.app"
DEMO_PASS = "demo1234"

INGRESOS = [("Sueldo", 1800000, 1), ("Trabajo por mi cuenta", 420000, 15)]
FIJOS = [
    ("Alquiler", "casa", 520000, 5), ("Prepaga u obra social", "salud", 260000, 10), ("Colegio de los chicos", "chicos", 310000, 10),
    ("Luz", "servicios", 42000, 12), ("Gas", "servicios", 19000, 15), ("Teléfono e internet", "servicios", 34000, 22),
    ("Celular", "servicios", 18000, 8), ("Clases o gimnasio", "personal", 45000, 3), ("Actividades de los chicos", "chicos", 60000, 7),
    ("Seguro del auto", "transporte", 68000, 18), ("Cable o streaming", "servicios", 14000, 25),
]
VARIABLES = [
    ("Supermercado", "super", 38000, 65000), ("Verdulería", "super", 6000, 12000), ("Carnicería", "super", 15000, 30000),
    ("Nafta", "transporte", 30000, 50000), ("Farmacia", "salud", 6000, 18000), ("Café con amigas", "salidas", 9000, 16000),
    ("Kiosco", "otros", 3000, 8000), ("Útiles del colegio", "chicos", 8000, 22000), ("Peluquería", "personal", 18000, 28000),
    ("Regalo de cumpleaños", "salidas", 15000, 30000), ("Cena afuera", "salidas", 25000, 45000),
]


def seed_demo(con, force_daily=None):
    existe = con.execute("SELECT id FROM users WHERE email=?", (DEMO_EMAIL,)).fetchone()
    if existe and not force_daily:
        return existe["id"]
    if force_daily and get_setting(con, "demo_seed_day") == force_daily.isoformat():
        return existe["id"] if existe else None
    if existe:
        con.execute("DELETE FROM users WHERE id=?", (existe["id"],))
    rnd = random.Random(7)
    d = core.hoy()
    inicio = date(d.year, d.month, 1)
    for _ in range(5):
        inicio = date(inicio.year - (inicio.month == 1), 12 if inicio.month == 1 else inicio.month - 1, 1)
    uid = con.execute(
        "INSERT INTO users(email, pass_hash, name, created_at, accepted_terms, onboarded, trial_ends, notify_hour, meta_ahorro) "
        "VALUES(?,?,?,?,?,1,?,21,150000)",
        (DEMO_EMAIL, generate_password_hash(DEMO_PASS), "Carolina", inicio.isoformat() + " 10:00:00", inicio.isoformat(),
         (d + timedelta(days=3650)).isoformat())).lastrowid
    for n, m, dia in INGRESOS:
        con.execute("INSERT INTO ingresos(user_id, nombre, monto, dia, created_at) VALUES(?,?,?,?,?)", (uid, n, m, dia, core.stamp()))
    fids = []
    for n, c, m, dia in FIJOS:
        fids.append((con.execute("INSERT INTO fijos(user_id, nombre, cat, monto, dia, created_at) VALUES(?,?,?,?,?,?)",
                                 (uid, n, c, m, dia, core.stamp())).lastrowid, n, m, dia))

    visa = con.execute("INSERT INTO tarjetas(user_id, nombre, cierre, vence, created_at) VALUES(?,?,?,?,?)",
                       (uid, "Visa", 24, 5, core.stamp())).lastrowid

    def compra(precio, descr, cat, f, cuotas=1, interes=0, descuento=0):
        con.execute("INSERT INTO movs(user_id, tipo, cat, monto, descr, fecha, created_at, tarjeta_id, cuotas, primer_mes, precio, descuento, interes) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (uid, "egreso", cat, core.precio_final(precio, descuento, interes), descr, f.isoformat(), core.stamp(), visa, cuotas,
                     core.primer_mes(f, 24), precio if (interes or descuento) else None, descuento, interes))

    def mov(tipo, cat, monto, descr, f):
        con.execute("INSERT INTO movs(user_id, tipo, cat, monto, descr, fecha, created_at) VALUES(?,?,?,?,?,?,?)",
                    (uid, tipo, cat, round(monto, -2), descr, f.isoformat(), core.stamp()))

    mes = inicio
    i = 0
    while mes <= d:
        actual = core.mes_key(mes) == core.mes_key(d)
        ultimo = d.day - 1 if actual else core.dias_del_mes(mes)
        key = core.mes_key(mes)
        # gastos fijos pagados (la luz y el gas cambian un poco cada mes)
        for fid, n, m, dia in fids:
            if actual and (dia >= d.day or n == "Luz"):
                continue
            monto = m * (1 + rnd.uniform(-0.12, 0.15)) if n in ("Luz", "Gas") else m
            pagado = date(mes.year, mes.month, max(1, min(dia - rnd.randint(0, 2), core.dias_del_mes(mes))))
            con.execute("INSERT INTO fijo_pagos(fijo_id, mes, monto, pagado_el) VALUES(?,?,?,?)", (fid, key, round(monto, -2), pagado.isoformat()))
        # gastos del día a día
        extra = 1.35 if i == 2 else 1.0     # un mes con más gastos (vacaciones de invierno)
        for dia in range(1, ultimo + 1):
            veces = rnd.choice([0, 1, 1, 1])
            if actual and dia >= ultimo - 5:
                veces = max(veces, 1)      # racha de los últimos días
            for _ in range(veces):
                n, c, lo, hi = rnd.choice(VARIABLES)
                mov("egreso", c, rnd.uniform(lo, hi) * extra, n, date(mes.year, mes.month, dia))
        if i == 2:
            mov("egreso", "salidas", 380000, "Escapada de vacaciones", date(mes.year, mes.month, min(18, ultimo or 1)))
        if i in (1, 3, 4) and ultimo >= 2:
            mov("ahorro", "ahorro", 150000, "Separé al cobrar", date(mes.year, mes.month, 2))
        if i == 4 and ultimo >= 16:
            mov("ahorro", "inversion", 100000, "Plazo fijo", date(mes.year, mes.month, 16))
        if i == 1 and ultimo >= 10:
            compra(840000, "Heladera", "casa", date(mes.year, mes.month, 10), cuotas=12)
        if i == 4 and ultimo >= 20:
            compra(90000, "Zapatillas de los chicos", "chicos", date(mes.year, mes.month, 20), cuotas=3, interes=10)
        if actual and ultimo >= 3:
            compra(60000, "Anteojos", "salud", date(mes.year, mes.month, 3), cuotas=6, descuento=20)
        if i == 3 and ultimo >= 20:
            mov("ingreso", "extra", 90000, "Venta de ropa usada", date(mes.year, mes.month, 20))
        mes = date(mes.year + (mes.month == 12), 1 if mes.month == 12 else mes.month + 1, 1)
        i += 1
    if d.day > 5:   # el resumen de la Visa de este mes ya se pagó
        key = core.mes_key(d)
        total = sum(c["importe"] for c in core.cuotas_mes(con, uid, key, visa))
        if total:
            con.execute("INSERT INTO tarjeta_pagos(tarjeta_id, mes, monto, pagado_el) VALUES(?,?,?,?)",
                        (visa, key, total, date(d.year, d.month, 5).isoformat()))
    core.cerrar_meses(con, uid, d)
    logros.evaluar(con, uid, d, avisar=False)
    con.execute("UPDATE logros SET visto=1 WHERE user_id=?", (uid,))
    set_setting(con, "demo_seed_day", d.isoformat())
    return uid
