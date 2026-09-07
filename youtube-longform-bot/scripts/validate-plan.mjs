import fs from 'node:fs';

const path = process.argv[2] || 'content/demo-plan.json';
const plan = JSON.parse(fs.readFileSync(path, 'utf8'));

if (!Array.isArray(plan.scenes) || plan.scenes.length === 0) {
  throw new Error('Plan must contain at least one scene.');
}

const allowedTypes = new Set(['setup', 'infographic']);
const allowedActions = new Set([
  'walk_in','reach_handle','open_door','look_inside','empty_callout','return_look',
  'diagram_node_1','diagram_node_2','diagram_node_3','arrow_flow','highlight_reward'
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
  if (!Array.isArray(scene.beats) || scene.beats.length < 5) {
    throw new Error(`Scene ${index + 1} requires at least 5 animation beats.`);
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
if (plan.duration_seconds !== 8) {
  throw new Error(`Asset Quality MVP must be exactly 8 seconds; got ${plan.duration_seconds}.`);
}
if (beatCount < 10) {
  throw new Error(`Asset Quality MVP requires at least 10 visual beats; got ${beatCount}.`);
}

console.log(`Plan valid: ${plan.scenes.length} scenes, ${beatCount} visual beats, ${total}s total.`);
