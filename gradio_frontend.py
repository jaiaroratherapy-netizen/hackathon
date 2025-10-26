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
    """
    try:
        with open(audio_path, "rb") as audio_file:
            files = {"file": audio_file}
            
            response = requests.post(
                f"{API_BASE_URL}/transcribe",
                files=files,
                timeout=120
            )
        
        if response.status_code == 200:
            data = response.json()
            return data["transcript"], None
        else:
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
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate-minutes",
            json={"transcript": transcript},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["minutes"], None
        else:
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

def process_audio_to_minutes(audio_path: str) -> Tuple[str, str, gr.update]:
    """
    Main function: Convert audio file to formatted meeting minutes
    
    Args:
        audio_path: Path to uploaded audio file
    
    Returns:
        tuple: (status_message, minutes_markdown, accordion_update)
    """
    
    # Validate input
    if not audio_path:
        return "❌ Please upload an audio file first.", "", gr.update(open=False)
    
    # Check backend health
    if not check_backend_health():
        return "❌ Backend server is not running! Please start it with: python backend.py", "", gr.update(open=False)
    
    # Get file info
    try:
        file_size_mb = get_file_size_mb(audio_path)
        filename = os.path.basename(audio_path)
    except Exception as e:
        return f"❌ Error reading file: {str(e)}", "", gr.update(open=False)
    
    # Check file size
    if file_size_mb > 25:
        return f"❌ File too large ({file_size_mb}MB). Maximum size is 25MB.", "", gr.update(open=False)
    
    # STEP 1: Transcribe
    status_msg = f"🎙️ **Transcribing audio...** ({file_size_mb}MB)\n\n*Think of your favourite song in the meanwhile 🎵*"
    yield status_msg, "", gr.update(open=False)
    
    transcript, error = call_transcribe_api(audio_path)
    
    if error:
        yield f"❌ {error}", "", gr.update(open=False)
        return
    
    # Show transcript preview
    transcript_preview = transcript[:150] + "..." if len(transcript) > 150 else transcript
    status_msg = f"✅ **Transcription complete!**\n\n📝 Preview: *{transcript_preview}*"
    yield status_msg, "", gr.update(open=False)
    
    # STEP 2: Generate minutes
    status_msg = "📝 **Generating minutes...**\n\n*Think of your favourite TV Show in the meanwhile 📺*"
    yield status_msg, "", gr.update(open=False)
    
    minutes, error = call_generate_minutes_api(transcript)
    
    if error:
        yield f"❌ {error}", "", gr.update(open=False)
        return
    
    # Final result
    final_status = f"✅ **All done!** Minutes generated successfully.\n\n📄 **File:** {filename} ({file_size_mb}MB)"
    yield final_status, minutes, gr.update(open=True)

def refresh_page():
    """
    Clear all inputs and outputs
    
    Returns:
        tuple: (cleared_audio, cleared_status, cleared_minutes, closed_accordion)
    """
    return None, "Ready to process audio. Upload a file and click Generate Minutes.", "", gr.update(open=False)

# ============================================
# Build Gradio Interface
# ============================================

with gr.Blocks(title="Meeting Minutes Generator", theme=gr.themes.Soft()) as demo:
    
    # ========================================
    # Centered Header
    # ========================================
    gr.Markdown(
        """
        <div style="text-align: center; max-width: 800px; margin: 0 auto;">
            <h1>📝 Meeting Minutes Generator</h1>
            <p style="font-size: 1.2em; color: #666;">
                Upload meeting audio → Get formatted, professional minutes instantly
            </p>
        </div>
        """
    )
    
    gr.Markdown("<br>")
    
    # ========================================
    # Main Upload Section (Centered)
    # ========================================
    with gr.Row():
        with gr.Column(scale=1):
            pass  # Empty column for centering
        
        with gr.Column(scale=2):
            # Audio upload - HIDDEN waveform display
            audio_input = gr.Audio(
                label="Upload Meeting Audio",
                type="filepath",
                sources=["upload"],
                waveform_options=gr.WaveformOptions(show_controls=False)
            )
            
            gr.Markdown(
                """
                <div style="text-align: center; color: #888; font-size: 0.9em; margin-top: 10px;">
                    Supported: MP3, WAV, M4A, WEBM • Max: 25MB (~25 minutes)
                </div>
                """
            )
            
            gr.Markdown("<br>")
            
            with gr.Row():
                generate_btn = gr.Button(
                    "🚀 Generate Minutes",
                    variant="primary",
                    size="lg",
                    scale=2
                )
                refresh_btn = gr.Button(
                    "🔄 Refresh Page",
                    variant="secondary",
                    size="lg",
                    scale=1
                )
            
            gr.Markdown("<br>")
            
            # Status display
            status_output = gr.Markdown(
                "Ready to process audio. Upload a file and click Generate Minutes.",
                elem_classes=["status-box"]
            )
        
        with gr.Column(scale=1):
            pass  # Empty column for centering
    
    gr.Markdown("<br>")
    
    # ========================================
    # Generated Minutes Section (Collapsible)
    # ========================================
    with gr.Accordion("📄 Generated Minutes", open=False) as minutes_accordion:
        minutes_output = gr.Markdown(
            "",
            show_copy_button=True,
            elem_classes=["minutes-output"]
        )
    
    gr.Markdown("<br><br>")
    
    # ========================================
    # Instructions (Simplified)
    # ========================================
    with gr.Accordion("ℹ️ Quick Start Guide", open=False):
        gr.Markdown("""
        ### How to use:
        
        1. **Upload Audio** - Click the upload box and select your meeting recording
        2. **Generate** - Click the "Generate Minutes" button
        3. **Wait** - Transcription takes ~30 seconds, formatting takes ~5 seconds
        4. **Copy** - Use the copy button to save your minutes
        5. **Refresh** - Click refresh to start over with a new recording
        """)
    
    gr.Markdown("<br>")
    
    # ========================================
    # Footer
    # ========================================
    gr.Markdown(
        """
        <div style="text-align: center; color: #888; padding: 20px;">
            Made with ❤️ by Jai
        </div>
        """
    )
    
    # ========================================
    # Event Handlers
    # ========================================
    
    # Generate button
    generate_btn.click(
        fn=process_audio_to_minutes,
        inputs=[audio_input],
        outputs=[status_output, minutes_output, minutes_accordion]
    )
    
    # Refresh button
    refresh_btn.click(
        fn=refresh_page,
        inputs=[],
        outputs=[audio_input, status_output, minutes_output, minutes_accordion]
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
    print("📍 Frontend will be available at: http://localhost:7861")
    print()
    print("=" * 60)
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,
        show_error=True,
        share=False,
        show_api=False
    )
