# Use official Python image as base
FROM python:3.11

# Set working directory
WORKDIR /app

# Copy dependencies file first (to leverage Docker caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Set environment variables (use .env file in production)
ENV ENV_PATH=/app/local.env

# Run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
