from typing import Callable, Dict, List, Optional
from ddgs import DDGS
import ast
import operator
import json
import subprocess
import os


class ToolRegistry:
    """Registry for executor tools"""

    def __init__(self):
        self._tools: Dict[str, dict] = {}
        self._functions: Dict[str, Callable] = {}

    def register(self, name: str, description: str, parameters: dict, function: Callable):
        """Register a tool"""
        self._tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
        self._functions[name] = function

    def get_tools(self, names: Optional[List[str]] = None) -> List[dict]:
        """Get tool definitions (all or filtered)"""
        if names is None:
            return list(self._tools.values())
        return [self._tools[n] for n in names if n in self._tools]

    def get_tool_names(self) -> List[str]:
        """Get list of registered tool names"""
        return list(self._tools.keys())

    def execute(self, name: str, arguments: dict) -> dict:
        """Execute a tool by name"""
        if name not in self._functions:
            return {"error": f"Unknown tool: {name}"}
        try:
            return self._functions[name](**arguments)
        except Exception as e:
            return {"error": str(e)}


# ============== Tool Implementations ==============

def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web using DuckDuckGo"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return {
            "success": True,
            "results": [
                {
                    "title": r["title"],
                    "snippet": r["body"],
                    "url": r["href"]
                }
                for r in results
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def calculate(expression: str) -> dict:
    """Safely evaluate a mathematical expression"""
    try:
        # Supported operators
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        def eval_node(node):
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Num):  # Python 3.7 compatibility
                return node.n
            elif isinstance(node, ast.BinOp):
                left = eval_node(node.left)
                right = eval_node(node.right)
                return ops[type(node.op)](left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = eval_node(node.operand)
                return ops[type(node.op)](operand)
            elif isinstance(node, ast.Expression):
                return eval_node(node.body)
            else:
                raise ValueError(f"Unsupported node type: {type(node).__name__}")

        tree = ast.parse(expression, mode='eval')
        result = eval_node(tree)
        return {
            "success": True,
            "expression": expression,
            "result": result
        }
    except Exception as e:
        return {"success": False, "expression": expression, "error": str(e)}


def format_json(data: str) -> dict:
    """Format/validate JSON string"""
    try:
        parsed = json.loads(data)
        formatted = json.dumps(parsed, indent=2)
        return {"success": True, "formatted": formatted}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============== Coding Tools ==============

def read_file(path: str) -> dict:
    """Read a file's content"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            "success": True,
            "path": path,
            "content": content,
            "lines": len(content.splitlines())
        }
    except Exception as e:
        return {"success": False, "path": path, "error": str(e)}


def write_file(path: str, content: str) -> dict:
    """Write content to a file"""
    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {
            "success": True,
            "path": path,
            "bytes_written": len(content)
        }
    except Exception as e:
        return {"success": False, "path": path, "error": str(e)}


def list_files(path: str = ".", pattern: str = None) -> dict:
    """List files in a directory"""
    try:
        if not os.path.exists(path):
            return {"success": False, "error": f"Path does not exist: {path}"}

        if os.path.isfile(path):
            return {"success": True, "files": [path], "count": 1}

        files = []
        for root, dirs, filenames in os.walk(path):
            # Skip hidden and common non-essential directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git']]

            for filename in filenames:
                if pattern is None or pattern in filename:
                    rel_path = os.path.relpath(os.path.join(root, filename), path)
                    files.append(rel_path)

        return {
            "success": True,
            "path": path,
            "files": files[:100],  # Limit to 100 files
            "count": len(files),
            "truncated": len(files) > 100
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_command(command: str, timeout: int = 30) -> dict:
    """Run a shell command"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "command": command,
            "return_code": result.returncode,
            "stdout": result.stdout[:5000] if result.stdout else "",  # Limit output
            "stderr": result.stderr[:2000] if result.stderr else ""
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "command": command, "error": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "command": command, "error": str(e)}


def search_in_files(path: str, pattern: str, file_pattern: str = None) -> dict:
    """Search for a pattern in files"""
    try:
        matches = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git']]

            for filename in files:
                if file_pattern and file_pattern not in filename:
                    continue

                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern in line:
                                matches.append({
                                    "file": os.path.relpath(filepath, path),
                                    "line": line_num,
                                    "content": line.strip()[:200]
                                })
                                if len(matches) >= 50:  # Limit matches
                                    return {
                                        "success": True,
                                        "pattern": pattern,
                                        "matches": matches,
                                        "truncated": True
                                    }
                except:
                    continue

        return {
            "success": True,
            "pattern": pattern,
            "matches": matches,
            "count": len(matches)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============== Global Registry ==============

registry = ToolRegistry()

# Register web_search
registry.register(
    name="web_search",
    description="Search the web for current information. Use when you need recent data or facts.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 5)"
            }
        },
        "required": ["query"]
    },
    function=web_search
)

# Register calculate
registry.register(
    name="calculate",
    description="Evaluate a mathematical expression. Supports +, -, *, /, ** (power).",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Math expression like '2 + 2' or '10 * 5 ** 2'"
            }
        },
        "required": ["expression"]
    },
    function=calculate
)

# Register format_json
registry.register(
    name="format_json",
    description="Format and validate a JSON string",
    parameters={
        "type": "object",
        "properties": {
            "data": {
                "type": "string",
                "description": "JSON string to format"
            }
        },
        "required": ["data"]
    },
    function=format_json
)

# Register read_file
registry.register(
    name="read_file",
    description="Read the contents of a file. Use to examine source code or config files.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read"
            }
        },
        "required": ["path"]
    },
    function=read_file
)

# Register write_file
registry.register(
    name="write_file",
    description="Write content to a file. Creates directories if needed. Use to create or modify code files.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to write"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            }
        },
        "required": ["path", "content"]
    },
    function=write_file
)

# Register list_files
registry.register(
    name="list_files",
    description="List files in a directory. Useful for exploring project structure.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to list (default: current directory)"
            },
            "pattern": {
                "type": "string",
                "description": "Optional filter pattern (e.g., '.py' for Python files)"
            }
        },
        "required": []
    },
    function=list_files
)

# Register run_command
registry.register(
    name="run_command",
    description="Run a shell command. Use for running tests, builds, linters, etc.",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute (e.g., 'pytest', 'npm test', 'python script.py')"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30)"
            }
        },
        "required": ["command"]
    },
    function=run_command
)

# Register search_in_files
registry.register(
    name="search_in_files",
    description="Search for a text pattern in files. Useful for finding code, functions, or references.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory to search in"
            },
            "pattern": {
                "type": "string",
                "description": "Text pattern to search for"
            },
            "file_pattern": {
                "type": "string",
                "description": "Optional file filter (e.g., '.py' for Python files)"
            }
        },
        "required": ["path", "pattern"]
    },
    function=search_in_files
)
