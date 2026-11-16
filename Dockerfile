FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential default-libmysqlclient-dev pkg-config gettext \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY dndtools /app/dndtools
RUN cd /app/dndtools && DND_DEBUG=1 DND_DB_HOST=127.0.0.1 DND_DB_NAME=unused \
    DND_DB_USER=unused DND_DB_PASSWORD=unused DND_SECRET_KEY=build-placeholder \
    python manage.py compilemessages
RUN groupadd --gid 10001 dndtools && useradd --uid 10001 --gid 10001 --no-create-home dndtools \
    && mkdir -p /var/www/static /var/www/media \
    && chmod -R a+rX /app/dndtools \
    && chown -R 10001:10001 /var/www
WORKDIR /app/dndtools
USER 10001:10001

CMD ["sh", "-c", "python manage.py collectstatic --noinput && exec gunicorn dndproject.wsgi:application --bind 0.0.0.0:8765 --workers 2"]
