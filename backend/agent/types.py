"""
Type definitions for Pentamind backend.
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# ==================== Request Models ====================

class Message(BaseModel):
    """Chat message format."""
    role: str
    content: str


class InferRequest(BaseModel):
    """Request schema for /infer endpoint."""
    model: str
    messages: List[Message]
    max_tokens: int = 200
    temperature: float = 0.2


class RunJuryRequest(BaseModel):
    """Request schema for /run_jury endpoint."""
    task: Literal["summarize", "research", "solve", "code", "rewrite"]
    input: str
    mode: Literal["best", "fast", "cheap"] = "best"


# ==================== Response Models ====================

class TraceStep(BaseModel):
    """Single step in execution trace."""
    step: str
    model: Optional[str] = None
    latency_ms: int = 0
    data: Dict[str, Any] = Field(default_factory=dict)


class InferResponse(BaseModel):
    """Response schema for /infer endpoint."""
    final: str
    model: str
    latency_ms: int
    usage: Dict[str, Any] = Field(default_factory=dict)
    trace: List[TraceStep]


class TaskSpec(BaseModel):
    """Task classification result."""
    intent: Literal["code", "reasoning", "general"]
    format: Literal["text", "diff", "json"]
    needs_citations: bool = False
    confidence: float = 0.0


class ScoreboardEntry(BaseModel):
    """Model performance entry."""
    model: str
    quality: float = 0.0
    latency_ms: int = 0
    cost_tier: Literal["high", "med", "low"] = "med"
    notes: str = ""


class RunJuryResponse(BaseModel):
    """Response schema for /run_jury endpoint."""
    final: str
    winner_model: str
    task_spec: TaskSpec
    scoreboard: List[ScoreboardEntry]
    trace: List[TraceStep]


# ==================== Internal State Models ====================

class GraphState(BaseModel):
    """LangGraph state object."""
    # Input
    task: str
    input: str
    mode: str
    
    # Classification
    task_spec: Optional[TaskSpec] = None
    
    # Model selection
    chosen_model: Optional[str] = None
    
    # Execution
    result: Optional[str] = None
    verification_passed: bool = False
    fallback_attempted: bool = False
    
    # Metrics
    scoreboard: List[ScoreboardEntry] = Field(default_factory=list)
    trace: List[TraceStep] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True


class ModelCallResult(BaseModel):
    """Result from model API call."""
    content: str
    latency_ms: int
    usage: Dict[str, Any] = Field(default_factory=dict)
    model: str

