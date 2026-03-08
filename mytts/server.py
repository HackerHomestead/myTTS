from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
from pydantic import BaseModel
from typing import Optional
import io
import wave
import numpy as np

from mytts.engine.coqui import CoquiEngine
from mytts.engine.piper import PiperEngine


class TTSRequest(BaseModel):
    text: str
    voice: str = "en_US-lessac-medium"
    engine: str = "coqui"
    model: str = "tts_models/en/ljspeech/vits"  # Changed to VITS for better stability
    split_sentences: bool = True  # Enable text splitting for long texts


app = FastAPI(title="myTTS Server")
engines = {}
import gc
import torch


def get_engine(engine_name: str, voice: str, model: Optional[str] = None):
    import torch
    key = f"{engine_name}:{voice}:{model}"
    if key not in engines:
        if engine_name == "coqui":
            model = model or "tts_models/en/ljspeech/vits"  # Default to VITS
            # Enable GPU mode if available
            try:
                gpu = torch.cuda.is_available()
                if gpu:
                    torch.zeros(1).cuda()  # Test GPU allocation
            except Exception:
                gpu = False
            engines[key] = CoquiEngine(voice=voice, model=model, gpu=gpu)
        elif engine_name == "piper":
            engines[key] = PiperEngine(voice=voice)
        else:
            raise ValueError(f"Unknown engine: {engine_name}")
    return engines[key]


@app.post("/tts")
def generate_speech(req: TTSRequest):
    try:
        # Validate input
        if not req.text or len(req.text.strip()) == 0:
            raise ValueError("Text cannot be empty")
        
        if len(req.text) > 5000:  # Limit text length
            raise ValueError("Text too long (max 5000 characters)")
        
        engine = get_engine(req.engine, req.voice, req.model)
        audio = engine.speak(req.text, split_sentences=req.split_sentences)
        
        if audio is None:
            raise ValueError("Engine returned no audio")
        
        if isinstance(audio, list):
            audio = np.array(audio)
        
        # Apply additional audio processing to reduce drift
        if isinstance(audio, np.ndarray):
            # Remove silence at beginning and end
            silence_threshold = 0.01
            non_silent = np.where(np.abs(audio) > silence_threshold)[0]
            if len(non_silent) > 0:
                start_idx = non_silent[0]
                end_idx = non_silent[-1] + 1
                audio = audio[start_idx:end_idx]
            
            # Apply fade in/out to reduce artifacts
            fade_samples = int(0.05 * 22050)  # 50ms fade
            if len(audio) > fade_samples * 2:
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                audio[:fade_samples] *= fade_in
                audio[-fade_samples:] *= fade_out
        
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            if isinstance(audio, np.ndarray):
                # Ensure audio is in proper range
                audio = np.clip(audio, -1.0, 1.0)
                audio = (audio * 32767).astype(np.int16)
            wf.writeframes(audio.tobytes())
        
        buffer.seek(0)
        
        # Clean up GPU memory after processing
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # Force garbage collection periodically
        gc.collect()
        
        return StreamingResponse(
            buffer,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )
    except Exception as e:
        import traceback
        # Clean up on error
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@app.get("/health")
def health():
    import torch
    import psutil
    import gc
    
    # Get memory info
    memory = psutil.virtual_memory()
    gpu_info = {}
    
    if torch.cuda.is_available():
        gpu_info = {
            "available": True,
            "device_count": torch.cuda.device_count(),
            "current_device": torch.cuda.current_device(),
            "memory_allocated": torch.cuda.memory_allocated(),
            "memory_reserved": torch.cuda.memory_reserved(),
            "max_memory": torch.cuda.max_memory_allocated()
        }
    else:
        gpu_info = {"available": False}
    
    return {
        "status": "ok",
        "engines": list(engines.keys()),
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used
        },
        "gpu": gpu_info,
        "gc_stats": gc.get_stats()
    }


@app.get("/voices")
def list_voices():
    return {
        "voices": [
            "en_US-lessac-medium",
            "en_US-lessac-medium",
        ]
    }

@app.post("/cleanup")
def cleanup_resources():
    """Clean up GPU memory and reset engines"""
    import torch
    import gc
    
    # Clean up all engines
    for engine_key, engine in engines.items():
        if hasattr(engine, 'cleanup'):
            engine.cleanup()
    
    # Clear engine cache
    engines.clear()
    
    # Clean up GPU memory
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    
    # Force garbage collection
    gc.collect()
    
    return {"status": "cleaned", "engines_cleared": len(engines)}


def run_server(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
