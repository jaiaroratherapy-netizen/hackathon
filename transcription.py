"""
Meeting Minutes Generator - Backend API
Handles audio transcription using Groq Whisper Large v3
"""

# ============================================
# IMPORTS
# ============================================
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import Optional
from groq import Groq
import os
from dotenv import load_dotenv

# ============================================
# LOAD ENVIRONMENT VARIABLES
# ============================================
load_dotenv()  # Reads .env file and loads variables

# ============================================
# INITIALIZE FASTAPI APP
# ============================================
app = FastAPI(
    title="Meeting Minutes API",
    version="1.0.0",
    description="Transcribe meeting audio to text using Whisper"
)

# ============================================
# INITIALIZE GROQ CLIENT
# ============================================
# Get API key from environment
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Validate API key exists
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not found in environment. Check your .env file!")

# Create Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

# ============================================
# PYDANTIC MODELS (Type Safety & Documentation)
# ============================================

class TranscribeResponse(BaseModel):
    """
    Response model for successful transcription
    """
    transcript: str          # The transcribed text
    file_size_mb: float      # Size of uploaded file in MB
    filename: str            # Original filename
    success: bool            # Always True for successful responses

class ErrorResponse(BaseModel):
    """
    Response model for errors
    """
    error: str              # Error message
    detail: Optional[str]   # Additional error details

# ============================================
# CONSTANTS
# ============================================
MAX_FILE_SIZE_MB = 25              # Groq Whisper limit
WHISPER_MODEL = "whisper-large-v3"  # Most accurate Whisper model
TEMPERATURE = 0.1                   # Slight randomness for better output

# ============================================
# HELPER FUNCTIONS
# ============================================

def check_file_size(file_bytes: bytes) -> tuple[bool, float]:
    """
    Check if uploaded file is within size limit
    
    Args:
        file_bytes: Raw file bytes
    
    Returns:
        tuple: (is_valid, size_in_mb)
        - is_valid: True if file is under limit
        - size_in_mb: Actual file size in megabytes
    """
    size_mb = len(file_bytes) / (1024 * 1024)  # Convert bytes to MB
    is_valid = size_mb <= MAX_FILE_SIZE_MB
    return is_valid, size_mb

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
def root():
    """
    Health check endpoint
    
    Returns API status and version info
    Used to verify backend is running correctly
    """
    return {
        "message": "🎙️ Meeting Minutes API is running!",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "transcribe": "/transcribe (POST)",
            "health": "/ (GET)"
        }
    }

@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe audio file to text using Groq Whisper Large v3
    
    FLOW:
    1. Receive audio file from client (Gradio UI)
    2. Read file bytes into memory
    3. Validate file size (must be < 25MB)
    4. Send file to Groq Whisper API
    5. Receive transcript text
    6. Validate transcript is not empty
    7. Return transcript with metadata
    
    Args:
        file: Uploaded audio file
              Supported formats: mp3, wav, m4a, webm, flac
    
    Returns:
        TranscribeResponse: Contains transcript text and metadata
    
    Raises:
        HTTPException 400: File too large or invalid
        HTTPException 500: Groq API error
    """
    
    # ========================================
    # STEP 1: Read uploaded file bytes
    # ========================================
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read uploaded file: {str(e)}"
        )
    
    # ========================================
    # STEP 2: Validate file size
    # ========================================
    is_valid_size, size_mb = check_file_size(file_bytes)
    
    if not is_valid_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size_mb:.2f}MB). Maximum allowed is {MAX_FILE_SIZE_MB}MB. "
                   f"Please upload a shorter recording or compress the audio."
        )
    
    # ========================================
    # STEP 3: Call Groq Whisper API
    # ========================================
    try:
        # Create transcription request
        # Note: file parameter expects tuple of (filename, bytes)
        transcription = groq_client.audio.transcriptions.create(
            file=(file.filename, file_bytes),  # Tuple: (name, bytes)
            model=WHISPER_MODEL,               # whisper-large-v3
            temperature=TEMPERATURE,            # 0.1 for slightly varied but consistent output
            response_format="text"             # Returns plain text (not JSON)
        )
        
        # Extract transcript text from response
        # When response_format="text", the response IS the text string
        transcript_text = transcription
        
    except Exception as e:
        # Catch any Groq API errors (rate limits, network issues, etc.)
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}. Please try again."
        )
    
    # ========================================
    # STEP 4: Validate transcript is not empty
    # ========================================
    if not transcript_text or len(transcript_text.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="No speech detected in audio file. Please ensure the recording contains clear speech."
        )
    
    # ========================================
    # STEP 5: Return successful response
    # ========================================
    return TranscribeResponse(
        transcript=transcript_text.strip(),  # Remove leading/trailing whitespace
        file_size_mb=round(size_mb, 2),      # Round to 2 decimal places
        filename=file.filename,               # Original filename
        success=True                          # Success flag
    )

# ============================================
# RUN SERVER (for local testing)
# ============================================
if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Meeting Minutes Backend...")
    print("📍 Server will run on: http://localhost:8000")
    print("📖 API docs available at: http://localhost:8000/docs")
    print("🔍 Health check: http://localhost:8000")
    
    # Run the FastAPI app with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",  # Listen on all network interfaces
        port=8000,        # Port 8000 (standard for APIs)
        log_level="info"  # Show request logs
    )
