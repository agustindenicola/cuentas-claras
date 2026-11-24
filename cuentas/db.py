"""Base de datos SQLite: esquema, conexión y configuración guardada."""
import os
import secrets
import sqlite3
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("CUENTAS_DATA") or os.path.join(BASE_DIR, "datos")
DB_PATH = os.path.join(DATA_DIR, "cuentas.db")
BACKUP_DIR = os.path.join(DATA_DIR, "copias")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  pass_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',          -- user | admin
  created_at TEXT NOT NULL,
  accepted_terms TEXT,
  last_seen TEXT,
  onboarded INTEGER NOT NULL DEFAULT 0,
  trial_ends TEXT NOT NULL,                   -- último día de la prueba gratis (YYYY-MM-DD)
  paid_until TEXT,                            -- último día pagado (YYYY-MM-DD)
  mp_preapproval_id TEXT,                     -- suscripción de Mercado Pago
  mp_status TEXT,
  notify_hour INTEGER NOT NULL DEFAULT 21,    -- hora del recordatorio diario
  av_diario INTEGER NOT NULL DEFAULT 1,
  av_vencimientos INTEGER NOT NULL DEFAULT 1,
  av_resumen INTEGER NOT NULL DEFAULT 1,
  meta_ahorro REAL,                           -- meta de ahorro mensual
  grande INTEGER NOT NULL DEFAULT 0           -- letra más grande
);
CREATE TABLE IF NOT EXISTS ingresos (           -- ingresos que se repiten todos los meses
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  nombre TEXT NOT NULL,
  monto REAL NOT NULL,
  dia INTEGER NOT NULL,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS fijos (              -- gastos fijos mensuales
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  nombre TEXT NOT NULL,
  cat TEXT NOT NULL DEFAULT 'servicios',
  monto REAL NOT NULL,                        -- monto habitual
  dia INTEGER NOT NULL,                       -- día de vencimiento
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS fijo_pagos (         -- qué fijos se pagaron cada mes y por cuánto
  fijo_id INTEGER NOT NULL REFERENCES fijos(id) ON DELETE CASCADE,
  mes TEXT NOT NULL,                          -- YYYY-MM
  monto REAL NOT NULL,
  pagado_el TEXT NOT NULL,                    -- fecha (YYYY-MM-DD)
  PRIMARY KEY (fijo_id, mes)
);
CREATE TABLE IF NOT EXISTS movs (               -- egresos variables, ingresos extra y ahorros
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tipo TEXT NOT NULL,                         -- egreso | ingreso | ahorro
  cat TEXT NOT NULL,
  monto REAL NOT NULL,
  descr TEXT NOT NULL DEFAULT '',
  fecha TEXT NOT NULL,                        -- YYYY-MM-DD
  created_at TEXT
);
CREATE INDEX IF NOT EXISTS movs_user_fecha ON movs(user_id, fecha);
CREATE TABLE IF NOT EXISTS ingreso_cobros (     -- lo que se cobró de verdad cada mes (si cambia mes a mes)
  ingreso_id INTEGER NOT NULL REFERENCES ingresos(id) ON DELETE CASCADE,
  mes TEXT NOT NULL,
  monto REAL NOT NULL,
  cobrado_el TEXT NOT NULL,
  PRIMARY KEY (ingreso_id, mes)
);
CREATE TABLE IF NOT EXISTS tarjetas (           -- tarjetas de crédito
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  nombre TEXT NOT NULL,
  cierre INTEGER NOT NULL,                    -- día de cierre del resumen
  vence INTEGER NOT NULL,                     -- día de vencimiento (del mes siguiente al cierre)
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS tarjeta_pagos (      -- resúmenes pagados (puede ser otro monto: impuestos, intereses)
  tarjeta_id INTEGER NOT NULL REFERENCES tarjetas(id) ON DELETE CASCADE,
  mes TEXT NOT NULL,                          -- mes en que se paga (YYYY-MM)
  monto REAL NOT NULL,
  pagado_el TEXT NOT NULL,
  PRIMARY KEY (tarjeta_id, mes)
);
CREATE TABLE IF NOT EXISTS checkins (           -- «hoy no gasté nada»: cuenta para la racha
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  fecha TEXT NOT NULL,
  PRIMARY KEY (user_id, fecha)
);
CREATE TABLE IF NOT EXISTS cierres (            -- foto de cada mes terminado (para el gráfico por mes)
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  mes TEXT NOT NULL,
  ing REAL NOT NULL,
  egr REAL NOT NULL,
  ahorro REAL NOT NULL,
  PRIMARY KEY (user_id, mes)
);
CREATE TABLE IF NOT EXISTS logros (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  logro_id TEXT NOT NULL,
  fecha TEXT NOT NULL,
  visto INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, logro_id)
);
CREATE TABLE IF NOT EXISTS pagos (              -- pagos de la suscripción
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  monto REAL,
  fuente TEXT NOT NULL,                       -- manual | mercadopago
  ref TEXT UNIQUE,
  hasta TEXT,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  url TEXT,
  kind TEXT,
  read INTEGER NOT NULL DEFAULT 0,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS avisos_enviados (    -- para no mandar dos veces el mismo recordatorio
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  clave TEXT NOT NULL,
  PRIMARY KEY (user_id, clave)
);
CREATE TABLE IF NOT EXISTS push_subs (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  endpoint TEXT UNIQUE NOT NULL,
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS activity (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  day TEXT NOT NULL,
  PRIMARY KEY (user_id, day)
);
CREATE TABLE IF NOT EXISTS app_feedback (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  kind TEXT NOT NULL DEFAULT 'idea',
  text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'nuevo',
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS password_resets (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TEXT NOT NULL,
  used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""

DEFAULT_SETTINGS = {
    "precio_mensual": "4000",          # lo cambia el admin desde el panel
    "dias_prueba": "14",
    "mp_link": "",                     # link de suscripción armado a mano en Mercado Pago (si no hay integración)
    "alias_transferencia": "",         # alias o CBU para pagar por transferencia
    "contact_email": "",
}

# (tabla, columna, tipo) agregadas después de la primera versión: se suman solas a bases existentes
MIGRATIONS = [
    ("movs", "tarjeta_id", "INTEGER REFERENCES tarjetas(id)"),   # compra con tarjeta de crédito
    ("movs", "cuotas", "INTEGER NOT NULL DEFAULT 1"),
    ("movs", "primer_mes", "TEXT"),                                # mes en que se paga la primera cuota
    ("movs", "precio", "REAL"),                                    # precio antes de descuento o recargo
    ("movs", "descuento", "REAL NOT NULL DEFAULT 0"),              # % de descuento o reintegro
    ("movs", "interes", "REAL NOT NULL DEFAULT 0"),                # % de interés o recargo
]


def connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    return con


@contextmanager
def db():
    con = connect()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    with db() as con:
        con.executescript(SCHEMA)
        for table, col, typ in MIGRATIONS:
            if col not in {r[1] for r in con.execute(f"PRAGMA table_info({table})")}:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        for k, v in DEFAULT_SETTINGS.items():
            con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('secret_key',?)", (secrets.token_hex(32),))


def get_setting(con, key, default=None):
    r = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r and r["value"] is not None else default


def set_setting(con, key, value):
    con.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def backup(keep=14, today=None):
    """Copia diaria de la base (se guardan las últimas `keep`)."""
    from datetime import date
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dest = os.path.join(BACKUP_DIR, f"cuentas-{(today or date.today()).isoformat()}.db")
    if os.path.exists(dest):
        return dest
    src = connect()
    try:
        out = sqlite3.connect(dest)
        src.backup(out)
        out.close()
    finally:
        src.close()
    files = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("cuentas-") and f.endswith(".db"))
    for f in files[:-keep]:
        os.remove(os.path.join(BACKUP_DIR, f))
    return dest
