# python:3.12-slim, not alpine -- torch/transformers ship manylinux wheels
# that are unreliable to build/run on musl.
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install \
    torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# Bakes the DistilBERT weights into the image so containers don't hit the
# network or pay a cold-start download on first request.
ENV PYTHONPATH=/install/lib/python3.12/site-packages
RUN python -c "from transformers import pipeline; pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english')"


FROM python:3.12-slim

WORKDIR /app

RUN useradd --create-home appuser && chown appuser:appuser /app
ENV HOME=/home/appuser
# console-script entry points don't add cwd to sys.path the way `python -m`
# does; set explicitly so `import app.*` resolves regardless of invocation.
ENV PYTHONPATH=/app

COPY --from=builder /install /usr/local
COPY --from=builder --chown=appuser:appuser /root/.cache/huggingface /home/appuser/.cache/huggingface
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini .

# writable so `alembic upgrade head` can create ./reviews.db as appuser
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
