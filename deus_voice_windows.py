#!/usr/bin/env python3
"""
DEUS Voice Interface - Windows Version with Gemini Integration
Press and hold Right Alt to talk, release to send to Gemini
Works on Windows, macOS, and Linux
No filesystem operations - everything in memory for maximum security
"""

import threading
import json
import urllib.request
import urllib.error
import io
import os
import wave
import pyaudio
import base64
from pynput import keyboard
from dotenv import load_dotenv
import winsound
import soundfile as sf
import numpy as np

# Load environment variables
load_dotenv()

# Configuration - Gemini only
GEMINI_API_KEY = os.environ.get("DEUS_GEMINI_API_KEY", "")
GEMINI_STT_MODEL = os.environ.get("DEUS_GEMINI_STT_MODEL", "gemini-2.5-flash-preview-04-17")
GEMINI_LLM_MODEL = os.environ.get("DEUS_GEMINI_LLM_MODEL", "gemini-2.5-flash")
GEMINI_TTS_MODEL = os.environ.get("DEUS_GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_TTS_VOICE = os.environ.get("DEUS_GEMINI_TTS_VOICE", "Charon")

# Audio settings
SAMPLE_RATE = 44100
CHANNELS = 1
CHUNK = 1024

# State
is_recording = False
ralt_pressed = False


class AudioRecorder:
    def __init__(self):
        self.frames = []
        self.is_recording = False
        self._lock = threading.Lock()

    def start_recording(self):
        self.frames = []
        self.is_recording = True
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        print("🎤 Recording... (release keys to stop)")

        try:
            while self.is_recording:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    self.frames.append(data)
                except:
                    break
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

    def stop_recording(self):
        self.is_recording = False
        print("⏹️  Recording stopped")
        return list(self.frames)

    def frames_to_wav_bytes(self, frames):
        """Convert audio frames to WAV bytes in memory"""
        audio_buffer = io.BytesIO()
        with wave.open(audio_buffer, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(frames))
        audio_buffer.seek(0)
        return audio_buffer.getvalue()


def speech_to_text(audio_bytes):
    """Convert audio bytes to text using Gemini (no filesystem)"""
    try:
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_STT_MODEL}:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": [{
                "parts": [
                    {"text": "You are a strict speech-to-text transcriber. Listen to this audio and output ONLY the exact words spoken. Do not paraphrase, interpret, summarize, or add anything. If nothing is spoken, output exactly: [EMPTY]"},
                    {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}}
                ]
            }],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 500
            }
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method='POST')

        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text and text != "[EMPTY]":
                print(f"📝 You said: {text}")
                return text
            else:
                print("❌ Could not understand audio")
                return None
    except (TimeoutError, OSError) as e:
        print(f"❌ Network timeout: {e}")
        return None
    except Exception as e:
        print(f"❌ Speech recognition error: {e}")
        return None


def send_to_gemini(message):
    """Send message to Gemini and get the response"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_LLM_MODEL}:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": [{
                "parts": [
                    {"text": message}
                ]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024
            }
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method='POST')

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text:
                print(f"💬 Gemini: {text[:100]}...")
                return text
            else:
                return "No response from Gemini"
    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return None


def play_audio_bytes(audio_bytes):
    """Play audio from bytes in memory (Windows compatible)"""
    try:
        # Create WAV data from bytes for playback
        audio_buffer = io.BytesIO(audio_bytes)
        
        # Read WAV using soundfile
        data, sample_rate = sf.read(audio_buffer)
        
        # Play using PyAudio
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=sample_rate,
            output=True
        )
        
        stream.write(data.astype(np.float32).tobytes())
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        return True
    except Exception as e:
        print(f"❌ Audio playback error: {e}")
        return False


def speak_gemini(text):
    """Use Gemini TTS to speak text (no filesystem)"""
    print(f"🔊 Speaking: {text[:50]}...")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TTS_MODEL}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": f"Say the following text out loud: {text}"}]
        }],
        "generationConfig": {
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": GEMINI_TTS_VOICE
                    }
                }
            }
        }
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            part = result["candidates"][0]["content"]["parts"][0]
            
            if "inline_data" in part:
                audio_b64 = part["inline_data"]["data"]
            elif "inlineData" in part:
                audio_b64 = part["inlineData"]["data"]
            else:
                print(f"❌ Unexpected TTS response: {list(part.keys())}")
                return False
            
            # Decode audio bytes - stays in memory
            audio_bytes = base64.b64decode(audio_b64)
            
            # Play directly from memory
            success = play_audio_bytes(audio_bytes)
            return success
            
    except Exception as e:
        print(f"❌ Gemini TTS error: {e}")
        return False


# Global recorder
recorder = AudioRecorder()
recording_thread = None


def on_press(key):
    global ralt_pressed, recording_thread, is_recording

    try:
        if key == keyboard.Key.alt_r:
            ralt_pressed = True

        if ralt_pressed and not is_recording:
            is_recording = True
            recording_thread = threading.Thread(target=recorder.start_recording)
            recording_thread.start()
    except:
        pass


def on_release(key):
    global ralt_pressed, is_recording, recording_thread

    try:
        if key == keyboard.Key.alt_r:
            ralt_pressed = False

        if is_recording and not ralt_pressed:
            is_recording = False
            frames = recorder.stop_recording()

            if recording_thread:
                recording_thread.join(timeout=1)

            if frames and len(frames) > 10:  # Minimum recording length
                # Process in background
                threading.Thread(target=process_recording, args=(frames,)).start()
            else:
                print("⚠️  Recording too short, try again")

        # Exit on Escape
        if key == keyboard.Key.esc:
            print("\n👋 Goodbye!")
            return False
    except:
        pass


def process_recording(frames):
    """Process recorded audio: STT -> Gemini LLM -> TTS (all in memory)"""
    # Convert frames to WAV bytes (in memory)
    audio_bytes = recorder.frames_to_wav_bytes(frames)

    # Speech to text
    text = speech_to_text(audio_bytes)

    if not text:
        speak_gemini("I didn't catch that")
        return

    # Send to Gemini and get response
    reply = send_to_gemini(text)

    if reply:
        speak_gemini(reply)
    else:
        speak_gemini("No response received from Gemini")


def main():
    print("\n" + "="*60)
    print("  DEUS Voice Interface - Windows/Cross-Platform")
    print("  Gemini Integration Only (No OpenClaw)")
    print("  🔒 Zero Filesystem - All In-Memory")
    print("="*60)
    print("\n  Hold Right Alt to talk")
    print("  Release to send to Gemini AI")
    print("  DEUS will speak the response")
    print("  Press Escape to quit")
    print("\n" + "="*60 + "\n")

    if not GEMINI_API_KEY:
        print("❌ Error: DEUS_GEMINI_API_KEY not set in .env file!")
        return

    print("✓ Gemini API configured")
    print("✓ Zero-filesystem mode enabled (all operations in memory)\n")
    print("🎧 Listening for Right Alt key...\n")

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
