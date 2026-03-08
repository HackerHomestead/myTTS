"""TUI (Text User Interface) for myTTS reader using Textual framework."""

import threading
import logging
import traceback
from pathlib import Path
from typing import Optional, List

from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Static, ProgressBar
from textual.reactive import reactive
from textual.binding import Binding
from rich.text import Text
from rich.style import Style

from mytts import TTSEngine, TTSMode, TTSBackend
from mytts.client import ProgressiveTTSClient

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tui_errors.log'),
    ]
)
logger = logging.getLogger(__name__)


class ChunkDisplay(Static):
    """Widget to display multiple chunks with current one highlighted."""
    
    chunks: reactive[List[str]] = reactive(list)
    current_idx: reactive[int] = reactive(0)
    selected_idx: reactive[int] = reactive(0)
    scroll_offset: reactive[int] = reactive(0)
    total_sentences: reactive[int] = reactive(0)
    
    VISIBLE_LINES = 7
    
    def render(self) -> Text:
        if not self.chunks:
            return Text("Ready to read...", style="dim italic")
        
        text = Text()
        text.append("\n")
        
        visible_start = self.scroll_offset
        visible_end = min(visible_start + self.VISIBLE_LINES, len(self.chunks))
        
        for i in range(visible_start, visible_end):
            chunk = self.chunks[i]
            chunk_num = i + 1
            
            is_current = (i == self.current_idx)
            is_selected = (i == self.selected_idx)
            
            if is_current:
                text.append("  ▶ ", style="yellow bold")
                text.append(f"{chunk_num:3d}. ", style="yellow bold")
                text.append(f"{chunk}\n", style="yellow")
            elif is_selected:
                text.append("  ◆ ", style="cyan bold")
                text.append(f"{chunk_num:3d}. ", style="cyan bold")
                text.append(f"{chunk}\n", style="white")
            else:
                text.append("     ", style="dim")
                text.append(f"{chunk_num:3d}. ", style="dim")
                text.append(f"{chunk}\n", style="white dim")
        
        text.append("\n")
        return text
    
    def scroll_to_current(self):
        if self.current_idx < self.scroll_offset:
            self.scroll_offset = self.current_idx
        elif self.current_idx >= self.scroll_offset + self.VISIBLE_LINES:
            self.scroll_offset = self.current_idx - self.VISIBLE_LINES + 1
    
    def scroll_to_selected(self):
        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + self.VISIBLE_LINES:
            self.scroll_offset = self.selected_idx - self.VISIBLE_LINES + 1


class StatusDisplay(Static):
    """Widget to display current status (speed, position, etc.)."""
    
    speed = reactive(1.0)
    words_spoken = reactive(0)
    total_words = reactive(0)
    is_paused = reactive(False)
    current_bookmark: reactive[int | None] = reactive(None)
    
    def render(self):
        text = Text()
        
        speed_color = "yellow" if self.speed != 1.0 else "white"
        text.append(f"  Speed: {self.speed:.2f}x  ", style=f"{speed_color} bold")
        
        if self.is_paused:
            text.append("⏸ PAUSED  ", style="yellow bold")
        else:
            text.append("▶ Playing  ", style="green")
        
        text.append(f"Words: {self.words_spoken:,}/{self.total_words:,}  ", 
                   style="cyan")
        
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
            ("↑/↓", "Navigate"),
            ("Enter", "Jump"),
            ("+/−", "Speed"),
            ("0", "Reset"),
            ("r", "Repeat"),
            ("m", "Bookmark"),
            ("[/]", "Jump bm"),
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
    
    ChunkDisplay {
        height: auto;
        min-height: 10;
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
        Binding("up", "select_prev", "Prev Chunk"),
        Binding("down", "select_next", "Next Chunk"),
        Binding("enter", "jump_to_selected", "Jump"),
        Binding("n", "next_sentence", "Next"),
        Binding("p", "prev_sentence", "Previous"),
        Binding("plus,equals", "increase_speed", "Faster"),
        Binding("minus,underscore", "decrease_speed", "Slower"),
        Binding("0", "reset_speed", "Reset Speed"),
        Binding("r", "repeat_sentence", "Repeat"),
        Binding("m", "set_bookmark", "Bookmark"),
        Binding("bracketleft", "prev_bookmark", "← Bookmark"),
        Binding("bracketright", "next_bookmark", "Bookmark →"),
        Binding("home,b", "goto_beginning", "Beginning"),
        Binding("end,e", "goto_end", "End"),
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
        
        self.engine: Optional[TTSEngine] = None
        self.client: Optional[ProgressiveTTSClient] = None
        self.sentences: List[str] = []
        self.current_sentence_idx = 0
        self.total_words = 0
        self.words_spoken = 0
        
        self.bookmarks: List[int] = []
        self.current_bookmark_idx = -1
        
        self.is_reading = False
        self.should_stop = False
        self.read_thread: Optional[threading.Thread] = None
        self._reading_start_idx = 0
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            with Container(id="header-container"):
                yield Static(
                    f"📖 Reading: {self.file_path.name}",
                    classes="title"
                )
            
            with Container(id="content-container"):
                yield ChunkDisplay()
            
            with Container(id="progress-container"):
                yield ProgressBar(total=100)
            
            with Container(id="status-container"):
                yield StatusDisplay()
            
            with Container(id="controls-container"):
                yield ControlsDisplay()
        yield Footer()
    
    def on_mount(self):
        try:
            backend = TTSBackend.SERVER
            self.engine = TTSEngine(
                mode=TTSMode.READING,
                backend=backend,
                engine="piper",
                voice=self.voice or "en_US-lessac-medium",
                server_url=self.server_url,
            )
            
            self.client = ProgressiveTTSClient(
                self.engine,
                num_workers=4,
                buffer_size=2,
                on_play=self._on_sentence_play
            )
            
            self.client.speed = self.initial_speed
            
            text = self.file_path.read_text()
            self.sentences = self.client.split_into_sentences(text)
            self.total_words = sum(len(s.split()) for s in self.sentences)
            
            chunk_display = self.query_one(ChunkDisplay)
            chunk_display.chunks = self.sentences
            chunk_display.total_sentences = len(self.sentences)
            chunk_display.current_idx = 0
            chunk_display.selected_idx = 0
            
            status_display = self.query_one(StatusDisplay)
            status_display.total_words = self.total_words
            status_display.speed = self.initial_speed
            
            if self.start_word > 0:
                self._seek_to_word(self.start_word)
            
            self._start_reading()
        except Exception as e:
            logger.error(f"Error during TUI initialization: {e}\n{traceback.format_exc()}")
            self._show_error(f"Initialization failed: {e}")
    
    def on_unmount(self):
        self.should_stop = True
        if self.client:
            self.client.stop()
            self.client.close()
    
    def _on_sentence_play(self, sentence: str, index: int):
        self.words_spoken += len(sentence.split())
        self.current_sentence_idx = self._reading_start_idx + index
        
        self.call_from_thread(self._update_display)
    
    def _update_display(self):
        chunk_display = self.query_one(ChunkDisplay)
        chunk_display.current_idx = self.current_sentence_idx
        chunk_display.selected_idx = self.current_sentence_idx
        chunk_display.scroll_to_current()
        chunk_display.refresh()
        
        status_display = self.query_one(StatusDisplay)
        status_display.words_spoken = self.words_spoken
        status_display.speed = self.client.speed if self.client else 1.0
        status_display.is_paused = self.client.is_paused if self.client else False
        
        progress = self.query_one(ProgressBar)
        progress.update(progress=int(100 * self.words_spoken / self.total_words))
    
    def _start_reading(self):
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
                logger.error(f"Error in read thread: {e}\n{traceback.format_exc()}")
                self.call_from_thread(self._show_error, str(e))
            finally:
                self.is_reading = False
        
        self.read_thread = threading.Thread(target=read_thread, daemon=True)
        self.read_thread.start()
    
    def _seek_to_word(self, word_num: int):
        words_counted = 0
        for i, sentence in enumerate(self.sentences):
            sentence_words = len(sentence.split())
            if words_counted + sentence_words > word_num:
                self.current_sentence_idx = i
                self.words_spoken = words_counted
                break
            words_counted += sentence_words
    
    def _show_error(self, message: str):
        logger.error(f"Displaying error to user: {message}")
        self.query_one(ChunkDisplay).chunks = [f"Error: {message}"]
    
    def action_toggle_pause(self):
        if self.client:
            self.client.toggle_pause()
            status = self.query_one(StatusDisplay)
            status.is_paused = self.client.is_paused
    
    def action_select_prev(self):
        chunk_display = self.query_one(ChunkDisplay)
        if chunk_display.selected_idx > 0:
            chunk_display.selected_idx -= 1
            chunk_display.scroll_to_selected()
    
    def action_select_next(self):
        chunk_display = self.query_one(ChunkDisplay)
        if chunk_display.selected_idx < len(self.sentences) - 1:
            chunk_display.selected_idx += 1
            chunk_display.scroll_to_selected()
    
    def action_jump_to_selected(self):
        chunk_display = self.query_one(ChunkDisplay)
        self._jump_to_sentence(chunk_display.selected_idx)
    
    def action_next_sentence(self):
        if self.client and self.current_sentence_idx < len(self.sentences) - 1:
            self.client.skip_forward()
            self.current_sentence_idx = min(self.current_sentence_idx + 1, len(self.sentences) - 1)
    
    def action_prev_sentence(self):
        if self.client and self.current_sentence_idx > 0:
            self.client.skip_backward()
            self.current_sentence_idx = max(self.current_sentence_idx - 1, 0)
            self.words_spoken = sum(len(s.split()) for s in self.sentences[:self.current_sentence_idx])
    
    def action_increase_speed(self):
        if self.client:
            self.client.increase_speed()
            self.query_one(StatusDisplay).speed = self.client.speed
    
    def action_decrease_speed(self):
        if self.client:
            self.client.decrease_speed()
            self.query_one(StatusDisplay).speed = self.client.speed
    
    def action_reset_speed(self):
        if self.client:
            self.client.reset_speed()
            self.query_one(StatusDisplay).speed = self.client.speed
    
    def action_repeat_sentence(self):
        if self.client and self.current_sentence_idx < len(self.sentences):
            self._jump_to_sentence(self.current_sentence_idx)
    
    def action_set_bookmark(self):
        if self.current_sentence_idx not in self.bookmarks:
            self.bookmarks.append(self.current_sentence_idx)
            self.bookmarks.sort()
            self.current_bookmark_idx = self.bookmarks.index(self.current_sentence_idx)
            self.query_one(StatusDisplay).current_bookmark = self.current_sentence_idx + 1
    
    def action_prev_bookmark(self):
        if self.bookmarks and self.current_bookmark_idx > 0:
            self.current_bookmark_idx -= 1
            target = self.bookmarks[self.current_bookmark_idx]
            self._jump_to_sentence(target)
    
    def action_next_bookmark(self):
        if self.bookmarks and self.current_bookmark_idx < len(self.bookmarks) - 1:
            self.current_bookmark_idx += 1
            target = self.bookmarks[self.current_bookmark_idx]
            self._jump_to_sentence(target)
    
    def _jump_to_sentence(self, idx: int):
        try:
            if self.client:
                self.should_stop = True
                self.client.stop()
                
                if self.read_thread and self.read_thread.is_alive():
                    self.read_thread.join(timeout=2.0)
                
                self.client.reset()
                
                self.current_sentence_idx = idx
                self.words_spoken = sum(len(s.split()) for s in self.sentences[:idx])
                
                chunk_display = self.query_one(ChunkDisplay)
                chunk_display.current_idx = idx
                chunk_display.selected_idx = idx
                chunk_display.scroll_to_current()
                
                self.should_stop = False
                self._start_reading()
        except Exception as e:
            logger.error(f"Error jumping to sentence {idx}: {e}\n{traceback.format_exc()}")
            self._show_error(f"Jump failed: {e}")
    
    def action_goto_beginning(self):
        self._jump_to_sentence(0)
    
    def action_goto_end(self):
        self._jump_to_sentence(len(self.sentences) - 1)
    
    async def action_quit(self):
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
    app = TTSReaderApp(
        file_path=file_path,
        server_url=server_url,
        voice=voice,
        start_word=start_word,
        initial_speed=speed,
    )
    app.run()
