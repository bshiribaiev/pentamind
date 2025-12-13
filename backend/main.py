"""
Pentamind FastAPI backend server.

Production-ready backend with intelligent model routing via LangGraph.
"""
import logging
import os
import tempfile
import io
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError, BaseModel
from typing import Optional

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

# Document parsing imports
try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# Speech recognition imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

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


# ==================== Document Parsing ====================

class DocumentResponse(BaseModel):
    text: str
    pages: Optional[int] = None
    filename: Optional[str] = None


@app.post("/parse_document", response_model=DocumentResponse)
async def parse_document(file: UploadFile = File(...)):
    """
    Parse a document (PDF, DOCX, DOC, TXT) and extract text.
    
    Args:
        file: Uploaded file
        
    Returns:
        DocumentResponse with extracted text
    """
    logger.info(f"POST /parse_document - filename={file.filename}")
    
    filename = file.filename or "unknown"
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    
    try:
        content = await file.read()
        
        if ext == "txt" or ext == "md" or ext == "json" or ext == "csv":
            # Plain text files
            text = content.decode("utf-8", errors="ignore")
            return DocumentResponse(text=text, filename=filename)
            
        elif ext == "pdf":
            if not PDF_AVAILABLE:
                raise HTTPException(
                    status_code=501,
                    detail="PDF parsing not available. Install pypdf: pip install pypdf"
                )
            
            # Parse PDF
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            text = "\n\n".join(text_parts)
            logger.info(f"✓ Parsed PDF: {len(reader.pages)} pages, {len(text)} chars")
            
            return DocumentResponse(
                text=text,
                pages=len(reader.pages),
                filename=filename
            )
            
        elif ext == "docx":
            if not DOCX_AVAILABLE:
                raise HTTPException(
                    status_code=501,
                    detail="DOCX parsing not available. Install python-docx: pip install python-docx"
                )
            
            # Parse DOCX
            docx_file = io.BytesIO(content)
            doc = DocxDocument(docx_file)
            
            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            
            text = "\n\n".join(text_parts)
            logger.info(f"✓ Parsed DOCX: {len(text_parts)} paragraphs, {len(text)} chars")
            
            return DocumentResponse(text=text, filename=filename)
            
        elif ext == "doc":
            raise HTTPException(
                status_code=400,
                detail="DOC format not supported. Please convert to DOCX or PDF."
            )
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {ext}. Supported: txt, md, json, csv, pdf, docx"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error parsing document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse document: {str(e)}"
        )


# ==================== Speech Recognition ====================

class TranscribeResponse(BaseModel):
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Transcribe audio to text using Whisper API or fallback to Google Speech Recognition.
    
    Args:
        audio: Uploaded audio file (webm, wav, mp3, etc.)
        
    Returns:
        TranscribeResponse with transcribed text
    """
    logger.info(f"POST /transcribe - filename={audio.filename}")
    
    try:
        content = await audio.read()
        
        # Try OpenAI Whisper first (best quality)
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        if OPENAI_AVAILABLE and openai_api_key:
            logger.info("Using OpenAI Whisper for transcription")
            
            try:
                client = openai.OpenAI(api_key=openai_api_key)
                
                # Save to temp file (Whisper API needs a file)
                with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                
                try:
                    with open(tmp_path, "rb") as audio_file:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="text"
                        )
                    
                    logger.info(f"✓ Whisper transcription: {len(transcript)} chars")
                    return TranscribeResponse(text=transcript)
                    
                finally:
                    # Clean up temp file
                    os.unlink(tmp_path)
                    
            except Exception as e:
                logger.warning(f"Whisper API failed, trying fallback: {e}")
        
        # Fallback to SpeechRecognition library (free, uses Google)
        if SR_AVAILABLE:
            logger.info("Using Google Speech Recognition (fallback)")
            
            try:
                recognizer = sr.Recognizer()
                
                # Save to temp file
                with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                
                try:
                    # Convert to WAV if needed (SpeechRecognition works best with WAV)
                    # For webm, we need to use pydub for conversion
                    try:
                        from pydub import AudioSegment
                        
                        # Load audio and convert to WAV
                        audio_segment = AudioSegment.from_file(tmp_path)
                        wav_path = tmp_path.replace(".webm", ".wav")
                        audio_segment.export(wav_path, format="wav")
                        
                        with sr.AudioFile(wav_path) as source:
                            audio_data = recognizer.record(source)
                        
                        os.unlink(wav_path)
                        
                    except ImportError:
                        # Try direct recognition (may not work for webm)
                        with sr.AudioFile(tmp_path) as source:
                            audio_data = recognizer.record(source)
                    
                    # Use Google Speech Recognition (free)
                    text = recognizer.recognize_google(audio_data)
                    
                    logger.info(f"✓ Google SR transcription: {len(text)} chars")
                    return TranscribeResponse(text=text)
                    
                finally:
                    os.unlink(tmp_path)
                    
            except sr.UnknownValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Could not understand audio. Please speak clearly and try again."
                )
            except sr.RequestError as e:
                logger.error(f"Google SR request error: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Speech recognition service unavailable. Try again later."
                )
            except Exception as e:
                logger.exception(f"SpeechRecognition error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Transcription failed: {str(e)}"
                )
        
        # No speech recognition available
        raise HTTPException(
            status_code=501,
            detail="Speech recognition not available. Set OPENAI_API_KEY for Whisper, or install SpeechRecognition."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in transcription: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription error: {str(e)}"
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
            "parse_document": "POST /parse_document",
            "transcribe": "POST /transcribe",
        },
        "features": [
            "Smart model routing (coding/reasoning/general)",
            "Perplexity web search integration",
            "Gemini long-context support (2M tokens)",
            "Document parsing (PDF, DOCX)",
            "Speech-to-text (Whisper)",
            "Full execution traces"
        ],
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

