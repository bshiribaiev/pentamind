"""
LangGraph workflow for intelligent model routing.
"""
import json
import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from .types import (
    GraphState,
    TaskSpec,
    ScoreboardEntry,
    TraceStep,
    Message,
)
from .call_model import call_do_chat_completion, ModelAPIError

logger = logging.getLogger(__name__)

# Model identifiers
# Using DigitalOcean-owned models to avoid subscription tier issues
ROUTER_MODEL = "llama3-8b-instruct"  # Fast & cheap for routing
CODING_MODEL = "llama3.3-70b-instruct"  # Best DO model for coding
REASONING_MODEL = "deepseek-r1-distill-llama-70b"  # DO model for reasoning
FALLBACK_MODEL = "llama3.3-70b-instruct"  # Reliable DO fallback

# Router prompt for task classification
ROUTER_SYSTEM_PROMPT = """You are a task classifier. Analyze the user's task and return ONLY a JSON object with this exact structure:

{
  "intent": "code|reasoning|general",
  "format": "text|diff|json",
  "needs_citations": true|false,
  "confidence": 0.0
}

Guidelines:
- intent="code" for coding tasks, refactoring, debugging, writing code
- intent="reasoning" for complex problem-solving, analysis, research, math
- intent="general" for summarization, rewriting, simple questions
- format="diff" if output should be code changes
- format="json" if structured data is expected
- format="text" otherwise
- needs_citations=true if sources/references are needed
- confidence is 0.0-1.0 based on clarity of the task

Return ONLY the JSON object, no explanation."""


def classify_task(state: GraphState) -> Dict[str, Any]:
    """
    Node: Classify the task using the router model.
    """
    logger.info(f"Classifying task: {state.task}")
    
    user_prompt = f"Task type: {state.task}\nUser input: {state.input}"
    
    messages = [
        Message(role="system", content=ROUTER_SYSTEM_PROMPT),
        Message(role="user", content=user_prompt),
    ]
    
    try:
        result = call_do_chat_completion(
            model=ROUTER_MODEL,
            messages=messages,
            max_tokens=200,
            temperature=0.1,
            timeout=30.0,
        )
        
        # Try to parse JSON
        try:
            task_spec_data = json.loads(result.content.strip())
            task_spec = TaskSpec(**task_spec_data)
        except Exception as e:
            logger.warning(f"Failed to parse task spec JSON: {e}, using defaults")
            # Fallback to defaults
            task_spec = TaskSpec(
                intent="general",
                format="text",
                needs_citations=False,
                confidence=0.5,
            )
        
        trace_step = TraceStep(
            step="classify_task",
            model=ROUTER_MODEL,
            latency_ms=result.latency_ms,
            data=task_spec.dict(),
        )
        
        return {
            "task_spec": task_spec,
            "trace": state.trace + [trace_step],
        }
        
    except ModelAPIError as e:
        logger.error(f"Classification failed: {e}")
        # Use default classification on error
        task_spec = TaskSpec(
            intent="general",
            format="text",
            needs_citations=False,
            confidence=0.3,
        )
        
        trace_step = TraceStep(
            step="classify_task",
            model=ROUTER_MODEL,
            latency_ms=0,
            data={"error": str(e), "fallback": task_spec.dict()},
        )
        
        return {
            "task_spec": task_spec,
            "trace": state.trace + [trace_step],
        }


def choose_model(state: GraphState) -> Dict[str, Any]:
    """
    Node: Select the best model based on task classification.
    """
    task_spec = state.task_spec
    
    if task_spec.intent == "code":
        chosen = CODING_MODEL
        cost_tier = "high"
    elif task_spec.intent == "reasoning":
        chosen = REASONING_MODEL
        cost_tier = "med"
    else:
        chosen = FALLBACK_MODEL
        cost_tier = "high"
    
    logger.info(f"Chosen model: {chosen} (intent={task_spec.intent})")
    
    # Build scoreboard with all candidates
    scoreboard = [
        ScoreboardEntry(
            model=CODING_MODEL,
            cost_tier="high",
            notes="Best for coding tasks" if chosen == CODING_MODEL else "",
        ),
        ScoreboardEntry(
            model=REASONING_MODEL,
            cost_tier="med",
            notes="Best for reasoning tasks" if chosen == REASONING_MODEL else "",
        ),
        ScoreboardEntry(
            model=FALLBACK_MODEL,
            cost_tier="high",
            notes="General purpose fallback" if chosen == FALLBACK_MODEL else "",
        ),
    ]
    
    trace_step = TraceStep(
        step="choose_model",
        data={"winner": chosen, "intent": task_spec.intent},
    )
    
    return {
        "chosen_model": chosen,
        "scoreboard": scoreboard,
        "trace": state.trace + [trace_step],
    }


def execute(state: GraphState) -> Dict[str, Any]:
    """
    Node: Execute the task using the chosen model.
    """
    model = state.chosen_model
    task_spec = state.task_spec
    
    # Build task-specific prompt
    if task_spec.intent == "code":
        system_prompt = "You are an expert coding assistant. Provide clear, correct code."
    elif task_spec.intent == "reasoning":
        system_prompt = "You are a reasoning expert. Think step-by-step and provide detailed analysis."
    else:
        system_prompt = "You are a helpful assistant."
    
    # Format instructions
    format_instructions = ""
    if task_spec.format == "diff":
        format_instructions = "\n\nProvide output as a unified diff format starting with --- and +++."
    elif task_spec.format == "json":
        format_instructions = "\n\nProvide output as valid JSON."
    
    system_prompt += format_instructions
    
    if task_spec.needs_citations:
        system_prompt += "\n\nInclude citations and references where applicable."
    
    user_prompt = f"Task: {state.task}\n\n{state.input}"
    
    messages = [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]
    
    try:
        result = call_do_chat_completion(
            model=model,
            messages=messages,
            max_tokens=2000,
            temperature=0.3,
            timeout=60.0,
        )
        
        # Update scoreboard with actual latency
        updated_scoreboard = []
        for entry in state.scoreboard:
            if entry.model == model:
                entry.latency_ms = result.latency_ms
                entry.quality = 0.9  # Placeholder
            updated_scoreboard.append(entry)
        
        trace_step = TraceStep(
            step="execute",
            model=model,
            latency_ms=result.latency_ms,
        )
        
        return {
            "result": result.content,
            "scoreboard": updated_scoreboard,
            "trace": state.trace + [trace_step],
        }
        
    except ModelAPIError as e:
        logger.error(f"Execution failed with {model}: {e}")
        
        trace_step = TraceStep(
            step="execute",
            model=model,
            latency_ms=0,
            data={"error": str(e)},
        )
        
        return {
            "result": None,
            "trace": state.trace + [trace_step],
        }


def verify(state: GraphState) -> Dict[str, Any]:
    """
    Node: Verify the result meets format requirements.
    """
    result = state.result
    task_spec = state.task_spec
    
    if not result:
        logger.warning("No result to verify")
        return {"verification_passed": False}
    
    passed = True
    verification_notes = []
    
    if task_spec.format == "json":
        try:
            json.loads(result)
            verification_notes.append("Valid JSON")
        except Exception:
            passed = False
            verification_notes.append("Invalid JSON")
    
    elif task_spec.format == "diff":
        if not ("+++" in result and "---" in result):
            if not result.startswith("diff"):
                passed = False
                verification_notes.append("Not a valid diff format")
            else:
                verification_notes.append("Diff format detected")
        else:
            verification_notes.append("Diff format valid")
    
    else:
        # Text format - minimal check
        if len(result.strip()) > 0:
            verification_notes.append("Non-empty response")
        else:
            passed = False
            verification_notes.append("Empty response")
    
    logger.info(f"Verification: {'PASSED' if passed else 'FAILED'} - {verification_notes}")
    
    trace_step = TraceStep(
        step="verify",
        data={"passed": passed, "notes": verification_notes},
    )
    
    return {
        "verification_passed": passed,
        "trace": state.trace + [trace_step],
    }


def fallback(state: GraphState) -> Dict[str, Any]:
    """
    Node: Fallback to GPT-5 if verification fails.
    """
    logger.info("Running fallback with GPT-5")
    
    task_spec = state.task_spec
    
    system_prompt = "You are a helpful assistant. Provide accurate responses."
    if task_spec.format == "json":
        system_prompt += "\n\nProvide output as valid JSON."
    elif task_spec.format == "diff":
        system_prompt += "\n\nProvide output as a unified diff format."
    
    user_prompt = f"Task: {state.task}\n\n{state.input}"
    
    messages = [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]
    
    try:
        result = call_do_chat_completion(
            model=FALLBACK_MODEL,
            messages=messages,
            max_tokens=2000,
            temperature=0.3,
            timeout=60.0,
        )
        
        # Update scoreboard
        updated_scoreboard = []
        for entry in state.scoreboard:
            if entry.model == FALLBACK_MODEL:
                entry.latency_ms = result.latency_ms
                entry.quality = 0.8
                entry.notes = "Used as fallback"
            updated_scoreboard.append(entry)
        
        trace_step = TraceStep(
            step="fallback",
            model=FALLBACK_MODEL,
            latency_ms=result.latency_ms,
        )
        
        return {
            "result": result.content,
            "chosen_model": FALLBACK_MODEL,
            "fallback_attempted": True,
            "verification_passed": True,  # Accept fallback result
            "scoreboard": updated_scoreboard,
            "trace": state.trace + [trace_step],
        }
        
    except ModelAPIError as e:
        logger.error(f"Fallback failed: {e}")
        
        trace_step = TraceStep(
            step="fallback",
            model=FALLBACK_MODEL,
            latency_ms=0,
            data={"error": str(e)},
        )
        
        # Return original result even if fallback fails
        return {
            "fallback_attempted": True,
            "verification_passed": True,  # Accept what we have
            "trace": state.trace + [trace_step],
        }


def should_fallback(state: GraphState) -> str:
    """
    Conditional edge: Decide if fallback is needed.
    """
    if not state.verification_passed and not state.fallback_attempted:
        logger.info("Routing to fallback")
        return "fallback"
    else:
        logger.info("Routing to end")
        return END


def build_jury_graph() -> StateGraph:
    """
    Build and compile the LangGraph workflow.
    """
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("classify_task", classify_task)
    workflow.add_node("choose_model", choose_model)
    workflow.add_node("execute", execute)
    workflow.add_node("verify", verify)
    workflow.add_node("fallback", fallback)
    
    # Add edges
    workflow.set_entry_point("classify_task")
    workflow.add_edge("classify_task", "choose_model")
    workflow.add_edge("choose_model", "execute")
    workflow.add_edge("execute", "verify")
    
    # Conditional edge from verify
    workflow.add_conditional_edges(
        "verify",
        should_fallback,
        {
            "fallback": "fallback",
            END: END,
        }
    )
    
    workflow.add_edge("fallback", END)
    
    return workflow.compile()


def run_jury_workflow(task: str, input_text: str, mode: str = "best") -> GraphState:
    """
    Execute the full jury workflow.
    
    Args:
        task: Task type (summarize, research, solve, code, rewrite)
        input_text: User input
        mode: Execution mode (best, fast, cheap)
        
    Returns:
        Final GraphState with results and trace
    """
    logger.info(f"Starting jury workflow: task={task}, mode={mode}")
    
    graph = build_jury_graph()
    
    initial_state = GraphState(
        task=task,
        input=input_text,
        mode=mode,
        trace=[],
        scoreboard=[],
    )
    
    final_state = graph.invoke(initial_state)
    
    logger.info("Jury workflow completed")
    
    return GraphState(**final_state)

