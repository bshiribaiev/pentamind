"""
Pentamind FastAPI backend server.

Production-ready backend with intelligent model routing via LangGraph.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from agent.types import (
    InferRequest,
    InferResponse,
    RunJuryRequest,
    RunJuryResponse,
    TraceStep,
    Message,
)
from agent.call_model import call_do_chat_completion, ModelAPIError, get_model_access_key
from agent.langgraph_flow import run_jury_workflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    """
    # Startup: Validate environment
    logger.info("Starting Pentamind backend...")
    try:
        get_model_access_key()
        logger.info("✓ MODEL_ACCESS_KEY found")
    except ModelAPIError as e:
        logger.error(f"✗ Startup validation failed: {e}")
        logger.error("Please set MODEL_ACCESS_KEY environment variable")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Pentamind backend...")


app = FastAPI(
    title="Pentamind API",
    description="Intelligent multi-model routing with web search and long-context support",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Exception Handlers ====================

@app.exception_handler(ModelAPIError)
async def model_api_error_handler(request: Request, exc: ModelAPIError):
    """Handle ModelAPIError exceptions."""
    logger.error(f"ModelAPIError: {exc}")
    return JSONResponse(
        status_code=502,
        content={
            "error": "model_api_error",
            "message": str(exc),
        },
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    logger.error(f"ValidationError: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "validation_error",
            "message": "Invalid request payload",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
        },
    )


# ==================== Endpoints ====================

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON with ok status
    """
    return {"ok": True}


@app.post("/infer", response_model=InferResponse)
async def infer(request: InferRequest):
    """
    Generic single-model inference endpoint.
    
    Args:
        request: InferRequest with model, messages, and parameters
        
    Returns:
        InferResponse with final output, model, latency, usage, and trace
        
    Raises:
        HTTPException: On validation or API errors
    """
    logger.info(f"POST /infer - model={request.model}")
    
    try:
        # Validate environment
        get_model_access_key()
    except ModelAPIError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Configuration error: {str(e)}",
        )
    
    try:
        # Call the model
        result = call_do_chat_completion(
            model=request.model,
            messages=request.messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        
        # Build response
        response = InferResponse(
            final=result.content,
            model=result.model,
            latency_ms=result.latency_ms,
            usage=result.usage,
            trace=[
                TraceStep(
                    step="infer",
                    model=result.model,
                    latency_ms=result.latency_ms,
                )
            ],
        )
        
        logger.info(f"✓ /infer completed in {result.latency_ms}ms")
        return response
        
    except ModelAPIError as e:
        logger.error(f"Model API error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Model API error: {str(e)}",
        )
    
    except Exception as e:
        logger.exception(f"Unexpected error in /infer: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}",
        )


@app.post("/run_jury", response_model=RunJuryResponse)
async def run_jury(request: RunJuryRequest):
    """
    Run the LangGraph jury routing pipeline.
    
    This endpoint:
    1. Classifies the task using a router model
    2. Selects the best model for the task
    3. Executes the task
    4. Verifies the result
    5. Falls back to GPT-5 if needed
    
    Args:
        request: RunJuryRequest with task, input, and mode
        
    Returns:
        RunJuryResponse with final result, winner model, task spec, scoreboard, and trace
        
    Raises:
        HTTPException: On validation or API errors
    """
    logger.info(f"POST /run_jury - task={request.task}, mode={request.mode}")
    
    try:
        # Validate environment
        get_model_access_key()
    except ModelAPIError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Configuration error: {str(e)}",
        )
    
    try:
        # Run the workflow
        final_state = run_jury_workflow(
            task=request.task,
            input_text=request.input,
            mode=request.mode,
        )
        
        # Build response
        response = RunJuryResponse(
            final=final_state.result or "No result generated",
            winner_model=final_state.chosen_model or "none",
            task_spec=final_state.task_spec,
            scoreboard=final_state.scoreboard,
            trace=final_state.trace,
        )
        
        logger.info(
            f"✓ /run_jury completed - winner={response.winner_model}, "
            f"steps={len(response.trace)}"
        )
        return response
        
    except ModelAPIError as e:
        logger.error(f"Model API error in jury workflow: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Model API error: {str(e)}",
        )
    
    except Exception as e:
        logger.exception(f"Unexpected error in /run_jury: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}",
        )


# ==================== Root ====================

@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "service": "Pentamind API",
        "version": "1.0.0",
        "description": "Intelligent multi-model routing platform",
        "endpoints": {
            "health": "GET /health",
            "infer": "POST /infer",
            "run_jury": "POST /run_jury",
        },
        "features": [
            "Smart model routing (coding/reasoning/general)",
            "Perplexity web search integration",
            "Gemini long-context support (2M tokens)",
            "Full execution traces"
        ],
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

