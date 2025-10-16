FROM python:3.13.3-slim

WORKDIR /app
COPY . .
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8080
ENTRYPOINT [ "python", "run.py" ]
