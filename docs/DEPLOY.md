# Cuentas Claras

App para anotar ingresos y egresos, controlar los gastos fijos y ver cómo viene el mes.
Cuentas privadas, 14 días de prueba, suscripción mensual con Mercado Pago, recordatorios y logros.

## Probarla en la compu

```
pip install -r requirements.txt
python run.py
```

Abrí http://127.0.0.1:8780. Con «Ver un ejemplo sin registrarme» entrás a la cuenta de Carolina (datos inventados).

Pruebas automáticas: `python -m pytest`

## Publicarla en internet (Railway)

1. Creá una cuenta en https://railway.com (con tu GitHub).
2. **New Project → Deploy from GitHub repo** → elegí `cuentas-claras`.
3. En el servicio, **Settings → Volumes → Add volume** con *mount path* `/data`.
   Ahí quedan la base de datos, las claves de notificaciones y las copias diarias. Sin volumen se borra todo en cada actualización.
4. **Variables** (las que dicen «opcional» se pueden agregar después):

| Variable | Para qué |
|---|---|
| `CUENTAS_ADMIN_EMAIL` | tu mail: esa cuenta ve el panel de Administración |
| `CUENTAS_ADMIN_PASSWORD` | contraseña de esa cuenta (mínimo 8 caracteres) |
| `CUENTAS_DEMO` | `1` para mostrar «Ver un ejemplo»; `0` para sacarlo |
| `CUENTAS_MP_TOKEN` | opcional: Access Token de producción de Mercado Pago (cobro automático) |
| `CUENTAS_MP_WEBHOOK_SECRET` | opcional: clave secreta de los webhooks de Mercado Pago |
| `CUENTAS_SMTP_HOST`, `CUENTAS_SMTP_USER`, `CUENTAS_SMTP_PASSWORD` | opcional: mail para recuperar contraseñas (con Gmail: `smtp.gmail.com` y una «contraseña de aplicación») |
| `CUENTAS_BACKUP_EMAIL` | opcional: a dónde mandar la copia diaria de la base (si no, va al mail de admin). Necesita el mail configurado |

5. **Settings → Networking → Generate Domain**. Ese es el link para pasarles a todas.
   Si querés un dominio propio (ej. `cuentasclaras.com.ar`), se agrega en el mismo lugar.

Cada vez que se sube un cambio a GitHub, Railway la actualiza sola.

## Cobro con Mercado Pago

**Opción simple (sin programar):** en Mercado Pago armá un plan de suscripción mensual («Suscripciones» → «Crear plan»),
copiá el link y pegalo en la app: Administración → Cobro. Cuando alguien te pague, marcá «+1 mes pago» en su fila.

**Opción automática:** en https://www.mercadopago.com.ar/developers → Tus integraciones → crear aplicación →
Credenciales de producción → copiá el *Access Token* en `CUENTAS_MP_TOKEN`. Después, en esa misma aplicación,
**Webhooks** → URL `https://TU-LINK/api/mp/webhook`, eventos **Planes y suscripciones**, y copiá la clave secreta en
`CUENTAS_MP_WEBHOOK_SECRET`. Desde ahí la suscripción se crea y se renueva sola, y el acceso se activa con cada pago.

El precio y los días de prueba se cambian desde Administración.

## Notificaciones

- **Android y compu:** funcionan desde el navegador o con la app instalada.
- **iPhone:** solo con la app agregada a la pantalla de inicio desde Safari (iOS 16.4 o más nuevo).
  La app lo explica paso a paso en «Mi cuenta» → Instalar.

Avisos que manda (en hora de Argentina): recordatorio diario si no anotó nada (a la hora que elija cada una),
vencimientos (el día antes, el mismo día y si se pasó), día de cobro, resumen del mes el día 1, fin de la prueba y logros nuevos.

## Datos y copias

Todo vive en `datos/` (o `/data` en Railway): `cuentas.db` y una copia diaria en `copias/` (se guardan las últimas 14).
Si el mail está configurado, la copia de cada día además llega por mail (comprimida), así queda guardada fuera del servidor.
`datos/` nunca se sube al repositorio.
