FROM python:3.12.12-slim@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c
ENV PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
WORKDIR /worker
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 espeak-ng && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir torch==2.9.1+cpu torchvision==0.24.1+cpu --index-url https://download.pytorch.org/whl/cpu
COPY apps/inference/requirements.txt .
COPY apps/inference/constraints.txt .
RUN pip install --no-cache-dir -c constraints.txt -r requirements.txt && useradd --create-home --uid 10001 inference
COPY apps/inference/main.py apps/inference/audio_decode.py apps/inference/asr_profiles.py ./
USER inference
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","9000","--workers","1","--no-access-log"]
