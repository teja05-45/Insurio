"""
Voice input module for PolicyPilot AI.
Handles microphone input and speech-to-text conversion.
"""

import streamlit as st

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False


def transcribe_audio() -> dict:
    """
    Record audio from microphone and transcribe to text.
    
    Returns:
        dict with 'text' and 'error' keys
    """
    if not SR_AVAILABLE:
        return {
            "text": None,
            "error": "speech_recognition not installed. Run: pip install SpeechRecognition pyaudio"
        }
    
    recognizer = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Listen for audio (timeout after 5 seconds of silence)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
        
        # Try Google Speech Recognition (free, no API key)
        try:
            text = recognizer.recognize_google(audio)
            return {"text": text, "error": None}
        except sr.UnknownValueError:
            return {"text": None, "error": "Could not understand audio. Please speak clearly and try again."}
        except sr.RequestError as e:
            # Fallback: try offline Sphinx if available
            try:
                text = recognizer.recognize_sphinx(audio)
                return {"text": text, "error": None}
            except Exception:
                return {"text": None, "error": f"Speech service unavailable: {str(e)}"}
    
    except sr.WaitTimeoutError:
        return {"text": None, "error": "No speech detected. Please click the mic button and speak."}
    except OSError as e:
        return {"text": None, "error": f"Microphone not accessible: {str(e)}"}
    except Exception as e:
        return {"text": None, "error": f"Voice error: {str(e)}"}


def is_voice_available() -> bool:
    """Check if voice input is available on this system."""
    if not SR_AVAILABLE:
        return False
    try:
        import pyaudio
        return True
    except ImportError:
        return False


def get_voice_status() -> str:
    """Return a human-readable status of voice capabilities."""
    if not SR_AVAILABLE:
        return "unavailable"
    try:
        import pyaudio
        return "available"
    except ImportError:
        return "partial"  # SR available but no audio input
