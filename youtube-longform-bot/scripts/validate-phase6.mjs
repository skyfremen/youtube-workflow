import fs from 'node:fs';

const planPath = process.argv[2] || 'content/phase6-plan.json';
const registryPath = process.argv[3] || 'assets/registry.json';
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));

if (plan.timing_mode !== 'narration_first') throw new Error('Phase 6 must use narration_first timing.');
if (!Array.isArray(plan.scenes) || plan.scenes.length < 5) throw new Error('Phase 6 requires at least 5 scenes.');
if (![24, 30].includes(plan.fps)) throw new Error(`Phase 6 fps must be 24 or 30; got ${plan.fps}.`);

const validTypes = new Set(registry.scene_types || []);
const validMotions = new Set(registry.motions || []);
const forbiddenSlideTypes = new Set(['infographic', 'comparison', 'summary']);
let beats = 0;
let narrationWords = 0;
let environmentScenes = 0;

const verifyFile = (path) => {
  if (!path) return;
  if (!fs.existsSync(`public/${path}`)) throw new Error(`Registry asset file missing: public/${path}`);
};

for (const item of Object.values(registry.environments || {})) verifyFile(item.file);
for (const item of Object.values(registry.infographics || {})) verifyFile(item.file);
for (const item of Object.values(registry.characters || {})) {
  verifyFile(item.body);
  verifyFile(item.head);
}
for (const item of Object.values(registry.props || {})) {
  verifyFile(item.file);
  verifyFile(item.base);
  verifyFile(item.door);
}

for (const scene of plan.scenes) {
  if (!validTypes.has(scene.type)) throw new Error(`Unsupported scene type ${scene.type} in ${scene.id}.`);
  if (forbiddenSlideTypes.has(scene.type)) throw new Error(`PowerPoint-style scene type forbidden in Phase 6: ${scene.type}`);
  if (!scene.narration?.trim()) throw new Error(`Scene ${scene.id} has no narration.`);
  if (!scene.caption?.trim()) throw new Error(`Scene ${scene.id} has no caption.`);
  if (scene.caption.trim().split(/\s+/).length > (registry.visual_policy?.max_caption_words || 7)) {
    throw new Error(`Scene ${scene.id} caption is too long.`);
  }
  if (!Array.isArray(scene.beats) || scene.beats.length < 4) throw new Error(`Scene ${scene.id} needs at least 4 visual beats.`);
  if ('duration' in scene || 'start' in scene || 'end' in scene) {
    throw new Error(`Scene ${scene.id} must not contain fixed timing; Phase 6 timing comes from narration.`);
  }

  if (scene.environment) {
    if (!registry.environments?.[scene.environment]) throw new Error(`Unknown environment ${scene.environment}.`);
    environmentScenes += 1;
  }
  if (scene.character && !registry.characters?.[scene.character]) throw new Error(`Unknown character ${scene.character}.`);
  for (const prop of scene.props || []) if (!registry.props?.[prop]) throw new Error(`Unknown prop ${prop}.`);

  let prev = -1;
  for (const beat of scene.beats) {
    if (!Number.isFinite(beat.at_pct) || beat.at_pct < 0 || beat.at_pct >= 1) throw new Error(`Scene ${scene.id} has invalid at_pct.`);
    if (beat.at_pct < prev) throw new Error(`Scene ${scene.id} beats must be chronological.`);
    if (!validMotions.has(beat.motion)) throw new Error(`Scene ${scene.id} uses unknown motion ${beat.motion}.`);
    if (!beat.target) throw new Error(`Scene ${scene.id} has a beat with no target.`);
    prev = beat.at_pct;
    beats += 1;
  }

  narrationWords += scene.narration.trim().split(/\s+/).length;
}

if (environmentScenes / plan.scenes.length < 0.75) throw new Error('At least 75% of scenes must be environment-led.');
if (beats < 20) throw new Error(`Phase 6 requires at least 20 visual beats; got ${beats}.`);
if (narrationWords < 75 || narrationWords > 120) throw new Error(`Phase 6 narration should be ~75-120 words; got ${narrationWords}.`);

console.log(`Phase 6 source valid: ${plan.scenes.length} scenes, ${beats} beats, ${narrationWords} narration words, narration-first timing.`);
