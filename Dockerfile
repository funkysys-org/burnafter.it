FROM python:3.12-slim-bookworm

WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py schema.sql passenger_wsgi.py ./
COPY templates/ templates/
COPY static/ static/

ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "exec gunicorn --bind ${HOST}:${PORT} --workers 2 --threads 4 --timeout 60 app:create_app()"]
