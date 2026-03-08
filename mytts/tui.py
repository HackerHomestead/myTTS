"""TUI (Text User Interface) for myTTS reader using Textual framework."""

import asyncio
import threading
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, ProgressBar
from textual.reactive import reactive
from textual.binding import Binding
from rich.text import Text

from mytts import TTSEngine, TTSMode, TTSBackend
from mytts.client import ProgressiveTTSClient


class SentenceDisplay(Static):
    """Widget to display the current sentence being read."""
    
    sentence = reactive("")
    sentence_number = reactive(0)
    total_sentences = reactive(0)
    
    def render(self):
        if not self.sentence:
            return Text("Ready to read...", style="dim italic")
        
        text = Text()
        text.append(f"\n  Sentence {self.sentence_number:,} of {self.total_sentences:,}\n\n", 
                   style="cyan bold")
        text.append(f"  {self.sentence}", style="white")
        return text


class StatusDisplay(Static):
    """Widget to display current status (speed, position, etc.)."""
    
    speed = reactive(1.0)
    words_spoken = reactive(0)
    total_words = reactive(0)
    is_paused = reactive(False)
    current_bookmark: reactive[int | None] = reactive(None)
    
    def render(self):
        text = Text()
        
        # Speed indicator
        speed_color = "yellow" if self.speed != 1.0 else "white"
        text.append(f"  Speed: {self.speed:.2f}x  ", style=f"{speed_color} bold")
        
        # Pause indicator
        if self.is_paused:
            text.append("⏸ PAUSED  ", style="yellow bold")
        else:
            text.append("▶ Playing  ", style="green")
        
        # Word count
        text.append(f"Words: {self.words_spoken:,}/{self.total_words:,}  ", 
                   style="cyan")
        
        # Bookmark
        if self.current_bookmark is not None:
            text.append(f"🔖 Bookmark at {self.current_bookmark}", 
                       style="magenta")
        
        return text


class ControlsDisplay(Static):
    """Widget to display available controls."""
    
    def render(self):
        text = Text()
        text.append("\n  ")
        
        controls = [
            ("Space", "Pause"),
            ("n/p", "Next/Prev"),
            ("+/−", "Speed"),
            ("0", "Reset"),
            ("r", "Repeat"),
            ("g", "Go to"),
            ("m", "Bookmark"),
            ("[/]", "Jump bookmark"),
            ("Home/End", "Begin/End"),
            ("q", "Quit"),
        ]
        
        for i, (key, action) in enumerate(controls):
            if i > 0:
                text.append("  ")
            text.append(f"[{key}]", style="cyan bold")
            text.append(f" {action}", style="white")
        
        text.append("\n")
        return text


class TTSReaderApp(App):
    """TUI application for reading text with TTS."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #main-container {
        height: 100%;
        padding: 1 2;
    }
    
    #header-container {
        height: auto;
        margin-bottom: 1;
    }
    
    #content-container {
        height: 1fr;
        margin: 1 0;
    }
    
    #progress-container {
        height: auto;
        margin-top: 1;
    }
    
    #status-container {
        height: auto;
    }
    
    #controls-container {
        height: auto;
        margin-top: 1;
    }
    
    .title {
        text-style: bold;
        color: $text-primary;
    }
    
    .progress-bar {
        height: 1;
    }
    
    SentenceDisplay {
        height: auto;
        min-height: 5;
        padding: 1 2;
        background: $panel;
        border: solid $primary;
    }
    
    StatusDisplay {
        height: auto;
        padding: 0 2;
        background: $panel;
    }
    
    ControlsDisplay {
        height: auto;
        padding: 0 2;
        background: $panel;
    }
    
    ProgressBar {
        height: 1;
    }
    """
    
    BINDINGS = [
        Binding("space", "toggle_pause", "Pause/Resume"),
        Binding("n", "next_sentence", "Next"),
        Binding("p", "prev_sentence", "Previous"),
        Binding("plus,equals", "increase_speed", "Faster"),
        Binding("minus,underscore", "decrease_speed", "Slower"),
        Binding("0", "reset_speed", "Reset Speed"),
        Binding("r", "repeat_sentence", "Repeat"),
        Binding("g", "goto_sentence", "Go To"),
        Binding("m", "set_bookmark", "Bookmark"),
        Binding("bracketleft", "prev_bookmark", "← Bookmark"),
        Binding("bracketright", "next_bookmark", "Bookmark →"),
        Binding("home,b", "goto_beginning", "Beginning"),
        Binding("end,e", "goto_end", "End"),
        Binding("question,i", "show_info", "Info"),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(
        self,
        file_path: str,
        server_url: str = "http://localhost:8000",
        voice: Optional[str] = None,
        start_word: int = 0,
        initial_speed: float = 1.0,
    ):
        super().__init__()
        self.file_path = Path(file_path)
        self.server_url = server_url
        self.voice = voice
        self.start_word = start_word
        self.initial_speed = initial_speed
        
        # TTS components
        self.engine: Optional[TTSEngine] = None
        self.client: Optional[ProgressiveTTSClient] = None
        self.sentences: List[str] = []
        self.current_sentence_idx = 0
        self.total_words = 0
        self.words_spoken = 0
        
        # Bookmarks
        self.bookmarks: List[int] = []
        self.current_bookmark_idx = -1
        
        # State
        self.is_reading = False
        self.should_stop = False
        self.read_thread: Optional[threading.Thread] = None
        self._reading_start_idx = 0  # Track starting index for current reading session
    
    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        with Container(id="main-container"):
            with Container(id="header-container"):
                yield Static(
                    f"📖 Reading: {self.file_path.name}",
                    classes="title"
                )
            
            with Container(id="content-container"):
                yield SentenceDisplay()
            
            with Container(id="progress-container"):
                yield ProgressBar(total=100, classes="progress-bar")
            
            with Container(id="status-container"):
                yield StatusDisplay()
            
            with Container(id="controls-container"):
                yield ControlsDisplay()
        yield Footer()
    
    def on_mount(self):
        """Initialize the TTS system when app starts."""
        # Initialize TTS engine
        backend = TTSBackend.SERVER
        self.engine = TTSEngine(
            mode=TTSMode.READING,
            backend=backend,
            engine="piper",
            voice=self.voice or "en_US-lessac-medium",
            server_url=self.server_url,
        )
        
        # Create client
        self.client = ProgressiveTTSClient(
            self.engine,
            num_workers=4,
            buffer_size=2,
            on_play=self._on_sentence_play
        )
        
        # Set initial speed
        self.client.speed = self.initial_speed
        
        # Load text
        text = self.file_path.read_text()
        self.sentences = self.client.split_into_sentences(text)
        self.total_words = sum(len(s.split()) for s in self.sentences)
        
        # Update UI
        sentence_display = self.query_one(SentenceDisplay)
        sentence_display.total_sentences = len(self.sentences)
        
        status_display = self.query_one(StatusDisplay)
        status_display.total_words = self.total_words
        status_display.speed = self.initial_speed
        
        # Start from specified word
        if self.start_word > 0:
            self._seek_to_word(self.start_word)
        
        # Start reading
        self._start_reading()
    
    def on_unmount(self):
        """Clean up when app closes."""
        self.should_stop = True
        if self.client:
            self.client.stop()
            self.client.close()
    
    def _on_sentence_play(self, sentence: str, index: int):
        """Callback when a sentence is played."""
        self.words_spoken += len(sentence.split())
        self.current_sentence_idx = self._reading_start_idx + index
        
        # Update UI (thread-safe)
        self.call_from_thread(self._update_display, sentence)
    
    def _update_display(self, sentence: str):
        """Update the display with current sentence."""
        sentence_display = self.query_one(SentenceDisplay)
        sentence_display.sentence = sentence
        sentence_display.sentence_number = self.current_sentence_idx + 1
        
        status_display = self.query_one(StatusDisplay)
        status_display.words_spoken = self.words_spoken
        status_display.speed = self.client.speed if self.client else 1.0
        status_display.is_paused = self.client.is_paused if self.client else False
        
        # Update progress bar
        progress = self.query_one(ProgressBar)
        progress.update(progress=int(100 * self.words_spoken / self.total_words))
        
        # Force refresh
        sentence_display.refresh()
    
    def _start_reading(self):
        """Start the reading thread."""
        if self.is_reading:
            return
        
        self.is_reading = True
        self.should_stop = False
        self._reading_start_idx = self.current_sentence_idx
        
        def read_thread():
            try:
                if self.client:
                    text = " ".join(self.sentences[self.current_sentence_idx:])
                    self.client.speak(text)
            except Exception as e:
                self.call_from_thread(self._show_error, str(e))
            finally:
                self.is_reading = False
        
        self.read_thread = threading.Thread(target=read_thread, daemon=True)
        self.read_thread.start()
    
    def _seek_to_word(self, word_num: int):
        """Seek to a specific word position."""
        words_counted = 0
        for i, sentence in enumerate(self.sentences):
            sentence_words = len(sentence.split())
            if words_counted + sentence_words > word_num:
                self.current_sentence_idx = i
                self.words_spoken = words_counted
                break
            words_counted += sentence_words
    
    def _show_error(self, message: str):
        """Display an error message."""
        self.query_one(SentenceDisplay).sentence = f"Error: {message}"
    
    # Actions
    
    def action_toggle_pause(self):
        """Toggle pause/resume."""
        if self.client:
            self.client.toggle_pause()
            status = self.query_one(StatusDisplay)
            status.is_paused = self.client.is_paused
    
    def action_next_sentence(self):
        """Skip to next sentence."""
        if self.client and self.current_sentence_idx < len(self.sentences) - 1:
            self.client.skip_forward()
            self.current_sentence_idx = min(self.current_sentence_idx + 1, len(self.sentences) - 1)
    
    def action_prev_sentence(self):
        """Go to previous sentence."""
        if self.client and self.current_sentence_idx > 0:
            self.client.skip_backward()
            self.current_sentence_idx = max(self.current_sentence_idx - 1, 0)
            self.words_spoken = sum(len(s.split()) for s in self.sentences[:self.current_sentence_idx])
    
    def action_increase_speed(self):
        """Increase playback speed."""
        if self.client:
            self.client.increase_speed()
            self.query_one(StatusDisplay).speed = self.client.speed
    
    def action_decrease_speed(self):
        """Decrease playback speed."""
        if self.client:
            self.client.decrease_speed()
            self.query_one(StatusDisplay).speed = self.client.speed
    
    def action_reset_speed(self):
        """Reset speed to default."""
        if self.client:
            self.client.reset_speed()
            self.query_one(StatusDisplay).speed = self.client.speed
    
    def action_repeat_sentence(self):
        """Repeat current sentence."""
        if self.client and self.current_sentence_idx < len(self.sentences):
            self._jump_to_sentence(self.current_sentence_idx)
    
    def action_goto_sentence(self):
        """Go to a specific sentence."""
        # This would ideally show an input dialog
        # For now, we'll just show a message
        self.query_one(SentenceDisplay).sentence = "Enter sentence number (not implemented in this version)"
    
    def action_set_bookmark(self):
        """Set a bookmark at current position."""
        if self.current_sentence_idx not in self.bookmarks:
            self.bookmarks.append(self.current_sentence_idx)
            self.bookmarks.sort()
            self.current_bookmark_idx = self.bookmarks.index(self.current_sentence_idx)
            self.query_one(StatusDisplay).current_bookmark = self.current_sentence_idx + 1
    
    def action_prev_bookmark(self):
        """Jump to previous bookmark."""
        if self.bookmarks and self.current_bookmark_idx > 0:
            self.current_bookmark_idx -= 1
            target = self.bookmarks[self.current_bookmark_idx]
            self._jump_to_sentence(target)
    
    def action_next_bookmark(self):
        """Jump to next bookmark."""
        if self.bookmarks and self.current_bookmark_idx < len(self.bookmarks) - 1:
            self.current_bookmark_idx += 1
            target = self.bookmarks[self.current_bookmark_idx]
            self._jump_to_sentence(target)
    
    def _jump_to_sentence(self, idx: int):
        """Jump to a specific sentence index."""
        if self.client:
            # Stop current playback
            self.should_stop = True
            self.client.stop()
            
            # Wait for thread to finish
            if self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=2.0)
            
            # Reset client state
            self.client.reset()
            
            # Update position
            self.current_sentence_idx = idx
            self.words_spoken = sum(len(s.split()) for s in self.sentences[:idx])
            
            # Update display
            self._update_display(self.sentences[idx] if idx < len(self.sentences) else "")
            
            # Restart reading
            self.should_stop = False
            self._start_reading()
    
    def action_goto_beginning(self):
        """Jump to beginning."""
        self._jump_to_sentence(0)
    
    def action_goto_end(self):
        """Jump to end."""
        self._jump_to_sentence(len(self.sentences) - 1)
    
    def action_show_info(self):
        """Show info about current position."""
        info = f"Position: {self.current_sentence_idx + 1}/{len(self.sentences)} sentences, "
        info += f"{self.words_spoken:,}/{self.total_words:,} words"
        if self.bookmarks:
            info += f", {len(self.bookmarks)} bookmarks"
        self.query_one(SentenceDisplay).sentence = info
    
    async def action_quit(self):
        """Quit the application."""
        self.should_stop = True
        if self.client:
            self.client.stop()
        self.exit()


def run_tui_reader(
    file_path: str,
    server_url: str = "http://localhost:8000",
    voice: Optional[str] = None,
    start_word: int = 0,
    speed: float = 1.0,
):
    """Run the TUI reader application."""
    app = TTSReaderApp(
        file_path=file_path,
        server_url=server_url,
        voice=voice,
        start_word=start_word,
        initial_speed=speed,
    )
    app.run()
