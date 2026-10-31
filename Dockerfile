FROM python:3.14-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY guard ./guard
COPY data/train.jsonl data/val.jsonl data/threshold.json ./data/
# Train at build time from committed data; threshold comes from data/threshold.json.
RUN python -m guard.classifier && useradd -r -u 10001 guard && mkdir -p /var/guard && chown guard /var/guard
USER guard
ENV SPEND_FILE=/var/guard/spend.json
EXPOSE 8080
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8080/health')"
CMD ["uvicorn", "guard.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
