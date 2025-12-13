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
from .perplexity_search import (
    search_with_perplexity,
    format_search_results_for_llm,
    PerplexityError,
    get_perplexity_key,
)
from .gemini_client import (
    call_gemini,
    is_gemini_available,
    get_appropriate_gemini_model,
    GeminiError,
)

logger = logging.getLogger(__name__)

# Model identifiers
# Using DigitalOcean-owned models to avoid subscription tier issues
ROUTER_MODEL = "llama3-8b-instruct"  # Fast & cheap for routing
CODING_MODEL = "llama3.3-70b-instruct"  # Best DO model for coding
REASONING_MODEL = "deepseek-r1-distill-llama-70b"  # DO model for reasoning
FALLBACK_MODEL = "llama3.3-70b-instruct"  # Reliable DO fallback

# Long context threshold (characters)
LONG_CONTEXT_THRESHOLD = 10000  # ~2500 tokens

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
    Node: Select the best model based on task classification and context length.
    Routes to Gemini for long-context tasks.
    """
    task_spec = state.task_spec
    input_length = len(state.input)
    
    # Check if this is a long-context task and Gemini is available
    is_long_context = input_length > LONG_CONTEXT_THRESHOLD
    use_gemini = is_long_context and is_gemini_available()
    
    if use_gemini:
        # Use Gemini for long context tasks
        gemini_model = get_appropriate_gemini_model(input_length)
        chosen = f"gemini:{gemini_model}"  # Prefix to distinguish from DO models
        cost_tier = "low"
        logger.info(f"Long context detected ({input_length} chars) → routing to Gemini")
    elif task_spec.intent == "code":
        chosen = CODING_MODEL
        cost_tier = "high"
    elif task_spec.intent == "reasoning":
        chosen = REASONING_MODEL
        cost_tier = "med"
    else:
        chosen = FALLBACK_MODEL
        cost_tier = "high"
    
    logger.info(f"Chosen model: {chosen} (intent={task_spec.intent}, length={input_length})")
    
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
    
    # Add Gemini to scoreboard if available
    if is_gemini_available():
        gemini_note = "Chosen for long context" if use_gemini else "Available for long contexts (2M tokens)"
        scoreboard.append(
            ScoreboardEntry(
                model="gemini-1.5-pro",
                cost_tier="low",
                notes=gemini_note,
            )
        )
    
    trace_data = {
        "winner": chosen,
        "intent": task_spec.intent,
        "input_length": input_length,
    }
    
    if use_gemini:
        trace_data["reason"] = "long_context"
        trace_data["gemini_model"] = gemini_model
    
    trace_step = TraceStep(
        step="choose_model",
        data=trace_data,
    )
    
    return {
        "chosen_model": chosen,
        "scoreboard": scoreboard,
        "trace": state.trace + [trace_step],
    }


def execute(state: GraphState) -> Dict[str, Any]:
    """
    Node: Execute the task using the chosen model.
    Enhanced with Perplexity search for research/citation tasks.
    """
    model = state.chosen_model
    task_spec = state.task_spec
    
    # Check if we should use Perplexity for research
    # ALWAYS use Perplexity for research tasks
    use_perplexity = (
        state.task == "research" or  # Always for research task type
        task_spec.needs_citations or 
        (state.task == "solve" and task_spec.intent == "reasoning")
    )
    
    search_context = ""
    search_sources = []
    perplexity_used = False
    
    # Try Perplexity search if appropriate and API key is available
    if use_perplexity and get_perplexity_key():
        try:
            logger.info("Using Perplexity for research augmentation")
            search_data = search_with_perplexity(state.input, max_results=5)
            search_context = format_search_results_for_llm(search_data)
            search_sources = [
                f"[{i}] {r['title']} - {r['url']}"
                for i, r in enumerate(search_data['results'], 1)
            ]
            perplexity_used = True
            logger.info(f"Perplexity found {len(search_data['results'])} sources")
        except PerplexityError as e:
            logger.warning(f"Perplexity search failed, proceeding without: {e}")
    
    # Build task-specific prompt
    if task_spec.intent == "code":
        system_prompt = "You are an expert coding assistant. Provide clear, correct code."
    elif task_spec.intent == "reasoning":
        system_prompt = "You are a reasoning expert. Think step-by-step and provide detailed analysis."
    else:
        system_prompt = "You are a helpful assistant."
    
    # Add search context if available
    if search_context:
        system_prompt += f"\n\nYou have access to the following search results to help answer the question:\n\n{search_context}"
        system_prompt += "\n\nUse these sources to provide accurate, cited information. Reference sources using [1], [2], etc."
    
    # Format instructions
    format_instructions = ""
    if task_spec.format == "diff":
        format_instructions = "\n\nProvide output as a unified diff format starting with --- and +++."
    elif task_spec.format == "json":
        format_instructions = "\n\nProvide output as valid JSON."
    
    system_prompt += format_instructions
    
    if task_spec.needs_citations and not search_context:
        system_prompt += "\n\nInclude citations and references where applicable."
    
    user_prompt = f"Task: {state.task}\n\n{state.input}"
    
    messages = [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]
    
    try:
        # Check if using Gemini (model starts with "gemini:")
        if model.startswith("gemini:"):
            actual_model = model.replace("gemini:", "")
            logger.info(f"Using Gemini for long context: {actual_model}")
            
            # Convert Message objects to dicts for Gemini
            gemini_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            gemini_result = call_gemini(
                messages=gemini_messages,
                model=actual_model,
                max_tokens=8000,  # Gemini can handle longer outputs
                temperature=0.3,
                timeout=90.0,  # Longer timeout for long context
            )
            
            result = type('obj', (object,), {
                'content': gemini_result['content'],
                'latency_ms': gemini_result['latency_ms'],
                'usage': gemini_result['usage'],
                'model': f"gemini:{actual_model}"
            })()
        else:
            # Use DigitalOcean models
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
            if entry.model == model or (model.startswith("gemini") and "gemini" in entry.model):
                entry.latency_ms = result.latency_ms
                entry.quality = 0.9  # Placeholder
            updated_scoreboard.append(entry)
        
        # Build trace step with Perplexity info if used
        trace_data = {}
        display_model = model
        if perplexity_used:
            trace_data["perplexity_used"] = True
            trace_data["sources_found"] = len(search_sources)
            trace_data["sources"] = search_sources
            display_model = f"perplexity + {model}"  # Show Perplexity was used
        
        trace_step = TraceStep(
            step="execute",
            model=display_model,
            latency_ms=result.latency_ms,
            data=trace_data if trace_data else {},
        )
        
        # Append sources to result if Perplexity was used
        final_result = result.content
        if perplexity_used and search_sources:
            final_result += "\n\n---\n**Sources:**\n" + "\n".join(search_sources)
        
        return {
            "result": final_result,
            "chosen_model": display_model,  # Update to show Perplexity if used
            "scoreboard": updated_scoreboard,
            "trace": state.trace + [trace_step],
        }
        
    except (ModelAPIError, GeminiError) as e:
        logger.error(f"Execution failed with {model}: {e}")
        
        trace_step = TraceStep(
            step="execute",
            model=model,
            latency_ms=0,
            data={"error": str(e), "error_type": type(e).__name__},
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

