"""Arranca Cuentas Claras.

    python run.py                      # con la cuenta de ejemplo (Carolina)
    python run.py --sin-demo           # sin cuenta de ejemplo
    python run.py crear-admin MAIL     # crea o convierte una cuenta en administradora
    python run.py avisos               # corre una vez la revisión de recordatorios
"""
import getpass
import logging
import os
import sys


def main():
    args = sys.argv[1:]
    if "--sin-demo" in args:
        os.environ["CUENTAS_DEMO"] = "0"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from cuentas import core, scheduler
    from cuentas.db import db
    from cuentas.server import create_app

    if args[:1] == ["crear-admin"]:
        from werkzeug.security import generate_password_hash
        create_app(seed_demo=False)
        email = args[1].strip().lower()
        with db() as con:
            r = con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if r:
                con.execute("UPDATE users SET role='admin' WHERE id=?", (r["id"],))
            else:
                pw = getpass.getpass("Contraseña nueva: ")
                con.execute("INSERT INTO users(email, pass_hash, name, role, onboarded, created_at, trial_ends) VALUES(?,?,?,?,1,?,?)",
                            (email, generate_password_hash(pw), "Administración", "admin", core.stamp(), core.hoy().isoformat()))
        print("Listo:", email, "es administradora.")
        return
    if args[:1] == ["avisos"]:
        create_app(seed_demo=False)
        scheduler.tick()
        print("Revisión de avisos hecha.")
        return

    app = create_app()
    scheduler.start()
    port = int(os.environ.get("PORT", "8780"))
    host = os.environ.get("HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    print(f"Cuentas Claras en http://{host}:{port}  (Ctrl+C para cerrar)")
    from waitress import serve
    serve(app, host=host, port=port, threads=8)


if __name__ == "__main__":
    main()
