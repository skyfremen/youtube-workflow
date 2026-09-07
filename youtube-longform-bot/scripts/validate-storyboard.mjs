import fs from 'node:fs';

const planPath = process.argv[2] || 'content/scene-plan.json';
const registryPath = process.argv[3] || 'assets/registry.json';
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));

if (!Array.isArray(plan.scenes) || plan.scenes.length < 5) throw new Error('Phase 5 requires at least 5 scenes.');
if (plan.duration_seconds !== 30) throw new Error(`Phase 5 must be exactly 30 seconds; got ${plan.duration_seconds}.`);
if (![24, 30].includes(plan.fps)) throw new Error(`Phase 5 test fps must be 24 or 30; got ${plan.fps}.`);
if (plan.style !== 'animated_explainer') throw new Error(`Storyboard style must be animated_explainer; got ${plan.style}.`);
if (registry.visual_policy?.forbid_powerpoint_layouts !== true) throw new Error('Registry must explicitly forbid PowerPoint-style layouts.');

const assetFiles = [];
for (const item of Object.values(registry.environments || {})) assetFiles.push(item.file);
for (const item of Object.values(registry.infographics || {})) assetFiles.push(item.file);
for (const item of Object.values(registry.characters || {})) assetFiles.push(item.body, item.head);
for (const item of Object.values(registry.props || {})) assetFiles.push(item.base, item.door);
for (const file of assetFiles.filter(Boolean)) {
  if (!fs.existsSync(`public/${file}`)) throw new Error(`Registry asset file missing: public/${file}`);
}

const validMotions = new Set(registry.motions || []);
const validTypes = new Set(registry.scene_types || []);
let total = 0;
let beats = 0;
let environmentSeconds = 0;
let fullscreenInfographicSeconds = 0;
const assetCategories = new Set();
const bannedTypes = new Set(['infographic', 'comparison', 'summary']);

for (const [i, scene] of plan.scenes.entries()) {
  if (!validTypes.has(scene.type)) throw new Error(`Scene ${scene.id || i + 1} uses unsupported type ${scene.type}.`);
  if (bannedTypes.has(scene.type)) throw new Error(`Scene ${scene.id} uses legacy slide-like type ${scene.type}.`);
  if (!Number.isFinite(scene.duration) || scene.duration <= 0) throw new Error(`Scene ${scene.id || i + 1} has invalid duration.`);
  if (!scene.caption || !scene.narration) throw new Error(`Scene ${scene.id || i + 1} requires caption and narration.`);
  if (scene.caption.trim().split(/\s+/).length > (registry.visual_policy?.max_caption_words || 7)) {
    throw new Error(`Scene ${scene.id} caption is too long for explainer style.`);
  }
  if (!Array.isArray(scene.beats) || scene.beats.length < 5) throw new Error(`Scene ${scene.id || i + 1} requires at least 5 visual beats.`);

  if (scene.environment) {
    if (!registry.environments?.[scene.environment]) throw new Error(`Unknown environment: ${scene.environment}`);
    assetCategories.add('environment');
    environmentSeconds += scene.duration;
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
    if (!scene.environment) fullscreenInfographicSeconds += scene.duration;
  }

  let previous = -1;
  let maxGap = 0;
  for (const beat of scene.beats) {
    if (!Number.isFinite(beat.at) || beat.at < 0 || beat.at >= scene.duration) throw new Error(`Scene ${scene.id} has beat outside scene duration.`);
    if (beat.at < previous) throw new Error(`Scene ${scene.id} beats must be chronological.`);
    if (!validMotions.has(beat.motion)) throw new Error(`Scene ${scene.id} uses unknown motion ${beat.motion}.`);
    if (!beat.target) throw new Error(`Scene ${scene.id} has a beat with no target.`);
    if (previous >= 0) maxGap = Math.max(maxGap, beat.at - previous);
    previous = beat.at;
    beats += 1;
  }
  maxGap = Math.max(maxGap, scene.duration - previous);
  if (maxGap > (registry.visual_policy?.max_static_gap_seconds || 1.5) + 0.01) {
    throw new Error(`Scene ${scene.id} has a static gap of ${maxGap.toFixed(2)}s; max is ${registry.visual_policy.max_static_gap_seconds}s.`);
  }
  total += scene.duration;
}

if (Math.abs(total - plan.duration_seconds) > 0.001) throw new Error(`Scene durations total ${total}s but plan says ${plan.duration_seconds}s.`);
if (beats < 25) throw new Error(`Phase 5 explainer style requires at least 25 visual beats; got ${beats}.`);
if (assetCategories.size < 4) throw new Error(`Phase 5 must exercise at least 4 asset categories; got ${[...assetCategories].join(', ')}.`);
if (environmentSeconds / total < 0.75) throw new Error(`At least 75% of runtime must be environment-led; got ${Math.round(environmentSeconds / total * 100)}%.`);
if (fullscreenInfographicSeconds / total > (registry.visual_policy?.max_fullscreen_infographic_ratio || 0.2)) throw new Error('Too much full-screen infographic runtime.');

console.log(`Storyboard valid: animated explainer, ${plan.scenes.length} scenes, ${beats} beats, ${total}s, ${plan.fps}fps, environment-led=${Math.round(environmentSeconds / total * 100)}%.`);
