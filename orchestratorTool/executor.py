import ollama
import json
from typing import Union, List
from models import (
    TaskAssignment, TaskResult, ClarificationRequest,
    ClarificationResponse, MessageStatus
)
from tools import registry
from config import EXECUTOR_MAX_TOOL_CALLS


EXECUTOR_SYSTEM_PROMPT = """You are a task executor AI. Your role is to:
1. Execute specific tasks assigned by the orchestrator
2. Use available tools effectively to complete tasks
3. Report results clearly and honestly
4. Ask for clarification if instructions are ambiguous

Guidelines:
- Be thorough but efficient in tool usage
- If you cannot complete a task, explain why
- If instructions are unclear, ask for clarification instead of guessing
- Always provide useful results, even if partial

Available tools: {tool_names}

Response format:
- If task is complete: Provide the result clearly
- If you need clarification: Ask a specific question
- If task failed: Explain what went wrong"""


class Executor:
    """Executor AI that performs tasks using tools"""

    def __init__(self, model: str, client: ollama.Client):
        self.model = model
        self.client = client
        self.tools = registry.get_tools()
        self.tool_names = registry.get_tool_names()

    def _get_system_prompt(self) -> str:
        return EXECUTOR_SYSTEM_PROMPT.format(tool_names=", ".join(self.tool_names))

    async def execute_task(
        self,
        assignment: TaskAssignment
    ) -> Union[TaskResult, ClarificationRequest]:
        """Execute an assigned task, return result or clarification request"""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": f"""Task ID: {assignment.task_id}

Instructions:
{assignment.content}

{f"Context: {assignment.context}" if assignment.context else ""}

Execute this task using the available tools. Provide a clear result."""}
        ]

        tools_used = []
        tool_call_count = 0

        # Tool calling loop
        for _ in range(EXECUTOR_MAX_TOOL_CALLS):
            response = self.client.chat(
                model=self.model,
                messages=messages,
                tools=self.tools
            )

            message = response["message"]
            tool_calls = message.get("tool_calls", [])

            # No tool calls = we have a final response
            if not tool_calls:
                content = message.get("content", "")

                # Check if executor is asking for clarification
                clarification_indicators = [
                    "unclear", "clarify", "clarification",
                    "what do you mean", "could you explain",
                    "not sure what", "ambiguous"
                ]
                is_clarification = any(
                    indicator in content.lower()
                    for indicator in clarification_indicators
                )

                if is_clarification and "?" in content:
                    return ClarificationRequest(
                        task_id=assignment.task_id,
                        content=content
                    )

                # Determine status based on content
                failure_indicators = ["failed", "error", "could not", "unable to"]
                status = MessageStatus.FAILURE if any(
                    ind in content.lower() for ind in failure_indicators
                ) else MessageStatus.SUCCESS

                return TaskResult(
                    task_id=assignment.task_id,
                    status=status,
                    content=content,
                    tools_used=tools_used
                )

            # Process tool calls
            messages.append(message)

            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                args = tool_call["function"]["arguments"]

                print(f"[Executor] Calling tool: {func_name}({args})")

                if func_name not in tools_used:
                    tools_used.append(func_name)
                tool_call_count += 1

                # Execute the tool
                result = registry.execute(func_name, args)

                # Add tool response to messages
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result, ensure_ascii=False)
                })

        # Max tool calls reached
        return TaskResult(
            task_id=assignment.task_id,
            status=MessageStatus.PARTIAL,
            content="Maximum tool calls reached. Partial results may be available.",
            tools_used=tools_used
        )

    async def continue_after_clarification(
        self,
        assignment: TaskAssignment,
        clarification: ClarificationResponse
    ) -> TaskResult:
        """Continue task after receiving clarification"""

        # Build context with clarification
        enhanced_content = f"""{assignment.content}

Additional clarification from orchestrator:
{clarification.content}"""

        if clarification.action == "abort":
            return TaskResult(
                task_id=assignment.task_id,
                status=MessageStatus.FAILURE,
                content="Task aborted by orchestrator.",
                tools_used=[]
            )

        # Create modified assignment with clarification
        modified_assignment = TaskAssignment(
            task_id=assignment.task_id,
            content=enhanced_content,
            context=assignment.context
        )

        # Re-execute with clarification
        result = await self.execute_task(modified_assignment)

        # If still asking for clarification, force a result
        if isinstance(result, ClarificationRequest):
            return TaskResult(
                task_id=assignment.task_id,
                status=MessageStatus.PARTIAL,
                content=f"Could not complete task even with clarification. Last response: {result.content}",
                tools_used=[]
            )

        return result
