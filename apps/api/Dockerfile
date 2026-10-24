FROM python:3.12.12-slim@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace/apps/api
COPY apps/api/pyproject.toml ./
COPY apps/api/constraints.txt ./
RUN python -c "import tomllib,pathlib; p=tomllib.loads(pathlib.Path('pyproject.toml').read_text()); pathlib.Path('/tmp/requirements.txt').write_text('\n'.join(p['project']['dependencies']))" \
    && pip install --no-cache-dir -c constraints.txt -r /tmp/requirements.txt \
    && useradd --create-home --uid 10001 appuser
COPY apps/api/app ./app
RUN pip install --no-cache-dir --no-deps .
COPY apps/api/alembic.ini ./
COPY apps/api/alembic ./alembic
COPY benchmarks/fixtures /workspace/benchmarks/fixtures
COPY data/sources /workspace/data/sources
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
