from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

import numpy as np
import sounddevice as sd
from TTS.api import TTS


class BaseEngine(ABC):
    @abstractmethod
    def speak(
        self,
        text: str,
        output: Optional[Union[str, Path]] = None,
        streaming: bool = False,
    ):
        pass

    @abstractmethod
    def stream(self, text: str):
        pass


class CoquiEngine(BaseEngine):
    def __init__(self, voice: Optional[str] = None, mode=None, model: str = None, gpu: bool = False):
        import torch
        self.voice = voice or "en_US-lessac-medium"
        self.mode = mode
        self.gpu = gpu
        
        model = model or "tts_models/en/ljspeech/vits"
        # Use GPU mode if enabled and available
        if gpu and torch.cuda.is_available():
            try:
                torch.zeros(1).cuda()  # Test GPU allocation
            except Exception:
                gpu = False
                self.gpu = False
        self.tts = TTS(model, gpu=gpu)

    def speak(
        self,
        text: str,
        output: Optional[Union[str, Path]] = None,
        streaming: bool = False,
        split_sentences: bool = True,
    ):
        # Split long text to reduce drift
        max_length = 150  # characters - reduced for better stability
        if split_sentences and len(text) > max_length:
            # Split text into sentences or chunks
            import re
            # Better sentence splitting
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # If sentences are too long, split them further
            all_chunks = []
            for sentence in sentences:
                if len(sentence) > max_length:
                    # Split long sentences
                    words = sentence.split()
                    current_chunk = ""
                    for word in words:
                        if len(current_chunk + " " + word) <= max_length:
                            current_chunk += (" " if current_chunk else "") + word
                        else:
                            if current_chunk:
                                all_chunks.append(current_chunk)
                            current_chunk = word
                    if current_chunk:
                        all_chunks.append(current_chunk)
                else:
                    all_chunks.append(sentence)
            
            # Generate audio for each chunk
            audio_chunks = []
            for chunk in all_chunks:
                if len(chunk) > 0:
                    try:
                        chunk_audio = self.tts.tts(chunk)
                        # Normalize each chunk
                        if isinstance(chunk_audio, np.ndarray):
                            max_val = np.max(np.abs(chunk_audio))
                            if max_val > 0:
                                chunk_audio = chunk_audio / max_val * 0.9
                        audio_chunks.append(chunk_audio)
                    except Exception as e:
                        print(f"Error processing chunk: {e}")
                        continue
            
            # Concatenate audio chunks with small silence between them
            if audio_chunks:
                silence_duration = 0.1  # 100ms silence between chunks
                silence_samples = int(silence_duration * 22050)
                silence = np.zeros(silence_samples)
                
                audio = audio_chunks[0]
                for i in range(1, len(audio_chunks)):
                    audio = np.concatenate([audio, silence, audio_chunks[i]])
            else:
                audio = self.tts.tts(text[:max_length])
        else:
            audio = self.tts.tts(text)
        
        # Apply audio normalization to reduce artifacts
        if isinstance(audio, np.ndarray):
            # Normalize audio to prevent clipping and drift
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val * 0.95  # Slight headroom
        
        if output:
            import scipy.io.wavfile as wav
            wav.write(output, 22050, audio)
            return None
        
        return audio

    def stream(self, text: str):
        return self.speak(text)
    
    def cleanup(self):
        """Clean up GPU memory and resources"""
        import torch
        if self.gpu and torch.cuda.is_available():
            torch.cuda.empty_cache()
        import gc
        gc.collect()
