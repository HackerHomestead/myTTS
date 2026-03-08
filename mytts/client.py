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
        on_play: Optional[Callable[[str, int], None]] = None,
        audio_buffer_size: int = 4096,
        audio_latency: str = 'high',
    ):
        self.engine = engine
        self.num_workers = num_workers
        self.buffer_size = buffer_size
        self.on_play = on_play
        self.audio_buffer_size = audio_buffer_size
        self.audio_latency = audio_latency
        
        self._executor = ThreadPoolExecutor(max_workers=num_workers)
        self._pending_futures: queue.Queue[Future] = queue.Queue()
        self._chunk_queue: queue.Queue[SentenceChunk] = queue.Queue()
        
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._playback_lock = threading.Lock()
        
        self._current_audio: Optional[np.ndarray] = None
        self._current_sample_rate = 22050
        self._is_playing = False
        self._playback_lock = threading.Lock()
        
        self._speed = 1.0
        self._speed_lock = threading.Lock()
        
        self._skip_forward = threading.Event()
        self._skip_backward = threading.Event()
        self._paused = threading.Event()
        self._current_chunk_index = 0
        self._chunks_list: List[SentenceChunk] = []
        
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
    
    def increase_speed(self, delta: float = 0.1):
        with self._speed_lock:
            self._speed = min(4.0, self._speed + delta)
    
    def decrease_speed(self, delta: float = 0.1):
        with self._speed_lock:
            self._speed = max(0.25, self._speed - delta)
    
    def reset_speed(self):
        with self._speed_lock:
            self._speed = 1.0
    
    @property
    def is_paused(self) -> bool:
        return self._paused.is_set()
    
    @property
    def current_position(self) -> int:
        return self._current_chunk_index
    
    @property
    def total_chunks(self) -> int:
        return len(self._chunks_list)
    
    def skip_forward(self):
        self._skip_forward.set()
        self._stop_playback()
    
    def skip_backward(self):
        self._skip_backward.set()
        self._stop_playback()
    
    def toggle_pause(self):
        if self._paused.is_set():
            self._paused.clear()
        else:
            self._paused.set()
            self._stop_playback()
    
    def stop(self):
        self._stop_event.set()
        self._stop_playback()
    
    def _stop_playback(self):
        """Safely stop audio playback."""
        with self._playback_lock:
            if self._is_playing:
                try:
                    sd.stop()
                    sd.wait()
                except Exception:
                    pass
                self._is_playing = False
    
    def reset(self):
        self._stop_event.clear()
        self._skip_forward.clear()
        self._skip_backward.clear()
        self._paused.clear()
        self._current_chunk_index = 0
        self._chunks_list = []
        with self._playback_lock:
            self._is_playing = False
    
    def split_into_sentences(self, text: str) -> List[str]:
        sentences = SENTENCE_ENDINGS.split(text.strip())
        result = []
        for s in sentences:
            s = " ".join(s.split())
            if s:
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

    def _apply_fade(self, audio: np.ndarray, sample_rate: int, fade_ms: int = 10) -> np.ndarray:
        fade_samples = int(sample_rate * fade_ms / 1000)
        if len(audio) < fade_samples * 2:
            return audio
        
        faded = audio.copy()
        fade_in = np.linspace(0.0, 1.0, fade_samples)
        fade_out = np.linspace(1.0, 0.0, fade_samples)
        faded[:fade_samples] *= fade_in
        faded[-fade_samples:] *= fade_out
        return faded
    
    def _play_chunk(self, chunk: SentenceChunk):
        if chunk.audio is None:
            return
        
        if self.on_play:
            self.on_play(chunk.text, chunk.index)
            
        self._current_audio = chunk.audio
        self._current_sample_rate = chunk.sample_rate
        
        with self._speed_lock:
            speed = self._speed
        
        adjusted_rate = int(chunk.sample_rate * speed)
        
        faded_audio = self._apply_fade(chunk.audio, adjusted_rate)
        
        with self._playback_lock:
            self._is_playing = True
        
        start = time.perf_counter()
        try:
            sd.play(
                faded_audio,
                samplerate=adjusted_rate,
                blocksize=self.audio_buffer_size,
                latency=self.audio_latency,
            )
            sd.wait()
        except Exception as e:
            pass
        finally:
            with self._playback_lock:
                self._is_playing = False
        
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
        self._skip_forward.clear()
        self._skip_backward.clear()
        self._chunks_list = chunks
        self._current_chunk_index = 0
        
        self._stats = {
            "chunks_generated": 0,
            "chunks_played": 0,
            "total_generation_time": 0.0,
            "total_playback_time": 0.0,
        }
        
        # Pre-generate first few chunks
        submitted_futures = {}
        for i in range(min(self.buffer_size, len(chunks))):
            future = self._executor.submit(self._generate_audio, chunks[i])
            submitted_futures[i] = future
        
        while self._current_chunk_index < len(chunks) and not self._stop_event.is_set():
            # Check for pause
            while self._paused.is_set() and not self._stop_event.is_set():
                time.sleep(0.1)
            
            if self._stop_event.is_set():
                break
            
            # Check for skip events
            if self._skip_forward.is_set():
                self._skip_forward.clear()
                self._current_chunk_index = min(self._current_chunk_index + 1, len(chunks) - 1)
                # Pre-generate upcoming chunks if needed
                for i in range(self._current_chunk_index, min(self._current_chunk_index + self.buffer_size, len(chunks))):
                    if i not in submitted_futures:
                        future = self._executor.submit(self._generate_audio, chunks[i])
                        submitted_futures[i] = future
                continue
            
            if self._skip_backward.is_set():
                self._skip_backward.clear()
                self._current_chunk_index = max(self._current_chunk_index - 1, 0)
                # Pre-generate upcoming chunks if needed
                for i in range(self._current_chunk_index, min(self._current_chunk_index + self.buffer_size, len(chunks))):
                    if i not in submitted_futures:
                        future = self._executor.submit(self._generate_audio, chunks[i])
                        submitted_futures[i] = future
                continue
            
            # Get current chunk
            chunk_idx = self._current_chunk_index
            chunk = chunks[chunk_idx]
            
            # Generate audio if not already done
            if chunk_idx in submitted_futures:
                chunk = submitted_futures[chunk_idx].result()
            else:
                chunk = self._generate_audio(chunk)
            
            # Play chunk
            if not self._stop_event.is_set():
                self._play_chunk(chunk)
            
            # Move to next chunk
            self._current_chunk_index += 1
            
            # Pre-generate next chunk if needed
            next_idx = self._current_chunk_index + self.buffer_size - 1
            if next_idx < len(chunks) and next_idx not in submitted_futures:
                future = self._executor.submit(self._generate_audio, chunks[next_idx])
                submitted_futures[next_idx] = future
        
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
    
    def get_audio_config(self) -> dict:
        """Get current audio configuration."""
        return {
            "buffer_size": self.audio_buffer_size,
            "latency": self.audio_latency,
            "default_output_device": sd.query_devices(kind='output'),
        }
    
    @staticmethod
    def get_recommended_buffer_size() -> int:
        """Get recommended buffer size based on system."""
        try:
            device_info = sd.query_devices(kind='output')
            default_samplerate = device_info.get('default_samplerate', 22050)
            
            if default_samplerate >= 44100:
                return 4096
            else:
                return 2048
        except Exception:
            return 4096
    
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
