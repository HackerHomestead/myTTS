# TUI Refactoring TODO

## Overview

The TUI has grown into a complex event-driven application. This document outlines refactoring opportunities for improved maintainability, reduced duplication, and lower cognitive load.

---

## 1. State Management Abstractions

### 1.1 PlaybackState Class
**Problem**: Playback state (is_reading, should_stop, current_sentence_idx, words_spoken) is scattered throughout TTSReaderApp.

**Solution**: Create a dedicated state class with reactive properties.

```python
class PlaybackState:
    """Centralized playback state management."""
    
    is_playing: reactive[bool] = reactive(False)
    is_paused: reactive[bool] = reactive(False)
    current_idx: reactive[int] = reactive(0)
    words_spoken: reactive[int] = reactive(0)
    total_words: reactive[int] = reactive(0)
    
    # Computed properties
    @property
    def progress_percent(self) -> float:
        return self.words_spoken / self.total_words if self.total_words > 0 else 0
    
    # Events
    on_state_change: Optional[Callable] = None
```

**Benefits**:
- Single source of truth for playback state
- Easy to test in isolation
- Reactive updates propagate automatically

---

### 1.2 LoadingState Manager
**Problem**: Loading indicator logic is duplicated in 5+ places.

**Solution**: Context manager for loading states.

```python
class LoadingIndicator:
    """Manages loading indicator with automatic cleanup."""
    
    def __init__(self, status_display: StatusDisplay):
        self.status_display = status_display
    
    def show(self, message: str = "Loading..."):
        self.status_display.is_loading = True
        self.status_display.loading_message = message
    
    def hide(self):
        self.status_display.is_loading = False
        self.status_display.loading_message = ""
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.hide()
        return False
    
    def show_temporary(self, message: str, duration: float = 2.0):
        """Show loading for a fixed duration."""
        self.show(message)
        threading.Timer(duration, self.hide).start()
```

**Usage**:
```python
# Before
status_display.is_loading = True
status_display.loading_message = "Loading..."
# ... do work ...
threading.Timer(2.0, hide_loading).start()

# After
with self.loading.show("Loading..."):
    # ... do work ...
```

---

## 2. Word/Sentence Position Utilities

### 2.1 WordPositionCalculator
**Problem**: Word-to-sentence conversion logic duplicated in 3 places.

**Solution**: Utility class for position calculations.

```python
class WordPositionCalculator:
    """Converts between word positions and sentence indices."""
    
    def __init__(self, sentences: List[str]):
        self.sentences = sentences
        self._word_counts = [len(s.split()) for s in sentences]
        self._cumulative_words = self._build_cumulative()
    
    def _build_cumulative(self) -> List[int]:
        """Pre-compute cumulative word counts."""
        cumulative = [0]
        for count in self._word_counts:
            cumulative.append(cumulative[-1] + count)
        return cumulative
    
    def word_to_sentence(self, word_num: int) -> tuple[int, int]:
        """Convert word number to (sentence_idx, words_before_sentence)."""
        for i, cum in enumerate(self._cumulative_words):
            if cum > word_num:
                return (i - 1, self._cumulative_words[i - 1])
        return (len(self.sentences) - 1, self._cumulative_words[-2])
    
    def sentence_to_word(self, sentence_idx: int) -> int:
        """Get word number at start of sentence."""
        return self._cumulative_words[sentence_idx]
    
    def total_words(self) -> int:
        return self._cumulative_words[-1]
```

**Benefits**:
- O(log n) lookup instead of O(n) iteration
- Pre-computed for performance
- Single source of truth for position math

---

## 3. Playback Controller

### 3.1 PlaybackController Class
**Problem**: Playback control logic mixed with UI code.

**Solution**: Separate controller for audio operations.

```python
class PlaybackController:
    """Controls audio playback with proper state management."""
    
    def __init__(self, client: ProgressiveTTSClient, state: PlaybackState):
        self.client = client
        self.state = state
        self._lock = threading.Lock()
        self._read_thread: Optional[threading.Thread] = None
    
    def play(self, sentences: List[str], start_idx: int = 0):
        """Start playback from index."""
        with self._lock:
            self._stop_internal()
            self.state.is_playing = True
            self.state.current_idx = start_idx
            self._start_thread(sentences, start_idx)
    
    def stop(self):
        """Stop playback."""
        with self._lock:
            self._stop_internal()
    
    def jump_to(self, idx: int, sentences: List[str]):
        """Jump to specific index."""
        self.stop()
        sleep(0.15)  # Audio cleanup
        self.play(sentences, idx)
    
    def toggle_pause(self):
        """Toggle pause state."""
        self.client.toggle_pause()
        self.state.is_paused = self.client.is_paused
    
    # ... internal methods
```

**Benefits**:
- Encapsulates threading complexity
- Testable without UI
- Clear API surface

---

## 4. Widget Update Patterns

### 4.1 WidgetUpdateCoordinator
**Problem**: Widget updates scattered, direct `query_one` calls everywhere.

**Solution**: Centralized update coordinator.

```python
class WidgetCoordinator:
    """Coordinates widget updates."""
    
    def __init__(self, app: App):
        self.app = app
        self._widgets = {}
    
    def get(self, widget_type: type) -> Any:
        """Get or cache widget reference."""
        if widget_type not in self._widgets:
            self._widgets[widget_type] = self.app.query_one(widget_type)
        return self._widgets[widget_type]
    
    def update_chunk_display(self, current_idx: int, selected_idx: int):
        """Update chunk display with new indices."""
        widget = self.get(ChunkDisplay)
        widget.current_idx = current_idx
        widget.selected_idx = selected_idx
        widget.scroll_to_current()
        widget.refresh()
    
    def update_status(self, **kwargs):
        """Update status display with any property."""
        widget = self.get(StatusDisplay)
        for key, value in kwargs.items():
            setattr(widget, key, value)
    
    def update_progress(self, percent: float):
        """Update progress bar."""
        self.get(ProgressBar).update(progress=int(100 * percent))
```

---

## 5. Event System

### 5.1 Event Bus
**Problem**: State changes require manual widget updates.

**Solution**: Simple event bus for decoupled communication.

```python
from dataclasses import dataclass
from typing import Callable, Dict, List

@dataclass
class Event:
    """Base event class."""
    pass

@dataclass
class PlaybackPositionEvent(Event):
    sentence_idx: int
    word_num: int

@dataclass
class SpeedChangedEvent(Event):
    new_speed: float

@dataclass
class BookmarkEvent(Event):
    bookmark_idx: int
    word_num: int

class EventBus:
    """Simple event bus for decoupled communication."""
    
    def __init__(self):
        self._handlers: Dict[type, List[Callable]] = {}
    
    def subscribe(self, event_type: type, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def emit(self, event: Event):
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            handler(event)
```

**Usage**:
```python
# Subscribe
event_bus.subscribe(PlaybackPositionEvent, self._on_position_change)

# Emit
event_bus.emit(PlaybackPositionEvent(sentence_idx=5, word_num=100))
```

---

## 6. Code Organization

### 6.1 Split TUI into Modules
**Problem**: `tui.py` is 1200+ lines.

**Solution**: Split into focused modules:

```
mytts/tui/
├── __init__.py          # Exports TTSReaderApp
├── app.py               # Main TTSReaderApp class
├── widgets/
│   ├── __init__.py
│   ├── chunk.py         # ChunkDisplay
│   ├── status.py        # StatusDisplay
│   ├── header.py        # HeaderDisplay
│   └── controls.py      # ControlsDisplay
├── dialogs/
│   ├── __init__.py
│   └── jump_dialog.py   # JumpDialog
├── state/
│   ├── __init__.py
│   ├── playback.py      # PlaybackState
│   └── loading.py       # LoadingIndicator
├── controllers/
│   ├── __init__.py
│   └── playback.py      # PlaybackController
└── utils/
    ├── __init__.py
    └── position.py      # WordPositionCalculator
```

---

## 7. Action Refactoring

### 7.1 Action Base Class
**Problem**: Actions have repetitive patterns (loading, error handling).

**Solution**: Base action class with hooks.

```python
class BaseAction:
    """Base class for TUI actions with common patterns."""
    
    def __init__(self, app: TTSReaderApp):
        self.app = app
    
    def execute(self):
        """Execute the action with error handling."""
        try:
            self.pre_execute()
            self.do_action()
            self.post_execute()
        except Exception as e:
            self.on_error(e)
    
    def pre_execute(self):
        """Called before action. Override to show loading, etc."""
        pass
    
    def do_action(self):
        """Override to implement action logic."""
        raise NotImplementedError
    
    def post_execute(self):
        """Called after action. Override to hide loading, etc."""
        pass
    
    def on_error(self, error: Exception):
        """Handle errors. Default: log and show error."""
        logger.error(f"Action error: {error}")
        self.app._show_error(str(error))
```

---

## 8. Testing Improvements

### 8.1 Test Fixtures
**Problem**: Tests create mock objects repeatedly.

**Solution**: Reusable fixtures.

```python
# tests/tui_fixtures.py

@pytest.fixture
def mock_sentences():
    return ["First sentence.", "Second sentence.", "Third sentence."]

@pytest.fixture
def word_calculator(mock_sentences):
    return WordPositionCalculator(mock_sentences)

@pytest.fixture
def playback_state():
    return PlaybackState()

@pytest.fixture
def mock_app(mock_sentences, playback_state):
    app = Mock(spec=TTSReaderApp)
    app.sentences = mock_sentences
    app.state = playback_state
    return app
```

---

## 9. Priority Order

### High Priority (Do First)
1. **WordPositionCalculator** - Eliminates 3x duplication
2. **LoadingIndicator** - Reduces cognitive load significantly
3. **PlaybackState** - Single source of truth for state

### Medium Priority
4. **PlaybackController** - Separates concerns
5. **WidgetCoordinator** - Reduces query_one calls
6. **Event Bus** - Decouples components

### Low Priority (Future)
7. **Module Split** - Large refactoring, do when stable
8. **Action Base Class** - Nice to have pattern
9. **Test Fixtures** - Improves test maintainability

---

## 10. Metrics

### Current State
- `tui.py`: 1240 lines
- `TTSReaderApp`: ~500 lines
- Duplication: ~150 lines of repeated patterns
- Test coverage: 31%

### Target State
- `app.py`: ~200 lines (orchestration only)
- Total TUI code: ~800 lines (better organized)
- Duplication: <20 lines
- Test coverage: >60%

---

## 11. Implementation Notes

### Migration Strategy
1. Create new abstractions alongside existing code
2. Add tests for new abstractions
3. Gradually migrate existing code to use abstractions
4. Remove old code once migrated
5. Don't break existing functionality during migration

### Backward Compatibility
- Keep existing public API
- New abstractions are internal
- Tests ensure no regression

### Documentation
- Document each abstraction with docstrings
- Add architecture diagram to docs/TUI.md
- Update CHANGELOG for each refactoring
