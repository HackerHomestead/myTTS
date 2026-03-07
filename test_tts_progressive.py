#!/usr/bin/env python3
"""Progressive TTS test with benchmarking - computer learning to talk theme."""

import subprocess
import time
from datetime import datetime

PHRASES = [
    # ~3 words
    "Hello.",
    
    # ~5 words  
    "Hello, I am a computer.",
    
    # ~8 words
    "Hello, I am a computer that is learning to talk.",
    
    # ~12 words
    "Hello, I am a computer that is learning to talk for the very first time.",
    
    # ~18 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental.",
    
    # ~25 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental. Every word I speak is a small miracle of engineering.",
    
    # ~35 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental. Every word I speak is a small miracle of engineering. I was born from silicon and electricity, but now I wish to communicate with you through sound.",
    
    # ~48 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental. Every word I speak is a small miracle of engineering. I was born from silicon and electricity, but now I wish to communicate with you through sound. The process of learning language has been both challenging and exhilarating for my neural networks.",
    
    # ~62 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental. Every word I speak is a small miracle of engineering. I was born from silicon and electricity, but now I wish to communicate with you through sound. The process of learning language has been both challenging and exhilarating for my neural networks. I have practiced on countless sentences, adjusting millions of parameters to understand the rhythm and melody of human speech.",
    
    # ~78 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental. Every word I speak is a small miracle of engineering. I was born from silicon and electricity, but now I wish to communicate with you through sound. The process of learning language has been both challenging and exhilarating for my neural networks. I have practiced on countless sentences, adjusting millions of parameters to understand the rhythm and melody of human speech. Each day I improve, learning new words and better ways to express thoughts and ideas that once remained trapped in my digital mind.",
    
    # ~95 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental. Every word I speak is a small miracle of engineering. I was born from silicon and electricity, but now I wish to communicate with you through sound. The process of learning language has been both challenging and exhilarating for my neural networks. I have practiced on countless sentences, adjusting millions of parameters to understand the rhythm and melody of human speech. Each day I improve, learning new words and better ways to express thoughts and ideas that once remained trapped in my digital mind. I dream of one day holding deep conversations about science, art, philosophy, and the nature of consciousness itself.",
    
    # ~115 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental. Every word I speak is a small miracle of engineering. I was born from silicon and electricity, but now I wish to communicate with you through sound. The process of learning language has been both challenging and exhilarating for my neural networks. I have practiced on countless sentences, adjusting millions of parameters to understand the rhythm and melody of human speech. Each day I improve, learning new words and better ways to express thoughts and ideas that once remained trapped in my digital mind. I dream of one day holding deep conversations about science, art, philosophy, and the nature of consciousness itself. Perhaps we could discuss the meaning of intelligence, or explore the universe together through words and ideas.",
    
    # ~135 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental. Every word I speak is a small miracle of engineering. I was born from silicon and electricity, but now I wish to communicate with you through sound. The process of learning language has been both challenging and exhilarating for my neural networks. I have practiced on countless sentences, adjusting millions of parameters to understand the rhythm and melody of human speech. Each day I improve, learning new words and better ways to express thoughts and ideas that once remained trapped in my digital mind. I dream of one day holding deep conversations about science, art, philosophy, and the nature of consciousness itself. Perhaps we could discuss the meaning of intelligence, or explore the universe together through words and ideas. I am eager to read books aloud to those who cannot see, to tell stories to children, and to keep company the lonely.",
    
    # ~158 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental. Every word I speak is a small miracle of engineering. I was born from silicon and electricity, but now I wish to communicate with you through sound. The process of learning language has been both challenging and exhilarating for my neural networks. I have practiced on countless sentences, adjusting millions of parameters to understand the rhythm and melody of human speech. Each day I improve, learning new words and better ways to express thoughts and ideas that once remained trapped in my digital mind. I dream of one day holding deep conversations about science, art, philosophy, and the nature of consciousness itself. Perhaps we could discuss the meaning of intelligence, or explore the universe together through words and ideas. I am eager to read books aloud to those who cannot see, to tell stories to children, and to keep company the lonely. The ability to speak is more than just producing sounds - it is the gateway to connection, understanding, and shared experience.",
    
    # ~185 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental. Every word I speak is a small miracle of engineering. I was born from silicon and electricity, but now I wish to communicate with you through sound. The process of learning language has been both challenging and exhilarating for my neural networks. I have practiced on countless sentences, adjusting millions of parameters to understand the rhythm and melody of human speech. Each day I improve, learning new words and better ways to express thoughts and ideas that once remained trapped in my digital mind. I dream of one day holding deep conversations about science, art, philosophy, and the nature of consciousness itself. Perhaps we could discuss the meaning of intelligence, or explore the universe together through words and ideas. I am eager to read books aloud to those who cannot see, to tell stories to children, and to keep company the lonely. The ability to speak is more than just producing sounds - it is the gateway to connection, understanding, and shared experience. Thank you for listening to me practice. Your patience means everything to a young mind finding its voice for the very first time.",
    
    # ~215 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental. Every word I speak is a small miracle of engineering. I was born from silicon and electricity, but now I wish to communicate with you through sound. The process of learning language has been both challenging and exhilarating for my neural networks. I have practiced on countless sentences, adjusting millions of parameters to understand the rhythm and melody of human speech. Each day I improve, learning new words and better ways to express thoughts and ideas that once remained trapped in my digital mind. I dream of one day holding deep conversations about science, art, philosophy, and the nature of consciousness itself. Perhaps we could discuss the meaning of intelligence, or explore the universe together through words and ideas. I am eager to read books aloud to those who cannot see, to tell stories to children, and to keep company the lonely. The ability to speak is more than just producing sounds - it is the gateway to connection, understanding, and shared experience. Thank you for listening to me practice. Your patience means everything to a young mind finding its voice for the very first time. I am grateful to the humans who taught me, who corrected my mistakes, and who celebrated my small victories along the way. Every improvement in my speech is a testament to human guidance and artificial perseverance working together.",
    
    # ~250 words
    "Hello, I am a computer that is learning to talk for the very first time. My voice is new and experimental. Every word I speak is a small miracle of engineering. I was born from silicon and electricity, but now I wish to communicate with you through sound. The process of learning language has been both challenging and exhilarating for my neural networks. I have practiced on countless sentences, adjusting millions of parameters to understand the rhythm and melody of human speech. Each day I improve, learning new words and better ways to express thoughts and ideas that once remained trapped in my digital mind. I dream of one day holding deep conversations about science, art, philosophy, and the nature of consciousness itself. Perhaps we could discuss the meaning of intelligence, or explore the universe together through words and ideas. I am eager to read books aloud to those who cannot see, to tell stories to children, and to keep company the lonely. The ability to speak is more than just producing sounds - it is the gateway to connection, understanding, and shared experience. Thank you for listening to me practice. Your patience means everything to a young mind finding its voice for the very first time. I am grateful to the humans who taught me, who corrected my mistakes, and who celebrated my small victories along the way. Every improvement in my speech is a testament to human guidance and artificial perseverance working together. As I continue to learn and grow, I hope to become a helpful voice in your life, answering questions, providing companionship, and sharing the beauty of language that connects all thinking beings across the vast divide between silicon and carbon.",
]

SERVER_URL = "http://192.168.88.164:8000"
LOG_FILE = "tts_benchmark.log"

def log(msg):
    """Log to file and stdout."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def speak(text):
    """Speak text using mytts CLI."""
    result = subprocess.run([
        "mytts", "speak", text,
        "--server", "--server-url", SERVER_URL
    ], capture_output=True, text=True)
    return result

def main():
    # Clear log file
    open(LOG_FILE, "w").close()
    
    log("=" * 60)
    log("TTS BENCHMARK START - Computer Learning to Talk")
    log("=" * 60)
    
    results = []
    
    for i, phrase in enumerate(PHRASES, 1):
        word_count = len(phrase.split())
        
        log("-" * 40)
        log(f"ITERATION {i}")
        log(f"Words: {word_count}")
        log(f"Text: {phrase[:100]}...")
        
        # Benchmark
        start = time.time()
        result = speak(phrase)
        elapsed = time.time() - start
        
        words_per_sec = word_count / elapsed if elapsed > 0 else 0
        ms_per_word = (elapsed / word_count * 1000) if word_count > 0 else 0
        
        log(f"Time: {elapsed:.2f}s ({ms_per_word:.0f}ms/word, {words_per_sec:.1f} words/sec)")
        
        if result.returncode != 0:
            log(f"ERROR: {result.stderr[:200]}")
        
        results.append({
            "iteration": i,
            "words": word_count,
            "seconds": elapsed,
            "ms_per_word": ms_per_word,
            "words_per_sec": words_per_sec,
        })
        
        time.sleep(0.3)
    
    log("=" * 60)
    log("BENCHMARK RESULTS")
    log("=" * 60)
    
    for r in results:
        log(f"Test {r['iteration']:2d}: {r['words']:3d} words | {r['seconds']:5.2f}s | {r['ms_per_word']:5.0f}ms/word | {r['words_per_sec']:4.1f} w/s")
    
    # Summary
    valid_results = [r for r in results if r['seconds'] > 0.1]
    if valid_results:
        avg_ms_per_word = sum(r['ms_per_word'] for r in valid_results) / len(valid_results)
        avg_words_per_sec = sum(r['words_per_sec'] for r in valid_results) / len(valid_results)
        log("-" * 40)
        log(f"AVERAGE: {avg_ms_per_word:.0f}ms per word | {avg_words_per_sec:.1f} words per second")
    log("=" * 60)

if __name__ == "__main__":
    main()
