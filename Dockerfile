FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl \
    && curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | bash \
    && apt-get install -y speedtest \
    && apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the app on port 8080 inside the container
CMD ["python", "app.py"]