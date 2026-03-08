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
    chunk_scroll_offset: reactive[int] = reactive(0)
    total_sentences: reactive[int] = reactive(0)
    max_width: reactive[int] = reactive(80)
    
    def on_mount(self):
        """Calculate max width based on terminal size."""
        self._update_max_width()
    
    def on_resize(self, event):
        """Handle terminal resize events."""
        self._update_max_width()
    
    def _update_max_width(self):
        """Calculate max text width based on available space.
        
        Layout: ▶12345│text...
        - Indicator: 1 char
        - Word number: 5 chars
        - Separator: 1 char
        Total prefix: 7 chars
        Available for text: terminal_width - 7 - 4 (padding/borders)
        """
        try:
            if hasattr(self, 'region'):
                available_width = self.region.width
            else:
                available_width = 80
            
            self.max_width = max(40, available_width - 11)
        except Exception:
            self.max_width = 69
    
    def _count_lines_for_chunk(self, chunk: str) -> int:
        """Count how many lines a chunk will take after wrapping."""
        words = chunk.split()
        if not words:
            return 1
        
        line_count = 1
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > self.max_width and current_length > 0:
                line_count += 1
                current_length = len(word)
            else:
                current_length += len(word) + 1
        
        return line_count
    
    def _get_word_start_for_chunk(self, chunk_idx: int) -> int:
        """Get the starting word number for a chunk."""
        word_count = 0
        for i in range(chunk_idx):
            if i < len(self.chunks):
                word_count += len(self.chunks[i].split())
        return word_count + 1
    
    def render(self) -> Text:
        if not self.chunks:
            return Text("Ready to read...", style="dim italic")
        
        text = Text()
        
        try:
            available_height = self.region.height if hasattr(self, 'region') else 20
        except Exception:
            available_height = 20
        
        visible_start = self.chunk_scroll_offset
        current_height = 0
        visible_chunks = []
        
        for i in range(visible_start, len(self.chunks)):
            chunk = self.chunks[i]
            chunk_lines = self._count_lines_for_chunk(chunk)
            
            if current_height + chunk_lines > available_height:
                break
            
            visible_chunks.append(i)
            current_height += chunk_lines
        
        if not visible_chunks:
            visible_chunks = [visible_start] if visible_start < len(self.chunks) else [0]
        
        for idx, i in enumerate(visible_chunks):
            chunk = self.chunks[i]
            word_start = self._get_word_start_for_chunk(i)
            
            is_current = (i == self.current_idx)
            is_selected = (i == self.selected_idx)
            
            if is_current:
                text.append("▶", style="yellow bold")
                text.append(f"{word_start:5,}", style="yellow bold reverse")
                text.append("│", style="yellow bold")
            elif is_selected:
                text.append("◆", style="cyan bold")
                text.append(f"{word_start:5,}", style="cyan bold reverse")
                text.append("│", style="cyan bold")
            else:
                text.append(" ", style="dim")
                text.append(f"{word_start:5,}", style="white bold")
                text.append("│", style="dim")
            
            words = chunk.split()
            line_words = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 > self.max_width and line_words:
                    line_text = " ".join(line_words)
                    if is_current:
                        text.append(f"{line_text}\n", style="yellow")
                    elif is_selected:
                        text.append(f"{line_text}\n", style="white")
                    else:
                        text.append(f"{line_text}\n", style="white dim")
                    
                    text.append("      │", style="dim" if not is_current else "yellow")
                    line_words = [word]
                    current_length = len(word)
                else:
                    line_words.append(word)
                    current_length += len(word) + 1
            
            if line_words:
                line_text = " ".join(line_words)
                if is_current:
                    text.append(f"{line_text}", style="yellow")
                elif is_selected:
                    text.append(f"{line_text}", style="white")
                else:
                    text.append(f"{line_text}", style="white dim")
            
            if idx < len(visible_chunks) - 1:
                text.append("\n")
        
        return text
    
    def scroll_to_current(self):
        """Scroll to keep current chunk visible."""
        if self.current_idx < self.chunk_scroll_offset:
            self.chunk_scroll_offset = max(0, self.current_idx)
        else:
            try:
                available_height = self.region.height if hasattr(self, 'region') else 20
            except Exception:
                available_height = 20
            
            current_height = 0
            new_offset = self.chunk_scroll_offset
            
            for i in range(self.chunk_scroll_offset, self.current_idx + 1):
                if i < len(self.chunks):
                    chunk_lines = self._count_lines_for_chunk(self.chunks[i])
                    
                    while current_height + chunk_lines > available_height and new_offset < i:
                        if new_offset < len(self.chunks):
                            current_height -= self._count_lines_for_chunk(self.chunks[new_offset])
                        new_offset += 1
                    
                    current_height += chunk_lines
            
            self.chunk_scroll_offset = new_offset
    
    def scroll_to_selected(self):
        """Scroll to keep selected chunk visible."""
        if self.selected_idx < self.chunk_scroll_offset:
            self.chunk_scroll_offset = max(0, self.selected_idx)
        else:
            try:
                available_height = self.region.height if hasattr(self, 'region') else 20
            except Exception:
                available_height = 20
            
            current_height = 0
            new_offset = self.chunk_scroll_offset
            
            for i in range(self.chunk_scroll_offset, self.selected_idx + 1):
                if i < len(self.chunks):
                    chunk_lines = self._count_lines_for_chunk(self.chunks[i])
                    
                    while current_height + chunk_lines > available_height and new_offset < i:
                        if new_offset < len(self.chunks):
                            current_height -= self._count_lines_for_chunk(self.chunks[new_offset])
                        new_offset += 1
                    
                    current_height += chunk_lines
            
            self.chunk_scroll_offset = new_offset


class HeaderDisplay(Static):
    """Widget to display header with file name and terminal size."""
    
    file_name = reactive("")
    terminal_size: reactive[tuple[int, int]] = reactive((96, 30))
    
    def render(self):
        text = Text()
        text.append(f"📖 Reading: {self.file_name}", style="bold")
        
        padding = self.terminal_size[0] - len(f"📖 Reading: {self.file_name}") - 12
        if padding > 0:
            text.append(" " * padding)
        
        text.append(f"[{self.terminal_size[0]}x{self.terminal_size[1]}]", style="dim")
        
        return text


class StatusDisplay(Static):
    """Widget to display current status (speed, position, etc.)."""
    
    speed = reactive(1.0)
    words_spoken = reactive(0)
    total_words = reactive(0)
    is_paused = reactive(False)
    is_loading = reactive(False)
    loading_message = reactive("")
    current_bookmark: reactive[int | None] = reactive(None)
    current_voice = reactive("en_US-lessac-medium")
    terminal_size: reactive[tuple[int, int]] = reactive((0, 0))
    
    def render(self):
        text = Text()
        
        if self.is_loading:
            text.append(f"  ⏳ {self.loading_message}  ", style="yellow bold blink")
        
        speed_color = "yellow" if self.speed != 0.95 else "white"
        text.append(f"  Speed: {self.speed:.2f}x  ", style=f"{speed_color} bold")
        
        if self.is_paused:
            text.append("⏸ PAUSED  ", style="yellow bold")
        elif not self.is_loading:
            text.append("▶ Playing  ", style="green")
        
        text.append(f"Words: {self.words_spoken:,}/{self.total_words:,}  ", 
                   style="cyan")
        
        voice_name = self.current_voice.split('-')[-1].replace('-medium', '').title()
        text.append(f"🎤 {voice_name}  ", style="magenta bold")
        
        if self.current_bookmark is not None:
            text.append(f"🔖 Bookmark at {self.current_bookmark}", 
                       style="magenta")
        
        # Terminal size info in top right
        if self.terminal_size[0] > 0:
            text.append(f"  {self.terminal_size[0]}x{self.terminal_size[1]}  ", style="dim")
        
        return text


class ControlsDisplay(Static):
    """Widget to display available controls."""
    
    def render(self):
        text = Text()
        
        controls = [
            ("Spc", "⏸"),
            ("↑↓", "Nav"),
            ("Ent", "→"),
            ("+/-", "Spd"),
            ("0", "Rst"),
            ("v", "Vo"),
            ("r", "Rep"),
            ("m", "Bm"),
            ("[]", "Jmp"),
            ("H/E", "⇤⇥"),
            ("q", "✕"),
        ]
        
        for i, (key, action) in enumerate(controls):
            if i > 0:
                text.append(" ")
            text.append(f"[{key}]", style="cyan bold")
            text.append(action, style="white")
        
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
        padding: 0 1;
        overflow: hidden;
    }
    
    #header-container {
        height: 1;
        margin-bottom: 0;
    }
    
    #content-container {
        height: 1fr;
        width: 100%;
        margin: 0;
        overflow: hidden;
    }
    
    #progress-container {
        height: 1;
        margin-top: 0;
    }
    
    #status-container {
        height: 1;
    }
    
    #controls-container {
        height: 1;
        margin-top: 0;
    }
    
    .title {
        text-style: bold;
        color: $text-primary;
    }
    
    ChunkDisplay {
        height: 100%;
        width: 100%;
        padding: 0 1;
        background: $panel;
        border: solid $primary;
        overflow-y: auto;
    }
    
    StatusDisplay {
        height: 1;
        padding: 0 1;
        background: $panel;
    }
    
    ControlsDisplay {
        height: 1;
        padding: 0 1;
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
        initial_speed: float = 0.95,
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
                yield HeaderDisplay()
            
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
                on_play=self._on_sentence_play,
                audio_buffer_size=4096,
                audio_latency='high',
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
            
            header_display = self.query_one(HeaderDisplay)
            header_display.file_name = self.file_path.name
            header_display.terminal_size = (self.size.width, self.size.height)
            
            status_display = self.query_one(StatusDisplay)
            status_display.total_words = self.total_words
            status_display.speed = self.initial_speed
            status_display.current_voice = current_voice
            status_display.terminal_size = (self.size.width, self.size.height)
            
            if self.start_word > 0:
                # Show seeking indicator
                status_display.is_loading = True
                status_display.loading_message = f"Seeking to word {self.start_word:,}..."
                status_display.refresh()
                
                # Perform seek
                self._seek_to_word(self.start_word)
                
                # Update display to show current position
                chunk_display.current_idx = self.current_sentence_idx
                chunk_display.selected_idx = self.current_sentence_idx
                chunk_display.scroll_to_current()
                
                # Update status
                status_display.words_spoken = self.words_spoken
                
                # Hide loading after a short delay
                def hide_loading():
                    try:
                        self.call_from_thread(lambda: setattr(
                            self.query_one(StatusDisplay), 'is_loading', False
                        ))
                        self.call_from_thread(lambda: setattr(
                            self.query_one(StatusDisplay), 'loading_message', ""
                        ))
                    except Exception:
                        pass
                
                threading.Timer(1.0, hide_loading).start()
            
            self._start_reading()
        except Exception as e:
            logger.error(f"Error during TUI initialization: {e}\n{traceback.format_exc()}")
            self._show_error(f"Initialization failed: {e}")
    
    def on_resize(self, event):
        """Handle terminal resize events."""
        try:
            chunk_display = self.query_one(ChunkDisplay)
            chunk_display._update_max_width()
            chunk_display.refresh()
            
            header_display = self.query_one(HeaderDisplay)
            header_display.terminal_size = (self.size.width, self.size.height)
            
            status_display = self.query_one(StatusDisplay)
            status_display.terminal_size = (self.size.width, self.size.height)
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
        """Seek to a specific word position."""
        words_counted = 0
        target_idx = 0
        
        for i, sentence in enumerate(self.sentences):
            sentence_words = len(sentence.split())
            if words_counted + sentence_words > word_num:
                target_idx = i
                self.words_spoken = words_counted
                break
            words_counted += sentence_words
        else:
            # If word_num is beyond the end, go to last sentence
            target_idx = len(self.sentences) - 1
            self.words_spoken = sum(len(s.split()) for s in self.sentences[:-1])
        
        self.current_sentence_idx = target_idx
    
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
            # Show loading indicator
            try:
                status_display = self.query_one(StatusDisplay)
                status_display.is_loading = True
                status_display.loading_message = "Generating audio..."
                self.call_from_thread(lambda: status_display.refresh())
            except Exception:
                pass
            
            self.current_sentence_idx = idx
            self.words_spoken = sum(len(s.split()) for s in self.sentences[:idx])
            
            chunk_display = self.query_one(ChunkDisplay)
            chunk_display.current_idx = idx
            chunk_display.selected_idx = idx
            chunk_display.scroll_to_current()
            
            self.should_stop = False
            self._start_reading()
            
            # Hide loading indicator after a short delay
            def hide_loading():
                try:
                    status_display = self.query_one(StatusDisplay)
                    status_display.is_loading = False
                    status_display.loading_message = ""
                except Exception:
                    pass
            
            # Schedule hiding loading after 2 seconds
            threading.Timer(2.0, hide_loading).start()
    
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
        
        # Show loading immediately
        status_display = self.query_one(StatusDisplay)
        status_display.is_loading = True
        status_display.loading_message = f"Loading chunk {idx + 1}..."
        
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
        
        # Show loading immediately
        voice_name = new_voice.split('-')[-1].replace('-medium', '').title()
        status_display = self.query_one(StatusDisplay)
        status_display.is_loading = True
        status_display.loading_message = f"Changing voice to {voice_name}..."
        
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
                    on_play=self._on_sentence_play,
                    audio_buffer_size=4096,
                    audio_latency='high',
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
        """Quit the TUI and print resume command."""
        self.should_stop = True
        self.action_queue.clear()
        if self.client:
            self.client.stop()
        
        # Calculate current word position
        current_word = sum(len(s.split()) for s in self.sentences[:self.current_sentence_idx])
        
        # Get current voice
        current_voice = self.available_voices[self.current_voice_index]
        
        # Get current speed
        current_speed = self.client.speed if self.client else self.initial_speed
        
        # Build resume command
        cmd_parts = [
            "python -m mytts.cli read",
            "--tui",
            f"--server-url {self.server_url}",
            f"--voice {current_voice}",
            f"-w {current_word}",
            f"-s {current_speed:.2f}",
            f'"{self.file_path}"'
        ]
        resume_cmd = " ".join(cmd_parts)
        
        # Build summary
        summary = (
            f"\n{'='*60}\n"
            f"To resume from this position, run:\n"
            f"{'='*60}\n"
            f"{resume_cmd}\n"
            f"{'='*60}\n"
            f"Position: Sentence {self.current_sentence_idx + 1}/{len(self.sentences)}, Word {current_word:,}\n"
            f"Voice: {current_voice}\n"
            f"Speed: {current_speed:.2f}x\n"
            f"{'='*60}\n"
        )
        
        # Exit with message
        self.exit(message=summary)


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
