
###### multi-stage Docker build with separate debug and production configurations ####### Stage 1: Base image
FROM python:3.13 AS base

# Set the working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose Flask port
EXPOSE 5000

### 🛠️ START NEW IMAGE: DEBUG ###
FROM base AS debug

# Install debug tools
RUN pip install debugpy

# Run Flask in debug mode, waiting for a debugger to attach
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]

### 🚀 START NEW IMAGE: PRODUCTION ###
FROM base AS prod

# Install production server
RUN pip install gunicorn

# Run Flask in production mode
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
