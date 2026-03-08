# Refactoring Guide for myTTS

## Overview

This document provides a comprehensive refactoring guide for the myTTS (Text-to-Speech) system. The codebase has grown organically and would benefit from systematic refactoring to improve maintainability, testability, and code quality.

## Current Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        myTTS System                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Client Side (Local)          Server Side (Remote)           │
│  ┌─────────────────┐          ┌──────────────────┐          │
│  │  CLI (cli.py)   │          │  Server (server.py)│          │
│  │  - Commands     │          │  - FastAPI         │          │
│  │  - Controls     │          │  - GPU Support     │          │
│  └────────┬────────┘          └────────┬──────────┘          │
│           │                             │                      │
│  ┌────────▼────────┐          ┌────────▼──────────┐          │
│  │  TUI (tui.py)    │          │  Engine (piper.py) │          │
│  │  - Textual App   │          │  - Piper TTS       │          │
│  │  - Action Queue  │          │  - Audio Gen      │          │
│  │  - Chunk Display │          └───────────────────┘          │
│  └────────┬────────┘                                         │
│           │                                                   │
│  ┌────────▼────────────────────┐                             │
│  │  Client (client.py)          │                             │
│  │  - ProgressiveTTSClient     │                             │
│  │  - Audio Playback            │                             │
│  │  - Speed Control             │                             │
│  │  - Sentence Splitting        │                             │
│  └──────────────────────────────┘                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
myTTS/
├── mytts/
│   ├── __init__.py          # Package init, exports
│   ├── cli.py               # CLI interface (445 lines)
│   ├── client.py            # ProgressiveTTSClient (436 lines)
│   ├── tui.py               # TUI application (910 lines)
│   ├── server.py            # FastAPI server (191 lines)
│   ├── server_improved.py   # Improved server (369 lines)
│   ├── ollama.py            # Ollama integration (166 lines)
│   └── engine/
│       ├── __init__.py
│       ├── piper.py         # Piper TTS engine (64 lines)
│       ├── coqui.py         # Coqui TTS engine
│       └── remote.py       # Remote engine (60 lines)
├── tests/
│   └── test_client.py       # Unit tests (289 lines)
├── test_comprehensive.py    # Integration tests (486 lines)
├── test_server_durability.py # Durability tests
└── docs/
    ├── HOWTO.md             # Development workflow
    ├── TDD.md               # TDD guide
    ├── MANUAL.md            # User manual
    ├── BUILD.md             # Build guide
    └── TUI.md               # TUI documentation
```

## Code Quality Issues

### 1. Large Files

**Problem:** Several files exceed reasonable size limits:
- `tui.py`: 910 lines (should be <500)
- `cli.py`: 445 lines (acceptable but could be split)
- `client.py`: 436 lines (acceptable but complex)

**Impact:**
- Hard to navigate and understand
- Difficult to test
- Multiple responsibilities in one file

### 2. Mixed Responsibilities

**Problem:** Classes/files handle multiple concerns:

**`tui.py` contains:**
- UI rendering (ChunkDisplay, StatusDisplay, ControlsDisplay)
- Application logic (TTSReaderApp)
- State management (reactive properties)
- Audio control (playback management)
- Action queuing (ActionQueue class)

**`client.py` contains:**
- TTS generation
- Audio playback
- Speed control
- Sentence splitting
- Buffer management
- Worker pool management

### 3. Tight Coupling

**Problem:** Components are tightly coupled:

```python
# In tui.py - direct dependency on TTSEngine, ProgressiveTTSClient
self.engine = TTSEngine(...)
self.client = ProgressiveTTSClient(self.engine, ...)
```

**Impact:**
- Hard to test in isolation
- Hard to swap implementations
- Changes ripple through codebase

### 4. Low Test Coverage

**Current Coverage:**
- `client.py`: 52%
- `tui.py`: 0%
- `cli.py`: 0%
- `server.py`: 0%

**Impact:**
- Refactoring is risky
- Bugs may go undetected
- Hard to verify behavior

### 5. Inconsistent Error Handling

**Problem:** Mixed error handling patterns:

```python
# Pattern 1: Silent ignore
except Exception:
    pass

# Pattern 2: Log and continue
except Exception as e:
    logger.error(f"Error: {e}")
    pass

# Pattern 3: Show to user
except Exception as e:
    self._show_error(f"Error: {e}")
```

### 6. Magic Numbers

**Problem:** Hard-coded values throughout:

```python
# In client.py
blocksize=4096
latency='high'
fade_ms=10

# In tui.py
max_width = 60
visible_lines = 7
sleep(0.15)
```

## Refactoring Priorities

### Priority 1: Extract Components (High Impact, Medium Effort)

#### 1.1 Split `tui.py` into Multiple Files

**Current Structure:**
```
tui.py (910 lines)
├── ActionQueue
├── ChunkDisplay
├── StatusDisplay
├── ControlsDisplay
└── TTSReaderApp
```

**Proposed Structure:**
```
tui/
├── __init__.py
├── app.py              # TTSReaderApp (main application)
├── widgets/
│   ├── __init__.py
│   ├── chunk_display.py    # ChunkDisplay
│   ├── status_display.py   # StatusDisplay
│   └── controls_display.py # ControlsDisplay
├── action_queue.py     # ActionQueue
└── constants.py        # UI constants
```

**Benefits:**
- Each file <200 lines
- Clear separation of concerns
- Easier to test
- Easier to understand

**Steps:**
1. Create `tui/` directory structure
2. Extract ActionQueue to `action_queue.py`
3. Extract widgets to `widgets/` directory
4. Extract constants to `constants.py`
5. Update imports in `app.py`
6. Update imports in `cli.py`
7. Run all tests
8. Commit incrementally

#### 1.2 Split `client.py` into Modules

**Current Structure:**
```
client.py (436 lines)
├── SentenceChunk (dataclass)
├── ProgressiveTTSClient
│   ├── Initialization
│   ├── Speed control
│   ├── Audio playback
│   ├── Sentence splitting
│   ├── Worker management
│   └── Statistics
```

**Proposed Structure:**
```
client/
├── __init__.py
├── progressive_client.py  # Main client class
├── audio_player.py        # Audio playback logic
├── sentence_splitter.py   # Sentence splitting
├── models.py              # SentenceChunk, etc.
├── constants.py           # Audio constants
└── exceptions.py          # Custom exceptions
```

**Benefits:**
- Single responsibility per module
- Easier to test audio separately
- Easier to swap audio backend
- Clear interfaces

**Steps:**
1. Create `client/` directory structure
2. Extract SentenceChunk to `models.py`
3. Extract audio playback to `audio_player.py`
4. Extract sentence splitting to `sentence_splitter.py`
5. Extract constants to `constants.py`
6. Create custom exceptions in `exceptions.py`
7. Refactor ProgressiveTTSClient to use modules
8. Update imports throughout codebase
9. Run all tests
10. Commit incrementally

### Priority 2: Improve Testability (High Impact, High Effort)

#### 2.1 Add Dependency Injection

**Current:**
```python
class TTSReaderApp(App):
    def on_mount(self):
        self.engine = TTSEngine(...)  # Hard dependency
        self.client = ProgressiveTTSClient(self.engine, ...)
```

**Proposed:**
```python
class TTSReaderApp(App):
    def __init__(self, engine_factory=None, client_factory=None):
        self.engine_factory = engine_factory or TTSEngine
        self.client_factory = client_factory or ProgressiveTTSClient
    
    def on_mount(self):
        self.engine = self.engine_factory(...)
        self.client = self.client_factory(self.engine, ...)
```

**Benefits:**
- Easy to mock in tests
- Can swap implementations
- Better separation of concerns

**Steps:**
1. Identify all hard dependencies
2. Create factory interfaces
3. Add dependency injection to constructors
4. Update tests to use mocks
5. Verify all tests pass
6. Commit incrementally

#### 2.2 Increase Test Coverage

**Target Coverage:**
- `client.py`: 90%
- `tui/`: 80%
- `cli.py`: 70%
- `server.py`: 80%

**Steps:**
1. Run coverage report: `pytest --cov=mytts --cov-report=html`
2. Identify uncovered lines
3. Write tests for each uncovered area
4. Focus on critical paths first:
   - Audio playback
   - Speed control
   - Sentence splitting
   - Error handling
5. Run tests after each addition
6. Commit after each module reaches target

#### 2.3 Add Integration Tests

**Create `tests/integration/`:**
```
tests/integration/
├── test_client_server.py    # Client-server interaction
├── test_tui_playback.py     # TUI playback flow
├── test_cli_commands.py     # CLI command flows
└── test_error_recovery.py   # Error scenarios
```

**Benefits:**
- Catch integration bugs
- Verify end-to-end flows
- Document expected behavior

### Priority 3: Improve Code Quality (Medium Impact, Medium Effort)

#### 3.1 Extract Constants

**Create `constants.py` files:**

```python
# mytts/constants.py
AUDIO_BUFFER_SIZE = 4096
AUDIO_LATENCY = 'high'
FADE_DURATION_MS = 10
DEFAULT_SPEED = 0.95
SPEED_INCREMENT = 0.05
MIN_SPEED = 0.25
MAX_SPEED = 4.0

# mytts/tui/constants.py
MAX_TEXT_WIDTH = 60
DEFAULT_VISIBLE_LINES = 7
ACTION_DELAY_MS = 100
PLAYBACK_STOP_DELAY_MS = 150
```

**Benefits:**
- Single source of truth
- Easy to tune parameters
- Self-documenting code

#### 3.2 Standardize Error Handling

**Create exception hierarchy:**

```python
# mytts/exceptions.py
class MyTTSError(Exception):
    """Base exception for myTTS."""
    pass

class AudioPlaybackError(MyTTSError):
    """Audio playback failed."""
    pass

class TTSEngineError(MyTTSError):
    """TTS engine error."""
    pass

class ServerConnectionError(MyTTSError):
    """Cannot connect to server."""
    pass

class InvalidTextError(MyTTSError):
    """Invalid text input."""
    pass
```

**Use consistently:**

```python
# Before
except Exception as e:
    pass

# After
except AudioPlaybackError as e:
    logger.error(f"Audio playback failed: {e}")
    # Handle appropriately
```

#### 3.3 Add Type Hints

**Current:**
```python
def split_into_sentences(self, text):
    sentences = SENTENCE_ENDINGS.split(text.strip())
    ...
```

**Proposed:**
```python
def split_into_sentences(self, text: str) -> List[str]:
    """Split text into sentences.
    
    Args:
        text: Input text to split
        
    Returns:
        List of sentences with proper punctuation
        
    Raises:
        InvalidTextError: If text is None or empty
    """
    sentences = SENTENCE_ENDINGS.split(text.strip())
    ...
```

**Benefits:**
- Better IDE support
- Catch type errors early
- Self-documenting code

### Priority 4: Improve Architecture (High Impact, High Effort)

#### 4.1 Introduce Service Layer

**Create service layer:**

```python
# mytts/services/tts_service.py
class TTSService:
    """High-level TTS operations."""
    
    def __init__(self, engine: TTSEngine, player: AudioPlayer):
        self.engine = engine
        self.player = player
    
    def speak(self, text: str, speed: float = 1.0) -> None:
        """Speak text at given speed."""
        audio = self.engine.generate(text)
        self.player.play(audio, speed)
    
    def stop(self) -> None:
        """Stop playback."""
        self.player.stop()
```

**Benefits:**
- Clear API for TTS operations
- Easier to test
- Decouples UI from implementation

#### 4.2 Introduce Repository Pattern

**For server-side voice management:**

```python
# mytts/repositories/voice_repository.py
class VoiceRepository:
    """Manage voice models."""
    
    def __init__(self, voices_dir: Path):
        self.voices_dir = voices_dir
    
    def list_voices(self) -> List[Voice]:
        """List available voices."""
        ...
    
    def get_voice(self, name: str) -> Voice:
        """Get voice by name."""
        ...
    
    def is_cached(self, name: str) -> bool:
        """Check if voice is cached."""
        ...
```

**Benefits:**
- Abstract voice management
- Easier to add new voice sources
- Testable in isolation

#### 4.3 Use Events for Decoupling

**Current:** Direct method calls create tight coupling

**Proposed:** Event-driven architecture

```python
# mytts/events.py
from dataclasses import dataclass

@dataclass
class PlaybackStarted:
    chunk_index: int
    text: str

@dataclass
class PlaybackStopped:
    reason: str

@dataclass
class SpeedChanged:
    old_speed: float
    new_speed: float

# mytts/event_bus.py
class EventBus:
    """Simple event bus for decoupling."""
    
    def __init__(self):
        self._handlers = defaultdict(list)
    
    def subscribe(self, event_type, handler):
        self._handlers[event_type].append(handler)
    
    def publish(self, event):
        for handler in self._handlers[type(event)]:
            handler(event)
```

**Usage:**

```python
# In client
event_bus.publish(PlaybackStarted(index, text))

# In TUI
event_bus.subscribe(PlaybackStarted, self._on_playback_started)
```

**Benefits:**
- Decouple components
- Easy to add new event handlers
- Testable in isolation

## Refactoring Workflow

### Step-by-Step Process

1. **Write Tests First**
   - Before refactoring any code, ensure it has tests
   - Run coverage report
   - Add tests for uncovered code
   - Verify tests pass

2. **Make Small Changes**
   - Refactor one file/class at a time
   - Run tests after each change
   - Commit after each successful refactor
   - Keep changes atomic

3. **Use Feature Branches**
   ```bash
   git checkout -b refactor/split-tui
   # Make changes
   pytest tests/
   git commit -m "refactor: Extract ChunkDisplay to separate file"
   git push origin refactor/split-tui
   ```

4. **Update Documentation**
   - Update docstrings
   - Update architecture docs
   - Update HOWTO.md if workflow changes

5. **Review and Test**
   - Run all test suites
   - Manual testing of TUI
   - Check for regressions
   - Verify performance

### Testing Strategy

**During Refactoring:**
```bash
# Run unit tests
pytest tests/test_client.py -v

# Run integration tests
python test_comprehensive.py

# Run durability tests
python test_server_durability.py

# Check coverage
pytest --cov=mytts --cov-report=html
open htmlcov/index.html
```

**After Refactoring:**
```bash
# Full test suite
pytest tests/ -v --cov=mytts

# Manual TUI testing
python -m mytts.cli read --tui --server-url http://192.168.88.164:8000 test.txt

# Test all features:
# - Navigation (arrows, Enter)
# - Speed control (+/-)
# - Voice cycling (v)
# - Pause/resume (Space)
# - Resume from position (-w flag)
# - Quit and resume command
```

## Specific Refactoring Tasks

### Task 1: Extract Audio Player

**File:** `mytts/client/audio_player.py`

**Extract from:** `client.py`

**Interface:**
```python
class AudioPlayer:
    """Handle audio playback."""
    
    def __init__(self, buffer_size: int = 4096, latency: str = 'high'):
        self.buffer_size = buffer_size
        self.latency = latency
        self._is_playing = False
        self._stream_active = False
    
    def play(self, audio: np.ndarray, sample_rate: int, speed: float = 1.0) -> None:
        """Play audio at given speed."""
        ...
    
    def stop(self) -> None:
        """Stop playback."""
        ...
    
    def apply_fade(self, audio: np.ndarray, sample_rate: int, fade_ms: int = 10) -> np.ndarray:
        """Apply fade in/out to audio."""
        ...
    
    @property
    def is_playing(self) -> bool:
        """Check if audio is playing."""
        return self._is_playing
```

**Tests to write:**
- `test_play_calls_sd_play()`
- `test_stop_when_playing()`
- `test_stop_when_not_playing()`
- `test_apply_fade_normal_audio()`
- `test_apply_fade_short_audio()`

### Task 2: Extract Sentence Splitter

**File:** `mytts/client/sentence_splitter.py`

**Extract from:** `client.py`

**Interface:**
```python
class SentenceSplitter:
    """Split text into sentences."""
    
    def __init__(self, pattern: Pattern = SENTENCE_ENDINGS):
        self.pattern = pattern
    
    def split(self, text: str) -> List[str]:
        """Split text into sentences.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences with proper punctuation
        """
        ...
```

**Tests to write:**
- `test_split_simple_sentence()`
- `test_split_multiple_sentences()`
- `test_split_with_newlines()`
- `test_split_empty_text()`
- `test_split_no_ending_punctuation()`

### Task 3: Extract TUI Widgets

**Files:**
- `mytts/tui/widgets/chunk_display.py`
- `mytts/tui/widgets/status_display.py`
- `mytts/tui/widgets/controls_display.py`

**Extract from:** `tui.py`

**Example:**
```python
# mytts/tui/widgets/chunk_display.py
class ChunkDisplay(Static):
    """Widget to display multiple chunks with current one highlighted."""
    
    chunks: reactive[List[str]] = reactive(list)
    current_idx: reactive[int] = reactive(0)
    selected_idx: reactive[int] = reactive(0)
    scroll_offset: reactive[int] = reactive(0)
    total_sentences: reactive[int] = reactive(0)
    visible_lines: reactive[int] = reactive(7)
    
    def __init__(self, max_text_width: int = 60):
        self.max_text_width = max_text_width
        super().__init__()
    
    def render(self) -> Text:
        """Render the chunk display."""
        ...
    
    def scroll_to_current(self) -> None:
        """Scroll to keep current chunk centered."""
        ...
    
    def scroll_to_selected(self) -> None:
        """Scroll to keep selected chunk centered."""
        ...
```

### Task 4: Add Configuration

**File:** `mytts/config.py`

**Purpose:** Centralize all configuration

```python
from dataclasses import dataclass

@dataclass
class AudioConfig:
    buffer_size: int = 4096
    latency: str = 'high'
    fade_duration_ms: int = 10
    sample_rate: int = 22050

@dataclass
class SpeedConfig:
    default: float = 0.95
    increment: float = 0.05
    minimum: float = 0.25
    maximum: float = 4.0

@dataclass
class TUIConfig:
    max_text_width: int = 60
    default_visible_lines: int = 7
    action_delay_ms: int = 100
    playback_stop_delay_ms: int = 150

@dataclass
class Config:
    audio: AudioConfig = AudioConfig()
    speed: SpeedConfig = SpeedConfig()
    tui: TUIConfig = TUIConfig()
    
    @classmethod
    def from_file(cls, path: str) -> 'Config':
        """Load config from YAML/JSON file."""
        ...
```

**Usage:**
```python
config = Config()
client = ProgressiveTTSClient(
    engine,
    audio_buffer_size=config.audio.buffer_size,
    audio_latency=config.audio.latency
)
```

## Testing Improvements

### Add Test Fixtures

**File:** `tests/conftest.py`

```python
import pytest
from unittest.mock import Mock, MagicMock
from mytts import TTSEngine, TTSMode, TTSBackend

@pytest.fixture
def mock_engine():
    """Create a mock TTS engine."""
    engine = Mock(spec=TTSEngine)
    engine.backend = TTSBackend.SERVER
    engine.server_url = "http://localhost:8000"
    engine.voice = "en_US-lessac-medium"
    engine.engine_name = "piper"
    return engine

@pytest.fixture
def mock_audio():
    """Create mock audio data."""
    import numpy as np
    return np.ones(22050, dtype=np.float32)

@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return "This is a test. This is another sentence. And a third one."

@pytest.fixture
def config():
    """Test configuration."""
    from mytts.config import Config
    return Config()
```

### Add Property-Based Testing

**File:** `tests/test_client_properties.py`

```python
from hypothesis import given, strategies as st
from mytts.client.sentence_splitter import SentenceSplitter

@given(st.text())
def test_split_never_returns_empty_strings(text):
    """Split should never return empty strings."""
    splitter = SentenceSplitter()
    sentences = splitter.split(text)
    assert all(s for s in sentences)

@given(st.floats(min_value=0.25, max_value=4.0))
def test_speed_always_in_bounds(speed):
    """Speed should always be clamped to valid range."""
    client = ProgressiveTTSClient(mock_engine)
    client.speed = speed
    assert 0.25 <= client.speed <= 4.0
```

## Performance Optimizations

### Profile and Optimize

**Identify bottlenecks:**
```python
import cProfile
import pstats

# Profile TUI
cProfile.run('app.run()', 'tui_profile.stats')
stats = pstats.Stats('tui_profile.stats')
stats.sort_stats('cumulative')
stats.print_stats(20)
```

**Potential optimizations:**
1. Cache sentence splits
2. Lazy-load voice models
3. Pre-generate audio in background
4. Use connection pooling for server requests
5. Optimize text rendering in TUI

## Documentation Improvements

### Add Architecture Decision Records

**File:** `docs/adr/`

```
docs/adr/
├── 001-action-queue-for-thread-safety.md
├── 002-progressive-tts-with-workers.md
├── 003-server-side-tts-generation.md
├── 004-textual-for-tui.md
└── 005-piper-for-voice-synthesis.md
```

**Example ADR:**
```markdown
# ADR-001: Action Queue for Thread Safety

## Status
Accepted

## Context
The TUI needs to handle user actions (navigation, speed control) while
audio is playing in a background thread. Direct method calls from
background threads to update UI caused race conditions and PortAudio
errors.

## Decision
Implement an ActionQueue that serializes actions and processes them
sequentially with a minimum delay between actions.

## Consequences
- Thread-safe UI updates
- No race conditions
- Slight delay in UI responsiveness (100ms)
- Simpler mental model for developers
```

### Add API Documentation

**Use Sphinx or MkDocs:**

```bash
pip install sphinx sphinx-rtd-theme
cd docs
sphinx-quickstart
sphinx-apidoc -o source ../mytts
make html
```

## Migration Guide

### For Each Refactoring

1. **Create feature branch**
   ```bash
   git checkout -b refactor/task-name
   ```

2. **Write/update tests**
   ```bash
   # Add tests for code being refactored
   pytest tests/test_file.py -v
   ```

3. **Make changes incrementally**
   - One file/class at a time
   - Run tests after each change
   - Commit frequently

4. **Update imports**
   - Update all files that import refactored code
   - Run tests to verify

5. **Update documentation**
   - Update docstrings
   - Update architecture docs
   - Update HOWTO if needed

6. **Create pull request**
   - Describe changes
   - Reference this refactoring guide
   - List test coverage

7. **Review and merge**
   - Code review
   - Run all tests
   - Manual testing
   - Merge to main

## Success Metrics

### Code Quality Metrics

- **Test Coverage:** Target 80% overall
  - `client/`: 90%
  - `tui/`: 80%
  - `cli.py`: 70%
  - `server.py`: 80%

- **File Size:** All files <500 lines
  - `tui.py`: Split into 5+ files
  - `client.py`: Split into 4+ modules

- **Cyclomatic Complexity:** <10 per method

- **Maintainability Index:** >65

### Performance Metrics

- **Startup Time:** <2 seconds
- **Audio Latency:** <500ms from request to playback
- **Memory Usage:** <200MB for client
- **CPU Usage:** <10% when idle

### User Experience Metrics

- **No PortAudio Errors:** Zero errors during normal use
- **Smooth Scrolling:** 60fps in TUI
- **Responsive Controls:** <100ms response time

## Conclusion

This refactoring guide provides a roadmap for improving the myTTS codebase. The priorities are:

1. **Extract components** - Split large files into focused modules
2. **Improve testability** - Add dependency injection and increase coverage
3. **Improve code quality** - Extract constants, standardize errors, add types
4. **Improve architecture** - Add service layer, use events for decoupling

Each refactoring should be done incrementally with tests passing at each step. The goal is to make the codebase more maintainable, testable, and easier to understand for future developers.

## Resources

- [Refactoring: Improving the Design of Existing Code](https://martinfowler.com/books/refactoring.html) - Martin Fowler
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) - Robert C. Martin
- [Python Testing with pytest](https://pragprog.com/titles/bopytest/) - Brian Okken
- [Textual Documentation](https://textual.textualize.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
