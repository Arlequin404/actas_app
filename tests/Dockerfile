FROM mcr.microsoft.com/playwright/python:v1.49.1-noble
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY tests/requirements.txt /tmp/test-requirements.txt
RUN pip install --no-cache-dir -r /tmp/test-requirements.txt
COPY . /workspace
CMD ["bash", "scripts/run_full_test_suite.sh"]
