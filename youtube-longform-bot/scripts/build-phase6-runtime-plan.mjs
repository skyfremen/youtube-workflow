import fs from 'node:fs';

const sourcePath = process.argv[2] || 'content/phase6-plan.json';
const manifestPath = process.argv[3] || 'output/phase6-timing.json';
const outputPath = process.argv[4] || 'content/runtime-plan.json';

const source = JSON.parse(fs.readFileSync(sourcePath, 'utf8'));
const timing = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const timingById = new Map((timing.scenes || []).map((s) => [s.id, s]));

const scenes = source.scenes.map((scene) => {
  const measured = timingById.get(scene.id);
  if (!measured) throw new Error(`Missing measured narration timing for ${scene.id}`);
  if (!(measured.duration > 0)) throw new Error(`Invalid measured duration for ${scene.id}`);

  const beats = (scene.beats || []).map((beat) => ({
    ...beat,
    at: Number((beat.at_pct * measured.duration).toFixed(4))
  }));

  return {
    ...scene,
    start: measured.start,
    end: measured.end,
    duration: measured.duration,
    speech_duration: measured.speech_duration,
    gap_after: measured.gap_after,
    beats
  };
});

const runtime = {
  video_id: source.video_id,
  title: source.title,
  fps: source.fps || 24,
  format: source.format || '16:9',
  timing_mode: 'measured_kokoro_scene_audio',
  duration_seconds: timing.total_duration,
  scenes
};

fs.writeFileSync(outputPath, JSON.stringify(runtime, null, 2) + '\n');
console.log(`Runtime storyboard built from measured narration: ${runtime.duration_seconds.toFixed(2)}s, ${scenes.length} scenes.`);
