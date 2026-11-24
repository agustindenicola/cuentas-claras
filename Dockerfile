FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CUENTAS_DATA=/data \
    CUENTAS_HTTPS=1 \
    PORT=8080

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY run.py .
COPY cuentas ./cuentas

# los datos (base, claves de notificaciones, copias de seguridad) viven en /data: montá ahí un volumen para no perderlos
VOLUME ["/data"]
EXPOSE 8080
CMD ["python", "run.py"]
