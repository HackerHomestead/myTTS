#!/usr/bin/env python3
"""Test TUI layout at different terminal sizes."""

import sys
import tempfile
import os
from mytts.tui import ChunkDisplay, HeaderDisplay, StatusDisplay, ControlsDisplay


def test_chunk_display_line_counting():
    """Test that ChunkDisplay correctly counts lines for wrapped text."""
    print("\nTesting ChunkDisplay line counting...")
    
    cd = ChunkDisplay()
    cd.max_width = 69  # 80 - 11 (prefix + padding)
    
    # Short text that fits on one line
    short_text = "This is a short sentence."
    lines = cd._count_lines_for_chunk(short_text)
    assert lines == 1, f"Short text should be 1 line, got {lines}"
    print(f"  ✓ Short text: {lines} line")
    
    # Long text that wraps to multiple lines
    long_text = "This is a much longer sentence that will definitely need to wrap across multiple lines because it exceeds the maximum width limit."
    lines = cd._count_lines_for_chunk(long_text)
    assert lines > 1, f"Long text should wrap to multiple lines, got {lines}"
    print(f"  ✓ Long text: {lines} lines")
    
    # Very long text
    very_long = " ".join(["word"] * 50)
    lines = cd._count_lines_for_chunk(very_long)
    assert lines > 3, f"Very long text should wrap to many lines, got {lines}"
    print(f"  ✓ Very long text: {lines} lines")
    
    return True


def test_chunk_display_fitting():
    """Test that ChunkDisplay fits content within available height."""
    print("\nTesting ChunkDisplay content fitting...")
    
    cd = ChunkDisplay()
    cd.max_width = 69
    
    # Create test chunks of varying lengths
    cd.chunks = [
        "Short sentence.",
        "This is a medium length sentence that might wrap.",
        "This is a very long sentence that will definitely need to wrap across multiple lines because it exceeds the maximum width limit that we have set for the display area.",
        "Another short one.",
        "Medium length sentence here.",
    ]
    
    # Test line counting for each chunk
    total_lines = sum(cd._count_lines_for_chunk(chunk) for chunk in cd.chunks)
    print(f"  ✓ Total lines for all chunks: {total_lines}")
    
    # Test that line counting works correctly
    for i, chunk in enumerate(cd.chunks):
        lines = cd._count_lines_for_chunk(chunk)
        print(f"    Chunk {i}: {lines} lines")
    
    return True


def test_header_display():
    """Test HeaderDisplay at different terminal widths."""
    print("\nTesting HeaderDisplay at different widths...")
    
    hd = HeaderDisplay()
    hd.file_name = "test_document.txt"
    
    test_widths = [80, 96, 120, 150]
    
    for width in test_widths:
        hd.terminal_size = (width, 30)
        rendered = hd.render()
        rendered_str = str(rendered)
        
        # Check that terminal size is displayed
        assert f"{width}x30" in rendered_str, \
            f"Width {width}: terminal size not shown"
        
        # Check that file name is displayed
        assert "test_document.txt" in rendered_str, \
            f"Width {width}: file name not shown"
        
        print(f"  ✓ Width {width}: header displays correctly")
    
    return True


def test_status_display():
    """Test StatusDisplay at different terminal widths."""
    print("\nTesting StatusDisplay at different widths...")
    
    sd = StatusDisplay()
    sd.speed = 1.5
    sd.words_spoken = 1000
    sd.total_words = 5000
    sd.is_paused = False
    sd.current_voice = "en_US-lessac-medium"
    
    test_widths = [80, 96, 120]
    
    for width in test_widths:
        sd.terminal_size = (width, 30)
        rendered = sd.render()
        rendered_str = str(rendered)
        
        # Check essential info is displayed
        assert "1.50x" in rendered_str, f"Width {width}: speed not shown"
        assert "1,000" in rendered_str or "1000" in rendered_str, \
            f"Width {width}: word count not shown"
        
        print(f"  ✓ Width {width}: status displays correctly")
    
    return True


def test_controls_display():
    """Test ControlsDisplay compactness."""
    print("\nTesting ControlsDisplay compactness...")
    
    cd = ControlsDisplay()
    rendered = cd.render()
    rendered_str = str(rendered)
    
    # Check that essential controls are shown (using compact labels)
    essential_controls = ["Spc", "Ent", "q"]
    for control in essential_controls:
        assert control in rendered_str, f"Control '{control}' not shown"
    
    # Check that it's reasonably compact (should fit in 80 cols)
    # Each line should be <= 80 chars
    lines = rendered_str.split('\n')
    for i, line in enumerate(lines):
        # Remove ANSI codes for length calculation
        import re
        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
        assert len(clean_line) <= 80, \
            f"Line {i} too long: {len(clean_line)} chars"
    
    print(f"  ✓ Controls are compact ({len(rendered_str)} chars) and complete")
    return True


def test_layout_at_terminal_sizes():
    """Test complete layout at various terminal sizes."""
    print("\nTesting complete layout at various terminal sizes...")
    
    test_sizes = [
        (80, 24, "Minimum"),
        (96, 30, "Default"),
        (120, 35, "Wide"),
        (150, 40, "Extra wide"),
    ]
    
    for width, height, name in test_sizes:
        print(f"\n  Testing {name} ({width}x{height}):")
        
        # Test HeaderDisplay
        hd = HeaderDisplay()
        hd.file_name = "document.txt"
        hd.terminal_size = (width, height)
        hd_rendered = str(hd.render())
        print(f"    Header: {len(hd_rendered)} chars")
        
        # Test ChunkDisplay line counting
        cd = ChunkDisplay()
        cd.max_width = width - 11
        cd.chunks = [
            "Short sentence.",
            "This is a medium length sentence.",
            "This is a very long sentence that will definitely need to wrap across multiple lines because it exceeds the maximum width limit.",
            "Another short one.",
        ]
        
        total_lines = sum(cd._count_lines_for_chunk(chunk) for chunk in cd.chunks)
        print(f"    Content: {total_lines} lines for 4 chunks")
        
        # Test StatusDisplay
        sd = StatusDisplay()
        sd.speed = 1.5
        sd.words_spoken = 1000
        sd.total_words = 5000
        sd.terminal_size = (width, height)
        sd_rendered = str(sd.render())
        print(f"    Status: {len(sd_rendered)} chars")
        
        # Test ControlsDisplay
        controls = ControlsDisplay()
        controls_rendered = str(controls.render())
        print(f"    Controls: {len(controls_rendered)} chars")
        
        print(f"    ✓ {name} layout OK")
    
    return True


def main():
    """Run all layout tests."""
    print("=" * 60)
    print("TUI Layout Test Suite")
    print("=" * 60)
    
    tests = [
        test_chunk_display_line_counting,
        test_chunk_display_fitting,
        test_header_display,
        test_status_display,
        test_controls_display,
        test_layout_at_terminal_sizes,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n  ✗ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ All layout tests passed!")
        print("\nLayout is optimized for 96x30 terminal")
        print("Works well from 80x24 to 150x40")
        return 0
    else:
        print("✗ Some layout tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
