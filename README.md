# Meeting Minutes Generator

Upload meeting audio, get professional minutes instantly.

## Features
- Audio transcription using Whisper Large v3
- Automated minutes formatting using GPT-OSS-120B
- Clean Markdown output
- No login required
- Privacy-focused (no data stored)

## Setup
1. Clone repo
2. Install: pip install -r requirements.txt
3. Add GROQ_API_KEY to .env
4. Run backend: python backend.py
5. Run frontend: python frontend.py
6. Open: http://localhost:7860

## Tech Stack
- Backend: FastAPI
- Frontend: Gradio
- AI: Groq (Whisper + GPT-OSS-120B)
