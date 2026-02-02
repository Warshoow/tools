from fastapi import FastAPI
import ollama
from typing import List, Union

from config import (
    OLLAMA_HOST, ORCHESTRATOR_MODEL, EXECUTOR_MODEL,
    MAX_ITERATIONS, MAX_CLARIFICATIONS
)
from models import (
    OrchestrateRequest, OrchestrateResponse,
    ClarificationRequest, TaskResult, MessageStatus
)
from orchestrator import Orchestrator
from executor import Executor
from tools import registry


def extract_task_description(value: Union[str, dict, None]) -> str:
    """Extract task description string from various formats LLM might return"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # LLM might return subtask dict or nested structure
        if "description" in value:
            return str(value["description"])
        if "task_description" in value:
            return str(value["task_description"])
        if "content" in value:
            return str(value["content"])
        # Fallback: convert dict to readable string
        return str(value)
    return str(value)


app = FastAPI(
    title="AI Orchestrator/Executor Tool",
    description="Bidirectional AI interaction with orchestrator and executor pattern",
    version="1.0.0"
)


@app.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    """
    Main orchestration endpoint.
    User submits a task, orchestrator plans, executor performs, bidirectional loop until complete.
    """
    client = ollama.Client(host=OLLAMA_HOST)

    # Initialize both AIs
    orchestrator = Orchestrator(
        model=request.orchestrator_model or ORCHESTRATOR_MODEL,
        client=client
    )
    executor = Executor(
        model=request.executor_model or EXECUTOR_MODEL,
        client=client
    )

    conversation_history: List[dict] = []
    completed_tasks: List[str] = []
    failed_tasks: List[str] = []
    iteration = 0
    clarifications = 0

    try:
        # Phase 1: Orchestrator analyzes and plans
        print(f"\n{'='*50}")
        print(f"Starting orchestration for: {request.task[:100]}...")
        print(f"{'='*50}\n")

        plan = await orchestrator.analyze_and_plan(request.task)
        conversation_history.append({
            "phase": "planning",
            "plan": plan
        })

        # Phase 2: Main execution loop
        current_task_description = None

        while iteration < request.max_iterations:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")

            # Orchestrator decides next action
            action = await orchestrator.decide_next_action(completed_tasks, failed_tasks)

            if action.get("action") == "complete":
                print("[Main] Orchestrator signals completion")
                break

            elif action.get("action") in ["assign_task", "retry"]:
                # Get task description (handle various formats LLM might return)
                current_task_description = extract_task_description(action.get("task_description"))
                if not current_task_description:
                    # Fallback to next planned subtask
                    subtasks = plan.get("subtasks", [])
                    remaining = [
                        s for s in subtasks
                        if s["id"] not in completed_tasks and s["id"] not in failed_tasks
                    ]
                    if remaining:
                        current_task_description = extract_task_description(remaining[0])
                    else:
                        break

                # Create and send task assignment
                assignment = await orchestrator.create_task_assignment(current_task_description)
                conversation_history.append({
                    "type": "task_assignment",
                    "sender": "orchestrator",
                    "task_id": assignment.task_id,
                    "content": assignment.content
                })

                print(f"[Main] Assigned task: {assignment.content[:80]}...")

                # Executor executes the task
                response = await executor.execute_task(assignment)

                # Handle clarification request
                if isinstance(response, ClarificationRequest):
                    conversation_history.append({
                        "type": "clarification_request",
                        "sender": "executor",
                        "task_id": response.task_id,
                        "content": response.content
                    })

                    print(f"[Main] Executor asking: {response.content[:80]}...")

                    if clarifications >= request.max_clarifications:
                        print("[Main] Max clarifications reached, marking task as failed")
                        failed_tasks.append(assignment.task_id)
                        continue

                    clarifications += 1

                    # Orchestrator provides clarification
                    clarification = await orchestrator.provide_clarification(
                        response, current_task_description
                    )
                    conversation_history.append({
                        "type": "clarification_response",
                        "sender": "orchestrator",
                        "task_id": clarification.task_id,
                        "content": clarification.content
                    })

                    print(f"[Main] Orchestrator clarifies: {clarification.content[:80]}...")

                    # Executor continues with clarification
                    response = await executor.continue_after_clarification(
                        assignment, clarification
                    )

                # Now we have a TaskResult
                if isinstance(response, TaskResult):
                    conversation_history.append({
                        "type": "task_result",
                        "sender": "executor",
                        "task_id": response.task_id,
                        "status": response.status.value,
                        "content": response.content,
                        "tools_used": response.tools_used
                    })

                    print(f"[Main] Executor result ({response.status.value}): {response.content[:80]}...")

                    # Orchestrator evaluates result
                    evaluation = await orchestrator.evaluate_result(
                        response, current_task_description
                    )

                    if evaluation.get("accepted", False):
                        completed_tasks.append(assignment.task_id)
                        print(f"[Main] Task accepted")
                    else:
                        failed_tasks.append(assignment.task_id)
                        print(f"[Main] Task rejected: {evaluation.get('reasoning', '')[:50]}")

            else:
                # Unknown action, break to prevent infinite loop
                print(f"[Main] Unknown action: {action.get('action')}")
                break

        # Phase 3: Generate final summary
        final_summary = await orchestrator.generate_final_summary(completed_tasks, failed_tasks)

        return OrchestrateResponse(
            success=len(failed_tasks) == 0 and len(completed_tasks) > 0,
            final_result=final_summary,
            total_iterations=iteration,
            clarifications_made=clarifications,
            tasks_completed=len(completed_tasks),
            tasks_failed=len(failed_tasks),
            conversation_history=conversation_history if request.include_conversation_history else None
        )

    except Exception as e:
        import traceback
        print(f"[Main] Error: {e}")
        traceback.print_exc()

        return OrchestrateResponse(
            success=False,
            final_result=f"Orchestration failed: {str(e)}",
            total_iterations=iteration,
            clarifications_made=clarifications,
            tasks_completed=len(completed_tasks),
            tasks_failed=len(failed_tasks),
            conversation_history=conversation_history if request.include_conversation_history else None,
            error=str(e)
        )


@app.get("/health")
async def health():
    """Health check with model availability"""
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        models = client.list()
        model_list = models.get("models", [])
        available = [m.get("model") or m.get("name", "unknown") for m in model_list]

        return {
            "status": "ok",
            "ollama_host": OLLAMA_HOST,
            "orchestrator_model": ORCHESTRATOR_MODEL,
            "executor_model": EXECUTOR_MODEL,
            "available_models": available
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "ollama_host": OLLAMA_HOST
        }


@app.get("/tools")
async def list_tools():
    """List available executor tools"""
    return {
        "tools": registry.get_tools(),
        "tool_names": registry.get_tool_names()
    }


@app.get("/config")
async def get_config():
    """Get current configuration"""
    return {
        "ollama_host": OLLAMA_HOST,
        "orchestrator_model": ORCHESTRATOR_MODEL,
        "executor_model": EXECUTOR_MODEL,
        "max_iterations": MAX_ITERATIONS,
        "max_clarifications": MAX_CLARIFICATIONS
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
