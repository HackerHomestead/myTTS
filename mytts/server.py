from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
from pydantic import BaseModel
from typing import Optional
import io
import wave
import numpy as np
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import psutil

from mytts.engine.coqui import CoquiEngine
from mytts.engine.piper import PiperEngine


class TTSRequest(BaseModel):
    text: str
    voice: str = "en_US-lessac-medium"
    engine: str = "coqui"
    model: str = "tts_models/en/ljspeech/tacotron2-DDC"


app = FastAPI(title="myTTS Server")
engines = {}

_cpu_count = os.cpu_count() or 4
_max_workers = max(1, _cpu_count - 1)
_executor = ThreadPoolExecutor(max_workers=_max_workers)

_wps_history = deque(maxlen=30)
_cpu_history = deque(maxlen=30)
_request_times = []
_last_adjustment = time.time()
_current_workers = _max_workers


def get_engine(engine_name: str, voice: str, model: Optional[str] = None):
    import torch
    key = f"{engine_name}:{voice}:{model}"
    if key not in engines:
        if engine_name == "coqui":
            model = model or "tts_models/en/ljspeech/tacotron2-DDC"
            # Force CPU-only mode
            gpu = False
            
            # Disable NNPACK to avoid hardware compatibility issues
            try:
                torch.backends.nnpack.flags(enabled=False)
            except Exception:
                pass
                
            engines[key] = CoquiEngine(voice=voice, model=model, gpu=gpu)
        elif engine_name == "piper":
            engines[key] = PiperEngine(voice=voice)
        else:
            raise ValueError(f"Unknown engine: {engine_name}")
    return engines[key]


def _record_metrics(text: str, duration: float):
    words = len(text.split())
    wps = words / duration if duration > 0 else 0
    _wps_history.append(wps)
    _cpu_history.append(psutil.cpu_percent(interval=0.1))


def _adjust_workers():
    global _current_workers, _max_workers, _executor
    
    if len(_wps_history) < 5:
        return
    
    avg_wps = sum(_wps_history) / len(_wps_history)
    avg_cpu = sum(_cpu_history) / len(_cpu_history) if _cpu_history else 0
    
    prev_wps = sum(list(_wps_history)[:-5]) / max(1, len(_wps_history) - 5) if len(_wps_history) > 5 else avg_wps
    wps_change = (avg_wps - prev_wps) / max(1, prev_wps)
    
    decision = "stable"
    new_workers = _current_workers
    
    if avg_cpu > 85 and wps_change < -0.2:
        new_workers = max(1, _current_workers - 1)
        decision = "throttle"
    elif avg_cpu < 60 and wps_change > 0.1 and _current_workers < _max_workers:
        new_workers = min(_max_workers, _current_workers + 1)
        decision = "scale_up"
    elif avg_cpu < 40 and _current_workers < _max_workers:
        new_workers = min(_max_workers, _current_workers + 1)
        decision = "scale_up"
    
    if new_workers != _current_workers:
        _current_workers = new_workers
        _executor._max_workers = _current_workers
    
    return {
        "current_workers": _current_workers,
        "max_workers": _max_workers,
        "avg_wps": round(avg_wps, 2),
        "avg_cpu": round(avg_cpu, 1),
        "wps_change": round(wps_change * 100, 1),
        "decision": decision,
    }


@app.post("/tts")
def generate_speech(req: TTSRequest):
    global _last_adjustment
    
    start_time = time.time()
    
    try:
        engine = get_engine(req.engine, req.voice, req.model)
        
        future = _executor.submit(engine.speak, req.text)
        audio = future.result(timeout=300)
        
        duration = time.time() - start_time
        _record_metrics(req.text, duration)
        
        if time.time() - _last_adjustment > 5:
            _last_adjustment = time.time()
        
        if audio is None:
            raise ValueError("Engine returned no audio")
        
        if isinstance(audio, list):
            audio = np.array(audio)
        
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            if isinstance(audio, np.ndarray):
                audio = (audio * 32767).astype(np.int16)
            wf.writeframes(audio.tobytes())
        
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "engines": list(engines.keys()),
        "workers": {
            "current": _current_workers,
            "max": _max_workers,
        }
    }


@app.get("/metrics")
def metrics():
    avg_wps = sum(_wps_history) / len(_wps_history) if _wps_history else 0
    avg_cpu = sum(_cpu_history) / len(_cpu_history) if _cpu_history else 0
    
    return {
        "workers": {
            "current": _current_workers,
            "max": _max_workers,
            "cpu_count": _cpu_count,
        },
        "performance": {
            "avg_wps": round(avg_wps, 2),
            "avg_cpu_percent": round(avg_cpu, 1),
            "wps_history": list(_wps_history),
            "cpu_history": [round(c, 1) for c in _cpu_history],
        },
        "queue": {
            "pending": _executor._work_queue.qsize() if hasattr(_executor, '_work_queue') else 0,
        }
    }


@app.post("/workers/adjust")
def adjust_workers(target: Optional[int] = None):
    global _current_workers, _executor
    
    if target is not None:
        target = max(1, min(_max_workers, target))
        _current_workers = target
        _executor._max_workers = target
        return {"workers": _current_workers, "message": f"Set to {target}"}
    
    return _adjust_workers()


@app.get("/benchmark")
def benchmark(text: str = "This is a test of the text to speech system"):
    results = []
    
    for _ in range(3):
        start = time.time()
        engine = get_engine("coqui", "en_US-lessac-medium")
        audio = engine.speak(text)
        duration = time.time() - start
        words = len(text.split())
        wps = words / duration
        results.append({
            "duration": round(duration, 2),
            "words": words,
            "wps": round(wps, 2),
        })
    
    avg_wps = sum(r["wps"] for r in results) / len(results)
    
    return {
        "text": text,
        "runs": results,
        "avg_wps": round(avg_wps, 2),
        "recommended_workers": min(_max_workers, max(1, int(avg_wps / 5))),
    }


@app.get("/voices")
def list_voices():
    return {
        "voices": [
            "en_US-lessac-medium",
            "en_US-lessac-medium",
        ]
    }


def run_server(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
