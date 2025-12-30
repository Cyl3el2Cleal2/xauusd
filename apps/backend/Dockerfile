FROM python:3.13-slim

WORKDIR /app

# Install system dependencies if any (usually none minimal for pure python, but maybe gcc for some libs)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

RUN playwright install

COPY . .

# Expose the port
EXPOSE 8000

# Run the application
CMD ["fastapi", "run", "src/app.py", "--port", "8000"]