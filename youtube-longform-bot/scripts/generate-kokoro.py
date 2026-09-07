#!/usr/bin/env python3
import argparse
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline


def main():
    parser = argparse.ArgumentParser(description="Generate local Kokoro narration for the longform MVP")
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()

    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit("Narration text is empty")

    pipeline = KPipeline(lang_code="a")
    chunks = []
    for _, _, audio in pipeline(text, voice=args.voice, speed=args.speed):
        chunks.append(np.asarray(audio, dtype=np.float32))

    if not chunks:
        raise SystemExit("Kokoro produced no audio")

    combined = np.concatenate(chunks)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output, combined, 24000)

    duration = len(combined) / 24000
    print(f"Kokoro voice={args.voice} speed={args.speed:.2f} duration={duration:.2f}s output={output}")


if __name__ == "__main__":
    main()
