FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "fastapi>=0.115.0" "uvicorn[standard]>=0.34.0" "pydantic>=2.10.0"

COPY app.py .

EXPOSE 8002

HEALTHCHECK --interval=5s --timeout=3s --retries=10 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health')"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
