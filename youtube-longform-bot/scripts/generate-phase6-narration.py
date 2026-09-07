#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

SAMPLE_RATE = 24000


def synthesize(pipeline, text, voice, speed):
    chunks = []
    for _, _, audio in pipeline(text, voice=voice, speed=speed):
        chunks.append(np.asarray(audio, dtype=np.float32))
    if not chunks:
        raise RuntimeError("Kokoro produced no audio")
    return np.concatenate(chunks)


def main():
    parser = argparse.ArgumentParser(description="Generate Phase 6 scene narration and exact timing manifest")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--segments-dir", required=True)
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--gap", type=float, default=0.10)
    args = parser.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    scenes = plan.get("scenes") or []
    if not scenes:
        raise SystemExit("Phase 6 plan has no scenes")

    output_path = Path(args.output)
    manifest_path = Path(args.manifest)
    segments_dir = Path(args.segments_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)

    pipeline = KPipeline(lang_code="a")
    gap_samples = max(0, int(args.gap * SAMPLE_RATE))
    pieces = []
    manifest_scenes = []
    cursor_samples = 0

    for index, scene in enumerate(scenes):
        scene_id = str(scene.get("id") or f"scene-{index + 1}")
        narration = str(scene.get("narration") or "").strip()
        if not narration:
            raise SystemExit(f"Scene {scene_id} narration is empty")

        audio = synthesize(pipeline, narration, args.voice, args.speed)
        speech_samples = len(audio)
        is_last = index == len(scenes) - 1
        this_gap_samples = 0 if is_last else gap_samples

        segment_path = segments_dir / f"{scene_id}.wav"
        sf.write(segment_path, audio, SAMPLE_RATE)

        start = cursor_samples / SAMPLE_RATE
        speech_duration = speech_samples / SAMPLE_RATE
        duration = (speech_samples + this_gap_samples) / SAMPLE_RATE
        end = start + duration

        manifest_scenes.append({
            "id": scene_id,
            "start": round(start, 6),
            "speech_duration": round(speech_duration, 6),
            "gap_after": round(this_gap_samples / SAMPLE_RATE, 6),
            "duration": round(duration, 6),
            "end": round(end, 6),
            "segment_file": str(segment_path).replace('\\', '/')
        })

        pieces.append(audio)
        if this_gap_samples:
            pieces.append(np.zeros(this_gap_samples, dtype=np.float32))
        cursor_samples += speech_samples + this_gap_samples

    combined = np.concatenate(pieces)
    sf.write(output_path, combined, SAMPLE_RATE)
    total_duration = len(combined) / SAMPLE_RATE

    manifest = {
        "timing_mode": "measured_kokoro_scene_audio",
        "sample_rate": SAMPLE_RATE,
        "voice": args.voice,
        "speed": args.speed,
        "total_duration": round(total_duration, 6),
        "scenes": manifest_scenes
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Phase 6 narration: {len(scenes)} scenes, {total_duration:.2f}s, voice={args.voice}")
    for scene in manifest_scenes:
        print(f"  {scene['id']}: {scene['speech_duration']:.2f}s speech + {scene['gap_after']:.2f}s gap")


if __name__ == "__main__":
    main()
