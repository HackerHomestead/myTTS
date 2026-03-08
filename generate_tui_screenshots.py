#!/usr/bin/env python3
"""Generate TUI screenshots at different terminal sizes for UX validation."""

import asyncio
import tempfile
import os
from pathlib import Path


async def generate_screenshots():
    """Generate SVG screenshots at different terminal sizes."""
    from mytts.tui import TTSReaderApp
    
    # Create test content
    test_content = """This is the first sentence of our test document. It contains enough text to demonstrate the TUI layout.

This is the second sentence, which is a bit longer and will help us see how text wrapping works in the content area.

The third sentence is quite long and will definitely need to wrap across multiple lines because it exceeds the maximum width limit that we have set for the display area in the terminal.

Fourth sentence is short.

Fifth sentence is medium length and provides good contrast.

The sixth sentence is another very long sentence that will wrap across multiple lines to demonstrate how the TUI handles longer content while maintaining readability and proper layout within the terminal window.

Seventh sentence.

Eighth sentence with some more content to fill the display.

Ninth sentence continues the pattern.

The tenth and final sentence wraps up our test document with a reasonably long piece of text that should demonstrate the scrolling behavior."""
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        # Terminal sizes to test
        test_sizes = [
            (80, 24, "minimum_80x24"),
            (96, 30, "default_96x30"),
            (120, 35, "wide_120x35"),
            (150, 40, "extrawide_150x40"),
        ]
        
        # Create output directory
        output_dir = Path("tui_screenshots")
        output_dir.mkdir(exist_ok=True)
        
        print("=" * 60)
        print("TUI Screenshot Generator")
        print("=" * 60)
        print(f"\nTest file: {test_file}")
        print(f"Output directory: {output_dir.absolute()}")
        print()
        
        for width, height, name in test_sizes:
            print(f"Generating {name} ({width}x{height})...")
            
            # Create app
            app = TTSReaderApp(
                file_path=test_file,
                server_url="http://localhost:8000",
                voice="en_US-lessac-medium",
                start_word=0,
                initial_speed=0.95,
            )
            
            # Run app with specific size
            async with app.run_test(size=(width, height)) as pilot:
                # Wait for initialization
                await pilot.pause()
                
                # Export screenshot SVG
                svg_content = app.export_screenshot()
                
                # Save to file
                svg_path = output_dir / f"{name}.svg"
                svg_path.write_text(svg_content)
                
                print(f"  ✓ Saved: {svg_path.name}")
        
        print()
        print("=" * 60)
        print("Screenshots generated successfully!")
        print("=" * 60)
        print(f"\nView screenshots in: {output_dir.absolute()}")
        print("\nFiles generated:")
        for width, height, name in test_sizes:
            print(f"  - {name}.svg ({width}x{height})")
        
        return 0
        
    finally:
        # Cleanup temp file
        os.unlink(test_file)


def main():
    """Main entry point."""
    try:
        exit_code = asyncio.run(generate_screenshots())
        return exit_code
    except Exception as e:
        print(f"\n✗ Error generating screenshots: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
