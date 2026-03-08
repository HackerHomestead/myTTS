import click
import signal
from pathlib import Path

from mytts import TTSEngine, TTSMode, TTSBackend


_interrupted = False
_client = None

def _signal_handler(signum, frame):
    global _interrupted, _client
    _interrupted = True
    if _client:
        _client.stop()


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
def read(file_path, output, engine, voice, use_server, server_url, workers, buffer_size, start_word):
    """Read a text file aloud"""
    global _interrupted, _client
    _interrupted = False
    _client = None
    
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
            
            # Clear, accessible output
            click.echo("")
            click.echo(click.style("─" * 60, dim=True))
            click.echo("")
            click.echo(f"  {click.style('▶', fg='green', bold=True)}  {sentence_text}")
            click.echo("")
            click.echo(f"     {click.style('└─', dim=True)} {click.style(f'{words_spoken:,}', fg='cyan', bold=True)} of {total_words:,} words  {click.style(bar, dim=True)} {pct}%")
        
        client = ProgressiveTTSClient(
            engine_obj,
            num_workers=workers,
            buffer_size=buffer_size,
            on_play=on_play
        )
        
        _client = client
        
        try:
            # Header
            click.echo("")
            click.echo(click.style("═" * 60, fg='cyan'))
            click.echo(click.style(f"  📖  Reading: {Path(file_path).name}", fg='cyan', bold=True))
            click.echo(click.style(f"     {total_words:,} words total", fg='cyan', dim=True))
            click.echo(click.style("═" * 60, fg='cyan'))
            
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
                click.echo("")
                click.echo(click.style("═" * 60, fg='yellow'))
                click.echo(click.style("  ⏹  STOPPED", fg='yellow', bold=True))
                click.echo(click.style("═" * 60, fg='yellow'))
                click.echo("")
                click.echo(f"  {click.style('📊', fg='cyan')}  Progress")
                click.echo(click.style("  " + "─" * 40, dim=True))
                click.echo(f"     Words:     {click.style(f'{words_spoken:,}', fg='cyan', bold=True)} of {total_words:,}")
                click.echo(f"     Sentences: {sentences_played}")
                click.echo("")
                click.echo(f"  {click.style('▶️', fg='green')}  Resume Command")
                click.echo(click.style("  " + "─" * 40, dim=True))
                click.echo("")
                resume_cmd = f"mytts read {file_path} --server -w {words_spoken}"
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
