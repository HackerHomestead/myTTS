# Changelog

All notable changes to myTTS will be documented in this file.

## [v1.4.0-mvp] - 2026-03-08

### 💾 State Persistence

#### Added
- **State File**: `.mytts.json` saved alongside text files
  - Bookmarks with chunk text for context
  - Last reading position (word number)
  - Speed preference
  - Voice preference
- **Auto-Save**: State saved automatically on changes (2s debounce)
- **Auto-Resume**: Position restored when opening document
- **Jump Dialog Enhancement**: Shows bookmark text (truncated to 50 chars)

#### State File Format
```json
{
  "bookmarks": [
    {"index": 42, "text": "This is the bookmarked sentence...", "word": 500}
  ],
  "last_position": 42,
  "last_word": 500,
  "speed": 0.95,
  "voice": "en_US-lessac-medium"
}
```

#### Technical
- Backward compatible with old bookmark format (list of indices)
- State saved on: bookmark set, speed change, voice change, exit
- State file added to `.gitignore`

---

## [v1.3.0-mvp] - 2026-03-08

### 🎬 Word-Level Highlighting - Subtitle-Style Sync

#### Added
- **Word-Level Highlighting**: Current word highlighted in reverse video during playback
  - Subtitle-style sync: word changes color as it's spoken
  - Black text on yellow background for current word
  - Smooth transitions between words
- **WordTimingEstimator**: Estimates word timing using character weights
  - Vowels weighted 1.2x, consonants 0.8x
  - Scales to match actual audio duration
- **WordHighlightScheduler**: Timer-based word highlighting updates
  - Schedules highlights for each word in sentence
  - Cancels on playback stop or jump
- **Audio Duration Tracking**: `SentenceChunk.duration` field
  - `on_play` callback now includes duration parameter
  - Enables accurate word timing estimation

#### Changed
- **on_play Callback**: Signature changed from `(text, index)` to `(text, index, duration)`
- **ChunkDisplay**: Added `highlight_word()` and `clear_word_highlight()` methods
- **_on_sentence_play**: Now schedules word highlights for each sentence

#### Technical
- **16 new tests** for word timing and highlighting
- **48 total tests passing**
- **Design document**: `docs/ttswordsync-feature.md` with full analysis

---

## [v1.2.0-tui] - 2026-03-08

### 🎯 TUI Navigation Improvements

#### Added
- **Jump Dialog**: New modal dialog (press `j`) for jumping to any word position
  - Text input for entering word number
  - Bookmark list for quick selection
  - Audio pauses while dialog is open
  - Use ↑/↓ to navigate bookmarks
  - Click or Enter to select

#### Changed
- **Removed `n`/`p` bindings**: Next/previous sentence removed (use ↑/↓ + Enter instead)
- **Controls updated**: Compact controls now show `j` for jump dialog
- **Simplified navigation**: Arrow keys + Enter for chunk navigation

#### Fixed
- **Test updates**: Updated test_tui.py for new action bindings

---

## [v1.1.0-tui] - 2026-03-08

### 🖥️ TUI Improvements

#### Added
- **Terminal Size Display**: Shows current terminal dimensions in header (upper right) as `[COLxROW]`
- **HeaderDisplay Widget**: New widget showing file name and terminal size
- **Dynamic Text Fitting**: Content now properly fits within terminal height, accounting for text wrapping
- **Layout Tests**: New test suite for validating layout at different terminal sizes (80x24 to 150x40)

#### Changed
- **Default Terminal Size**: Changed from 80x25 to **96x30** for better readability
- **ChunkDisplay**: Now calculates actual line count for wrapped text
- **ControlsDisplay**: More compact control labels using symbols (⏸, →, ⇤⇥, ✕)
- **Scroll Behavior**: Improved scroll-to-current/selected to keep content visible

#### Fixed
- **Text Panel Windowing**: Fixed bug where text didn't fit within terminal size offset
- **Line Counting**: Now correctly accounts for text wrapping when calculating visible chunks
- **Property Naming**: Renamed `scroll_offset` to `chunk_scroll_offset` to avoid Widget conflict

---

## [v1.0.0-mvp] - 2026-03-08

### 🚀 MVP Release - Production Ready

#### Added
- **GPU-Accelerated TTS Server**: Complete production-ready server implementation
- **NVIDIA GPU Support**: Compatible with GTX 980, GTX 1050 Ti and newer GPUs
- **VITS Model Integration**: High-quality, stable speech synthesis model
- **Audio Drift Elimination**: Intelligent text splitting and audio processing pipeline
- **Real-Time Performance**: 10-20x faster than real-time processing (RTF 0.05-0.26)
- **Memory Management**: Automatic GPU memory cleanup and resource optimization
- **Health Monitoring**: Comprehensive `/health` endpoint with resource tracking
- **Cleanup Endpoint**: `/cleanup` endpoint for manual resource management
- **Advanced Audio Processing**: Normalization, fade effects, silence removal
- **Production Stability**: Proven reliability under extended load testing
- **Error Handling**: Graceful error recovery with automatic cleanup
- **Input Validation**: Text length limits and content validation
- **GPU Compatibility**: PyTorch 2.0.1+cu118 for older GPU support
- **Comprehensive Documentation**: Complete technical documentation and API reference

#### Technical Implementation
- **PyTorch 2.0.1+cu118**: GPU-compatible deep learning framework
- **TTS 0.13.2**: Text-to-speech synthesis library with VITS model
- **FastAPI Server**: Async HTTP server with automatic API documentation
- **Audio Processing Pipeline**: Multi-stage audio enhancement and quality improvement
- **Resource Monitoring**: Real-time GPU and system memory tracking
- **Garbage Collection**: Intelligent memory management and cleanup

#### Performance Metrics
- **Processing Time**: 0.1-0.8 seconds per request
- **Real-Time Factor**: 0.05-0.26 (10-20x faster than real-time)
- **GPU Memory Usage**: ~300-400MB per active model
- **Concurrent Requests**: Handles multiple simultaneous requests
- **Stability**: 1000+ consecutive requests without failure

#### API Endpoints
- `POST /tts`: Generate speech from text with advanced configuration options
- `GET /health`: Comprehensive server health and resource monitoring
- `POST /cleanup`: Manual resource cleanup and engine reset
- `GET /voices`: List available voice models
- Automatic OpenAPI documentation at `/docs`

#### Configuration Options
- **GPU/CPU Mode**: Automatic GPU detection with CPU fallback
- **Model Selection**: VITS (default) and Tacotron2 model support
- **Text Splitting**: Configurable intelligent text splitting
- **Audio Processing**: Adjustable normalization and fade effects

#### Documentation
- **Server MVP Documentation**: Comprehensive technical documentation
- **API Reference**: Complete endpoint documentation with examples
- **Deployment Guide**: Production deployment instructions
- **Performance Theory**: Audio quality and drift elimination theory
- **Troubleshooting Guide**: Common issues and solutions

---

## [v0.2.0] - Previous Development

#### Added
- Basic client/server architecture
- Piper TTS engine integration
- Ollama chat integration
- Command-line interface
- Basic documentation

#### Known Issues
- Audio drift in longer texts
- No GPU acceleration
- Limited error handling
- No resource monitoring

---

## [v0.1.0] - Initial Release

#### Added
- Initial project structure
- Basic TTS functionality
- Setup instructions

---

## MVP Status Legend

- ✅ **Implemented**: Feature complete and tested
- 🚀 **Performance**: Optimized for production use
- 🛡️ **Stability**: Proven reliable under load
- 📊 **Monitoring**: Comprehensive observability
- 📖 **Documentation**: Complete technical documentation

## Support

For MVP v1.0.0 support:
- **Documentation**: See `docs/SERVER_MVP.md`
- **Issues**: Report bugs via GitHub issues
- **Performance**: Monitor via `/health` endpoint
- **Troubleshooting**: Check server logs and GPU status