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

ENV PORT=8000
EXPOSE 8000

# Exec form, NO shell: Debian's /bin/sh is dash and parses '(' in
# "app:create_app()" as a syntax error — the container never reached
# gunicorn. The app object comes from passenger_wsgi:application
# (create_app() at import; also keeps the shim honest in-container).
# The internal bind is fixed; compose maps the variable host port.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "60", "passenger_wsgi:application"]
