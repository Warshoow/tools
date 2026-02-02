FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Environment variables (can be overridden at runtime)
ENV OLLAMA_HOST=http://host.docker.internal:11434
ENV ORCHESTRATOR_MODEL=llama3.1:8b
ENV EXECUTOR_MODEL=llama3.1:8b
ENV MAX_ITERATIONS=20
ENV MAX_CLARIFICATIONS=5

# Run the application
CMD ["python", "main.py"]
