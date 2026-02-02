from fastapi import FastAPI
from pydantic import BaseModel
import ollama
from ddgs import DDGS
import os
import json

app = FastAPI()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
MODEL = os.getenv("MODEL", "llama3.1:8b")

class ChatRequest(BaseModel):
    message: str
    model: str = None

def web_search(query: str, max_results: int = 5):
    """Outil MCP de recherche web"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return {
            "results": [
                {
                    "title": r['title'],
                    "snippet": r['body'],
                    "url": r['href']
                }
                for r in results
            ]
        }
    except Exception as e:
        return {"error": str(e)}

# Outils pour Ollama native tool calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. Use this when you need recent data or don't know the answer.",
            "parameters": {
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
            }
        }
    }
]

SYSTEM_PROMPT = """You are a helpful assistant with access to web search.
Use the web_search tool when you need current information or don't know the answer.
After receiving search results, provide a clear answer based on those results."""

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        model = request.model or MODEL
        client = ollama.Client(host=OLLAMA_HOST)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request.message}
        ]

        max_iterations = 5
        searched_queries = set()

        for i in range(max_iterations):
            # Call with native tools support
            response = client.chat(
                model=model,
                messages=messages,
                tools=TOOLS
            )

            message = response['message']
            tool_calls = message.get('tool_calls', [])

            # No tool calls = final response
            if not tool_calls:
                return {
                    "response": message.get('content', ''),
                    "iterations": i + 1
                }

            # Process tool calls
            messages.append(message)

            for tool_call in tool_calls:
                func_name = tool_call['function']['name']
                args = tool_call['function']['arguments']

                if func_name == 'web_search':
                    query = args.get('query', '')
                    max_results = args.get('max_results', 5)

                    print(f"Recherche: {query}")

                    # Skip duplicate searches
                    if query.lower().strip() in searched_queries:
                        print(f"Duplicate search skipped: {query}")
                        result = {"note": "Already searched, use previous results"}
                    else:
                        searched_queries.add(query.lower().strip())
                        result = web_search(query=query, max_results=max_results)

                    # Add tool response
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False)
                    })

        return {"response": "Maximum iterations reached", "iterations": max_iterations}

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}

@app.get("/health")
async def health():
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        models = client.list()
        model_list = models.get('models', [])
        available = [m.get('model') or m.get('name', 'unknown') for m in model_list]
        return {
            "status": "ok",
            "ollama_host": OLLAMA_HOST,
            "model": MODEL,
            "available_models": available
        }
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}

@app.get("/tools")
async def list_tools():
    return {"tools": TOOLS}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
