#!/usr/bin/env python3
"""Tests for word timing and highlighting functionality."""

import pytest
import threading
import time
from unittest.mock import Mock, patch

from mytts.tui import WordTimingEstimator, WordHighlightScheduler


class TestWordTimingEstimator:
    """Tests for WordTimingEstimator class."""
    
    def test_basic_word_timing(self):
        """Test basic word timing estimation."""
        estimator = WordTimingEstimator()
        
        sentence = "Hello world"
        duration = 1.0
        
        timings = estimator.estimate_word_timings(sentence, duration)
        
        assert len(timings) == 2
        assert timings[0]['word'] == "Hello"
        assert timings[1]['word'] == "world"
        assert timings[0]['start'] == 0.0
        assert timings[0]['end'] > 0.0
        assert timings[1]['start'] > timings[0]['end']  # Second word starts after first ends
        assert timings[1]['end'] <= duration
    
    def test_single_word_timing(self):
        """Test single word timing."""
        estimator = WordTimingEstimator()
        
        sentence = "Test"
        duration = 0.5
        
        timings = estimator.estimate_word_timings(sentence, duration)
        
        assert len(timings) == 1
        assert timings[0]['word'] == "Test"
        assert timings[0]['start'] == 0.0
        assert abs(timings[0]['end'] - duration) < 0.01
    
    def test_empty_sentence(self):
        """Test empty sentence."""
        estimator = WordTimingEstimator()
        
        timings = estimator.estimate_word_timings("", 1.0)
        
        assert len(timings) == 0
    
    def test_long_sentence(self):
        """Test long sentence timing."""
        estimator = WordTimingEstimator()
        
        sentence = "The quick brown fox jumps over the lazy dog"
        duration = 3.0
        
        timings = estimator.estimate_word_timings(sentence, duration)
        
        assert len(timings) == 9
        assert timings[-1]['end'] <= duration
        assert all(t['start'] >= 0 for t in timings)
        assert all(t['end'] > t['start'] for t in timings)
    
    def test_word_order_preserved(self):
        """Test that word order is preserved."""
        estimator = WordTimingEstimator()
        
        sentence = "first second third fourth fifth"
        duration = 2.0
        
        timings = estimator.estimate_word_timings(sentence, duration)
        
        words = [t['word'] for t in timings]
        assert words == ["first", "second", "third", "fourth", "fifth"]
    
    def test_punctuation_handling(self):
        """Test punctuation handling."""
        estimator = WordTimingEstimator()
        
        sentence = "Hello, world!"
        duration = 1.0
        
        timings = estimator.estimate_word_timings(sentence, duration)
        
        assert len(timings) == 2
        assert "Hello," in timings[0]['word'] or timings[0]['word'] == "Hello,"
        assert "world!" in timings[1]['word'] or timings[1]['word'] == "world!"
    
    def test_timing_consistency(self):
        """Test that timings are consistent (monotonically increasing)."""
        estimator = WordTimingEstimator()
        
        sentence = "one two three four five six seven eight nine ten"
        duration = 5.0
        
        timings = estimator.estimate_word_timings(sentence, duration)
        
        for i in range(1, len(timings)):
            assert timings[i]['start'] >= timings[i-1]['end'] - 0.01  # Small tolerance for floating point
    
    def test_vowel_weighting(self):
        """Test that words with more vowels get more time."""
        estimator = WordTimingEstimator()
        
        # "aeiou" has 5 vowels, "xyz" has 0
        sentence = "aeiou xyz"
        duration = 1.0
        
        timings = estimator.estimate_word_timings(sentence, duration)
        
        # Word with vowels should have longer duration
        assert timings[0]['duration'] > timings[1]['duration']


class TestWordHighlightScheduler:
    """Tests for WordHighlightScheduler class."""
    
    def test_scheduler_creation(self):
        """Test scheduler creation."""
        app = Mock()
        scheduler = WordHighlightScheduler(app)
        
        assert scheduler.app == app
        assert len(scheduler._timers) == 0
    
    def test_schedule_highlights(self):
        """Test scheduling highlights."""
        app = Mock()
        scheduler = WordHighlightScheduler(app)
        estimator = WordTimingEstimator()
        
        sentence = "Hello world"
        duration = 1.0
        
        scheduler.schedule_highlights(sentence, 0, duration, estimator)
        
        # Should have scheduled timers for each word
        assert len(scheduler._timers) == 2
        
        # Clean up
        scheduler.cancel_highlights()
    
    def test_cancel_highlights(self):
        """Test canceling highlights."""
        app = Mock()
        scheduler = WordHighlightScheduler(app)
        estimator = WordTimingEstimator()
        
        sentence = "One two three"
        duration = 1.0
        
        scheduler.schedule_highlights(sentence, 0, duration, estimator)
        assert len(scheduler._timers) == 3
        
        scheduler.cancel_highlights()
        assert len(scheduler._timers) == 0
    
    def test_empty_sentence_no_timers(self):
        """Test that empty sentence creates no timers."""
        app = Mock()
        scheduler = WordHighlightScheduler(app)
        estimator = WordTimingEstimator()
        
        scheduler.schedule_highlights("", 0, 1.0, estimator)
        
        assert len(scheduler._timers) == 0
    
    def test_highlight_word_calls_app(self):
        """Test that _highlight_word calls app correctly."""
        app = Mock()
        app.call_from_thread = Mock()
        scheduler = WordHighlightScheduler(app)
        scheduler._current_sentence_idx = 0
        
        scheduler._highlight_word(0, 0)
        
        # Should have called call_from_thread
        app.call_from_thread.assert_called_once()
    
    def test_highlight_word_ignores_wrong_sentence(self):
        """Test that _highlight_word ignores wrong sentence."""
        app = Mock()
        app.call_from_thread = Mock()
        scheduler = WordHighlightScheduler(app)
        scheduler._current_sentence_idx = 5  # Different sentence
        
        scheduler._highlight_word(0, 0)
        
        # Should NOT have called call_from_thread
        app.call_from_thread.assert_not_called()
    
    def test_pause_cancels_timers(self):
        """Test that pause cancels all timers."""
        app = Mock()
        scheduler = WordHighlightScheduler(app)
        estimator = WordTimingEstimator()
        
        sentence = "One two three"
        duration = 1.0
        
        scheduler.schedule_highlights(sentence, 0, duration, estimator)
        assert len(scheduler._timers) == 3
        
        scheduler.pause()
        
        # Timers should be cleared
        assert len(scheduler._timers) == 0
        assert scheduler._is_paused is True
    
    def test_resume_reschedules_timers(self):
        """Test that resume reschedules timers with adjusted delays."""
        app = Mock()
        scheduler = WordHighlightScheduler(app)
        estimator = WordTimingEstimator()
        
        sentence = "One two three four five"
        duration = 2.0  # Longer duration to give more time
        
        scheduler.schedule_highlights(sentence, 0, duration, estimator)
        initial_timer_count = len(scheduler._timers)
        assert initial_timer_count == 5
        
        scheduler.pause()
        assert len(scheduler._timers) == 0
        
        scheduler.resume()
        
        # Timers should be rescheduled (some may have already fired)
        assert len(scheduler._timers) >= 1
        assert scheduler._is_paused is False
    
    def test_cancel_clears_pending_timers(self):
        """Test that cancel_highlights clears pending timers."""
        app = Mock()
        scheduler = WordHighlightScheduler(app)
        estimator = WordTimingEstimator()
        
        sentence = "One two three"
        duration = 1.0
        
        scheduler.schedule_highlights(sentence, 0, duration, estimator)
        assert len(scheduler._pending_timers) == 3
        
        scheduler.cancel_highlights()
        
        assert len(scheduler._pending_timers) == 0
        assert scheduler._is_paused is False


class TestWordTimingIntegration:
    """Integration tests for word timing."""
    
    def test_full_timing_workflow(self):
        """Test full timing workflow."""
        estimator = WordTimingEstimator()
        app = Mock()
        app.call_from_thread = Mock()
        scheduler = WordHighlightScheduler(app)
        
        sentence = "Testing the full workflow"
        duration = 2.0
        
        # Get timings
        timings = estimator.estimate_word_timings(sentence, duration)
        assert len(timings) == 4
        
        # Schedule highlights
        scheduler.schedule_highlights(sentence, 0, duration, estimator)
        assert len(scheduler._timers) == 4
        
        # Cancel
        scheduler.cancel_highlights()
        assert len(scheduler._timers) == 0
    
    def test_timing_with_speed_variation(self):
        """Test that timing scales with duration."""
        estimator = WordTimingEstimator()
        
        sentence = "Same sentence"
        
        # Normal speed
        timings_normal = estimator.estimate_word_timings(sentence, 1.0)
        
        # Fast speed (shorter duration)
        timings_fast = estimator.estimate_word_timings(sentence, 0.5)
        
        # Slow speed (longer duration)
        timings_slow = estimator.estimate_word_timings(sentence, 2.0)
        
        # Fast should be shorter than normal
        assert timings_fast[-1]['end'] < timings_normal[-1]['end']
        
        # Slow should be longer than normal
        assert timings_slow[-1]['end'] > timings_normal[-1]['end']
