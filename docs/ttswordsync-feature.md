# TTS Word Sync Feature - Design Document

## Overview

Feature request: Sync words being read to the text displayed so the reader can follow the audio, with the current word highlighted in a different color (like subtitles).

---

## Current Architecture Analysis

### Existing Infrastructure

| Component | Current State | Relevant for Word Sync |
|-----------|---------------|------------------------|
| `ProgressiveTTSClient` | Sentence-level `on_play` callback | ✅ Provides sentence timing |
| `sounddevice` playback | Known sample rate | ✅ Can calculate audio duration |
| `ChunkDisplay` | Shows sentences with highlighting | ✅ Can extend for word-level |
| Piper ONNX | Black box, no timing output | ❌ No word timestamps |

### Current Flow
```
Text → split_into_sentences() → generate_audio() → play_audio()
                                        ↓
                                   on_play(sentence, index)
                                        ↓
                                   UI update (sentence level)
```

---

## The Challenge

Piper (and most TTS engines) generate audio as a black box - they don't expose when each word is spoken. The ONNX models don't provide alignment data.

**Key insight from Piper issue #70:**
> "The word boundaries are not obtainable, because the sentences are synthesized as a whole"

---

## Options Analysis

### Option A: Double TTS (Piper PR #407)

**How it works:**
1. Generate audio for full sentence
2. Generate audio for each word individually
3. Calculate word timing from word-level durations
4. Apply correction factor

**Implementation:**
```python
# Generate full sentence
full_audio = tts.synthesize(sentence)
# Generate each word
word_audios = [tts.synthesize(word) for word in sentence.split()]
# Calculate timings
timings = calculate_word_timings(full_audio, word_audios)
```

**Pros:**
- More accurate than pure estimation
- Works with current Piper

**Cons:**
- 2x TTS generation (performance impact)
- Words can be combined/split differently ("in the" → "inthe")
- Not perfect accuracy
- Significant latency increase

**Performance Impact:**
- Current: ~0.1s per sentence
- With Option A: ~0.2s per sentence (2x slower)

---

### Option B: Phoneme Duration Estimation

**How it works:**
1. Convert text to phonemes using espeak-ng
2. Apply pre-defined duration coefficients
3. Scale to match actual audio duration
4. Map phonemes back to words

**Phoneme Duration Reference (from ovos-classifiers):**
```python
PHONEME_DURATIONS = {
    'AA': 2.56, 'AE': 2.60, 'AH': 2.79, 'AO': 2.75,
    'AW': 2.88, 'AY': 2.85, 'B': 2.53, 'CH': 2.85,
    'D': 2.86, 'DH': 2.45, 'EH': 2.36, 'ER': 2.80,
    'EY': 2.81, 'F': 2.73, 'G': 2.54, 'HH': 2.57,
    'IH': 2.73, 'IY': 2.76, 'JH': 2.45, 'K': 2.68,
    'L': 2.65, 'M': 2.64, 'N': 2.82, 'NG': 2.83,
    'OW': 2.71, 'OY': 2.77, 'P': 2.66, 'R': 2.82,
    'S': 2.62, 'SH': 2.76, 'T': 2.86, 'TH': 3.24,
    'UH': 2.60, 'UW': 2.80, 'V': 2.85, 'W': 2.71,
    'Y': 2.63, 'Z': 2.91, 'ZH': 3.04, '.': 2.61
}
```

**Pros:**
- Fast (no extra TTS calls)
- Works with any TTS engine
- Reasonable accuracy for highlighting

**Cons:**
- Estimation-based (not perfect)
- Requires phoneme mapping
- Additional dependency (espeak-ng for phonemization)

---

### Option C: Forced Alignment (Whisper)

**How it works:**
1. Generate audio with TTS
2. Run Whisper on generated audio
3. Get word-level timestamps from Whisper
4. Use timestamps for highlighting

**Implementation:**
```python
import whisper

model = whisper.load_model("base")
result = model.transcribe(audio_file, word_timestamps=True)
word_timings = [
    (w["word"], w["start"], w["end"]) 
    for w in result["words"]
]
```

**Pros:**
- Very accurate
- Works with any TTS
- No modification to TTS engine needed

**Cons:**
- Additional processing step (~0.2s per 10s audio)
- Requires Whisper dependency (~150MB model)
- More complex architecture
- GPU recommended for performance

---

### Option D: Hybrid Approach (SELECTED)

**How it works:**
1. Use existing sentence-level timing from `on_play` callback
2. Estimate word timing within sentence using character/phoneme durations
3. Update UI on timer based on estimated positions
4. Re-sync at each sentence boundary

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                    TTSReaderApp                              │
│                                                              │
│  ┌──────────────────┐      ┌──────────────────────────┐   │
│  │ ProgressiveTTS   │      │ WordTimingEstimator       │   │
│  │ Client           │──────▶│ - estimate_word_timings() │   │
│  │                  │      │ - scale_to_audio_duration()│   │
│  │ on_play(text,    │      └──────────────────────────┘   │
│  │        idx,      │                    │                │
│  │        duration) │                    ▼                │
│  └──────────────────┘      ┌──────────────────────────┐   │
│                            │ WordHighlightScheduler    │   │
│                            │ - schedule_highlights()   │   │
│                            │ - cancel_highlights()     │   │
│                            └──────────────────────────┘   │
│                                        │                    │
│                                        ▼                    │
│                            ┌──────────────────────────┐   │
│                            │ ChunkDisplay              │   │
│                            │ - current_word_idx        │   │
│                            │ - highlight_word(idx)    │   │
│                            └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- Minimal architecture changes
- Uses existing infrastructure
- Good enough for highlighting
- No extra TTS calls
- No additional dependencies
- Fast performance

**Cons:**
- Estimation-based within sentences
- Accuracy varies by word length
- May drift slightly within long sentences

**Accuracy:**
- Sentence boundaries: 100% accurate (from TTS)
- Word boundaries: ~85-90% accurate (estimation)
- Good enough for subtitle-style highlighting

---

## Implementation Plan

### Phase 1: Audio Duration Tracking

**File:** `mytts/client.py`

**Changes:**
1. Modify `SentenceChunk` to include audio duration
2. Update `_play_chunk()` to calculate and report duration
3. Update `on_play` callback signature

```python
@dataclass
class SentenceChunk:
    text: str
    index: int
    audio: Optional[np.ndarray] = None
    sample_rate: int = 22050
    duration: float = 0.0  # NEW: audio duration in seconds

def _play_chunk(self, chunk: SentenceChunk):
    # ... existing code ...
    
    # Calculate audio duration
    chunk.duration = len(chunk.audio) / adjusted_rate
    
    # Report with callback (updated signature)
    if self.on_play:
        self.on_play(chunk.text, chunk.index, chunk.duration)
```

---

### Phase 2: Word Timing Estimator

**File:** `mytts/tui.py` (new class)

```python
class WordTimingEstimator:
    """Estimates word timing within a sentence."""
    
    # Average phoneme durations (from research)
    # These are relative weights, will be scaled to actual audio duration
    PHONEME_WEIGHTS = {
        'AA': 2.56, 'AE': 2.60, 'AH': 2.79, 'AO': 2.75,
        'AW': 2.88, 'AY': 2.85, 'B': 2.53, 'CH': 2.85,
        'D': 2.86, 'DH': 2.45, 'EH': 2.36, 'ER': 2.80,
        'EY': 2.81, 'F': 2.73, 'G': 2.54, 'HH': 2.57,
        'IH': 2.73, 'IY': 2.76, 'JH': 2.45, 'K': 2.68,
        'L': 2.65, 'M': 2.64, 'N': 2.82, 'NG': 2.83,
        'OW': 2.71, 'OY': 2.77, 'P': 2.66, 'R': 2.82,
        'S': 2.62, 'SH': 2.76, 'T': 2.86, 'TH': 3.24,
        'UH': 2.60, 'UW': 2.80, 'V': 2.85, 'W': 2.71,
        'Y': 2.63, 'Z': 2.91, 'ZH': 3.04
    }
    
    # Simple character-based weights (fallback)
    CHAR_WEIGHTS = {
        'vowels': 1.2,      # a, e, i, o, u
        'consonants': 0.8,  # other letters
        'space': 0.3,       # word boundaries
        'punctuation': 0.5  # . , ! ?
    }
    
    def estimate_word_timings(
        self, 
        sentence: str, 
        audio_duration: float
    ) -> List[tuple]:
        """
        Estimate timing for each word in sentence.
        
        Returns: [(word, start_time, end_time), ...]
        """
        words = sentence.split()
        if not words:
            return []
        
        # Calculate word weights (simple character-based estimation)
        word_weights = []
        for word in words:
            weight = 0.0
            for char in word.lower():
                if char in 'aeiou':
                    weight += self.CHAR_WEIGHTS['vowels']
                elif char.isalpha():
                    weight += self.CHAR_WEIGHTS['consonants']
                elif char in '.,!?;:':
                    weight += self.CHAR_WEIGHTS['punctuation']
            word_weights.append(max(weight, 0.5))  # Minimum weight
        
        # Add inter-word gaps
        total_weight = sum(word_weights) + (len(words) - 1) * self.CHAR_WEIGHTS['space']
        
        # Scale to match audio duration
        scale = audio_duration / total_weight if total_weight > 0 else 1.0
        
        # Calculate timings
        timings = []
        current_time = 0.0
        
        for i, (word, weight) in enumerate(zip(words, word_weights)):
            word_duration = weight * scale
            gap_duration = self.CHAR_WEIGHTS['space'] * scale if i < len(words) - 1 else 0
            
            timings.append({
                'word': word,
                'start': current_time,
                'end': current_time + word_duration,
                'duration': word_duration
            })
            
            current_time += word_duration + gap_duration
        
        return timings
```

---

### Phase 3: Word Highlighting in ChunkDisplay

**File:** `mytts/tui.py`

**Changes to ChunkDisplay:**
```python
class ChunkDisplay(Static):
    # ... existing reactive properties ...
    current_word_idx: reactive[int] = reactive(-1)
    current_sentence_idx: reactive[int] = reactive(-1)
    
    def highlight_word(self, sentence_idx: int, word_idx: int):
        """Update word highlighting."""
        self.current_sentence_idx = sentence_idx
        self.current_word_idx = word_idx
        self.refresh()
    
    def clear_word_highlight(self):
        """Clear word highlighting."""
        self.current_word_idx = -1
        self.current_sentence_idx = -1
        self.refresh()
    
    def render(self) -> Text:
        # ... existing code ...
        
        # When rendering current sentence, highlight current word
        if i == self.current_sentence_idx and self.current_word_idx >= 0:
            words = chunk.split()
            for word_i, word in enumerate(words):
                if word_i == self.current_word_idx:
                    text.append(word, style="yellow bold reverse")
                else:
                    text.append(word, style="yellow")
                
                if word_i < len(words) - 1:
                    text.append(" ", style="yellow")
        # ... rest of render ...
```

---

### Phase 4: Word Highlight Scheduler

**File:** `mytts/tui.py`

```python
class WordHighlightScheduler:
    """Schedules word highlighting updates."""
    
    def __init__(self, app: 'TTSReaderApp'):
        self.app = app
        self._timers: List[threading.Timer] = []
        self._lock = threading.Lock()
    
    def schedule_highlights(
        self, 
        sentence: str, 
        sentence_idx: int,
        audio_duration: float,
        estimator: WordTimingEstimator
    ):
        """Schedule word highlighting for a sentence."""
        self.cancel_highlights()
        
        timings = estimator.estimate_word_timings(sentence, audio_duration)
        
        with self._lock:
            for word_timing in timings:
                timer = threading.Timer(
                    word_timing['start'],
                    self._highlight_word,
                    args=[sentence_idx, word_timing['word'], timings.index(word_timing)]
                )
                timer.daemon = True
                timer.start()
                self._timers.append(timer)
    
    def cancel_highlights(self):
        """Cancel all pending highlights."""
        with self._lock:
            for timer in self._timers:
                timer.cancel()
            self._timers.clear()
    
    def _highlight_word(self, sentence_idx: int, word: str, word_idx: int):
        """Highlight a word (called from timer)."""
        try:
            self.app.call_from_thread(
                lambda: self.app._update_word_highlight(sentence_idx, word_idx)
            )
        except Exception:
            pass  # App may have closed
```

---

### Phase 5: Integration in TTSReaderApp

**File:** `mytts/tui.py`

**Changes to TTSReaderApp:**
```python
class TTSReaderApp(App):
    def __init__(self, ...):
        # ... existing init ...
        self.word_estimator = WordTimingEstimator()
        self.word_scheduler = WordHighlightScheduler(self)
    
    def _on_sentence_play(self, sentence: str, index: int, duration: float):
        """Callback when a sentence is played."""
        self.words_spoken += len(sentence.split())
        self.current_sentence_idx = self._reading_start_idx + index
        
        # Schedule word highlighting
        self.word_scheduler.schedule_highlights(
            sentence, 
            index, 
            duration,
            self.word_estimator
        )
        
        self.call_from_thread(self._update_display)
    
    def _update_word_highlight(self, sentence_idx: int, word_idx: int):
        """Update word highlighting in display."""
        chunk_display = self.query_one(ChunkDisplay)
        chunk_display.highlight_word(sentence_idx, word_idx)
    
    def _safe_stop_playback(self):
        """Safely stop playback with proper state management."""
        # Cancel word highlighting
        self.word_scheduler.cancel_highlights()
        
        # Clear highlight
        try:
            chunk_display = self.query_one(ChunkDisplay)
            chunk_display.clear_word_highlight()
        except Exception:
            pass
        
        # ... existing stop logic ...
```

---

## Testing Plan

### Unit Tests

```python
# tests/test_word_timing.py

def test_word_timing_estimator_basic():
    """Test basic word timing estimation."""
    estimator = WordTimingEstimator()
    
    sentence = "Hello world"
    duration = 1.0  # 1 second
    
    timings = estimator.estimate_word_timings(sentence, duration)
    
    assert len(timings) == 2
    assert timings[0]['word'] == "Hello"
    assert timings[1]['word'] == "world"
    assert timings[0]['start'] == 0.0
    assert timings[1]['end'] <= duration

def test_word_timing_estimator_single_word():
    """Test single word timing."""
    estimator = WordTimingEstimator()
    
    sentence = "Test"
    duration = 0.5
    
    timings = estimator.estimate_word_timings(sentence, duration)
    
    assert len(timings) == 1
    assert timings[0]['word'] == "Test"
    assert timings[0]['start'] == 0.0
    assert timings[0]['end'] == duration

def test_word_timing_estimator_empty():
    """Test empty sentence."""
    estimator = WordTimingEstimator()
    
    timings = estimator.estimate_word_timings("", 1.0)
    
    assert len(timings) == 0

def test_word_timing_estimator_long_sentence():
    """Test long sentence timing."""
    estimator = WordTimingEstimator()
    
    sentence = "The quick brown fox jumps over the lazy dog"
    duration = 3.0
    
    timings = estimator.estimate_word_timings(sentence, duration)
    
    assert len(timings) == 9
    # All timings should fit within duration
    assert timings[-1]['end'] <= duration
```

### Integration Tests

```python
def test_word_highlight_scheduler():
    """Test word highlight scheduling."""
    app = Mock(spec=TTSReaderApp)
    scheduler = WordHighlightScheduler(app)
    estimator = WordTimingEstimator()
    
    sentence = "Hello world"
    duration = 1.0
    
    scheduler.schedule_highlights(sentence, 0, duration, estimator)
    
    # Wait for first highlight
    time.sleep(0.2)
    
    # Should have scheduled timers
    assert len(scheduler._timers) > 0
    
    # Cancel should clear timers
    scheduler.cancel_highlights()
    assert len(scheduler._timers) == 0
```

---

## Performance Considerations

### Memory
- Word timings: ~100 bytes per sentence
- Timers: ~1KB per sentence (cleaned up after playback)

### CPU
- Estimation: O(n) where n = word count
- Timer scheduling: O(n) per sentence
- UI updates: O(1) per word

### Latency
- No additional TTS latency
- Timer overhead: <1ms per word
- UI update: <10ms per word

---

## Future Enhancements

### Phase 6: Improved Estimation (Optional)
- Use phoneme counting instead of character counting
- Integrate with espeak-ng for phonemization
- Add per-voice calibration

### Phase 7: Whisper Alignment (Optional)
- Add Whisper as optional dependency
- Use for more accurate alignment
- Fallback to estimation if Whisper unavailable

### Phase 8: Visual Enhancements
- Smooth transitions between words
- Progress bar for current word
- Karaoke-style color gradient

---

## Rollback Plan

If issues arise:
1. Disable word highlighting via config flag
2. Revert to sentence-level highlighting only
3. No changes to TTS engine required

```python
# Config option
ENABLE_WORD_HIGHLIGHTING = True  # Set to False to disable
```

---

## Documentation Updates

- [ ] Update `docs/TUI.md` with word highlighting feature
- [ ] Add configuration options to README
- [ ] Update CHANGELOG.md
- [ ] Add troubleshooting section for timing issues

---

## References

- Piper PR #407: https://github.com/rhasspy/piper/pull/407
- Piper Issue #70: https://github.com/rhasspy/piper/issues/70
- Piper Issue #361: https://github.com/rhasspy/piper/issues/361
- OVOS Phonemizer: https://github.com/OpenVoiceOS/ovos-classifiers
- Whisper Word Alignment: https://arxiv.org/html/2509.09987v1
