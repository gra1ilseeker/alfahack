FROM python:3.12.14-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY credit_synth ./credit_synth
COPY demo/model ./demo/model
ENTRYPOINT ["python", "-m", "credit_synth"]
CMD ["generate", "--model", "demo/model", "--out", "/data/generated", "--companies", "1000"]
