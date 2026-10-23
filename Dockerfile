FROM python@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70

# python:3.12-slim-bookworm, digest-pinned (design §5)

WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py schema.sql passenger_wsgi.py ./
COPY templates/ templates/
COPY static/ static/

# Gate major #6: no root in the container
RUN useradd --system --no-create-home burnafter
USER burnafter

ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "exec gunicorn --bind ${HOST}:${PORT} --workers 2 --threads 4 --timeout 60 app:create_app()"]
