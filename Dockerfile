# AWS Lambda container image. Mangum (src.app.handler) turns Function URL events into ASGI requests.
#
# Run the API locally (no Lambda), either:
#   uvicorn src.app:app --reload
#   docker run --rm -p 8000:8000 --entrypoint uvicorn insurance-api src.app:app --host 0.0.0.0
#
# Test the Lambda image locally (the base image includes the Runtime Interface Emulator):
#   docker build -t insurance-api .
#   docker run --rm -p 9000:8080 insurance-api
#   curl -s localhost:9000/2015-03-31/functions/function/invocations -d @tests/lambda_event.json
FROM public.ecr.aws/lambda/python:3.14

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Base image sets WORKDIR to ${LAMBDA_TASK_ROOT} (/var/task).
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
COPY data/insurance.csv data/

# Train inside the image so model.joblib matches the installed scikit-learn version.
RUN python src/train.py

CMD ["src.app.handler"]
