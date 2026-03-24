"""
Voice Modulator Module
======================
Maps detected emotions to vocal parameters and generates
expressive speech using pyttsx3 (offline) and gTTS (online).
Supports SSML-like control for emphasis and pauses.
"""

import os
import re
import tempfile
import platform
from typing import Optional

import os
import re
import tempfile
import platform
import subprocess
from typing import Optional

import pyttsx3
from gtts import gTTS
from pydub import AudioSegment
from pydub.effects import speedup


# Try to locate ffmpeg if pydub can't find it
def _check_ffmpeg():
    try:
        if platform.system() == "Windows":
            # Check if ffmpeg is in PATH
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Warning: ffmpeg not found in PATH. Audio post-processing (pitch/rate) may fail.")
        print("   On Windows: 'winget install ffmpeg' or 'choco install ffmpeg'")

_check_ffmpeg()


# Emotion-to-voice parameter mappings
# Each emotion maps to: (rate_multiplier, pitch_shift_semitones, volume_multiplier)
# These are base values; intensity scaling is applied on top.
EMOTION_VOICE_MAP = {
    "happy": {
        "rate_multiplier": 1.10,
        "pitch_shift": 2.0,
        "volume_multiplier": 1.05,
        "description": "Warm, slightly upbeat delivery"
    },
    "excited": {
        "rate_multiplier": 1.25,
        "pitch_shift": 4.0,
        "volume_multiplier": 1.15,
        "description": "Energetic, fast-paced, high-pitched"
    },
    "calm": {
        "rate_multiplier": 0.90,
        "pitch_shift": -1.0,
        "volume_multiplier": 0.90,
        "description": "Slow, low-toned, gentle delivery"
    },
    "neutral": {
        "rate_multiplier": 1.0,
        "pitch_shift": 0.0,
        "volume_multiplier": 1.0,
        "description": "Standard, unmodulated delivery"
    },
    "concerned": {
        "rate_multiplier": 0.92,
        "pitch_shift": -0.5,
        "volume_multiplier": 0.95,
        "description": "Measured, slightly cautious tone"
    },
    "surprised": {
        "rate_multiplier": 1.15,
        "pitch_shift": 3.5,
        "volume_multiplier": 1.10,
        "description": "Quick, high-pitched, emphatic delivery"
    },
    "inquisitive": {
        "rate_multiplier": 0.95,
        "pitch_shift": 1.5,
        "volume_multiplier": 1.0,
        "description": "Thoughtful pace with rising intonation"
    },
    "frustrated": {
        "rate_multiplier": 1.12,
        "pitch_shift": -2.0,
        "volume_multiplier": 1.20,
        "description": "Tense, loud, slightly clipped delivery"
    },
    "sad": {
        "rate_multiplier": 0.80,
        "pitch_shift": -3.0,
        "volume_multiplier": 0.80,
        "description": "Slow, low, subdued delivery"
    }
}


class VoiceModulator:
    """
    Generates expressive speech audio by modulating vocal parameters
    based on detected emotion and intensity.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def get_voice_params(self, emotion: str, intensity: float) -> dict:
        """
        Calculate final voice parameters by applying intensity scaling
        to the base emotion mapping.
        
        Intensity scaling: parameters deviate more from neutral as intensity increases.
        """
        base = EMOTION_VOICE_MAP.get(emotion, EMOTION_VOICE_MAP["neutral"])

        # Scale deviation from neutral based on intensity
        # intensity 0.0 → neutral params, intensity 1.0 → full emotion params
        scale = max(min(intensity, 1.0), 0.0)

        rate = 1.0 + (base["rate_multiplier"] - 1.0) * scale
        pitch = base["pitch_shift"] * scale
        volume = 1.0 + (base["volume_multiplier"] - 1.0) * scale

        return {
            "rate_multiplier": round(rate, 3),
            "pitch_shift_semitones": round(pitch, 2),
            "volume_multiplier": round(volume, 3),
            "emotion": emotion,
            "intensity": round(intensity, 3),
            "description": base["description"]
        }

    def add_ssml_pauses(self, text: str, emotion: str) -> str:
        """
        Process text to add emotional emphasis.
        - Add pauses after punctuation based on emotion
        - Add emphasis markers for important words
        """
        processed = text

        # For sad/calm emotions, add longer pauses at commas and periods
        if emotion in ("sad", "calm", "concerned"):
            processed = re.sub(r'([.!?])\s+', r'\1   ', processed)  # Longer pauses
            processed = re.sub(r',\s+', r',  ', processed)
        
        # For excited/happy, compress pauses
        elif emotion in ("excited", "happy", "surprised"):
            processed = re.sub(r'([.!?])\s+', r'\1 ', processed)

        return processed

    def synthesize_with_gtts(self, text: str, emotion: str, intensity: float,
                              filename: Optional[str] = None) -> dict:
        """
        Synthesize speech using Google TTS and apply post-processing
        for pitch/rate/volume modulation using pydub.
        
        Returns dict with file path and voice parameters used.
        """
        params = self.get_voice_params(emotion, intensity)
        processed_text = self.add_ssml_pauses(text, emotion)

        # Generate base audio with gTTS
        tts = gTTS(text=processed_text, lang='en', slow=(emotion in ("sad", "calm")))

        # Save to temp file first
        temp_path = os.path.join(tempfile.gettempdir(), "empathy_temp.mp3")
        tts.save(temp_path)

        # Load with pydub for post-processing
        audio = AudioSegment.from_mp3(temp_path)

        # Apply volume modulation
        volume_db = 20 * (params["volume_multiplier"] - 1.0) * 10  # Convert to dB
        volume_db = max(min(volume_db, 10), -10)  # Clamp
        audio = audio + volume_db

        # Apply rate modulation via speed change
        rate = params["rate_multiplier"]
        if rate > 1.05:
            # Speed up
            playback_speed = rate
            # pydub speedup requires integer crossfade
            try:
                audio = speedup(audio, playback_speed=playback_speed, crossfade=25)
            except Exception:
                # Fallback: change frame rate
                new_frame_rate = int(audio.frame_rate * playback_speed)
                audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})
                audio = audio.set_frame_rate(44100)
        elif rate < 0.95:
            # Slow down by reducing frame rate
            new_frame_rate = int(audio.frame_rate * rate)
            audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})
            audio = audio.set_frame_rate(44100)

        # Apply pitch shift (approximate via frame rate manipulation)
        pitch_semitones = params["pitch_shift_semitones"]
        if abs(pitch_semitones) > 0.5:
            pitch_factor = 2 ** (pitch_semitones / 12.0)
            new_frame_rate = int(audio.frame_rate * pitch_factor)
            # Shift pitch
            pitched = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})
            # Restore to original frame rate to maintain duration
            audio = pitched.set_frame_rate(44100)

        # Export final audio
        if filename is None:
            filename = f"empathy_{emotion}_{int(intensity * 100)}.wav"

        output_path = os.path.join(self.output_dir, filename)
        audio.export(output_path, format="wav")

        # Clean up temp
        try:
            os.remove(temp_path)
        except OSError:
            pass

        return {
            "file_path": output_path,
            "filename": filename,
            "format": "wav",
            "voice_params": params,
            "engine": "gtts",
            "duration_ms": len(audio)
        }

    def synthesize_with_pyttsx3(self, text: str, emotion: str, intensity: float,
                                 filename: Optional[str] = None) -> dict:
        """
        Synthesize speech using pyttsx3 (offline engine) with direct
        rate/volume control. Pitch control is limited in pyttsx3.
        
        Returns dict with file path and voice parameters used.
        """
        params = self.get_voice_params(emotion, intensity)
        processed_text = self.add_ssml_pauses(text, emotion)

        engine = pyttsx3.init()

        # Set rate (default is ~200 wpm)
        base_rate = engine.getProperty('rate') or 200
        new_rate = int(base_rate * params["rate_multiplier"])
        engine.setProperty('rate', new_rate)

        # Set volume (0.0 to 1.0)
        base_volume = engine.getProperty('volume') or 1.0
        new_volume = min(max(base_volume * params["volume_multiplier"], 0.0), 1.0)
        engine.setProperty('volume', new_volume)

        # Try to select a voice
        voices = engine.getProperty('voices')
        if voices:
            # Use first available English voice
            for v in voices:
                if 'english' in v.name.lower() or 'en' in v.id.lower():
                    engine.setProperty('voice', v.id)
                    break

        if filename is None:
            filename = f"empathy_{emotion}_{int(intensity * 100)}.wav"

        output_path = os.path.join(self.output_dir, filename)

        engine.save_to_file(processed_text, output_path)
        engine.runAndWait()
        engine.stop()

        # Post-process with pydub for pitch shifting if needed
        if abs(params["pitch_shift_semitones"]) > 0.5 and os.path.exists(output_path):
            try:
                audio = AudioSegment.from_wav(output_path)
                pitch_factor = 2 ** (params["pitch_shift_semitones"] / 12.0)
                new_frame_rate = int(audio.frame_rate * pitch_factor)
                pitched = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})
                audio = pitched.set_frame_rate(44100)
                audio.export(output_path, format="wav")
            except Exception:
                pass  # If pitch shifting fails, keep original

        duration_ms = 0
        if os.path.exists(output_path):
            try:
                audio = AudioSegment.from_wav(output_path)
                duration_ms = len(audio)
            except Exception:
                pass

        return {
            "file_path": output_path,
            "filename": filename,
            "format": "wav",
            "voice_params": params,
            "engine": "pyttsx3",
            "duration_ms": duration_ms
        }

    def synthesize(self, text: str, emotion: str, intensity: float,
                    engine: str = "gtts", filename: Optional[str] = None) -> dict:
        """
        Main synthesis method. Choose between 'gtts' (online) and 'pyttsx3' (offline).
        """
        if engine == "pyttsx3":
            return self.synthesize_with_pyttsx3(text, emotion, intensity, filename)
        else:
            return self.synthesize_with_gtts(text, emotion, intensity, filename)


# Quick test
if __name__ == "__main__":
    modulator = VoiceModulator()

    for emotion in EMOTION_VOICE_MAP:
        params = modulator.get_voice_params(emotion, 0.7)
        print(f"{emotion:>12}: rate={params['rate_multiplier']:.2f}  "
              f"pitch={params['pitch_shift_semitones']:+.1f}st  "
              f"vol={params['volume_multiplier']:.2f}  "
              f"| {params['description']}")
