#!/usr/bin/env python3
"""Comprehensive test suite for myTTS system."""

import sys
import tempfile
import os
import time
import threading
import requests
from unittest.mock import Mock, patch, MagicMock
import numpy as np

SERVER_URL = "http://192.168.88.164:8000"


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name):
        self.passed += 1
        print(f"  ✓ {test_name}")
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, error))
        print(f"  ✗ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Results: {self.passed}/{total} passed, {self.failed} failed")
        if self.errors:
            print("\nFailed tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        return self.failed == 0


def test_server_health():
    """Test server is running and healthy."""
    result = TestResult()
    print("\n[Server Health Tests]")
    
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            result.add_pass("Server health check")
            data = response.json()
            if "status" in data and data["status"] == "ok":
                result.add_pass("Server status OK")
            else:
                result.add_fail("Server status", f"Unexpected status: {data}")
        else:
            result.add_fail("Server health", f"Status code: {response.status_code}")
    except Exception as e:
        result.add_fail("Server health", str(e))
    
    return result


def test_text_preprocessing():
    """Test text preprocessing for various edge cases."""
    result = TestResult()
    print("\n[Text Preprocessing Tests]")
    
    from mytts.client import ProgressiveTTSClient
    from mytts import TTSEngine, TTSMode, TTSBackend
    
    engine = TTSEngine(
        mode=TTSMode.READING,
        backend=TTSBackend.SERVER,
        engine="piper",
        server_url=SERVER_URL,
    )
    client = ProgressiveTTSClient(engine, num_workers=1, buffer_size=1)
    
    test_cases = [
        ("Simple sentence.", 1, "Simple sentence"),
        ("Two sentences. Second one.", 2, "Two sentences"),
        ("Text with\nnewlines\ninside.", 1, "Newlines"),
        ("Multiple\n\n\nnewlines.", 1, "Multiple newlines"),
        ("Text with tabs\t\there.", 1, "Tabs"),
        ("Special chars: @#$%^&*()", 1, "Special chars"),
        ("Numbers: 123 456.789", 1, "Numbers"),
        ("", 0, "Empty string"),
        ("   ", 0, "Whitespace only"),
        ("No ending punctuation", 1, "No ending"),
        ("Already has period. And another!", 2, "Multiple punctuation"),
        ("Question? Yes! Maybe.", 3, "Mixed punctuation"),
    ]
    
    for text, expected_count, test_name in test_cases:
        try:
            sentences = client.split_into_sentences(text)
            if len(sentences) == expected_count:
                result.add_pass(f"Split: {test_name}")
            else:
                result.add_fail(f"Split: {test_name}", 
                    f"Expected {expected_count} sentences, got {len(sentences)}: {sentences}")
        except Exception as e:
            result.add_fail(f"Split: {test_name}", str(e))
    
    return result


def test_tts_generation():
    """Test TTS generation with various text inputs."""
    result = TestResult()
    print("\n[TTS Generation Tests]")
    
    test_cases = [
        ("Simple sentence for TTS.", "Simple TTS"),
        ("Text with\nnewlines\nfor TTS.", "Newlines TTS"),
        ("Question? Yes! Exclamation!", "Mixed punctuation TTS"),
        ("A" * 100, "Long single sentence"),
        ("Short.", "Very short"),
    ]
    
    for text, test_name in test_cases:
        try:
            clean_text = " ".join(text.split())
            response = requests.post(
                f"{SERVER_URL}/tts",
                json={
                    "text": clean_text,
                    "voice": "en_US-lessac-medium",
                    "engine": "piper",
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result.add_pass(f"Generate: {test_name}")
            else:
                result.add_fail(f"Generate: {test_name}", 
                    f"Status {response.status_code}: {response.text[:100]}")
        except Exception as e:
            result.add_fail(f"Generate: {test_name}", str(e))
    
    return result


def test_progressive_client():
    """Test ProgressiveTTSClient functionality."""
    result = TestResult()
    print("\n[Progressive Client Tests]")
    
    from mytts.client import ProgressiveTTSClient
    from mytts import TTSEngine, TTSMode, TTSBackend
    
    try:
        engine = TTSEngine(
            mode=TTSMode.READING,
            backend=TTSBackend.SERVER,
            engine="piper",
            server_url=SERVER_URL,
        )
        client = ProgressiveTTSClient(engine, num_workers=2, buffer_size=2)
        
        result.add_pass("Client creation")
        
        if client.speed == 1.0:
            result.add_pass("Default speed")
        else:
            result.add_fail("Default speed", f"Expected 1.0, got {client.speed}")
        
        client.increase_speed()
        if client.speed == 1.05:
            result.add_pass("Increase speed")
        else:
            result.add_fail("Increase speed", f"Expected 1.05, got {client.speed}")
        
        client.decrease_speed()
        if client.speed == 1.0:
            result.add_pass("Decrease speed")
        else:
            result.add_fail("Decrease speed", f"Expected 1.0, got {client.speed}")
        
        client.reset_speed()
        if client.speed == 1.0:
            result.add_pass("Reset speed")
        else:
            result.add_fail("Reset speed", f"Expected 1.0, got {client.speed}")
        
        if not client.is_paused:
            result.add_pass("Initial not paused")
        else:
            result.add_fail("Initial not paused", "Client should not be paused initially")
        
        client.toggle_pause()
        if client.is_paused:
            result.add_pass("Toggle pause on")
        else:
            result.add_fail("Toggle pause on", "Client should be paused")
        
        client.toggle_pause()
        if not client.is_paused:
            result.add_pass("Toggle pause off")
        else:
            result.add_fail("Toggle pause off", "Client should not be paused")
        
        client.close()
        
    except Exception as e:
        result.add_fail("Client tests", str(e))
    
    return result


def test_audio_fade():
    """Test audio fade functionality."""
    result = TestResult()
    print("\n[Audio Fade Tests]")
    
    from mytts.client import ProgressiveTTSClient
    from mytts import TTSEngine, TTSMode, TTSBackend
    
    try:
        engine = TTSEngine(
            mode=TTSMode.READING,
            backend=TTSBackend.SERVER,
            engine="piper",
            server_url=SERVER_URL,
        )
        client = ProgressiveTTSClient(engine, num_workers=1, buffer_size=1)
        
        sample_rate = 22050
        duration = 1.0
        audio = np.ones(int(sample_rate * duration), dtype=np.float32)
        
        faded = client._apply_fade(audio, sample_rate, fade_ms=10)
        
        if faded.shape == audio.shape:
            result.add_pass("Fade preserves shape")
        else:
            result.add_fail("Fade preserves shape", 
                f"Expected {audio.shape}, got {faded.shape}")
        
        if faded[0] < 0.5:
            result.add_pass("Fade in applied")
        else:
            result.add_fail("Fade in applied", f"First sample should be < 0.5, got {faded[0]}")
        
        if faded[-1] < 0.5:
            result.add_pass("Fade out applied")
        else:
            result.add_fail("Fade out applied", f"Last sample should be < 0.5, got {faded[-1]}")
        
        if np.abs(faded[len(faded)//2] - 1.0) < 0.01:
            result.add_pass("Middle preserved")
        else:
            result.add_fail("Middle preserved", 
                f"Middle sample should be ~1.0, got {faded[len(faded)//2]}")
        
        short_audio = np.ones(100, dtype=np.float32)
        faded_short = client._apply_fade(short_audio, sample_rate, fade_ms=10)
        
        if np.array_equal(faded_short, short_audio):
            result.add_pass("Short audio unchanged")
        else:
            result.add_fail("Short audio unchanged", "Audio shorter than fade should be unchanged")
        
        client.close()
        
    except Exception as e:
        result.add_fail("Audio fade tests", str(e))
    
    return result


def test_tui_components():
    """Test TUI component creation and rendering."""
    result = TestResult()
    print("\n[TUI Component Tests]")
    
    try:
        from mytts.tui import TTSReaderApp, ChunkDisplay, StatusDisplay, ControlsDisplay
        
        test_text = "Test sentence one. Test sentence two. Test sentence three."
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_text)
            test_file = f.name
        
        try:
            app = TTSReaderApp(
                file_path=test_file,
                server_url=SERVER_URL,
                voice="en_US-lessac-medium",
            )
            result.add_pass("TUI app creation")
            
            chunk_display = ChunkDisplay()
            chunk_display.chunks = ["Sentence 1", "Sentence 2", "Sentence 3"]
            chunk_display.current_idx = 0
            chunk_display.selected_idx = 0
            
            rendered = chunk_display.render()
            if "Sentence 1" in str(rendered):
                result.add_pass("ChunkDisplay render")
            else:
                result.add_fail("ChunkDisplay render", "Sentence not in output")
            
            chunk_display.current_idx = 1
            rendered = chunk_display.render()
            if "▶" in str(rendered):
                result.add_pass("ChunkDisplay current indicator")
            else:
                result.add_fail("ChunkDisplay current indicator", "No ▶ indicator")
            
            chunk_display.selected_idx = 2
            rendered = chunk_display.render()
            if "◆" in str(rendered):
                result.add_pass("ChunkDisplay selected indicator")
            else:
                result.add_fail("ChunkDisplay selected indicator", "No ◆ indicator")
            
            status_display = StatusDisplay()
            status_display.speed = 1.5
            status_display.words_spoken = 100
            status_display.total_words = 1000
            status_display.is_paused = False
            
            rendered = status_display.render()
            if "1.50x" in str(rendered):
                result.add_pass("StatusDisplay render")
            else:
                result.add_fail("StatusDisplay render", "Speed not in output")
            
            controls_display = ControlsDisplay()
            rendered = controls_display.render()
            if "Space" in str(rendered) and "Pause" in str(rendered):
                result.add_pass("ControlsDisplay render")
            else:
                result.add_fail("ControlsDisplay render", "Controls not in output")
            
        finally:
            os.unlink(test_file)
        
    except Exception as e:
        result.add_fail("TUI component tests", str(e))
    
    return result


def test_error_handling():
    """Test error handling in various scenarios."""
    result = TestResult()
    print("\n[Error Handling Tests]")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/tts",
            json={"text": "", "voice": "en_US-lessac-medium"},
            timeout=5
        )
        if response.status_code == 400 or response.status_code == 500:
            result.add_pass("Empty text error handling")
        else:
            result.add_fail("Empty text error handling", 
                f"Expected error status, got {response.status_code}")
    except Exception as e:
        result.add_fail("Empty text error handling", str(e))
    
    try:
        response = requests.post(
            f"{SERVER_URL}/tts",
            json={"text": "x" * 6000, "voice": "en_US-lessac-medium"},
            timeout=5
        )
        if response.status_code == 400:
            result.add_pass("Long text error handling")
        else:
            result.add_fail("Long text error handling", 
                f"Expected 400, got {response.status_code}")
    except Exception as e:
        result.add_fail("Long text error handling", str(e))
    
    try:
        response = requests.post(
            f"{SERVER_URL}/tts",
            json={"text": "Test", "voice": "invalid_voice"},
            timeout=10
        )
        if response.status_code == 500 or response.status_code == 400:
            result.add_pass("Invalid voice error handling")
        else:
            result.add_fail("Invalid voice error handling", 
                f"Expected error status, got {response.status_code}")
    except Exception as e:
        result.add_fail("Invalid voice error handling", str(e))
    
    return result


def test_concurrent_requests():
    """Test handling of concurrent TTS requests."""
    result = TestResult()
    print("\n[Concurrent Request Tests]")
    
    def make_request(text, idx):
        try:
            clean_text = " ".join(text.split())
            response = requests.post(
                f"{SERVER_URL}/tts",
                json={
                    "text": clean_text,
                    "voice": "en_US-lessac-medium",
                    "engine": "piper",
                },
                timeout=30
            )
            return (idx, response.status_code == 200)
        except Exception as e:
            return (idx, False)
    
    texts = [
        "First concurrent test sentence.",
        "Second concurrent test sentence.",
        "Third concurrent test sentence.",
    ]
    
    threads = []
    results = {}
    
    for i, text in enumerate(texts):
        thread = threading.Thread(
            target=lambda idx, t: results.update({idx: make_request(t, idx)}),
            args=(i, text)
        )
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join(timeout=35)
    
    success_count = sum(1 for idx, success in results.values() if success)
    
    if success_count == len(texts):
        result.add_pass(f"Concurrent requests ({success_count}/{len(texts)})")
    else:
        result.add_fail("Concurrent requests", 
            f"Only {success_count}/{len(texts)} succeeded")
    
    return result


def main():
    """Run all tests."""
    print("=" * 60)
    print("myTTS Comprehensive Test Suite")
    print("=" * 60)
    
    all_results = []
    
    all_results.append(test_server_health())
    all_results.append(test_text_preprocessing())
    all_results.append(test_tts_generation())
    all_results.append(test_progressive_client())
    all_results.append(test_audio_fade())
    all_results.append(test_tui_components())
    all_results.append(test_error_handling())
    all_results.append(test_concurrent_requests())
    
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total_tests = total_passed + total_failed
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {total_passed}/{total_tests} tests passed")
    
    if total_failed > 0:
        print(f"\n{total_failed} tests failed:")
        for result in all_results:
            for test_name, error in result.errors:
                print(f"  - {test_name}: {error}")
        return 1
    else:
        print("\n✓ All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
