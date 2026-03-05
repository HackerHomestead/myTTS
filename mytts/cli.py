import click
from pathlib import Path

from mytts import TTSEngine, TTSMode, TTSBackend


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
    is_flag,
    help="Use remote TTS server",
)
@click.option(
    "--server-url",
    default="http://localhost:8000",
    help="TTS server URL",
)
def read(file_path, output, engine, voice, use_server, server_url):
    """Read a text file aloud"""
    backend = TTSBackend.SERVER if use_server else TTSBackend.LOCAL
    engine_obj = TTSEngine(
        mode=TTSMode.READING,
        backend=backend,
        engine=engine,
        voice=voice,
        server_url=server_url,
    )
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
    is_flag,
    help="Use remote TTS server",
)
@click.option(
    "--server-url",
    default="http://localhost:8000",
    help="TTS server URL",
)
def chat(engine, voice, use_server, server_url):
    """Interactive conversational TTS"""
    backend = TTSBackend.SERVER if use_server else TTSBackend.LOCAL
    engine_obj = TTSEngine(
        mode=TTSMode.CONVERSATIONAL,
        backend=backend,
        engine=engine,
        voice=voice,
        server_url=server_url,
    )
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
    is_flag,
    help="Use remote TTS server",
)
@click.option(
    "--server-url",
    default="http://localhost:8000",
    help="TTS server URL",
)
def speak(text, voice, use_server, server_url):
    """Speak text directly"""
    backend = TTSBackend.SERVER if use_server else TTSBackend.LOCAL
    engine_obj = TTSEngine(
        mode=TTSMode.CONVERSATIONAL,
        backend=backend,
        voice=voice,
        server_url=server_url,
    )
    engine_obj.speak(text)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8000, help="Server port")
def serve(host, port):
    """Start TTS server (run on GPU machine)"""
    from mytts.server import run_server
    click.echo(f"Starting TTS server on {host}:{port}")
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
