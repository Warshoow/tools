from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Union
from enum import Enum
from datetime import datetime
import uuid


# ============== Enums ==============

class MessageType(str, Enum):
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    CLARIFICATION_REQUEST = "clarification_request"
    CLARIFICATION_RESPONSE = "clarification_response"
    COMPLETION = "completion"


class MessageStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    NEEDS_CLARIFICATION = "needs_clarification"


# ============== Inter-AI Messages ==============

class BaseMessage(BaseModel):
    """Base for all inter-AI messages"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskAssignment(BaseMessage):
    """Orchestrator assigns a task to Executor"""
    message_type: Literal[MessageType.TASK_ASSIGNMENT] = MessageType.TASK_ASSIGNMENT
    sender: Literal["orchestrator"] = "orchestrator"
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:6]}")
    content: str = Field(..., description="Task instructions in natural language")
    context: Optional[str] = Field(None, description="Additional context from previous steps")


class TaskResult(BaseMessage):
    """Executor reports results to Orchestrator"""
    message_type: Literal[MessageType.TASK_RESULT] = MessageType.TASK_RESULT
    sender: Literal["executor"] = "executor"
    task_id: str
    status: MessageStatus
    content: str = Field(..., description="Result in natural language")
    result_data: Optional[dict] = None
    tools_used: List[str] = Field(default_factory=list)


class ClarificationRequest(BaseMessage):
    """Executor asks for clarification"""
    message_type: Literal[MessageType.CLARIFICATION_REQUEST] = MessageType.CLARIFICATION_REQUEST
    sender: Literal["executor"] = "executor"
    task_id: str
    content: str = Field(..., description="Clarification question")


class ClarificationResponse(BaseMessage):
    """Orchestrator provides clarification"""
    message_type: Literal[MessageType.CLARIFICATION_RESPONSE] = MessageType.CLARIFICATION_RESPONSE
    sender: Literal["orchestrator"] = "orchestrator"
    task_id: str
    content: str = Field(..., description="Clarification answer")
    action: Literal["continue", "modify_task", "abort"] = "continue"


class CompletionMessage(BaseMessage):
    """Orchestrator signals overall completion"""
    message_type: Literal[MessageType.COMPLETION] = MessageType.COMPLETION
    sender: Literal["orchestrator"] = "orchestrator"
    status: MessageStatus
    content: str = Field(..., description="Final summary")
    completed_tasks: List[str] = Field(default_factory=list)
    failed_tasks: List[str] = Field(default_factory=list)


# Union type for any message
InterAIMessage = Union[TaskAssignment, TaskResult, ClarificationRequest, ClarificationResponse, CompletionMessage]


# ============== API Request/Response ==============

class OrchestrateRequest(BaseModel):
    """User request to the orchestration system"""
    task: str = Field(..., description="High-level task description")
    orchestrator_model: Optional[str] = None
    executor_model: Optional[str] = None
    max_iterations: int = Field(default=20, ge=1, le=100)
    max_clarifications: int = Field(default=5, ge=0, le=20)
    include_conversation_history: bool = True


class OrchestrateResponse(BaseModel):
    """Response from orchestration system"""
    success: bool
    final_result: str
    total_iterations: int
    clarifications_made: int
    tasks_completed: int
    tasks_failed: int
    conversation_history: Optional[List[dict]] = None
    error: Optional[str] = None
