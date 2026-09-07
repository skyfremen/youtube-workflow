import fs from 'node:fs';

const planPath = process.argv[2] || 'content/scene-plan.json';
const registryPath = process.argv[3] || 'assets/registry.json';
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));

if (!Array.isArray(plan.scenes) || plan.scenes.length < 5) {
  throw new Error('Phase 5 requires at least 5 scenes.');
}

if (plan.duration_seconds !== 30) {
  throw new Error(`Phase 5 must be exactly 30 seconds; got ${plan.duration_seconds}.`);
}

const validMotions = new Set(registry.motions || []);
const validTypes = new Set(registry.scene_types || []);
let total = 0;
let beats = 0;
const assetCategories = new Set();

for (const [i, scene] of plan.scenes.entries()) {
  if (!validTypes.has(scene.type)) {
    throw new Error(`Scene ${scene.id || i + 1} uses unsupported type ${scene.type}.`);
  }
  if (!Number.isFinite(scene.duration) || scene.duration <= 0) {
    throw new Error(`Scene ${scene.id || i + 1} has invalid duration.`);
  }
  if (!scene.caption || !scene.narration) {
    throw new Error(`Scene ${scene.id || i + 1} requires caption and narration.`);
  }
  if (!Array.isArray(scene.beats) || scene.beats.length < 3) {
    throw new Error(`Scene ${scene.id || i + 1} requires at least 3 visual beats.`);
  }

  if (scene.environment) {
    if (!registry.environments?.[scene.environment]) throw new Error(`Unknown environment: ${scene.environment}`);
    assetCategories.add('environment');
  }
  if (scene.character) {
    if (!registry.characters?.[scene.character]) throw new Error(`Unknown character: ${scene.character}`);
    assetCategories.add('character');
  }
  for (const prop of scene.props || []) {
    if (!registry.props?.[prop]) throw new Error(`Unknown prop: ${prop}`);
    assetCategories.add('prop');
  }
  if (scene.infographic) {
    if (!registry.infographics?.[scene.infographic]) throw new Error(`Unknown infographic: ${scene.infographic}`);
    assetCategories.add('infographic');
  }

  let previous = -1;
  for (const beat of scene.beats) {
    if (!Number.isFinite(beat.at) || beat.at < 0 || beat.at >= scene.duration) {
      throw new Error(`Scene ${scene.id} has beat outside scene duration.`);
    }
    if (beat.at < previous) throw new Error(`Scene ${scene.id} beats must be chronological.`);
    if (!validMotions.has(beat.motion)) throw new Error(`Scene ${scene.id} uses unknown motion ${beat.motion}.`);
    if (!beat.target) throw new Error(`Scene ${scene.id} has a beat with no target.`);
    previous = beat.at;
    beats += 1;
  }
  total += scene.duration;
}

if (Math.abs(total - plan.duration_seconds) > 0.001) {
  throw new Error(`Scene durations total ${total}s but plan says ${plan.duration_seconds}s.`);
}
if (beats < 18) throw new Error(`Phase 5 requires at least 18 visual beats; got ${beats}.`);
if (assetCategories.size < 4) throw new Error(`Phase 5 must exercise at least 4 asset categories; got ${[...assetCategories].join(', ')}.`);

console.log(`Storyboard valid: ${plan.scenes.length} scenes, ${beats} beats, ${total}s, assets=${[...assetCategories].join(',')}.`);
