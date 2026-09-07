import fs from 'node:fs';

const path = process.argv[2] || 'content/demo-plan.json';
const plan = JSON.parse(fs.readFileSync(path, 'utf8'));

if (!Array.isArray(plan.scenes) || plan.scenes.length === 0) {
  throw new Error('Plan must contain at least one scene.');
}

const allowedTypes = new Set(['hook','character','diagram','comparison','end']);
let total = 0;
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
  total += scene.duration;
}

if (Math.abs(total - plan.duration_seconds) > 0.001) {
  throw new Error(`Scene durations total ${total}s but plan says ${plan.duration_seconds}s.`);
}
if (plan.duration_seconds !== 60) {
  throw new Error(`MVP test must be exactly 60 seconds; got ${plan.duration_seconds}.`);
}

console.log(`Plan valid: ${plan.scenes.length} scenes, ${total}s total.`);
