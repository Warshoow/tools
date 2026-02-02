import os

# Ollama connection
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")

# Model configuration - can use different models for each role
ORCHESTRATOR_MODEL = os.getenv("ORCHESTRATOR_MODEL", "llama3.1:8b")
EXECUTOR_MODEL = os.getenv("EXECUTOR_MODEL", "llama3.1:8b")

# Execution limits
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "20"))
MAX_CLARIFICATIONS = int(os.getenv("MAX_CLARIFICATIONS", "5"))
EXECUTOR_MAX_TOOL_CALLS = int(os.getenv("EXECUTOR_MAX_TOOL_CALLS", "10"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
