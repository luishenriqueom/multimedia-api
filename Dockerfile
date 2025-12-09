FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y libpq-dev gcc python3-dev

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENTRYPOINT ["sh", "-c", "alembic upgrade heads && uvicorn app.main:app --host 0.0.0.0 --port 8000"]