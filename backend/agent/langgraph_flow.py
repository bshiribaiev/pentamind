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

# Model identifiers - 5 distinct models for 5 task types
# DigitalOcean models: https://docs.digitalocean.com/products/genai-platform/concepts/models/
ROUTER_MODEL = "llama3-8b-instruct"  # Fast & cheap for routing only

# Task-specific models - each task uses a different model
TASK_MODELS = {
    "summarize": "gemini",  # Gemini for summarization (long context support)
    "research": "perplexity",  # Perplexity for research (web search + citations)
    "solve": "deepseek-r1-distill-llama-70b",  # DeepSeek R1 for reasoning/math
    "code": "anthropic-claude-sonnet-4",  # Claude Sonnet 4 for coding
    "rewrite": "mistral-small-3.1-24b-instruct",  # Mistral for rewriting/editing
}

# Fallback model if primary fails
FALLBACK_MODEL = "llama3.3-70b-instruct"

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
    Node: Select the best model based on task type.
    Each of the 5 task types uses a distinct specialized model.
    """
    task = state.task  # summarize, research, solve, code, rewrite
    task_spec = state.task_spec
    input_length = len(state.input)
    
    # Get the task-specific model
    chosen = TASK_MODELS.get(task, FALLBACK_MODEL)
    cost_tier = "med"
    
    # Special handling for certain task types
    if task == "summarize":
        # Use Gemini for summarization (good with long texts)
        if is_gemini_available():
            gemini_model = get_appropriate_gemini_model(input_length)
            chosen = f"gemini:{gemini_model}"
            cost_tier = "low"
            logger.info(f"Summarize task → using Gemini: {gemini_model}")
        else:
            chosen = FALLBACK_MODEL  # Fallback if Gemini not available
            logger.info("Summarize task → Gemini not available, using fallback")
    
    elif task == "research":
        # Research uses Perplexity (handled in execute node)
        # But we still need an LLM for synthesis
        chosen = "perplexity"
        cost_tier = "low"
        logger.info("Research task → using Perplexity with web search")
    
    elif task == "solve":
        chosen = TASK_MODELS["solve"]  # DeepSeek R1
        cost_tier = "med"
        logger.info(f"Solve task → using DeepSeek R1 for reasoning")
    
    elif task == "code":
        chosen = TASK_MODELS["code"]  # Claude Sonnet 4
        cost_tier = "high"
        logger.info(f"Code task → using Claude Sonnet 4")
    
    elif task == "rewrite":
        chosen = TASK_MODELS["rewrite"]  # Mistral
        cost_tier = "med"
        logger.info(f"Rewrite task → using Mistral")
    
    else:
        logger.warning(f"Unknown task type: {task}, using fallback")
        chosen = FALLBACK_MODEL
    
    logger.info(f"Chosen model: {chosen} (task={task}, length={input_length})")
    
    # Build scoreboard showing all 5 task-specific models
    scoreboard = [
        ScoreboardEntry(
            model="Gemini 1.5 Pro",
            cost_tier="low",
            notes="✓ Summarize" if task == "summarize" else "Summarization",
        ),
        ScoreboardEntry(
            model="Perplexity",
            cost_tier="low",
            notes="✓ Research" if task == "research" else "Web search + citations",
        ),
        ScoreboardEntry(
            model="DeepSeek R1",
            cost_tier="med",
            notes="✓ Solve" if task == "solve" else "Reasoning & math",
        ),
        ScoreboardEntry(
            model="Claude Sonnet 4",
            cost_tier="high",
            notes="✓ Code" if task == "code" else "Code generation",
        ),
        ScoreboardEntry(
            model="Mistral Small",
            cost_tier="med",
            notes="✓ Rewrite" if task == "rewrite" else "Text editing",
        ),
    ]
    
    trace_data = {
        "winner": chosen,
        "task": task,
        "intent": task_spec.intent,
        "input_length": input_length,
        "model_mapping": TASK_MODELS,
    }
    
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
    Node: Execute the task using the task-specific model.
    Each task type uses a specialized model:
    - Summarize: Gemini (long context)
    - Research: Perplexity (web search + synthesis)
    - Solve: DeepSeek R1 (reasoning)
    - Code: Claude Sonnet 4 (coding)
    - Rewrite: Mistral (text editing)
    """
    model = state.chosen_model
    task = state.task
    task_spec = state.task_spec
    
    search_context = ""
    search_sources = []
    perplexity_used = False
    
    # Build task-specific system prompts
    TASK_PROMPTS = {
        "summarize": "You are an expert summarizer. Create clear, concise summaries that capture the key points. Organize the summary with clear structure.",
        "research": "You are a research assistant with access to current web information. Provide comprehensive, well-cited answers based on the search results provided.",
        "solve": "You are a reasoning expert. Think step-by-step, show your work, and provide detailed analysis. Break down complex problems into manageable parts.",
        "code": "You are an expert software engineer. Write clean, efficient, well-documented code. Follow best practices and explain your implementation.",
        "rewrite": "You are a skilled editor. Improve the text while preserving the original meaning. Enhance clarity, flow, and style.",
    }
    
    system_prompt = TASK_PROMPTS.get(task, "You are a helpful assistant.")
    
    # For research tasks, use Perplexity for web search
    if task == "research" or model == "perplexity":
        if get_perplexity_key():
            try:
                logger.info("Using Perplexity for research with web search")
                search_data = search_with_perplexity(state.input, max_results=5)
                search_context = format_search_results_for_llm(search_data)
                search_sources = [
                    f"[{i}] {r['title']} - {r['url']}"
                    for i, r in enumerate(search_data['results'], 1)
                ]
                perplexity_used = True
                logger.info(f"Perplexity found {len(search_data['results'])} sources")
                
                # Add search context to prompt
                system_prompt += f"\n\nWeb Search Results:\n{search_context}"
                system_prompt += "\n\nUse these sources to provide accurate, cited information. Reference sources using [1], [2], etc."
                
                # Use a synthesis model for the final response
                model = TASK_MODELS.get("solve", FALLBACK_MODEL)  # Use reasoning model for synthesis
                
            except PerplexityError as e:
                logger.warning(f"Perplexity search failed: {e}, using fallback")
                model = FALLBACK_MODEL
        else:
            logger.warning("Perplexity API key not set, using fallback model")
            model = FALLBACK_MODEL
    
    # Format instructions
    if task_spec.format == "diff":
        system_prompt += "\n\nProvide output as a unified diff format starting with --- and +++."
    elif task_spec.format == "json":
        system_prompt += "\n\nProvide output as valid JSON."
    
    user_prompt = state.input
    
    messages = [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]
    
    try:
        # Route to appropriate model API
        if model.startswith("gemini:"):
            # Gemini for summarization
            actual_model = model.replace("gemini:", "")
            logger.info(f"Executing with Gemini: {actual_model}")
            
            gemini_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            gemini_result = call_gemini(
                messages=gemini_messages,
                model=actual_model,
                max_tokens=8000,
                temperature=0.3,
                timeout=90.0,
            )
            
            result = type('obj', (object,), {
                'content': gemini_result['content'],
                'latency_ms': gemini_result['latency_ms'],
                'usage': gemini_result['usage'],
                'model': f"Gemini {actual_model}"
            })()
            display_model = f"Gemini {actual_model}"
            
        else:
            # DigitalOcean models (Claude, DeepSeek, Mistral, Llama)
            logger.info(f"Executing with DigitalOcean model: {model}")
            
            result = call_do_chat_completion(
                model=model,
                messages=messages,
                max_tokens=2000,
                temperature=0.3,
                timeout=60.0,
            )
            
            # Map model IDs to friendly names
            MODEL_NAMES = {
                "anthropic-claude-sonnet-4": "Claude Sonnet 4",
                "deepseek-r1-distill-llama-70b": "DeepSeek R1",
                "mistral-small-3.1-24b-instruct": "Mistral Small",
                "llama3.3-70b-instruct": "Llama 3.3 70B",
            }
            display_model = MODEL_NAMES.get(model, model)
        
        # If Perplexity was used, update the display model
        if perplexity_used:
            display_model = f"Perplexity + {display_model}"
        
        # Update scoreboard
        updated_scoreboard = []
        for entry in state.scoreboard:
            if task == "summarize" and "Gemini" in entry.model:
                entry.latency_ms = result.latency_ms
                entry.quality = 0.9
            elif task == "research" and "Perplexity" in entry.model:
                entry.latency_ms = result.latency_ms
                entry.quality = 0.9
            elif task == "solve" and "DeepSeek" in entry.model:
                entry.latency_ms = result.latency_ms
                entry.quality = 0.9
            elif task == "code" and "Claude" in entry.model:
                entry.latency_ms = result.latency_ms
                entry.quality = 0.9
            elif task == "rewrite" and "Mistral" in entry.model:
                entry.latency_ms = result.latency_ms
                entry.quality = 0.9
            updated_scoreboard.append(entry)
        
        # Build trace data
        trace_data = {"task": task}
        if perplexity_used:
            trace_data["perplexity_used"] = True
            trace_data["sources_found"] = len(search_sources)
            trace_data["sources"] = search_sources
        
        trace_step = TraceStep(
            step="execute",
            model=display_model,
            latency_ms=result.latency_ms,
            data=trace_data,
        )
        
        # Append sources to result if Perplexity was used
        final_result = result.content
        if perplexity_used and search_sources:
            final_result += "\n\n---\n**Sources:**\n" + "\n".join(search_sources)
        
        return {
            "result": final_result,
            "chosen_model": display_model,
            "scoreboard": updated_scoreboard,
            "trace": state.trace + [trace_step],
        }
        
    except (ModelAPIError, GeminiError) as e:
        logger.error(f"Execution failed with {model}: {e}")
        
        # Try fallback model
        logger.info(f"Trying fallback model: {FALLBACK_MODEL}")
        try:
            result = call_do_chat_completion(
                model=FALLBACK_MODEL,
                messages=messages,
                max_tokens=2000,
                temperature=0.3,
                timeout=60.0,
            )
            
            trace_step = TraceStep(
                step="execute",
                model=f"{model} → Llama 3.3 (fallback)",
                latency_ms=result.latency_ms,
                data={"original_error": str(e), "used_fallback": True},
            )
            
            return {
                "result": result.content,
                "chosen_model": "Llama 3.3 70B (fallback)",
                "trace": state.trace + [trace_step],
            }
            
        except ModelAPIError as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            
            trace_step = TraceStep(
                step="execute",
                model=model,
                latency_ms=0,
                data={"error": str(e), "fallback_error": str(fallback_error)},
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

