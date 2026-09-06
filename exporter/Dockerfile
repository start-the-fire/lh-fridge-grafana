FROM python:3-slim

WORKDIR /app
RUN useradd --create-home --uid 10002 exporter
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore --requirement requirements.txt

COPY --chown=exporter:exporter export.py .
RUN chown exporter:exporter /app
USER exporter

CMD ["python", "-u", "export.py"]
