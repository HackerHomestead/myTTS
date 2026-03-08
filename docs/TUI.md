# TUI Mode for myTTS Reader

The Text User Interface (TUI) mode provides a modern, interactive interface for reading documents with myTTS.

## Terminal Requirements

The TUI is optimized for an **80x25 (COLxROW)** terminal with some flexibility:
- Minimum: 80 columns × 24 rows
- Recommended: 80 columns × 25 rows
- Works well up to: 120 columns × 40 rows

The current terminal size is displayed in the header (upper right) as `[COLxROW]`.

## Starting TUI Mode

```bash
# Basic usage
mytts read document.txt --server --tui

# With options
mytts read document.txt --server --tui --speed 1.5 --voice en_US-amy-medium

# Resume from position
mytts read document.txt --server --tui -w 1250
```

## Features

### Persistent UI Elements
- **Header**: Shows file name and reading status
- **Content Area**: Displays current sentence being read
- **Progress Bar**: Visual progress indicator
- **Status Bar**: Shows speed, word count, pause state, bookmarks
- **Controls Footer**: Always-visible control reference

### Keyboard Controls

| Key | Action |
|-----|--------|
| `Space` | Pause/Resume |
| `n` | Next sentence |
| `p` | Previous sentence |
| `+` / `=` | Increase speed |
| `-` / `_` | Decrease speed |
| `0` | Reset speed to 1.0x |
| `r` | Repeat current sentence |
| `g` | Go to specific sentence |
| `m` | Set bookmark at current position |
| `[` | Jump to previous bookmark |
| `]` | Jump to next bookmark |
| `Home` / `b` | Jump to beginning |
| `End` / `e` | Jump to end |
| `?` / `i` | Show info |
| `q` | Quit |

### Bookmarks

Bookmarks allow you to mark positions in the document for quick navigation:

1. Press `m` to set a bookmark at current position
2. Use `[` and `]` to jump between bookmarks
3. Bookmarks are shown in the status bar

### Speed Control

- Speed range: 0.25x to 4.0x
- Default: 1.0x
- Speed changes apply immediately
- Current speed shown in status bar (yellow when not 1.0x)

## Comparison: CLI vs TUI Mode

| Feature | CLI Mode | TUI Mode |
|---------|----------|----------|
| Interface | Simple text output | Full-screen TUI |
| Controls | Basic keyboard | Full keyboard + visual |
| Progress | Text-based | Visual progress bar |
| Bookmarks | No | Yes |
| Status Display | Intermittent | Always visible |
| Navigation | Limited | Full (bookmarks, jump) |
| Dependencies | Minimal | textual, rich |

## Requirements

TUI mode requires additional packages:

```bash
pip install textual rich
```

Or install myTTS with TUI support:

```bash
pip install -e .  # textual and rich are now dependencies
```

## Architecture

The TUI is built using:
- **Textual**: Modern TUI framework for Python
- **Rich**: Terminal formatting library
- **Threading**: Background audio processing
- **Reactive UI**: Auto-updating display

### Components

```
TTSReaderApp
├── Header (Textual header widget)
├── Main Container
│   ├── HeaderDisplay (file name + terminal size)
│   ├── ChunkDisplay (current and surrounding sentences)
│   ├── ProgressBar (visual progress)
│   ├── StatusDisplay (speed, position, bookmarks)
│   └── ControlsDisplay (keyboard shortcuts)
└── Footer (Textual footer widget)
```

## Server Requirements

**No server changes required!**

The TUI mode uses the same server API as CLI mode. All controls are client-side:
- Speed adjustment (client-side audio rate)
- Navigation (chunk index tracking)
- Bookmarks (client-side position storage)
- Pause/resume (client-side event)

## Troubleshooting

### TUI doesn't start

```bash
# Check dependencies
pip install textual rich

# Verify installation
python -c "from mytts.tui import TTSReaderApp; print('OK')"
```

### Display issues

- Ensure terminal supports 256 colors
- Try a modern terminal (iTerm2, Windows Terminal, etc.)
- Check terminal size (minimum 80x24, recommended 80x25)
- Terminal size is shown in header as `[COLxROW]`

### Controls not responding

- Make sure the TUI window has focus
- Check if paused (Space to resume)
- Verify keyboard isn't grabbed by another app

## Future Enhancements

Potential future features:
- [ ] Search within document
- [ ] Multiple bookmarks with labels
- [ ] Reading statistics dashboard
- [ ] Custom color themes
- [ ] Mouse support
- [ ] Split view (text + audio waveform)
- [ ] Export bookmarks
- [ ] Chapter/section navigation
