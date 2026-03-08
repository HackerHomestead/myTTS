"""TUI (Text User Interface) for myTTS reader using Textual framework."""

import threading
import logging
import traceback
from pathlib import Path
from typing import Optional, List, Callable
from queue import Queue, Empty
from time import sleep

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


class ActionQueue:
    """Queue for managing TUI actions with proper sequencing."""
    
    def __init__(self):
        self._queue: Queue = Queue()
        self._processing = False
        self._lock = threading.Lock()
        self._last_action_time = 0
        self._min_action_interval = 0.1  # 100ms between actions
    
    def enqueue(self, action: Callable, name: str = "action"):
        """Add an action to the queue."""
        logger.info(f"Enqueuing action: {name}")
        self._queue.put((action, name))
        if not self._processing:
            threading.Thread(target=self._process_queue, daemon=True).start()
    
    def _process_queue(self):
        """Process queued actions sequentially."""
        with self._lock:
            if self._processing:
                return
            self._processing = True
        
        try:
            while True:
                try:
                    action, name = self._queue.get(timeout=0.5)
                    
                    import time
                    elapsed = time.time() - self._last_action_time
                    if elapsed < self._min_action_interval:
                        sleep(self._min_action_interval - elapsed)
                    
                    logger.info(f"Processing action: {name}")
                    try:
                        action()
                    except Exception as e:
                        logger.error(f"Error in action {name}: {e}\n{traceback.format_exc()}")
                    
                    self._last_action_time = time.time()
                    self._queue.task_done()
                    
                except Empty:
                    break
        finally:
            with self._lock:
                self._processing = False
    
    def clear(self):
        """Clear all pending actions."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Empty:
                break


class ChunkDisplay(Static):
    """Widget to display multiple chunks with current one highlighted."""
    
    chunks: reactive[List[str]] = reactive(list)
    current_idx: reactive[int] = reactive(0)
    selected_idx: reactive[int] = reactive(0)
    scroll_offset: reactive[int] = reactive(0)
    total_sentences: reactive[int] = reactive(0)
    visible_lines: reactive[int] = reactive(7)
    
    def on_mount(self):
        """Calculate visible lines based on available space."""
        self._update_visible_lines()
    
    def on_resize(self, event):
        """Handle terminal resize events."""
        self._update_visible_lines()
    
    def _update_visible_lines(self):
        """Calculate how many lines can fit in the available space."""
        try:
            if hasattr(self, 'region'):
                available_height = self.region.height
                # Reserve space for padding and borders
                usable_height = max(available_height - 4, 3)
                self.visible_lines = min(usable_height, 15)
            else:
                self.visible_lines = 7
        except Exception:
            self.visible_lines = 7
    
    def render(self) -> Text:
        if not self.chunks:
            return Text("Ready to read...", style="dim italic")
        
        text = Text()
        text.append("\n")
        
        visible_start = self.scroll_offset
        visible_end = min(visible_start + self.visible_lines, len(self.chunks))
        
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
        elif self.current_idx >= self.scroll_offset + self.visible_lines:
            self.scroll_offset = self.current_idx - self.visible_lines + 1
    
    def scroll_to_selected(self):
        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + self.visible_lines:
            self.scroll_offset = self.selected_idx - self.visible_lines + 1


class StatusDisplay(Static):
    """Widget to display current status (speed, position, etc.)."""
    
    speed = reactive(1.0)
    words_spoken = reactive(0)
    total_words = reactive(0)
    is_paused = reactive(False)
    current_bookmark: reactive[int | None] = reactive(None)
    current_voice = reactive("en_US-lessac-medium")
    
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
        
        voice_name = self.current_voice.split('-')[-1].replace('-medium', '').title()
        text.append(f"🎤 {voice_name}  ", style="magenta bold")
        
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
            ("v", "Voice"),
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
        overflow: hidden;
    }
    
    #main-container {
        height: 100%;
        width: 100%;
        padding: 1 2;
        overflow: hidden;
    }
    
    #header-container {
        height: auto;
        margin-bottom: 1;
    }
    
    #content-container {
        height: 1fr;
        width: 100%;
        margin: 1 0;
        overflow: hidden;
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
        height: 100%;
        width: 100%;
        padding: 1 2;
        background: $panel;
        border: solid $primary;
        overflow-y: auto;
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
        Binding("v", "cycle_voice", "Voice"),
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
        
        self.action_queue = ActionQueue()
        
        self.available_voices = [
            "en_US-lessac-medium",
            "en_US-amy-medium",
            "en_US-ryan-medium",
            "en_US-danny-low",
            "en_US-joe-medium",
            "en_US-kathleen-low",
            "en_US-ljspeech-medium",
            "en_US-ryan-low",
        ]
        self.current_voice_index = 0
        
        if voice and voice in self.available_voices:
            self.current_voice_index = self.available_voices.index(voice)
        
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
        self._state_lock = threading.Lock()
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            with Container(id="header-container"):
                yield Static(
                    f"📖 Reading: {self.file_path.name}",
                    classes="title"
                )
            
            with ScrollableContainer(id="content-container"):
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
            current_voice = self.available_voices[self.current_voice_index]
            self.engine = TTSEngine(
                mode=TTSMode.READING,
                backend=backend,
                engine="piper",
                voice=current_voice,
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
            status_display.current_voice = current_voice
            
            if self.start_word > 0:
                self._seek_to_word(self.start_word)
            
            self._start_reading()
        except Exception as e:
            logger.error(f"Error during TUI initialization: {e}\n{traceback.format_exc()}")
            self._show_error(f"Initialization failed: {e}")
    
    def on_resize(self, event):
        """Handle terminal resize events."""
        try:
            chunk_display = self.query_one(ChunkDisplay)
            chunk_display._update_visible_lines()
            chunk_display.refresh()
        except Exception as e:
            logger.warning(f"Error handling resize: {e}")
    
    def on_unmount(self):
        """Clean up when TUI closes."""
        self.should_stop = True
        self.action_queue.clear()
        if self.client:
            self.client.stop()
            self.client.close()
    
    def _on_sentence_play(self, sentence: str, index: int):
        """Callback when a sentence is played."""
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
    
    def _safe_stop_playback(self):
        """Safely stop playback with proper state management."""
        with self._state_lock:
            self.should_stop = True
            if self.client:
                try:
                    self.client.stop()
                except Exception as e:
                    logger.warning(f"Error stopping client: {e}")
            
            if self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=1.0)
            
            if self.client:
                try:
                    self.client.reset()
                except Exception as e:
                    logger.warning(f"Error resetting client: {e}")
    
    def _safe_start_playback(self, idx: int):
        """Safely start playback from a given index."""
        with self._state_lock:
            self.current_sentence_idx = idx
            self.words_spoken = sum(len(s.split()) for s in self.sentences[:idx])
            
            chunk_display = self.query_one(ChunkDisplay)
            chunk_display.current_idx = idx
            chunk_display.selected_idx = idx
            chunk_display.scroll_to_current()
            
            self.should_stop = False
            self._start_reading()
    
    def action_toggle_pause(self):
        """Toggle pause state."""
        if self.client:
            self.client.toggle_pause()
            status = self.query_one(StatusDisplay)
            status.is_paused = self.client.is_paused
    
    def action_select_prev(self):
        """Select previous chunk."""
        chunk_display = self.query_one(ChunkDisplay)
        if chunk_display.selected_idx > 0:
            chunk_display.selected_idx -= 1
            chunk_display.scroll_to_selected()
    
    def action_select_next(self):
        """Select next chunk."""
        chunk_display = self.query_one(ChunkDisplay)
        if chunk_display.selected_idx < len(self.sentences) - 1:
            chunk_display.selected_idx += 1
            chunk_display.scroll_to_selected()
    
    def action_jump_to_selected(self):
        """Jump to selected chunk using action queue."""
        chunk_display = self.query_one(ChunkDisplay)
        idx = chunk_display.selected_idx
        
        def jump_action():
            self._safe_stop_playback()
            sleep(0.15)  # Wait for audio cleanup
            self._safe_start_playback(idx)
        
        self.action_queue.enqueue(jump_action, f"jump_to_{idx}")
    
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
        """Reset playback speed to default."""
        if self.client:
            self.client.reset_speed()
            self.query_one(StatusDisplay).speed = self.client.speed
    
    def action_cycle_voice(self):
        """Cycle to next voice using action queue."""
        self.current_voice_index = (self.current_voice_index + 1) % len(self.available_voices)
        new_voice = self.available_voices[self.current_voice_index]
        
        def voice_change_action():
            self._safe_stop_playback()
            sleep(0.15)
            
            try:
                backend = TTSBackend.SERVER
                self.engine = TTSEngine(
                    mode=TTSMode.READING,
                    backend=backend,
                    engine="piper",
                    voice=new_voice,
                    server_url=self.server_url,
                )
                
                self.client = ProgressiveTTSClient(
                    self.engine,
                    num_workers=4,
                    buffer_size=2,
                    on_play=self._on_sentence_play
                )
                
                self.client.speed = self.initial_speed
                
                status_display = self.query_one(StatusDisplay)
                status_display.current_voice = new_voice
                status_display.speed = self.client.speed
                
                self._safe_start_playback(self.current_sentence_idx)
                
            except Exception as e:
                logger.error(f"Error cycling voice: {e}\n{traceback.format_exc()}")
                self._show_error(f"Voice change failed: {e}")
        
        self.action_queue.enqueue(voice_change_action, f"change_voice_to_{new_voice}")
    
    def action_repeat_sentence(self):
        """Repeat current sentence using action queue."""
        if self.client and self.current_sentence_idx < len(self.sentences):
            idx = self.current_sentence_idx
            
            def repeat_action():
                self._safe_stop_playback()
                sleep(0.15)
                self._safe_start_playback(idx)
            
            self.action_queue.enqueue(repeat_action, "repeat_sentence")
    
    def action_set_bookmark(self):
        """Set bookmark at current position."""
        if self.current_sentence_idx not in self.bookmarks:
            self.bookmarks.append(self.current_sentence_idx)
            self.bookmarks.sort()
            self.current_bookmark_idx = self.bookmarks.index(self.current_sentence_idx)
            self.query_one(StatusDisplay).current_bookmark = self.current_sentence_idx + 1
    
    def action_prev_bookmark(self):
        """Jump to previous bookmark using action queue."""
        if self.bookmarks and self.current_bookmark_idx > 0:
            self.current_bookmark_idx -= 1
            target = self.bookmarks[self.current_bookmark_idx]
            
            def jump_action():
                self._safe_stop_playback()
                sleep(0.15)
                self._safe_start_playback(target)
            
            self.action_queue.enqueue(jump_action, f"jump_to_bookmark_{target}")
    
    def action_next_bookmark(self):
        """Jump to next bookmark using action queue."""
        if self.bookmarks and self.current_bookmark_idx < len(self.bookmarks) - 1:
            self.current_bookmark_idx += 1
            target = self.bookmarks[self.current_bookmark_idx]
            
            def jump_action():
                self._safe_stop_playback()
                sleep(0.15)
                self._safe_start_playback(target)
            
            self.action_queue.enqueue(jump_action, f"jump_to_bookmark_{target}")
    
    def action_goto_beginning(self):
        """Jump to beginning using action queue."""
        def jump_action():
            self._safe_stop_playback()
            sleep(0.15)
            self._safe_start_playback(0)
        
        self.action_queue.enqueue(jump_action, "goto_beginning")
    
    def action_goto_end(self):
        """Jump to end using action queue."""
        idx = len(self.sentences) - 1
        
        def jump_action():
            self._safe_stop_playback()
            sleep(0.15)
            self._safe_start_playback(idx)
        
        self.action_queue.enqueue(jump_action, "goto_end")
    
    async def action_quit(self):
        """Quit the TUI."""
        self.should_stop = True
        self.action_queue.clear()
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
