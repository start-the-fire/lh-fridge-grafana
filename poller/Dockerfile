FROM python:3-slim

WORKDIR /app
RUN useradd --create-home --uid 10001 poller
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore --requirement requirements.txt

COPY --chown=poller:poller poller.py .
USER poller

CMD ["python", "-u", "poller.py"]
