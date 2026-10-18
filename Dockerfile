FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY schemas ./schemas
COPY static ./static
RUN pip install --no-cache-dir . && useradd -m sanad && mkdir /data && chown sanad /data
USER sanad
ENV SANAD_DATA_DIR=/data PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "--factory", "sanad.api:create_app", "--host", "0.0.0.0", "--port", "8000"]
