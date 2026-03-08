import click
import signal
import sys
import threading
from pathlib import Path

from mytts import TTSEngine, TTSMode, TTSBackend


_interrupted = False
_client = None
_speed_changed = False

def _signal_handler(signum, frame):
    global _interrupted, _client
    _interrupted = True
    if _client:
        _client.stop()


def _keyboard_listener():
    """Listen for keyboard input in a separate thread."""
    global _client, _speed_changed, _interrupted
    
    try:
        while not _interrupted and _client:
            try:
                char = sys.stdin.read(1)
                if char == '+' or char == '=':
                    if _client:
                        _client.increase_speed()
                        _speed_changed = True
                elif char == '-' or char == '_':
                    if _client:
                        _client.decrease_speed()
                        _speed_changed = True
                elif char == 'q' or char == 'Q':
                    _interrupted = True
                    if _client:
                        _client.stop()
                    break
            except:
                break
    except:
        pass


@click.group()
def cli():
    """myTTS - Self-hosted text-to-speech toolchain"""
    pass


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output audio file")
@click.option(
    "--engine",
    type=click.Choice(["coqui", "piper"]),
    default="coqui",
    help="TTS engine to use",
)
@click.option("--voice", help="Voice model to use")
@click.option(
    "--server",
    "use_server",
    is_flag=True,
    help="Use remote TTS server",
)
@click.option(
    "--server-url",
    default="http://localhost:8000",
    help="TTS server URL",
)
@click.option(
    "--workers",
    type=int,
    default=4,
    help="Number of worker threads for progressive TTS",
)
@click.option(
    "--buffer-size",
    type=int,
    default=2,
    help="Number of sentences to pre-generate",
)
@click.option(
    "-w", "--start-word",
    type=int,
    default=0,
    help="Start reading from word number (0-indexed)",
)
@click.option(
    "-s", "--speed",
    type=float,
    default=1.0,
    help="Initial speech speed (0.25-4.0, default: 1.0)",
)
def read(file_path, output, engine, voice, use_server, server_url, workers, buffer_size, start_word, speed):
    """Read a text file aloud
    
    Controls:
      + / = : Increase speed
      - / _ : Decrease speed
      q / Q : Stop reading
      Ctrl+C: Stop reading
    """
    global _interrupted, _client, _speed_changed
    _interrupted = False
    _client = None
    _speed_changed = False
    
    signal.signal(signal.SIGINT, _signal_handler)
    
    backend = TTSBackend.SERVER if use_server else TTSBackend.LOCAL
    engine_obj = TTSEngine(
        mode=TTSMode.READING,
        backend=backend,
        engine=engine,
        voice=voice,
        server_url=server_url,
    )
    
    if use_server:
        from mytts.client import ProgressiveTTSClient
        
        text = Path(file_path).read_text()
        total_words = len(text.split())
        
        words_spoken = 0
        sentences_played = 0
        
        def on_play(sentence_text):
            nonlocal words_spoken, sentences_played
            if _interrupted:
                return
            
            sentence_words = len(sentence_text.split())
            words_spoken += sentence_words
            sentences_played += 1
            
            # Progress bar
            progress = int(40 * words_spoken / total_words) if total_words > 0 else 0
            bar = "█" * progress + "░" * (40 - progress)
            pct = int(100 * words_spoken / total_words) if total_words > 0 else 0
            
            # Get current speed
            current_speed = client.speed
            speed_indicator = f"{current_speed:.2f}x"
            
            # Clear, accessible output
            click.echo("")
            click.echo(click.style("─" * 60, dim=True))
            click.echo("")
            click.echo(f"  {click.style('▶', fg='green', bold=True)}  {sentence_text}")
            click.echo("")
            speed_color = 'yellow' if current_speed != 1.0 else 'white'
            click.echo(f"     {click.style('└─', dim=True)} {click.style(f'{words_spoken:,}', fg='cyan', bold=True)} of {total_words:,} words  {click.style(bar, dim=True)} {pct}%  {click.style(speed_indicator, fg=speed_color, bold=True)}")
        
        client = ProgressiveTTSClient(
            engine_obj,
            num_workers=workers,
            buffer_size=buffer_size,
            on_play=on_play
        )
        
        # Set initial speed
        client.speed = max(0.25, min(4.0, speed))
        
        _client = client
        
        # Start keyboard listener
        keyboard_thread = threading.Thread(target=_keyboard_listener, daemon=True)
        keyboard_thread.start()
        
        try:
            # Header
            click.echo("")
            click.echo(click.style("═" * 60, fg='cyan'))
            click.echo(click.style(f"  📖  Reading: {Path(file_path).name}", fg='cyan', bold=True))
            click.echo(click.style(f"     {total_words:,} words total", fg='cyan', dim=True))
            click.echo(click.style(f"     Speed: {client.speed:.2f}x", fg='cyan', dim=True))
            click.echo(click.style("═" * 60, fg='cyan'))
            click.echo("")
            click.echo(click.style("  Controls: [+] faster [-] slower [q] quit", fg='white', dim=True))
            
            if start_word > 0:
                click.echo("")
                click.echo(f"  {click.style('⏭', fg='yellow')}  Seeking to word {start_word:,}...")
                words_counted = 0
                sentences = client.split_into_sentences(text)
                
                for i, sentence in enumerate(sentences):
                    sentence_words = len(sentence.split())
                    if words_counted + sentence_words > start_word:
                        remaining_text = " ".join(sentences[i:])
                        click.echo(f"  {click.style('▶', fg='green')}  Resuming from word {words_counted:,}")
                        click.echo("")
                        client.speak(remaining_text)
                        break
                    words_counted += sentence_words
            else:
                click.echo("")
                client.speak(text)
        except KeyboardInterrupt:
            pass
        finally:
            _client = None
            client.close()
            
            if _interrupted:
                # Clear, accessible summary
                final_speed = client.speed
                click.echo("")
                click.echo(click.style("═" * 60, fg='yellow'))
                click.echo(click.style("  ⏹  STOPPED", fg='yellow', bold=True))
                click.echo(click.style("═" * 60, fg='yellow'))
                click.echo("")
                click.echo(f"  {click.style('📊', fg='cyan')}  Progress")
                click.echo(click.style("  " + "─" * 40, dim=True))
                click.echo(f"     Words:     {click.style(f'{words_spoken:,}', fg='cyan', bold=True)} of {total_words:,}")
                click.echo(f"     Sentences: {sentences_played}")
                click.echo(f"     Speed:     {click.style(f'{final_speed:.2f}x', fg='yellow', bold=True)}")
                click.echo("")
                click.echo(f"  {click.style('▶️', fg='green')}  Resume Command")
                click.echo(click.style("  " + "─" * 40, dim=True))
                click.echo("")
                speed_flag = f"-s {final_speed}" if final_speed != 1.0 else ""
                resume_cmd = f"mytts read {file_path} --server -w {words_spoken} {speed_flag}".strip()
                click.echo(f"     {click.style(resume_cmd, fg='green', bold=True)}")
                click.echo("")
                click.echo(click.style("═" * 60, fg='yellow'))
                click.echo("")
    else:
        engine_obj.speak(file_path=file_path, output=output)


@cli.command()
@click.option(
    "--engine",
    type=click.Choice(["coqui", "piper"]),
    default="piper",
    help="TTS engine to use (piper for low latency)",
)
@click.option("--voice", help="Voice model to use")
@click.option(
    "--server",
    "use_server",
    is_flag=True,
    help="Use remote TTS server",
)
@click.option(
    "--server-url",
    default="http://localhost:8000",
    help="TTS server URL",
)
@click.option(
    "--workers",
    type=int,
    default=4,
    help="Number of worker threads for progressive TTS",
)
@click.option(
    "--buffer-size",
    type=int,
    default=2,
    help="Number of sentences to pre-generate",
)
def chat(engine, voice, use_server, server_url, workers, buffer_size):
    """Interactive conversational TTS"""
    backend = TTSBackend.SERVER if use_server else TTSBackend.LOCAL
    engine_obj = TTSEngine(
        mode=TTSMode.CONVERSATIONAL,
        backend=backend,
        engine=engine,
        voice=voice,
        server_url=server_url,
    )
    
    if use_server:
        from mytts.client import ProgressiveTTSClient
        
        def on_play(text):
            click.echo(text)
        
        client = ProgressiveTTSClient(
            engine_obj,
            num_workers=workers,
            buffer_size=buffer_size,
            on_play=on_play
        )
        try:
            click.echo("Chat mode - type text to speak (Ctrl+C to exit)")
            while True:
                try:
                    text = input("> ")
                    client.speak(text)
                except KeyboardInterrupt:
                    break
        finally:
            client.close()
    else:
        click.echo("Chat mode - type text to speak (Ctrl+C to exit)")
        while True:
            try:
                text = input("> ")
                engine_obj.speak(text)
            except KeyboardInterrupt:
                break


@cli.command()
@click.argument("text")
@click.option("--voice", help="Voice model to use")
@click.option(
    "--server",
    "use_server",
    is_flag=True,
    help="Use remote TTS server",
)
@click.option(
    "--server-url",
    default="http://localhost:8000",
    help="TTS server URL",
)
@click.option(
    "--workers",
    type=int,
    default=4,
    help="Number of worker threads for progressive TTS",
)
@click.option(
    "--buffer-size",
    type=int,
    default=2,
    help="Number of sentences to pre-generate",
)
def speak(text, voice, use_server, server_url, workers, buffer_size):
    """Speak text directly"""
    backend = TTSBackend.SERVER if use_server else TTSBackend.LOCAL
    engine_obj = TTSEngine(
        mode=TTSMode.CONVERSATIONAL,
        backend=backend,
        voice=voice,
        server_url=server_url,
    )
    
    if use_server:
        from mytts.client import ProgressiveTTSClient
        
        def on_play(chunk_text):
            click.echo(chunk_text)
        
        client = ProgressiveTTSClient(
            engine_obj,
            num_workers=workers,
            buffer_size=buffer_size,
            on_play=on_play
        )
        try:
            client.speak(text)
        finally:
            client.close()
    else:
        engine_obj.speak(text)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8000, help="Server port")
@click.option("--cpu", is_flag=True, help="Force CPU mode (disable GPU)")
def serve(host, port, cpu):
    """Start TTS server"""
    import os
    if cpu:
        # Force CPU-only mode
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        mode_desc = " (CPU-only mode)"
    else:
        mode_desc = " (GPU mode if available)"
    from mytts.server import run_server
    click.echo(f"Starting TTS server on {host}:{port}{mode_desc}")
    run_server(host=host, port=port)


@cli.command()
@click.option("--model", default="llama3.2", help="Ollama model")
@click.option("--ollama-url", default="http://localhost:11434", help="Ollama URL")
@click.option("--tts-url", default="http://localhost:8000", help="TTS server URL")
@click.option("--voice", default="en_US-lessac-medium", help="Voice model")
def ollama(model, ollama_url, tts_url, voice):
    """Chat with Ollama + TTS"""
    from mytts.ollama import OllamaChat
    
    chat = OllamaChat(
        model=model,
        ollama_url=ollama_url,
        tts_url=tts_url,
        voice=voice,
    )
    chat.interactive()


def main():
    cli()


if __name__ == "__main__":
    main()
