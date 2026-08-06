FROM python:3.12-slim

WORKDIR /app

# Copy sources first so `pip install .` can discover the `app` package
# declared in pyproject.toml's [tool.setuptools] section.
COPY pyproject.toml .
COPY app/ app/
RUN pip install --no-cache-dir .

COPY samples/ samples/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
