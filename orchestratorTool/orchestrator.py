import ollama
import json
from typing import List, Optional
from models import (
    TaskAssignment, TaskResult, ClarificationRequest,
    ClarificationResponse, CompletionMessage, MessageStatus
)
from tools import registry


ORCHESTRATOR_SYSTEM_PROMPT = """You are a task orchestrator AI. Your role is to:
1. Analyze user requests and break them into discrete sub-tasks
2. Assign sub-tasks to an executor AI one at a time
3. Evaluate executor results and decide next steps
4. Answer clarification questions from the executor
5. Determine when the overall task is complete

Guidelines:
- Break complex tasks into simple, actionable steps
- Be clear and specific in task assignments
- Provide helpful context when assigning tasks
- Be helpful when answering clarification questions
- Only mark complete when all necessary work is done

Available executor tools: {tool_names}

You communicate via JSON. Always respond with valid JSON."""


PLAN_PROMPT = """Analyze this user request and create a plan:

USER REQUEST: {task}

Respond with JSON:
{{
    "understanding": "Brief summary of what the user wants",
    "subtasks": [
        {{"id": "1", "description": "First subtask", "depends_on": []}},
        {{"id": "2", "description": "Second subtask", "depends_on": ["1"]}}
    ],
    "success_criteria": "How to know when task is complete"
}}"""


NEXT_ACTION_PROMPT = """Current state:
- Original task: {original_task}
- Completed subtasks: {completed}
- Failed subtasks: {failed}
- Remaining planned subtasks: {remaining}

Previous results:
{context}

What should happen next? Respond with JSON:
{{
    "action": "assign_task" | "complete" | "retry",
    "reasoning": "Why this action",
    "task_description": "If assign_task, the detailed instructions for executor",
    "final_summary": "If complete, the final answer to user's original request"
}}"""


CLARIFICATION_PROMPT = """The executor is asking for clarification on this task:

Original task: {task_description}
Executor's question: {question}

Provide helpful clarification. Respond with JSON:
{{
    "clarification": "Your helpful answer",
    "action": "continue" | "modify_task" | "abort",
    "modified_instructions": "If modifying, new instructions"
}}"""


EVALUATE_PROMPT = """Evaluate this result from the executor:

Task assigned: {task_description}
Result status: {status}
Result content: {content}

Is this result acceptable? Respond with JSON:
{{
    "accepted": true | false,
    "reasoning": "Why accepted or rejected",
    "key_findings": "Important information from the result"
}}"""


class Orchestrator:
    """Orchestrator AI that plans, coordinates, and evaluates"""

    def __init__(self, model: str, client: ollama.Client):
        self.model = model
        self.client = client
        self.tool_names = registry.get_tool_names()
        self.plan = None
        self.context_history = []

    def _get_system_prompt(self) -> str:
        return ORCHESTRATOR_SYSTEM_PROMPT.format(
            tool_names=", ".join(self.tool_names)
        )

    def _call_llm(self, prompt: str) -> dict:
        """Call LLM and parse JSON response"""
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ]
        )

        content = response["message"]["content"]

        # Try to extract JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except json.JSONDecodeError:
            # Return raw content if not valid JSON
            return {"raw_response": content}

    async def analyze_and_plan(self, user_task: str) -> dict:
        """Analyze user task and create execution plan"""
        print(f"[Orchestrator] Analyzing task: {user_task}")

        prompt = PLAN_PROMPT.format(task=user_task)
        self.plan = self._call_llm(prompt)
        self.plan["original_task"] = user_task

        print(f"[Orchestrator] Plan created with {len(self.plan.get('subtasks', []))} subtasks")
        return self.plan

    async def decide_next_action(
        self,
        completed_tasks: List[str],
        failed_tasks: List[str]
    ) -> dict:
        """Decide what to do next based on current state"""

        # Build context from history
        context = "\n".join(self.context_history[-5:]) if self.context_history else "No previous results yet."

        # Get remaining subtasks
        all_subtasks = self.plan.get("subtasks", [])
        completed_ids = set(completed_tasks)
        failed_ids = set(failed_tasks)
        remaining = [
            s for s in all_subtasks
            if s["id"] not in completed_ids and s["id"] not in failed_ids
        ]

        prompt = NEXT_ACTION_PROMPT.format(
            original_task=self.plan.get("original_task", ""),
            completed=", ".join(completed_tasks) if completed_tasks else "None",
            failed=", ".join(failed_tasks) if failed_tasks else "None",
            remaining=json.dumps(remaining) if remaining else "None",
            context=context
        )

        result = self._call_llm(prompt)
        print(f"[Orchestrator] Next action: {result.get('action', 'unknown')}")
        return result

    async def create_task_assignment(
        self,
        task_description: str,
        context: Optional[str] = None
    ) -> TaskAssignment:
        """Create a task assignment for the executor"""
        return TaskAssignment(
            content=task_description,
            context=context or "\n".join(self.context_history[-3:])
        )

    async def provide_clarification(
        self,
        request: ClarificationRequest,
        original_task: str
    ) -> ClarificationResponse:
        """Answer executor's clarification question"""
        print(f"[Orchestrator] Providing clarification for: {request.content[:50]}...")

        prompt = CLARIFICATION_PROMPT.format(
            task_description=original_task,
            question=request.content
        )

        result = self._call_llm(prompt)

        return ClarificationResponse(
            task_id=request.task_id,
            content=result.get("clarification", "Please proceed with your best judgment."),
            action=result.get("action", "continue")
        )

    async def evaluate_result(self, result: TaskResult, task_description: str) -> dict:
        """Evaluate executor's result"""
        print(f"[Orchestrator] Evaluating result for task {result.task_id}")

        prompt = EVALUATE_PROMPT.format(
            task_description=task_description,
            status=result.status.value,
            content=result.content
        )

        evaluation = self._call_llm(prompt)

        # Add to context history
        self.context_history.append(
            f"Task: {task_description}\nResult: {result.content}\nFindings: {evaluation.get('key_findings', '')}"
        )

        return evaluation

    async def generate_final_summary(
        self,
        completed_tasks: List[str],
        failed_tasks: List[str]
    ) -> str:
        """Generate final summary for the user"""
        # Use decide_next_action with complete action to get summary
        result = await self.decide_next_action(completed_tasks, failed_tasks)

        if "final_summary" in result:
            return result["final_summary"]

        # Fallback summary
        context = "\n".join(self.context_history)
        return f"Task completed. {len(completed_tasks)} subtasks succeeded, {len(failed_tasks)} failed.\n\nResults:\n{context}"
