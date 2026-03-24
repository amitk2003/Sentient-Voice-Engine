"""
The Empathy Engine - FastAPI Backend
====================================
REST API that accepts text input, detects emotion, modulates voice
parameters, and returns expressive synthesized speech audio.
"""

import os
import uuid
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from emotion_analyzer import EmotionAnalyzer
from voice_modulator import VoiceModulator, EMOTION_VOICE_MAP


# Initialize app
app = FastAPI(
    title="The Empathy Engine",
    description="AI-powered expressive speech synthesis with emotion detection",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize modules
analyzer = EmotionAnalyzer()
modulator = VoiceModulator(output_dir="output")

# Ensure output directory exists
os.makedirs("output", exist_ok=True)


# =================== Pydantic Models ===================

class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    engine: str = Field(default="gtts", description="TTS engine: 'gtts' or 'pyttsx3'")
    override_emotion: Optional[str] = Field(
        default=None,
        description="Manually override detected emotion"
    )
    override_intensity: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Manually override intensity (0.0 to 1.0)"
    )


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to analyze")


class SynthesizeResponse(BaseModel):
    success: bool
    text: str
    emotion_analysis: dict
    voice_params: dict
    audio_url: str
    audio_filename: str
    duration_ms: int
    processing_time_ms: int


class AnalyzeResponse(BaseModel):
    success: bool
    text: str
    emotion_analysis: dict


class EmotionMapResponse(BaseModel):
    emotions: dict


# =================== API Endpoints ===================

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main web interface."""
    frontend_path = Path(__file__).parent / "static" / "index.html"
    if frontend_path.exists():
        return HTMLResponse(content=frontend_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Empathy Engine API</h1><p>Frontend not found. Please check /static/index.html</p>")


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_text(request: AnalyzeRequest):
    """Analyze text and return emotion classification without generating audio."""
    try:
        result = analyzer.analyze(request.text)
        return AnalyzeResponse(
            success=True,
            text=request.text,
            emotion_analysis=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/synthesize", response_model=SynthesizeResponse)
async def synthesize_speech(request: SynthesizeRequest):
    """
    Full pipeline: Analyze text emotion → Modulate voice → Generate audio.
    Returns emotion analysis, voice parameters, and audio file URL.
    """
    start_time = time.time()

    try:
        # Step 1: Emotion analysis
        emotion_result = analyzer.analyze(request.text)

        # Apply overrides if provided
        emotion = request.override_emotion or emotion_result["emotion"]
        intensity = request.override_intensity if request.override_intensity is not None else emotion_result["intensity"]

        # Validate emotion
        if emotion not in EMOTION_VOICE_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown emotion '{emotion}'. Valid: {list(EMOTION_VOICE_MAP.keys())}"
            )

        # Step 2: Generate unique filename
        unique_id = uuid.uuid4().hex[:8]
        filename = f"empathy_{emotion}_{int(intensity * 100)}_{unique_id}.wav"

        # Step 3: Synthesize with voice modulation
        synth_result = modulator.synthesize(
            text=request.text,
            emotion=emotion,
            intensity=intensity,
            engine=request.engine,
            filename=filename
        )

        processing_time = int((time.time() - start_time) * 1000)

        return SynthesizeResponse(
            success=True,
            text=request.text,
            emotion_analysis=emotion_result,
            voice_params=synth_result["voice_params"],
            audio_url=f"/api/audio/{filename}",
            audio_filename=filename,
            duration_ms=synth_result["duration_ms"],
            processing_time_ms=processing_time
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


@app.get("/api/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files."""
    filepath = os.path.join("output", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        filepath,
        media_type="audio/wav",
        filename=filename
    )


@app.get("/api/emotions", response_model=EmotionMapResponse)
async def get_emotion_map():
    """Return the complete emotion-to-voice parameter mapping."""
    return EmotionMapResponse(emotions=EMOTION_VOICE_MAP)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Empathy Engine",
        "version": "1.0.0"
    }


# Mount static files (CSS, JS, etc.)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# =================== CLI Mode ===================

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("  🎙️  The Empathy Engine - Starting Server")
    print("=" * 60)
    print("  Web UI:  http://localhost:8000")
    print("  API:     http://localhost:8000/api/synthesize")
    print("  Docs:    http://localhost:8000/docs")
    print("=" * 60 + "\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
