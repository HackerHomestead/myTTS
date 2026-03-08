# TUI Event Hardening Analysis

## Current Architecture

### Event Sources
1. **Audio Callbacks** (`_on_sentence_play`) - From sounddevice thread
2. **Keyboard Input** (Textual bindings) - From main thread
3. **Timer Events** (Word highlighting) - From timer threads
4. **Resize Events** (`on_resize`) - From main thread
5. **Action Queue** - From worker threads

### Threading Model
```
Main Thread (Textual)
├── UI rendering
├── Keyboard handling
├── Resize handling
└── call_from_thread() for cross-thread updates

Audio Thread (sounddevice)
├── Playback loop
└── Callbacks: _on_sentence_play()

Timer Threads
├── Word highlight timers
├── Auto-save timer
└── Loading hide timers

Action Queue Thread
├── Sequential action processing
└── Jump/repeat/voice change operations
```

---

## Identified Issues

### Issue #1: Race Condition in Word Highlighting

**Problem**: Timers fire regardless of audio state.

```python
# Current flow:
1. Sentence starts → schedule timers
2. User pauses → audio stops, timers continue
3. Timers fire → highlight moves (wrong!)
```

**Impact**: UX bug - highlighting continues during pause.

**Solution**: Pause-aware timer management.

---

### Issue #2: State Consistency During Rapid Operations

**Problem**: Multiple threads modify shared state without coordination.

```python
# Example race condition:
Thread 1 (Audio):     self.current_sentence_idx = 5
Thread 2 (Jump):      self.current_sentence_idx = 10
Thread 1 (UI update): displays index 5 (stale!)
```

**Impact**: UI may show incorrect state briefly.

**Solution**: State machine with atomic updates.

---

### Issue #3: Timer Cleanup on Jump

**Problem**: Old timers may not be fully cancelled before new ones scheduled.

```python
# Current:
def _safe_stop_playback():
    word_scheduler.cancel_highlights()  # Cancel timers
    # ... but timers may still be firing!
```

**Impact**: Brief flicker of wrong highlights.

**Solution**: Synchronous timer cancellation with join.

---

### Issue #4: Error Propagation

**Problem**: Errors in background threads are logged but not surfaced to user.

```python
# Current:
try:
    action()
except Exception as e:
    logger.error(...)  # Silent failure
```

**Impact**: User doesn't know something went wrong.

**Solution**: Error event bus with UI notification.

---

### Issue #5: Action Queue Thread Proliferation

**Problem**: Each queue processing creates a new thread.

```python
def enqueue(self, action, name):
    self._queue.put((action, name))
    if not self._processing:
        threading.Thread(...).start()  # New thread each time!
```

**Impact**: Thread creation overhead, potential resource exhaustion.

**Solution**: Persistent worker thread or thread pool.

---

### Issue #6: No Action Priority

**Problem**: All actions treated equally, even urgent ones.

```python
# Jump action queued after speed change
queue: [speed_change, jump_to_500]
# Speed change processes first (wrong order for UX)
```

**Impact**: Delayed response to user input.

**Solution**: Priority queue with user actions first.

---

### Issue #7: Missing State Validation

**Problem**: No validation of state transitions.

```python
# Can jump to any index without checking bounds
self.current_sentence_idx = 999  # But only 100 sentences!
```

**Impact**: Potential crashes or undefined behavior.

**Solution**: State validation layer.

---

## Proposed Improvements

### 1. Pause-Aware Timer Manager

```python
class PauseableTimerManager:
    """Manages timers that respect pause state."""
    
    def __init__(self):
        self._timers: List[threading.Timer] = []
        self._paused = False
        self._pause_time = 0
        self._lock = threading.Lock()
    
    def schedule(self, delay: float, callback: Callable) -> threading.Timer:
        """Schedule a pause-aware timer."""
        timer = threading.Timer(delay, self._wrap_callback(callback, delay))
        with self._lock:
            self._timers.append(timer)
        timer.start()
        return timer
    
    def pause(self):
        """Pause all timers."""
        with self._lock:
            self._paused = True
            self._pause_time = time.time()
            for timer in self._timers:
                timer.cancel()
            self._timers.clear()
    
    def resume(self):
        """Resume timers with adjusted delays."""
        with self._lock:
            self._paused = False
            # Re-schedule with remaining time
```

---

### 2. Event Bus for Decoupled Communication

```python
from dataclasses import dataclass
from typing import Callable, Dict, List
from enum import Enum

class EventType(Enum):
    PLAYBACK_STARTED = "playback_started"
    PLAYBACK_PAUSED = "playback_paused"
    PLAYBACK_RESUMED = "playback_resumed"
    PLAYBACK_STOPPED = "playback_stopped"
    SENTENCE_CHANGED = "sentence_changed"
    WORD_CHANGED = "word_changed"
    SPEED_CHANGED = "speed_changed"
    VOICE_CHANGED = "voice_changed"
    BOOKMARK_SET = "bookmark_set"
    ERROR = "error"
    STATE_SAVED = "state_saved"

@dataclass
class Event:
    type: EventType
    data: dict
    timestamp: float = time.time()

class EventBus:
    """Thread-safe event bus for decoupled communication."""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._lock = threading.Lock()
    
    def subscribe(self, event_type: EventType, handler: Callable):
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
    
    def emit(self, event: Event):
        """Emit event to all subscribers."""
        with self._lock:
            handlers = self._handlers.get(event.type, [])
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
```

---

### 3. State Machine for Playback

```python
from enum import Enum, auto

class PlaybackState(Enum):
    IDLE = auto()
    LOADING = auto()
    PLAYING = auto()
    PAUSED = auto()
    STOPPING = auto()
    ERROR = auto()

class PlaybackStateMachine:
    """State machine for playback with valid transitions."""
    
    TRANSITIONS = {
        PlaybackState.IDLE: [PlaybackState.LOADING],
        PlaybackState.LOADING: [PlaybackState.PLAYING, PlaybackState.ERROR],
        PlaybackState.PLAYING: [PlaybackState.PAUSED, PlaybackState.STOPPING, PlaybackState.LOADING],
        PlaybackState.PAUSED: [PlaybackState.PLAYING, PlaybackState.STOPPING],
        PlaybackState.STOPPING: [PlaybackState.IDLE],
        PlaybackState.ERROR: [PlaybackState.IDLE],
    }
    
    def __init__(self):
        self._state = PlaybackState.IDLE
        self._lock = threading.Lock()
    
    def transition(self, new_state: PlaybackState) -> bool:
        """Attempt state transition, returns True if valid."""
        with self._lock:
            if new_state in self.TRANSITIONS.get(self._state, []):
                old_state = self._state
                self._state = new_state
                logger.info(f"State: {old_state.name} → {new_state.name}")
                return True
            logger.warning(f"Invalid transition: {self._state.name} → {new_state.name}")
            return False
    
    @property
    def state(self) -> PlaybackState:
        return self._state
```

---

### 4. Improved Action Queue

```python
from queue import PriorityQueue
from dataclasses import dataclass, field
from typing import Any

@dataclass(order=True)
class PrioritizedAction:
    priority: int
    name: str = field(compare=False)
    action: Callable = field(compare=False)

class ImprovedActionQueue:
    """Priority-based action queue with persistent worker."""
    
    PRIORITY_HIGH = 0     # User actions (jump, pause)
    PRIORITY_NORMAL = 1  # State updates
    PRIORITY_LOW = 2      # Background tasks
    
    def __init__(self):
        self._queue: PriorityQueue = PriorityQueue()
        self._worker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._processing_lock = threading.Lock()
    
    def start(self):
        """Start the worker thread."""
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
    
    def _worker_loop(self):
        """Persistent worker loop."""
        while not self._stop_event.is_set():
            try:
                prioritized = self._queue.get(timeout=0.5)
                with self._processing_lock:
                    try:
                        prioritized.action()
                    except Exception as e:
                        logger.error(f"Action error: {e}")
                self._queue.task_done()
            except Empty:
                continue
    
    def enqueue(self, action: Callable, name: str, priority: int = 1):
        """Enqueue action with priority."""
        self._queue.put(PrioritizedAction(priority, name, action))
    
    def stop(self):
        """Stop the worker thread."""
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=1.0)
```

---

### 5. Error Handling with User Notification

```python
class ErrorHandler:
    """Centralized error handling with user notification."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._error_count = 0
        self._last_error_time = 0
    
    def handle(self, error: Exception, context: str = ""):
        """Handle error with logging and optional user notification."""
        self._error_count += 1
        self._last_error_time = time.time()
        
        # Log
        logger.error(f"Error in {context}: {error}\n{traceback.format_exc()}")
        
        # Emit event
        self.event_bus.emit(Event(
            type=EventType.ERROR,
            data={
                'error': str(error),
                'context': context,
                'count': self._error_count
            }
        ))
    
    def show_to_user(self, message: str):
        """Show error to user via event bus."""
        # This would be handled by a UI component subscribed to ERROR events
        pass
```

---

## Implementation Priority

### Phase 1: Critical Fixes
1. **Pause-aware timers** (Fixes Bug #1)
2. **Synchronous timer cancellation** (Fixes race condition)
3. **State validation** (Prevents crashes)

### Phase 2: Architecture Improvements
4. **Event bus** (Decouples components)
5. **State machine** (Valid state transitions)
6. **Improved action queue** (Priority + persistent worker)

### Phase 3: Polish
7. **Error handling** (User notification)
8. **State persistence improvements** (Atomic writes)
9. **Performance monitoring** (Event timing)

---

## Testing Strategy

### Unit Tests
- State machine transitions
- Event bus publish/subscribe
- Timer pause/resume
- Action queue priority

### Integration Tests
- Rapid jump operations
- Pause during playback
- Error recovery
- State consistency

### Stress Tests
- 100 rapid jumps
- Continuous playback for 1 hour
- Memory leak detection
