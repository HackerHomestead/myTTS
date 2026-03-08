#!/usr/bin/env python3
"""Test script for TUI functionality."""

import sys
import tempfile
import os

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from mytts.tui import TTSReaderApp, run_tui_reader
        print("  ✓ mytts.tui")
    except ImportError as e:
        print(f"  ✗ mytts.tui: {e}")
        return False
    
    try:
        from textual.app import App
        from textual.widgets import Header, Footer, Static
        print("  ✓ textual")
    except ImportError as e:
        print(f"  ✗ textual: {e}")
        return False
    
    try:
        from rich.text import Text
        from rich.style import Style
        print("  ✓ rich")
    except ImportError as e:
        print(f"  ✗ rich: {e}")
        return False
    
    return True


def test_app_creation():
    """Test that TTSReaderApp can be created."""
    print("\nTesting app creation...")
    
    from mytts.tui import TTSReaderApp
    
    # Create a test file
    test_text = "This is a test. It has multiple sentences."
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_text)
        test_file = f.name
    
    try:
        app = TTSReaderApp(
            file_path=test_file,
            server_url="http://localhost:8000",
            voice="en_US-lessac-medium",
            start_word=0,
            initial_speed=1.0,
        )
        print("  ✓ App created")
        
        # Check attributes
        assert app.file_path.name == os.path.basename(test_file)
        print("  ✓ File path set")
        
        assert app.server_url == "http://localhost:8000"
        print("  ✓ Server URL set")
        
        assert app.initial_speed == 1.0
        print("  ✓ Initial speed set")
        
        # Check bindings
        assert len(app.BINDINGS) == 15
        print(f"  ✓ {len(app.BINDINGS)} bindings defined")
        
        # Check CSS
        assert len(app.CSS) > 0
        print("  ✓ CSS defined")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False
    finally:
        os.unlink(test_file)


def test_widgets():
    """Test that all widgets work correctly."""
    print("\nTesting widgets...")
    
    from mytts.tui import SentenceDisplay, StatusDisplay, ControlsDisplay
    
    try:
        # Test SentenceDisplay
        sd = SentenceDisplay()
        sd.sentence = "Test sentence"
        sd.sentence_number = 1
        sd.total_sentences = 10
        rendered = sd.render()
        assert "Test sentence" in str(rendered)
        print("  ✓ SentenceDisplay")
        
        # Test StatusDisplay
        st = StatusDisplay()
        st.speed = 1.5
        st.words_spoken = 100
        st.total_words = 1000
        st.is_paused = False
        rendered = st.render()
        assert "1.50x" in str(rendered)
        print("  ✓ StatusDisplay")
        
        # Test ControlsDisplay
        cd = ControlsDisplay()
        rendered = cd.render()
        assert "Space" in str(rendered)
        print("  ✓ ControlsDisplay")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_actions():
    """Test that all action methods exist."""
    print("\nTesting action methods...")
    
    from mytts.tui import TTSReaderApp
    
    # Create a test file
    test_text = "Test sentence."
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_text)
        test_file = f.name
    
    try:
        app = TTSReaderApp(file_path=test_file, server_url="http://localhost:8000")
        
        actions = [
            'action_toggle_pause',
            'action_next_sentence',
            'action_prev_sentence',
            'action_increase_speed',
            'action_decrease_speed',
            'action_reset_speed',
            'action_repeat_sentence',
            'action_goto_sentence',
            'action_set_bookmark',
            'action_prev_bookmark',
            'action_next_bookmark',
            'action_goto_beginning',
            'action_goto_end',
            'action_show_info',
            'action_quit',
        ]
        
        for action in actions:
            method = getattr(app, action, None)
            if method and callable(method):
                print(f"  ✓ {action}")
            else:
                print(f"  ✗ {action} NOT FOUND")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False
    finally:
        os.unlink(test_file)


def main():
    """Run all tests."""
    print("=" * 60)
    print("TUI Test Suite")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_app_creation,
        test_widgets,
        test_actions,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ All tests passed!")
        print("\nTo run the TUI interactively:")
        print("  mytts read <file.txt> --server --tui")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
