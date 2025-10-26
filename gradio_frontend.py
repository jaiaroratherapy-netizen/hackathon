"""
Meeting Minutes Generator - Gradio Frontend
Connects to FastAPI backend for transcription and minutes generation
"""

import gradio as gr
import requests
from typing import Optional, Tuple
import os

# ============================================
# Configuration
# ============================================

# Backend URL (update if using different port)
API_BASE_URL = "http://localhost:8001"

# Maximum file size (25MB in bytes)
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

# ============================================
# Helper Functions
# ============================================

def check_backend_health() -> bool:
    """
    Check if FastAPI backend is running
    
    Returns:
        bool: True if backend is healthy, False otherwise
    """
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=2)
        return response.status_code == 200
    except:
        return False

def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes
    
    Args:
        file_path: Path to file
    
    Returns:
        float: File size in MB
    """
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    return round(size_mb, 2)

# ============================================
# API Communication Functions
# ============================================

def call_transcribe_api(audio_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Call /transcribe endpoint to convert audio to text
    
    Args:
        audio_path: Path to audio file
    
    Returns:
        tuple: (transcript_text, error_message)
        - If successful: (transcript, None)
        - If failed: (None, error_message)
    """
    try:
        # Open and send audio file
        with open(audio_path, "rb") as audio_file:
            files = {"file": audio_file}
            
            response = requests.post(
                f"{API_BASE_URL}/transcribe",
                files=files,
                timeout=120  # 2 minutes timeout for large files
            )
        
        # Check if successful
        if response.status_code == 200:
            data = response.json()
            return data["transcript"], None
        else:
            # Extract error message from response
            try:
                error_detail = response.json().get("detail", "Unknown error")
            except:
                error_detail = f"HTTP {response.status_code}"
            
            return None, f"Transcription failed: {error_detail}"
    
    except requests.exceptions.ConnectionError:
        return None, "❌ Cannot connect to backend. Is the server running on port 8001?"
    
    except requests.exceptions.Timeout:
        return None, "❌ Request timed out. The audio file might be too long."
    
    except Exception as e:
        return None, f"❌ Error: {str(e)}"

def call_generate_minutes_api(transcript: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Call /generate-minutes endpoint to convert transcript to formatted minutes
    
    Args:
        transcript: Raw transcript text
    
    Returns:
        tuple: (minutes_markdown, error_message)
        - If successful: (minutes, None)
        - If failed: (None, error_message)
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate-minutes",
            json={"transcript": transcript},
            timeout=60  # 1 minute timeout
        )
        
        # Check if successful
        if response.status_code == 200:
            data = response.json()
            return data["minutes"], None
        else:
            # Extract error message from response
            try:
                error_detail = response.json().get("detail", "Unknown error")
            except:
                error_detail = f"HTTP {response.status_code}"
            
            return None, f"Minutes generation failed: {error_detail}"
    
    except requests.exceptions.ConnectionError:
        return None, "❌ Cannot connect to backend. Is the server running on port 8001?"
    
    except requests.exceptions.Timeout:
        return None, "❌ Request timed out. Please try again."
    
    except Exception as e:
        return None, f"❌ Error: {str(e)}"

# ============================================
# Main Processing Function
# ============================================

def process_audio_to_minutes(audio_path: str) -> Tuple[str, str]:
    """
    Main function: Convert audio file to formatted meeting minutes
    
    This is the core function that:
    1. Validates input
    2. Calls transcription API
    3. Calls minutes generation API
    4. Returns formatted output
    
    Args:
        audio_path: Path to uploaded audio file
    
    Returns:
        tuple: (status_message, minutes_markdown)
    """
    
    # ========================================
    # STEP 0: Validate input
    # ========================================
    if not audio_path:
        return "❌ Please upload an audio file first.", ""
    
    # Check backend health
    if not check_backend_health():
        return "❌ Backend server is not running! Please start it with: python backend.py", ""
    
    # Get file info
    try:
        file_size_mb = get_file_size_mb(audio_path)
        filename = os.path.basename(audio_path)
    except Exception as e:
        return f"❌ Error reading file: {str(e)}", ""
    
    # Check file size
    if file_size_mb > 25:
        return f"❌ File too large ({file_size_mb}MB). Maximum size is 25MB.", ""
    
    # ========================================
    # STEP 1: Transcribe audio to text
    # ========================================
    status_msg = f"🎙️ **Transcribing audio...** ({file_size_mb}MB)\n\n*Think of your favourite song in the meanwhile 🎵*"
    yield status_msg, ""
    
    transcript, error = call_transcribe_api(audio_path)
    
    if error:
        yield f"❌ {error}", ""
        return
    
    # Show transcript preview
    transcript_preview = transcript[:200] + "..." if len(transcript) > 200 else transcript
    status_msg = f"✅ **Transcription complete!**\n\n📝 Preview: *{transcript_preview}*"
    yield status_msg, ""
    
    # ========================================
    # STEP 2: Generate formatted minutes
    # ========================================
    status_msg = "📝 **Generating minutes...**\n\n*Think of your favourite TV Show in the meanwhile 📺*"
    yield status_msg, ""
    
    minutes, error = call_generate_minutes_api(transcript)
    
    if error:
        yield f"❌ {error}", ""
        return
    
    # ========================================
    # STEP 3: Return final result
    # ========================================
    final_status = f"✅ **All done!** Minutes generated successfully.\n\n📄 **File:** {filename} ({file_size_mb}MB)"
    yield final_status, minutes

# ============================================
# Build Gradio Interface
# ============================================

with gr.Blocks(title="Meeting Minutes Generator", theme=gr.themes.Soft()) as demo:
    
    # Header
    gr.Markdown("# 📝 Meeting Minutes Generator")
    gr.Markdown("### Upload meeting audio → Get formatted, professional minutes instantly")
    gr.Markdown("---")
    
    with gr.Row():
        with gr.Column(scale=2):
            
            # ========================================
            # Input Section
            # ========================================
            gr.Markdown("## 🎙️ Step 1: Upload Audio")
            
            audio_input = gr.Audio(
                label="Upload Meeting Audio File",
                type="filepath",
                sources=["upload"],  # Only allow file upload
            )
            
            gr.Markdown("""
            **Supported formats:** MP3, WAV, M4A, WEBM, FLAC  
            **Maximum size:** 25 MB (~25 minutes at 128kbps)
            """)
            
            generate_btn = gr.Button(
                "🚀 Generate Minutes",
                variant="primary",
                size="lg"
            )
            
            gr.Markdown("---")
            
            # ========================================
            # Status Section
            # ========================================
            gr.Markdown("## 📊 Status")
            
            status_output = gr.Markdown(
                "Ready to process audio. Upload a file and click Generate Minutes.",
                elem_classes=["status-box"]
            )
        
        with gr.Column(scale=3):
            
            # ========================================
            # Output Section
            # ========================================
            gr.Markdown("## 📄 Generated Minutes")
            
            minutes_output = gr.Markdown(
                "",
                label="Meeting Minutes",
                show_copy_button=True,  # Built-in copy button!
                container=True,
                elem_classes=["minutes-output"]
            )
    
    # ========================================
    # Footer / Instructions
    # ========================================
    gr.Markdown("---")
    with gr.Accordion("ℹ️ How to use", open=False):
        gr.Markdown("""
        ### Quick Start Guide:
        
        1. **Upload Audio**: Click the audio upload box and select your meeting recording
        2. **Generate**: Click the "Generate Minutes" button
        3. **Wait**: Transcription takes ~30 seconds, minutes generation takes ~5 seconds
        4. **Copy**: Use the copy button in the top-right of the minutes output
        
        ### Tips:
        - Use clear, high-quality audio for best results
        - Shorter meetings (5-15 minutes) work best for MVP testing
        - The app removes filler words and formats content automatically
        - All processing happens in-memory (no data is stored)
        
        ### Troubleshooting:
        - If you see "Backend not running" → Run `python backend.py` in terminal
        - If transcription fails → Check audio quality and file size
        - If generation fails → Try a shorter transcript
        """)
    
    gr.Markdown("---")
    gr.Markdown("Made with ❤️ using Groq Whisper Large v3 + GPT-OSS-120B")
    
    # ========================================
    # Event Handlers
    # ========================================
    
    # Generate button click
    generate_btn.click(
        fn=process_audio_to_minutes,
        inputs=[audio_input],
        outputs=[status_output, minutes_output]
    )

# ============================================
# Launch the App
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting Meeting Minutes Generator Frontend")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT: Make sure FastAPI backend is running!")
    print("   Start backend with: python backend.py")
    print("   Backend should be running on: http://localhost:8001")
    print()
    print("📍 Frontend will be available at: http://localhost:7860")
    print()
    print("=" * 60)
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        share=False,  # Set to True if you want a public URL
        show_api=False
    )
