# Isolated sandbox for learner-submitted code. Built once, run per request with
# no network, a read-only filesystem, a non-root user and tight resource limits
# (see app/frontier/runner.py for the exact `docker run` flags).
FROM python:3.12-slim

RUN pip install --no-cache-dir "fastapi>=0.115,<1" "httpx>=0.27,<1" "pydantic>=2.7,<3" \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin learner

COPY harness/ /harness/

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001
WORKDIR /tmp
ENTRYPOINT ["python", "-I", "/harness/harness.py"]
