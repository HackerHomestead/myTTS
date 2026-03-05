from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
from pydantic import BaseModel
import io
import wave
import numpy as np

from mytts.engine.coqui import CoquiEngine
from mytts.engine.piper import PiperEngine


class TTSRequest(BaseModel):
    text: str
    voice: str = "en_US-lessac-medium"
    engine: str = "coqui"


app = FastAPI(title="myTTS Server")
engines = {}


def get_engine(engine_name: str, voice: str):
    key = f"{engine_name}:{voice}"
    if key not in engines:
        if engine_name == "coqui":
            engines[key] = CoquiEngine(voice=voice)
        elif engine_name == "piper":
            engines[key] = PiperEngine(voice=voice)
        else:
            raise ValueError(f"Unknown engine: {engine_name}")
    return engines[key]


@app.post("/tts")
def generate_speech(req: TTSRequest):
    try:
        engine = get_engine(req.engine, req.voice)
        audio = engine.speak(req.text)
        
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
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
        raise HTTPException(status_code=500, detail=str(e))


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
