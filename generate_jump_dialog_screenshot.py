#!/usr/bin/env python3
"""Generate screenshot of jump dialog with bookmarks."""

import asyncio
import tempfile
import os
from pathlib import Path


async def generate_jump_dialog_screenshot():
    """Generate SVG screenshot of jump dialog."""
    from mytts.tui import TTSReaderApp, JumpDialog
    
    # Create test content with multiple sentences
    test_content = """This is the first sentence of our test document.

This is the second sentence, which is a bit longer.

The third sentence is quite long and will help us see how text wrapping works.

Fourth sentence is short.

Fifth sentence is medium length.

Sixth sentence here.

Seventh sentence with more content.

Eighth sentence continues.

Ninth sentence for testing.

The tenth sentence wraps up our test document."""
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        # Create app
        app = TTSReaderApp(
            file_path=test_file,
            server_url="http://localhost:8000",
            voice="en_US-lessac-medium",
            start_word=0,
            initial_speed=0.95,
        )
        
        # Run app with specific size
        async with app.run_test(size=(96, 30)) as pilot:
            # Wait for initialization
            await pilot.pause()
            
            # Add some bookmarks
            app.bookmarks = [0, 2, 4, 6, 8]
            
            # Build bookmark data
            bookmark_data = []
            for bm_idx in app.bookmarks:
                if bm_idx < len(app.sentences):
                    word_num = sum(len(s.split()) for s in app.sentences[:bm_idx]) + 1
                    bookmark_data.append({
                        'index': bm_idx,
                        'text': app.sentences[bm_idx],
                        'word': word_num
                    })
            
            # Create jump dialog
            dialog = JumpDialog(
                total_words=app.total_words,
                bookmarks=bookmark_data,
                current_word=0,
            )
            
            # Push the dialog
            app.push_screen(dialog)
            await pilot.pause()
            
            # Generate SVG screenshot
            svg_content = app.export_screenshot()
            
            # Save to file
            output_dir = Path("tui_screenshots")
            output_dir.mkdir(exist_ok=True)
            svg_path = output_dir / "jump_dialog.svg"
            svg_path.write_text(svg_content)
            
            print(f"✓ Saved: {svg_path}")
            
            return 0
    
    finally:
        # Cleanup temp file
        os.unlink(test_file)


def main():
    """Main entry point."""
    try:
        exit_code = asyncio.run(generate_jump_dialog_screenshot())
        return exit_code
    except Exception as e:
        print(f"\n✗ Error generating screenshot: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
