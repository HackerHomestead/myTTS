import re
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from typing import Optional, Callable, List
import numpy as np
import sounddevice as sd
import io
import wave

from mytts import TTSEngine, TTSBackend


SENTENCE_ENDINGS = re.compile(r'[.!?]+[\s]+')


@dataclass
class SentenceChunk:
    text: str
    index: int
    audio: Optional[np.ndarray] = None
    sample_rate: int = 22050


class ProgressiveTTSClient:
    def __init__(
        self,
        engine: TTSEngine,
        num_workers: int = 4,
        buffer_size: int = 2,
        on_play: Optional[Callable[[str], None]] = None,
    ):
        self.engine = engine
        self.num_workers = num_workers
        self.buffer_size = buffer_size
        self.on_play = on_play
        
        self._executor = ThreadPoolExecutor(max_workers=num_workers)
        self._pending_futures: queue.Queue[Future] = queue.Queue()
        self._chunk_queue: queue.Queue[SentenceChunk] = queue.Queue()
        
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._playback_lock = threading.Lock()
        
        self._current_audio: Optional[np.ndarray] = None
        self._current_sample_rate = 22050
        
        self._speed = 1.0
        self._speed_lock = threading.Lock()
        
        self._stats = {
            "chunks_generated": 0,
            "chunks_played": 0,
            "total_generation_time": 0.0,
            "total_playback_time": 0.0,
        }
    
    @property
    def speed(self) -> float:
        with self._speed_lock:
            return self._speed
    
    @speed.setter
    def speed(self, value: float):
        with self._speed_lock:
            self._speed = max(0.25, min(4.0, value))
    
    def increase_speed(self, delta: float = 0.25):
        with self._speed_lock:
            self._speed = min(4.0, self._speed + delta)
    
    def decrease_speed(self, delta: float = 0.25):
        with self._speed_lock:
            self._speed = max(0.25, self._speed - delta)
    
    def reset_speed(self):
        with self._speed_lock:
            self._speed = 1.0
    
    def stop(self):
        self._stop_event.set()
        sd.stop()

    def split_into_sentences(self, text: str) -> List[str]:
        sentences = SENTENCE_ENDINGS.split(text.strip())
        result = []
        for s in sentences:
            s = s.strip()
            if s:
                # Add period only if not already ending with punctuation
                if not s[-1] in '.!?':
                    s = s + "."
                result.append(s)
        return result

    def _generate_audio(self, chunk: SentenceChunk) -> SentenceChunk:
        start = time.perf_counter()
        
        backend = self.engine.backend
        if backend == TTSBackend.SERVER:
            import requests
            response = requests.post(
                f"{self.engine.server_url}/tts",
                json={
                    "text": chunk.text,
                    "voice": self.engine.voice,
                    "engine": self.engine.engine_name,
                },
            )
            response.raise_for_status()
            wav_data = io.BytesIO(response.content)
            with wave.open(wav_data, 'rb') as wf:
                chunk.sample_rate = wf.getframerate()
                audio = wf.readframes(wf.getnframes())
                chunk.audio = np.frombuffer(audio, dtype=np.int16)
                chunk.audio = chunk.audio.astype(np.float32) / 32768.0
        else:
            audio = self.engine._engine.speak(chunk.text)
            if audio is not None:
                chunk.audio = audio
        
        self._stats["chunks_generated"] += 1
        self._stats["total_generation_time"] += time.perf_counter() - start
        return chunk

    def _play_chunk(self, chunk: SentenceChunk):
        if chunk.audio is None:
            return
        
        if self.on_play:
            self.on_play(chunk.text)
            
        self._current_audio = chunk.audio
        self._current_sample_rate = chunk.sample_rate
        
        # Apply speed adjustment
        with self._speed_lock:
            speed = self._speed
        
        # Adjust sample rate for speed (higher rate = faster playback)
        adjusted_rate = int(chunk.sample_rate * speed)
        
        start = time.perf_counter()
        sd.play(chunk.audio, samplerate=adjusted_rate)
        sd.wait()
        self._stats["total_playback_time"] += time.perf_counter() - start
        self._stats["chunks_played"] += 1

    def speak(self, text: str) -> dict:
        sentences = self.split_into_sentences(text)
        if not sentences:
            return self._stats
            
        chunks = [
            SentenceChunk(text=s, index=i) 
            for i, s in enumerate(sentences)
        ]
        
        self._stop_event.clear()
        self._stats = {
            "chunks_generated": 0,
            "chunks_played": 0,
            "total_generation_time": 0.0,
            "total_playback_time": 0.0,
        }
        
        submitted_futures = []
        pending_count = 0
        
        for chunk in chunks:
            if self._stop_event.is_set():
                break
            
            if pending_count < self.buffer_size:
                future = self._executor.submit(self._generate_audio, chunk)
                submitted_futures.append(future)
                pending_count += 1
            else:
                next_future = submitted_futures.pop(0)
                next_chunk = next_future.result()
                
                if not self._stop_event.is_set():
                    self._play_chunk(next_chunk)
                
                future = self._executor.submit(self._generate_audio, chunk)
                submitted_futures.append(future)
        
        if not self._stop_event.is_set():
            for future in submitted_futures:
                chunk = future.result()
                if not self._stop_event.is_set():
                    self._play_chunk(chunk)
        
        return self._stats

    def speak_async(self, text: str, callback: Optional[Callable] = None):
        def run():
            stats = self.speak(text)
            if callback:
                callback(stats)
        thread = threading.Thread(target=run)
        thread.start()
        return thread

    def close(self):
        self._executor.shutdown(wait=True)

    def get_stats(self) -> dict:
        return self._stats.copy()


class StreamingTTSClient(ProgressiveTTSClient):
    def __init__(
        self,
        engine: TTSEngine,
        num_workers: int = 4,
        lookahead: int = 2,
    ):
        super().__init__(engine, num_workers)
        self.lookahead = lookahead
        self._current_stream_idx = 0
        self._stream_chunks: List[SentenceChunk] = []
        self._chunk_futures: list[Future] = []
        self._submitted_indices = set()
        self._queue_lock = threading.Lock()
        
    def _stream_worker(self):
        while not self._stop_event.is_set():
            if self._current_stream_idx >= len(self._stream_chunks):
                time.sleep(0.05)
                continue
                
            chunk = self._stream_chunks[self._current_stream_idx]
            
            if chunk.audio is None:
                if self._chunk_futures and self._current_stream_idx < len(self._chunk_futures):
                    future = self._chunk_futures[self._current_stream_idx]
                    if future.done():
                        chunk.audio = future.result().audio
                else:
                    time.sleep(0.01)
                    continue
            
            self._play_chunk(chunk)
            self._current_stream_idx += 1
            
            with self._queue_lock:
                needed = min(self._current_stream_idx + self.lookahead, len(self._stream_chunks))
                for idx in range(len(self._chunk_futures), needed):
                    if idx < len(self._stream_chunks):
                        future = self._executor.submit(self._generate_audio, self._stream_chunks[idx])
                        self._chunk_futures.append(future)

    def feed(self, text: str):
        sentences = self.split_into_sentences(text)
        start_idx = len(self._stream_chunks)
        new_chunks = [
            SentenceChunk(text=s, index=start_idx + i)
            for i, s in enumerate(sentences)
        ]
        
        with self._queue_lock:
            self._stream_chunks.extend(new_chunks)
            for i, chunk in enumerate(new_chunks):
                if i < self.lookahead:
                    future = self._executor.submit(self._generate_audio, chunk)
                    self._chunk_futures.append(future)
                    self._submitted_indices.add(chunk.index)

    def play(self):
        self._stop_event.clear()
        self._playback_thread = threading.Thread(target=self._stream_worker)
        self._playback_thread.start()

    def stop(self):
        self._stop_event.set()
        sd.stop()
        if self._playback_thread:
            self._playback_thread.join()
