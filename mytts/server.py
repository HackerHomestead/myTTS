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
    model: str = "tts_models/en/ljspeech/tacotron2-DDC"


app = FastAPI(title="myTTS Server")
engines = {}


def get_engine(engine_name: str, voice: str, model: Optional[str] = None):
    import torch
    key = f"{engine_name}:{voice}:{model}"
    if key not in engines:
        if engine_name == "coqui":
            model = model or "tts_models/en/ljspeech/tacotron2-DDC"
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
        engine = get_engine(req.engine, req.voice, req.model)
        audio = engine.speak(req.text)
        
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
    return {"status": "ok", "engines": list(engines.keys())}


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
