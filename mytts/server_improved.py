"""Improved TTS server with durability and self-healing features."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
from pydantic import BaseModel
from typing import Optional, Dict, Any
import io
import wave
import numpy as np
import logging
import gc
import torch
import time
import signal
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta

from mytts.engine.coqui import CoquiEngine
from mytts.engine.piper import PiperEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TTSRequest(BaseModel):
    text: str
    voice: str = "en_US-lessac-medium"
    engine: str = "piper"
    model: str = "tts_models/en/ljspeech/vits"
    split_sentences: bool = True


class EngineInfo:
    """Track engine health and usage."""
    def __init__(self, engine, key: str):
        self.engine = engine
        self.key = key
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.request_count = 0
        self.error_count = 0
        self.last_error = None
        self.is_healthy = True
    
    def mark_success(self):
        self.last_used = datetime.now()
        self.request_count += 1
        self.is_healthy = True
    
    def mark_error(self, error: str):
        self.error_count += 1
        self.last_error = error
        self.last_used = datetime.now()
        if self.error_count >= 3:
            self.is_healthy = False
            logger.warning(f"Engine {self.key} marked unhealthy after {self.error_count} errors")
    
    def should_cleanup(self, max_age_hours: int = 24, max_idle_minutes: int = 30) -> bool:
        """Check if engine should be cleaned up."""
        age = datetime.now() - self.created_at
        idle = datetime.now() - self.last_used
        return age > timedelta(hours=max_age_hours) or idle > timedelta(minutes=max_idle_minutes)


class TTSServer:
    """TTS Server with durability features."""
    
    def __init__(self):
        self.engines: Dict[str, EngineInfo] = {}
        self.shutdown_requested = False
        self.request_count = 0
        self.error_count = 0
        self.start_time = datetime.now()
        
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown_requested = True
        self.cleanup_all_engines()
        sys.exit(0)
    
    def get_engine(self, engine_name: str, voice: str, model: Optional[str] = None):
        """Get or create engine with health checking."""
        key = f"{engine_name}:{voice}:{model}"
        
        if key in self.engines:
            engine_info = self.engines[key]
            
            if not engine_info.is_healthy:
                logger.info(f"Removing unhealthy engine: {key}")
                del self.engines[key]
            else:
                return engine_info.engine
        
        try:
            engine = self._create_engine(engine_name, voice, model)
            self.engines[key] = EngineInfo(engine, key)
            logger.info(f"Created new engine: {key}")
            return engine
        except Exception as e:
            logger.error(f"Failed to create engine {key}: {e}")
            raise
    
    def _create_engine(self, engine_name: str, voice: str, model: Optional[str] = None):
        """Create a new TTS engine."""
        if engine_name == "coqui":
            model = model or "tts_models/en/ljspeech/vits"
            try:
                gpu = torch.cuda.is_available()
                if gpu:
                    torch.zeros(1).cuda()
            except Exception:
                gpu = False
            return CoquiEngine(voice=voice, model=model, gpu=gpu)
        elif engine_name == "piper":
            return PiperEngine(voice=voice)
        else:
            raise ValueError(f"Unknown engine: {engine_name}")
    
    def cleanup_idle_engines(self):
        """Remove engines that haven't been used recently."""
        to_remove = []
        for key, engine_info in self.engines.items():
            if engine_info.should_cleanup():
                to_remove.append(key)
        
        for key in to_remove:
            logger.info(f"Cleaning up idle engine: {key}")
            del self.engines[key]
        
        if to_remove:
            self._force_cleanup()
    
    def cleanup_all_engines(self):
        """Clean up all engines."""
        logger.info(f"Cleaning up {len(self.engines)} engines")
        self.engines.clear()
        self._force_cleanup()
    
    def _force_cleanup(self):
        """Force cleanup of GPU memory and garbage collection."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        uptime = datetime.now() - self.start_time
        return {
            "uptime_seconds": int(uptime.total_seconds()),
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "engines_cached": len(self.engines),
            "engines_healthy": sum(1 for e in self.engines.values() if e.is_healthy),
        }


server = TTSServer()
app = FastAPI(title="myTTS Server - Durable Edition")


@app.middleware("http")
async def request_middleware(request, call_next):
    """Middleware for request tracking and cleanup."""
    server.request_count += 1
    
    if server.shutdown_requested:
        raise HTTPException(status_code=503, detail="Server shutting down")
    
    if server.request_count % 100 == 0:
        server.cleanup_idle_engines()
    
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        server.error_count += 1
        logger.error(f"Request error: {e}")
        raise


@app.post("/tts")
def generate_speech(req: TTSRequest):
    """Generate speech with comprehensive error handling."""
    try:
        logger.info(f"TTS Request - Voice: {req.voice}, Engine: {req.engine}")
        logger.info(f"Text ({len(req.text)} chars): {req.text[:100]}...")
        
        if not req.text or len(req.text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if len(req.text) > 5000:
            raise HTTPException(status_code=400, detail="Text too long (max 5000 characters)")
        
        clean_text = " ".join(req.text.split())
        
        engine = server.get_engine(req.engine, req.voice, req.model)
        
        try:
            audio = engine.speak(clean_text, split_sentences=req.split_sentences)
        except RuntimeError as e:
            if "phonemizer" in str(e).lower() or "lines" in str(e).lower():
                logger.warning(f"Phonemizer error, retrying with cleaned text: {e}")
                clean_text = " ".join(clean_text.split())
                audio = engine.speak(clean_text, split_sentences=False)
            else:
                raise
        
        if audio is None:
            raise HTTPException(status_code=500, detail="Engine returned no audio")
        
        if isinstance(audio, list):
            audio = np.array(audio)
        
        if isinstance(audio, np.ndarray):
            silence_threshold = 0.01
            non_silent = np.where(np.abs(audio) > silence_threshold)[0]
            if len(non_silent) > 0:
                start_idx = non_silent[0]
                end_idx = non_silent[-1] + 1
                audio = audio[start_idx:end_idx]
            
            fade_samples = int(0.05 * 22050)
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
                audio = np.clip(audio, -1.0, 1.0)
                audio = (audio * 32767).astype(np.int16)
            wf.writeframes(audio.tobytes())
        
        buffer.seek(0)
        
        engine_key = f"{req.engine}:{req.voice}:{req.model}"
        if engine_key in server.engines:
            server.engines[engine_key].mark_success()
        
        logger.info(f"TTS Response - Audio generated successfully ({len(audio)} samples)")
        
        return StreamingResponse(
            buffer,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        import traceback
        server.error_count += 1
        
        engine_key = f"{req.engine}:{req.voice}:{req.model}"
        if engine_key in server.engines:
            server.engines[engine_key].mark_error(str(e))
        
        server._force_cleanup()
        
        logger.error(f"TTS Error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check endpoint."""
    import psutil
    
    memory = psutil.virtual_memory()
    gpu_info = {}
    
    if torch.cuda.is_available():
        try:
            gpu_info = {
                "available": True,
                "device_count": torch.cuda.device_count(),
                "current_device": torch.cuda.current_device(),
                "memory_allocated": int(torch.cuda.memory_allocated()),
                "memory_reserved": int(torch.cuda.memory_reserved()),
                "max_memory": int(torch.cuda.max_memory_allocated()),
            }
        except Exception as e:
            gpu_info = {"available": False, "error": str(e)}
    else:
        gpu_info = {"available": False}
    
    stats = server.get_stats()
    
    return {
        "status": "ok",
        "engines": [
            {
                "key": key,
                "healthy": info.is_healthy,
                "requests": info.request_count,
                "errors": info.error_count,
                "last_used": info.last_used.isoformat(),
            }
            for key, info in server.engines.items()
        ],
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used
        },
        "gpu": gpu_info,
        "gc_stats": gc.get_stats(),
        "server_stats": stats,
    }


@app.get("/voices")
def list_voices():
    """List available voices."""
    return {
        "voices": [
            "en_US-lessac-medium",
            "en_US-amy-medium",
            "en_US-ryan-medium",
        ]
    }


@app.post("/cleanup")
def cleanup_resources():
    """Force cleanup of all resources."""
    server.cleanup_all_engines()
    return {
        "status": "cleaned",
        "engines_cleared": len(server.engines),
        "server_stats": server.get_stats(),
    }


@app.post("/engine/{engine_key}/reset")
def reset_engine(engine_key: str):
    """Reset a specific engine."""
    if engine_key in server.engines:
        del server.engines[engine_key]
        server._force_cleanup()
        return {"status": "reset", "engine": engine_key}
    raise HTTPException(status_code=404, detail=f"Engine {engine_key} not found")


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the TTS server."""
    logger.info(f"Starting TTS server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
