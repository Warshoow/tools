from fastapi import FastAPI
from pydantic import BaseModel
import ollama
from duckduckgo_search import DDGS
import os
import json
import re

app = FastAPI()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
MODEL = os.getenv("MODEL", "deepseek-r1:7b")

class ChatRequest(BaseModel):
    message: str
    model: str = None

class ToolCall(BaseModel):
    name: str
    arguments: dict

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

# Définition des outils MCP
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Recherche des informations actuelles sur le web. Utilise cet outil quand tu as besoin d'informations récentes ou que tu ne connais pas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La requête de recherche"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Nombre maximum de résultats (défaut: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    }
]

SYSTEM_PROMPT = """Tu es un assistant avec accès a un outil de recherche web.

Quand tu as besoin d'informations actuelles ou recentes, tu DOIS utiliser l'outil en repondant UNIQUEMENT avec ce format JSON:
{"tool": "web_search", "query": "ta recherche ici"}

Exemples:
- Pour la meteo: {"tool": "web_search", "query": "meteo Paris aujourd'hui"}
- Pour des news: {"tool": "web_search", "query": "actualites France"}

Si tu n'as pas besoin de recherche, reponds normalement sans JSON."""

def extract_tool_call(text: str):
    """Extrait un appel d'outil du texte du modele"""
    # Cherche un bloc JSON dans la reponse
    json_pattern = r'\{[^{}]*"tool"\s*:\s*"web_search"[^{}]*\}'
    match = re.search(json_pattern, text)
    if match:
        try:
            data = json.loads(match.group())
            if data.get('tool') == 'web_search' and data.get('query'):
                return data
        except json.JSONDecodeError:
            pass
    return None

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        model = request.model or MODEL
        client = ollama.Client(host=OLLAMA_HOST)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request.message}
        ]

        max_iterations = 3
        for i in range(max_iterations):
            response = client.chat(model=model, messages=messages)
            assistant_content = response['message'].get('content', '')

            # Detecter un appel d'outil dans la reponse
            tool_call = extract_tool_call(assistant_content)

            if not tool_call:
                # Pas d'outil, reponse finale
                return {
                    "response": assistant_content,
                    "iterations": i + 1
                }

            # Executer la recherche
            query = tool_call['query']
            print(f"Recherche: {query}")
            result = web_search(query=query)

            # Ajouter au contexte et continuer
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({
                "role": "user",
                "content": f"Resultats de recherche:\n{json.dumps(result, ensure_ascii=False, indent=2)}\n\nUtilise ces resultats pour repondre a la question initiale."
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
        # Ollama returns 'models' list with 'model' key (not 'name')
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
