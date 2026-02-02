# Local Coding Models & Integration Guide

## Hardware Reference

- **RAM**: 32GB
- **GPU**: RTX 4060 (8GB VRAM)

## Recommended Ollama Models for Coding

| Model | Size | VRAM Needed | Coding Quality | Install Command |
|-------|------|-------------|----------------|-----------------|
| `qwen2.5-coder:7b` | 4.7GB | ~6GB | Excellent | `ollama pull qwen2.5-coder:7b` |
| `qwen2.5-coder:14b` | 9GB | ~10GB (partial CPU) | Very strong | `ollama pull qwen2.5-coder:14b` |
| `deepseek-coder-v2:16b` | 8.9GB | ~10GB (partial CPU) | Excellent | `ollama pull deepseek-coder-v2:16b` |
| `codellama:13b` | 7.4GB | ~9GB | Good | `ollama pull codellama:13b` |
| `phi3:14b` | 7.9GB | ~9GB | Good general | `ollama pull phi3:14b` |

### Best Choice for 8GB VRAM

```bash
# Fast, fits entirely in VRAM
ollama pull qwen2.5-coder:7b

# Better quality, uses some CPU (slower but smarter)
ollama pull qwen2.5-coder:14b
```

## Using with Orchestrator

### Configure for Coding Tasks

```bash
docker run --rm -p 8080:8080 \
  -e ORCHESTRATOR_MODEL=qwen2.5-coder:14b \
  -e EXECUTOR_MODEL=qwen2.5-coder:7b \
  orchestrator
```

### Example Coding Requests

```bash
# Code review
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "Review this Python function and suggest improvements: def add(a,b): return a+b"}'

# Explain code
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "Explain how async/await works in Python with examples"}'

# Generate code
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "Write a Python function that validates email addresses using regex"}'
```

## VSCode Integration

### Option 1: Continue.dev Extension (Easiest)

1. Install "Continue" extension in VSCode
2. Create config file `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Qwen Coder",
      "provider": "ollama",
      "model": "qwen2.5-coder:7b"
    },
    {
      "title": "Qwen Coder Large",
      "provider": "ollama",
      "model": "qwen2.5-coder:14b"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Qwen Coder",
    "provider": "ollama",
    "model": "qwen2.5-coder:7b"
  }
}
```

3. Use `Ctrl+L` to chat, `Ctrl+I` to edit code inline

### Option 2: VSCode Task for Orchestrator

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Ask AI Orchestrator",
      "type": "shell",
      "command": "curl -s -X POST http://localhost:8080/orchestrate -H \"Content-Type: application/json\" -d \"{\\\"task\\\": \\\"${input:prompt}\\\"}\" | jq -r \".final_result\"",
      "problemMatcher": [],
      "presentation": {
        "echo": true,
        "reveal": "always",
        "panel": "new"
      }
    }
  ],
  "inputs": [
    {
      "id": "prompt",
      "type": "promptString",
      "description": "What do you want the AI to do?"
    }
  ]
}
```

Run with: `Ctrl+Shift+P` → "Tasks: Run Task" → "Ask AI Orchestrator"

### Option 3: Keybinding for Quick Access

Add to `.vscode/keybindings.json`:

```json
[
  {
    "key": "ctrl+shift+a",
    "command": "workbench.action.tasks.runTask",
    "args": "Ask AI Orchestrator"
  }
]
```

## Extending Orchestrator with Coding Tools

Add these tools to `tools.py` for file manipulation:

```python
def read_file(path: str) -> dict:
    """Read a file from the workspace"""
    try:
        with open(path, 'r') as f:
            return {"success": True, "content": f.read()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def write_file(path: str, content: str) -> dict:
    """Write content to a file"""
    try:
        with open(path, 'w') as f:
            f.write(content)
        return {"success": True, "path": path}
    except Exception as e:
        return {"success": False, "error": str(e)}

def run_command(command: str) -> dict:
    """Run a shell command"""
    import subprocess
    try:
        result = subprocess.run(
            command, shell=True,
            capture_output=True, text=True, timeout=30
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# Register tools
registry.register(
    "read_file",
    "Read a file's content",
    {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"]
    },
    read_file
)

registry.register(
    "write_file",
    "Write content to a file",
    {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"}
        },
        "required": ["path", "content"]
    },
    write_file
)

registry.register(
    "run_command",
    "Run a shell command (e.g., pytest, npm test)",
    {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"]
    },
    run_command
)
```

### Example with Coding Tools

```bash
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "Read main.py, add error handling, and run pytest"}'
```

## Performance Tips

1. **Use 7B model for fast iterations** - Best for autocomplete, quick questions
2. **Use 14B+ for complex tasks** - Better reasoning, code review, architecture
3. **Keep Ollama warm** - First request is slower (model loading)
4. **Monitor VRAM** - Use `nvidia-smi` to check GPU memory usage

```bash
# Watch GPU usage
watch -n 1 nvidia-smi
```
