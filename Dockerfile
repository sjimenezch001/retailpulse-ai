# The digest fixes the base image; dependency versions are separately pinned.
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    RETAILPULSE_CONTAINER=1 HOME=/tmp XDG_CACHE_HOME=/tmp/cache
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --no-create-home demo
COPY requirements-runtime.txt ./
RUN python -m pip install --no-cache-dir pip==26.2.1 setuptools==84.0.0 wheel==0.48.0 \
    && python -m pip install --no-cache-dir -r requirements-runtime.txt
COPY pyproject.toml README.md ./
COPY src ./src
COPY app ./app
COPY config ./config
COPY .streamlit ./.streamlit
COPY docs/web_demo.md ./docs/web_demo.md
RUN python -m pip install --no-cache-dir --no-deps --no-build-isolation . \
    && mkdir artifacts && chown demo:demo artifacts
USER 10001:10001
EXPOSE 8000 8501
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready',timeout=4); urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health',timeout=4)"
CMD ["python", "-m", "retailpulse", "demo", "--mode", "synthetic", "--provider", "deterministic"]
