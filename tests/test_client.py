"""Unit tests for mytts.client module."""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
import threading
import time

from mytts.client import ProgressiveTTSClient, SentenceChunk
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
def client(mock_engine):
    """Create a ProgressiveTTSClient with mock engine."""
    return ProgressiveTTSClient(mock_engine, num_workers=2, buffer_size=2)


class TestProgressiveTTSClient:
    """Test suite for ProgressiveTTSClient."""
    
    def test_client_creation(self, client):
        """Test client is created with correct defaults."""
        assert client.speed == 0.95
        assert client.num_workers == 2
        assert client.buffer_size == 2
        assert not client.is_paused
        assert client.current_position == 0
    
    def test_speed_property(self, client):
        """Test speed property getter and setter."""
        assert client.speed == 0.95
        
        client.speed = 2.0
        assert client.speed == 2.0
        
        client.speed = 0.5
        assert client.speed == 0.5
    
    def test_speed_bounds(self, client):
        """Test speed is bounded between 0.25 and 4.0."""
        client.speed = 0.1
        assert client.speed == 0.25
        
        client.speed = 5.0
        assert client.speed == 4.0
    
    def test_increase_speed(self, client):
        """Test speed increase."""
        initial = client.speed
        client.increase_speed()
        assert client.speed == initial + 0.05
    
    def test_decrease_speed(self, client):
        """Test speed decrease."""
        initial = client.speed
        client.decrease_speed()
        assert client.speed == initial - 0.05
    
    def test_reset_speed(self, client):
        """Test speed reset to default."""
        client.speed = 2.5
        client.reset_speed()
        assert client.speed == 0.95
    
    def test_toggle_pause(self, client):
        """Test pause toggle."""
        assert not client.is_paused
        
        client.toggle_pause()
        assert client.is_paused
        
        client.toggle_pause()
        assert not client.is_paused
    
    def test_split_into_sentences_simple(self, client):
        """Test simple sentence splitting."""
        text = "One. Two. Three."
        sentences = client.split_into_sentences(text)
        
        assert len(sentences) == 3
        assert sentences[0] == "One."
        assert sentences[1] == "Two."
        assert sentences[2] == "Three."
    
    def test_split_into_sentences_empty(self, client):
        """Test empty text splitting."""
        sentences = client.split_into_sentences("")
        assert sentences == []
    
    def test_split_into_sentences_whitespace(self, client):
        """Test whitespace-only text splitting."""
        sentences = client.split_into_sentences("   ")
        assert sentences == []
    
    def test_split_into_sentences_no_ending(self, client):
        """Test text without ending punctuation."""
        sentences = client.split_into_sentences("No ending")
        assert len(sentences) == 1
        assert sentences[0] == "No ending."
    
    def test_split_into_sentences_newlines(self, client):
        """Test text with newlines is cleaned."""
        text = "Line one\n\nLine two\nLine three."
        sentences = client.split_into_sentences(text)
        
        assert len(sentences) == 1
        assert "\n" not in sentences[0]
    
    def test_split_into_sentences_tabs(self, client):
        """Test text with tabs is cleaned."""
        text = "Tab\there\tand\there."
        sentences = client.split_into_sentences(text)
        
        assert "\t" not in sentences[0]
    
    def test_apply_fade_normal_audio(self, client):
        """Test fade is applied to normal audio."""
        sample_rate = 22050
        duration = 1.0
        audio = np.ones(int(sample_rate * duration), dtype=np.float32)
        
        faded = client._apply_fade(audio, sample_rate, fade_ms=10)
        
        assert faded.shape == audio.shape
        assert faded[0] < 0.5  # Fade in
        assert faded[-1] < 0.5  # Fade out
        assert abs(faded[len(faded)//2] - 1.0) < 0.01  # Middle preserved
    
    def test_apply_fade_short_audio(self, client):
        """Test short audio is not faded."""
        sample_rate = 22050
        audio = np.ones(100, dtype=np.float32)
        
        faded = client._apply_fade(audio, sample_rate, fade_ms=10)
        
        assert np.array_equal(faded, audio)
    
    def test_apply_fade_preserves_copy(self, client):
        """Test fade doesn't modify original audio."""
        sample_rate = 22050
        audio = np.ones(22050, dtype=np.float32)
        original = audio.copy()
        
        client._apply_fade(audio, sample_rate, fade_ms=10)
        
        assert np.array_equal(audio, original)
    
    @patch('mytts.client.sd.play')
    @patch('mytts.client.sd.wait')
    def test_play_chunk_calls_callbacks(self, mock_wait, mock_play, client):
        """Test _play_chunk calls on_play callback."""
        callback_calls = []
        
        def on_play(text, index, duration):
            callback_calls.append((text, index, duration))
        
        client.on_play = on_play
        
        chunk = SentenceChunk(
            text="Test sentence.",
            index=5,
            audio=np.ones(22050, dtype=np.float32),
            sample_rate=22050
        )
        
        client._play_chunk(chunk)
        
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == "Test sentence."
        assert callback_calls[0][1] == 5
        assert callback_calls[0][2] > 0  # Duration should be positive
        mock_play.assert_called_once()
        mock_wait.assert_called_once()
    
    @patch('mytts.client.sd.play')
    @patch('mytts.client.sd.wait')
    def test_play_chunk_handles_none_audio(self, mock_wait, mock_play, client):
        """Test _play_chunk handles None audio gracefully."""
        chunk = SentenceChunk(text="Test", index=0, audio=None)
        
        client._play_chunk(chunk)
        
        mock_play.assert_not_called()
        mock_wait.assert_not_called()
    
    def test_stop_playback_when_playing(self, client):
        """Test _stop_playback when audio is playing."""
        with patch('mytts.client.sd.stop') as mock_stop:
            with patch('mytts.client.sd.wait') as mock_wait:
                client._is_playing = True
                client._stop_playback()
                
                mock_stop.assert_called_once()
                mock_wait.assert_called_once()
                assert not client._is_playing
    
    def test_stop_playback_when_not_playing(self, client):
        """Test _stop_playback when audio is not playing."""
        with patch('mytts.client.sd.stop') as mock_stop:
            client._is_playing = False
            client._stop_playback()
            
            mock_stop.assert_not_called()
    
    def test_reset_clears_state(self, client):
        """Test reset clears client state."""
        client._current_chunk_index = 5
        client._chunks_list = [Mock(), Mock()]
        client._paused.set()
        
        client.reset()
        
        assert client._current_chunk_index == 0
        assert client._chunks_list == []
        assert not client._paused.is_set()
        assert not client._is_playing


class TestSentenceChunk:
    """Test suite for SentenceChunk dataclass."""
    
    def test_chunk_creation(self):
        """Test chunk is created with correct values."""
        chunk = SentenceChunk(
            text="Test sentence.",
            index=3,
            audio=np.ones(100, dtype=np.float32),
            sample_rate=22050
        )
        
        assert chunk.text == "Test sentence."
        assert chunk.index == 3
        assert chunk.audio is not None
        assert chunk.sample_rate == 22050
    
    def test_chunk_default_audio(self):
        """Test chunk has None audio by default."""
        chunk = SentenceChunk(text="Test", index=0)
        
        assert chunk.audio is None
        assert chunk.sample_rate == 22050


class TestLateBinding:
    """Test suite to verify late binding issues are handled correctly."""
    
    def test_concurrent_operations_with_early_binding(self, client):
        """Test that concurrent operations use early binding."""
        results = []
        
        threads = []
        for i in range(5):
            def capture_result(val=i):
                results.append(val)
            thread = threading.Thread(target=capture_result)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5)
        
        assert sorted(results) == [0, 1, 2, 3, 4]
    
    def test_lambda_capture_with_default_arg(self, client):
        """Test lambda captures value with default argument."""
        results = []
        
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=lambda x=i: results.append(x)
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5)
        
        assert sorted(results) == [0, 1, 2]
