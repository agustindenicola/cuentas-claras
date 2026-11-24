"""Tareas automáticas (cada minuto, en hora de Argentina): recordatorios, resumen del mes, aviso de fin de prueba y copias."""
import logging
import threading
import time
from datetime import date, timedelta

from . import core, logros
from .db import backup, db
from .push import notify

log = logging.getLogger(__name__)

HORA_MANANA = 9       # vencimientos y cobros
HORA_CUENTA = 10      # resumen del mes y avisos de la prueba

RECORDATORIOS = [
    ("¿Anotaste los gastos de hoy?", "Un minuto ahora y tus cuentas quedan claras."),
    ("Tus cuentas te esperan", "¿Hubo algún gasto hoy? Anotalo antes de que se olvide."),
    ("Cerrá el día en orden", "Cargá lo que gastaste hoy. Si no gastaste nada, tocá «Hoy no gasté»."),
    ("Un ratito para vos", "Anotá los gastos del día y mirá cómo viene el mes."),
]


def plata(n):
    return "$ " + f"{round(n):,}".replace(",", ".")


def _ya(con, uid, clave):
    """True si ya se mandó; si no, lo marca como mandado."""
    if con.execute("SELECT 1 FROM avisos_enviados WHERE user_id=? AND clave=?", (uid, clave)).fetchone():
        return True
    con.execute("INSERT INTO avisos_enviados(user_id, clave) VALUES(?,?)", (uid, clave))
    return False


def recordatorio_diario(con, u, now):
    if not u["av_diario"] or now.hour != u["notify_hour"]:
        return False
    d = now.date()
    r = core.racha(con, u["id"], d)
    if r["hoy_ok"] or _ya(con, u["id"], f"diario-{d}"):
        return False
    if r["dias"] >= 2:
        titulo, cuerpo = f"🔥 Llevás {r['dias']} días seguidos", "Anotá lo de hoy para no cortar la racha."
    elif r["ultimo"] and (d - date.fromisoformat(r["ultimo"])).days >= 3:
        titulo, cuerpo = "Hace unos días que no anotás nada", "No pasa nada: retomá hoy con lo que te acuerdes."
    else:
        titulo, cuerpo = RECORDATORIOS[d.toordinal() % len(RECORDATORIOS)]
    # botones en la notificación (Android y compu): marcar el día sin abrir la app, o ir directo a cargar
    notify(con, u["id"], titulo, cuerpo, "#cargar", "diario",
           actions=[{"action": "nogaste", "title": "🙌 Hoy no gasté"}, {"action": "anotar", "title": "✍️ Anotar un gasto"}])
    return True


def vencimientos(con, u, now):
    if not u["av_vencimientos"] or now.hour < HORA_MANANA or now.hour >= 22:
        return False
    d = now.date()
    mañana, ayer = d + timedelta(days=1), d - timedelta(days=1)
    lineas = []
    for f in core.fijos_del_mes(con, u["id"], d):
        if f["pagado"]:
            continue
        if f["vence"] == d.day:
            cuando = "hoy"
        elif mañana.month == d.month and f["vence"] == mañana.day:
            cuando = "mañana"
        elif f["vence"] == ayer.day and ayer.month == d.month:
            cuando = "ayer"
        else:
            continue
        if not _ya(con, u["id"], f"venc-{f['id']}-{d}"):
            lineas.append((cuando, f))
    for t in core.tarjetas_mes(con, u["id"], core.mes_key(d), d):
        if t["pagado"] or t["a_pagar"] <= 0:
            continue
        cuando = ("hoy" if t["vence_dia"] == d.day else "mañana" if mañana.month == d.month and t["vence_dia"] == mañana.day
                  else "ayer" if ayer.month == d.month and t["vence_dia"] == ayer.day else None)
        if cuando and not _ya(con, u["id"], f"venc-tarjeta-{t['id']}-{d}"):
            lineas.append((cuando, {"nombre": "la tarjeta " + t["nombre"], "monto": t["a_pagar"]}))
    # el último día del mes avisa lo que vence el 1.° del mes que viene
    if mañana.month != d.month:
        for f in con.execute("SELECT * FROM fijos WHERE user_id=? AND dia=1", (u["id"],)).fetchall():
            if not _ya(con, u["id"], f"venc-{f['id']}-{d}"):
                lineas.append(("mañana", dict(f)))
    if not lineas:
        return False
    if len(lineas) == 1:
        cuando, f = lineas[0]
        titulo = {"hoy": f"Hoy vence {f['nombre']}", "mañana": f"Mañana vence {f['nombre']}", "ayer": f"{f['nombre']} venció ayer"}[cuando]
        titulo = titulo[0].upper() + titulo[1:]
        cuerpo = f"{plata(f['monto'])}. " + ("¿Ya lo pagaste? Marcalo en la app." if cuando == "ayer" else "Cuando lo pagues, marcalo en la app.")
    else:
        titulo = f"Tenés {len(lineas)} vencimientos"
        cuerpo = " · ".join(f"{f['nombre']} ({cuando})" for cuando, f in lineas)
    notify(con, u["id"], titulo, cuerpo, "#fijos", "vencimiento")
    return True


def cobros(con, u, now):
    if not u["av_vencimientos"] or now.hour < HORA_MANANA or now.hour >= 22:
        return False
    d = now.date()
    hoy_cobra = [i for i in con.execute("SELECT * FROM ingresos WHERE user_id=?", (u["id"],)) if core.dia_real(i["dia"], d) == d.day]
    if not hoy_cobra or _ya(con, u["id"], f"cobro-{d}"):
        return False
    nombres = " y ".join(i["nombre"] for i in hoy_cobra)
    notify(con, u["id"], f"Hoy cobrás: {nombres}",
           "Si apartás una parte para ahorrar apenas cobrás, es mucho más fácil llegar a fin de mes.", "#cargar-ahorro", "cobro")
    return True


def resumen_mensual(con, u, now):
    d = now.date()
    if d.day != 1 or now.hour < HORA_CUENTA or not u["av_resumen"]:
        return False
    core.cerrar_meses(con, u["id"], d)
    prev = core.mes_anterior(core.mes_key(d))
    c = con.execute("SELECT * FROM cierres WHERE user_id=? AND mes=?", (u["id"], prev)).fetchone()
    if not c or c["ing"] <= 0 or _ya(con, u["id"], f"resumen-{prev}"):
        return False
    saldo = c["ing"] - c["egr"] - c["ahorro"]
    nombre = core.mes_nombre(prev).capitalize()
    if saldo >= 0:
        titulo = f"💚 {nombre} cerró en verde"
        cuerpo = f"Te quedó un saldo a favor de {plata(saldo)}" + (f" y ahorraste {plata(c['ahorro'])}." if c["ahorro"] else ".")
    else:
        titulo = f"Así cerró {nombre}"
        cuerpo = f"Los egresos superaron a los ingresos por {plata(-saldo)}. Mirá en qué categoría se fue más."
    notify(con, u["id"], titulo, cuerpo, "#inicio", "resumen")
    logros.evaluar(con, u["id"], d)
    return True


def avisos_cuenta(con, u, now):
    if now.hour < HORA_CUENTA:
        return False
    d = now.date()
    est = core.estado_cuenta(u, d)
    if est["estado"] == "prueba" and est["dias"] in (3, 1):
        clave = f"prueba-{est['dias']}"
        if _ya(con, u["id"], clave):
            return False
        titulo = "Te quedan 3 días de prueba" if est["dias"] == 3 else "Hoy es el último día de prueba"
        notify(con, u["id"], titulo, "Suscribite para seguir anotando sin cortes. Tus datos quedan guardados igual.", "#cuenta", "prueba")
        return True
    if est["estado"] == "vencida" and not _ya(con, u["id"], f"vencida-{est['hasta']}"):
        notify(con, u["id"], "Tu acceso está en pausa", "Tus datos siguen guardados. Suscribite para volver a cargar movimientos.", "#cuenta", "prueba")
        return True
    return False


def tick(now=None):
    now = now or core.ahora()
    with db() as con:
        users = con.execute("SELECT * FROM users WHERE role='user' AND email NOT LIKE '%@cuentasclaras.app'").fetchall()
        for u in users:
            for tarea in (recordatorio_diario, vencimientos, cobros, resumen_mensual, avisos_cuenta):
                try:
                    tarea(con, u, now)
                except Exception:  # noqa: BLE001
                    log.exception("Aviso %s para %s", tarea.__name__, u["id"])
        if now.hour == 4:
            try:
                from .seed import seed_demo
                seed_demo(con, force_daily=now.date())
            except Exception:  # noqa: BLE001
                log.exception("Datos de ejemplo")
    if now.hour == 3:
        try:
            enviar_copia(backup(today=now.date()), now.date())
        except Exception:  # noqa: BLE001
            log.exception("Copia de seguridad")


def enviar_copia(ruta, d):
    """Manda la copia del día por mail (comprimida), así queda guardada fuera del servidor. Una vez por día."""
    import gzip
    import os

    from . import mail
    destino = os.environ.get("CUENTAS_BACKUP_EMAIL") or os.environ.get("CUENTAS_ADMIN_EMAIL")
    marca = ruta + ".enviada"
    if not (destino and mail.configured()) or os.path.exists(marca):
        return False
    with open(ruta, "rb") as f:
        datos = gzip.compress(f.read())
    ok = mail.send(destino, f"Copia de Cuentas Claras {d.isoformat()}",
                   "Copia de seguridad diaria de la base de datos. Guardala: sirve para recuperar todo si pasa algo con el servidor.",
                   adjunto=(os.path.basename(ruta) + ".gz", datos))
    if ok:
        open(marca, "w").close()
    return ok


def start():
    def loop():
        while True:
            tick()
            time.sleep(60)
    threading.Thread(target=loop, daemon=True, name="tareas").start()
