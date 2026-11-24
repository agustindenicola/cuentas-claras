import os
import sys
import tempfile

import pytest

# base de datos aparte para las pruebas (nunca toca los datos reales) y sin mandar notificaciones de verdad
os.environ["CUENTAS_DATA"] = tempfile.mkdtemp(prefix="cuentas-test-")
os.environ["CUENTAS_NO_PUSH"] = "1"
os.environ["CUENTAS_DEMO"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cuentas.db import db  # noqa: E402
from cuentas.server import create_app  # noqa: E402

APP = create_app(seed_demo=True)
H = {"X-CC": "1"}
_n = [0]


@pytest.fixture(autouse=True)
def sin_limites():
    """Las pruebas crean muchas cuentas seguidas: se reinicia el límite de intentos."""
    from cuentas import server
    server._intentos.clear()


@pytest.fixture
def con():
    with db() as c:
        yield c


@pytest.fixture
def client():
    return APP.test_client()


def nueva(client, nombre="Prueba"):
    """Crea una cuenta nueva (con sesión iniciada) y devuelve su id y su mail."""
    _n[0] += 1
    email = f"persona{_n[0]}@ejemplo.com"
    r = client.post("/api/register", json={"email": email, "password": "clave-segura-1", "name": nombre, "accept_terms": True}, headers=H)
    assert r.status_code == 200, r.json
    return client.get("/api/me").json["user"]["id"], email
