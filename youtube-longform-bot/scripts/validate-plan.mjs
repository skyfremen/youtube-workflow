import fs from 'node:fs';

const path = process.argv[2] || 'content/demo-plan.json';
const plan = JSON.parse(fs.readFileSync(path, 'utf8'));

if (!Array.isArray(plan.scenes) || plan.scenes.length === 0) {
  throw new Error('Plan must contain at least one scene.');
}

const allowedTypes = new Set(['hook','character','diagram','comparison','end']);
const allowedActions = new Set([
  'character_enter','character_look','character_react','character_return','character_shocked',
  'fridge_open','fridge_close','pop_text','clock_jump','camera_pan','camera_punch_zoom',
  'diagram_step','shake','end_punchline'
]);

let total = 0;
let beatCount = 0;
for (const [index, scene] of plan.scenes.entries()) {
  if (!Number.isFinite(scene.duration) || scene.duration <= 0) {
    throw new Error(`Scene ${index + 1} has invalid duration.`);
  }
  if (!allowedTypes.has(scene.type)) {
    throw new Error(`Scene ${index + 1} has unsupported type: ${scene.type}`);
  }
  if (!scene.caption || !scene.narration) {
    throw new Error(`Scene ${index + 1} requires caption and narration.`);
  }
  if (!Array.isArray(scene.beats) || scene.beats.length < 4) {
    throw new Error(`Scene ${index + 1} requires at least 4 animation beats.`);
  }
  let previousAt = -1;
  for (const [beatIndex, beat] of scene.beats.entries()) {
    if (!Number.isFinite(beat.at) || beat.at < 0 || beat.at >= scene.duration) {
      throw new Error(`Scene ${index + 1} beat ${beatIndex + 1} has invalid time.`);
    }
    if (beat.at < previousAt) {
      throw new Error(`Scene ${index + 1} beats must be chronological.`);
    }
    if (!allowedActions.has(beat.action)) {
      throw new Error(`Scene ${index + 1} beat ${beatIndex + 1} has unsupported action: ${beat.action}`);
    }
    previousAt = beat.at;
    beatCount += 1;
  }
  total += scene.duration;
}

if (Math.abs(total - plan.duration_seconds) > 0.001) {
  throw new Error(`Scene durations total ${total}s but plan says ${plan.duration_seconds}s.`);
}
if (plan.duration_seconds !== 15) {
  throw new Error(`Animation MVP 2 must be exactly 15 seconds; got ${plan.duration_seconds}.`);
}
if (beatCount < 15) {
  throw new Error(`Animation MVP 2 requires at least 15 visual beats; got ${beatCount}.`);
}

console.log(`Plan valid: ${plan.scenes.length} scenes, ${beatCount} visual beats, ${total}s total.`);
