FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /app/frontend-react
COPY frontend-react/package*.json ./
RUN npm ci
COPY frontend-react/ ./
RUN npm run build


FROM python:3.10-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    EASYOCR_MODEL_DIR=/app/.cache/easyocr \
    EASYOCR_DOWNLOAD_ENABLED=false \
    OCR_CPU_THREADS=1 \
    OCR_MAX_IMAGE_DIMENSION=1600 \
    OCR_CANVAS_SIZE=1600 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    MALLOC_ARENA_MAX=2 \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libgl1 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

RUN EASYOCR_DOWNLOAD_ENABLED=true python -c "import easyocr; easyocr.Reader(['ch_sim', 'en'], gpu=False, quantize=True, model_storage_directory='/app/.cache/easyocr', download_enabled=True, verbose=False)"

COPY . .
COPY --from=frontend-builder /app/frontend-react/dist ./frontend-react/dist

RUN python rag/build_vector_db.py --model BAAI/bge-small-zh-v1.5

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend_api:app --host 0.0.0.0 --port ${PORT:-8000}"]
