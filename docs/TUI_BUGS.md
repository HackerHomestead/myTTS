# TUI Known Bugs

## Bug #1: Highlighting Continues During Pause

**Status:** ✅ FIXED
**Priority:** High
**Reported:** 2026-03-08
**Fixed:** 2026-03-08

### Description
When audio is paused (Space key), the word highlighting continues to progress through the sentence. The timers continue firing even though audio playback is stopped.

### Expected Behavior
- Highlighting should freeze on current word when paused
- Highlighting should resume when unpaused
- No new highlights should be scheduled while paused

### Root Cause
`WordHighlightScheduler` uses `threading.Timer` objects that are not aware of pause state. Timers fire regardless of whether audio is playing.

### Fix Implemented
Added pause/resume methods to `WordHighlightScheduler`:
- `pause()`: Cancels all timers and tracks pause time
- `resume()`: Reschedules timers with adjusted delays based on elapsed time
- `action_toggle_pause()`: Now calls `word_scheduler.pause()` and `word_scheduler.resume()`

### Files Changed
- `mytts/tui.py` - `WordHighlightScheduler` class
- `mytts/tui.py` - `action_toggle_pause()` method
- `tests/test_word_timing.py` - Added 3 new tests for pause/resume

---

## Bug #2: Timing Drifts on Jump/Navigation

**Status:** Open
**Priority:** High
**Reported:** 2026-03-08

### Description
Word highlighting timing drifts, especially when jumping to different sections of the document. The estimated word timing becomes increasingly inaccurate.

### Expected Behavior
- Timing should re-sync at each sentence boundary
- Jumping to a new position should reset timing
- No accumulated drift across the document

### Root Cause Analysis

#### Current Implementation
```
Sentence played → estimate_word_timings() → schedule timers
                                          ↓
                              Timers fire based on ESTIMATED duration
```

The estimation is based on:
1. Character weights (vowels=1.2x, consonants=0.8x)
2. Total audio duration (calculated from audio length / sample rate)

#### Problems

1. **No Keyframe Concept**: Each sentence is estimated independently, but there's no synchronization point to correct drift.

2. **Estimation vs Reality**: The character-weight estimation is approximate. A word like "queue" (4 chars, 3 vowels sound) might be estimated differently than it's actually spoken.

3. **Timer Accumulation**: When jumping, old timers may not be fully cancelled before new ones are scheduled.

4. **Speed Changes**: If speed is changed mid-sentence, the timers are not recalculated.

#### What We DO Have (Good)
- Duration is calculated from ACTUAL audio: `len(audio) / sample_rate`
- Each sentence gets fresh estimation
- Timers are cancelled on `_safe_stop_playback()`

#### What We're Missing
- **Keyframe sync**: A way to verify actual playback position
- **Drift correction**: Adjusting timing based on actual progress
- **Jump handling**: Ensuring clean timer cancellation on navigation

### Proposed Fixes

#### Option A: Sentence-Level Keyframes (Current Approach, Improved)
Each sentence IS a keyframe. The issue is that we're not using it correctly.

```python
# Current: Estimate once per sentence
timings = estimator.estimate_word_timings(sentence, duration)

# Problem: Timers are scheduled at t=0 relative to sentence start
# But if there's any delay in playback, timers drift

# Fix: Track actual sentence start time
sentence_start_time = time.time()
for word_timing in timings:
    actual_start = sentence_start_time + word_timing['start']
    # Schedule timer for actual_start
```

#### Option B: Audio Position Tracking
Query actual audio playback position and sync highlights.

```python
# Use sounddevice to get current position
current_sample = sd.get_current_position()
current_time = current_sample / sample_rate
# Update highlight based on actual position
```

**Problem**: `sounddevice` doesn't provide position during `sd.wait()` playback.

#### Option C: Chunked Playback with Callbacks
Break audio into smaller chunks with position callbacks.

```python
# Play in chunks, update highlight after each chunk
for chunk_start in range(0, len(audio), chunk_size):
    sd.play(audio[chunk_start:chunk_start+chunk_size], ...)
    sd.wait()
    # Update highlight position
```

**Problem**: Introduces latency between chunks.

#### Option D: Re-estimate on Jump (Recommended)
When jumping to a new position, ensure clean state and re-estimate.

```python
def _safe_start_playback(self, idx):
    # 1. Cancel ALL existing timers
    self.word_scheduler.cancel_highlights()
    
    # 2. Clear any pending state
    self.word_scheduler._current_sentence_idx = -1
    
    # 3. Start playback (will trigger _on_sentence_play with fresh estimation)
    self._start_reading()
```

### Files Affected
- `mytts/tui.py` - `WordHighlightScheduler` class
- `mytts/tui.py` - `WordTimingEstimator` class
- `mytts/tui.py` - `_safe_stop_playback()` method
- `mytts/tui.py` - `_safe_start_playback()` method

### Additional Considerations

1. **Speed Changes**: When speed changes, should we re-estimate current sentence?
2. **Long Sentences**: Sentences with many words will have more accumulated drift
3. **Voice Variation**: Different voices may have different timing characteristics

---

## Related Issues

- See `docs/ttswordsync-feature.md` for full design document
- See `docs/TUI_REFACTORING_TODO.md` for state management improvements

---

## Testing Notes

### Reproduction Steps for Bug #1
1. Start TUI: `mytts read test.txt --server --tui`
2. Wait for word highlighting to start
3. Press Space to pause
4. Observe: Highlighting continues to progress

### Reproduction Steps for Bug #2
1. Start TUI: `mytts read test.txt --server --tui`
2. Let it read a few sentences
3. Press `j` to open jump dialog
4. Jump to word position 500+
5. Observe: Timing is noticeably off

### Test Cases Needed
- [ ] Test pause freezes highlighting
- [ ] Test resume continues from correct position
- [ ] Test jump clears all timers
- [ ] Test timing accuracy within sentence
- [ ] Test timing after speed change
