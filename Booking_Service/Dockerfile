# Use a minimal Python base image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy application files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8001 for the Booking Service
EXPOSE 8001

# Load environment variables from .env file
COPY .env .env

# Command to run the FastAPI Booking Service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
