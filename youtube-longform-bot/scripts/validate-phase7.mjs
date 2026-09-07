import fs from 'node:fs';

const planPath = process.argv[2] || 'content/phase7-plan.json';
const registryPath = process.argv[3] || 'assets/registry.json';
const designPath = process.argv[4] || 'assets/design-system.json';
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
const design = JSON.parse(fs.readFileSync(designPath, 'utf8'));

if (plan.planner?.generated_by !== 'ChatGPT') throw new Error('Phase 7 plan must identify ChatGPT as planner.');
if (plan.planner?.design_system !== design.id) throw new Error('Plan design system does not match design-system.json.');
if (!plan.planner?.require_professional_assets) throw new Error('Professional asset quality must be mandatory.');
if (!Array.isArray(plan.asset_needs) || plan.asset_needs.length < 3) throw new Error('Phase 7 must exercise multiple asset needs.');
if (!Array.isArray(plan.scenes) || plan.scenes.length < 5) throw new Error('Phase 7 requires at least 5 scenes.');
if (plan.fps !== 24) throw new Error('Phase 7 MVP must remain at 24fps to control Actions minutes.');

const validCategories = new Set(['character','environment','prop','infographic']);
const needIds = new Set();
for (const need of plan.asset_needs) {
  if (!need.need_id || needIds.has(need.need_id)) throw new Error(`Duplicate or missing need_id: ${need.need_id}`);
  needIds.add(need.need_id);
  if (!validCategories.has(need.category)) throw new Error(`Unsupported category ${need.category}`);
  if (!need.description || !Array.isArray(need.tags) || need.tags.length < 3) throw new Error(`Asset need ${need.need_id} lacks descriptive metadata.`);
  if (need.generation) {
    if (!need.generation.asset_id || !need.generation.template) throw new Error(`Generation spec incomplete for ${need.need_id}`);
    if (!need.generation.description || !Array.isArray(need.generation.tags) || need.generation.tags.length < 3) throw new Error(`Generated asset metadata incomplete for ${need.need_id}`);
  }
}

const validTypes = new Set(registry.scene_types || []);
const validMotions = new Set(registry.motions || []);
let beats = 0;
for (const scene of plan.scenes) {
  if (!validTypes.has(scene.type)) throw new Error(`Unsupported scene type ${scene.type}`);
  if (!scene.environment || !scene.character) throw new Error(`Scene ${scene.id} must remain environment-led.`);
  if ((scene.caption || '').trim().split(/\s+/).length > 7) throw new Error(`Scene ${scene.id} caption is too long.`);
  if (!scene.narration) throw new Error(`Scene ${scene.id} narration missing.`);
  if (!Array.isArray(scene.visuals) || scene.visuals.length < 2) throw new Error(`Scene ${scene.id} needs at least 2 active visuals.`);
  if (!Array.isArray(scene.beats) || scene.beats.length < 4) throw new Error(`Scene ${scene.id} needs at least 4 beats.`);
  let prev = -1;
  for (const beat of scene.beats) {
    if (!(beat.at_pct >= 0 && beat.at_pct < 1)) throw new Error(`Invalid beat percentage in ${scene.id}`);
    if (beat.at_pct < prev) throw new Error(`Beat order invalid in ${scene.id}`);
    if (!validMotions.has(beat.motion)) throw new Error(`Unsupported motion ${beat.motion}`);
    if (!beat.target) throw new Error(`Beat target missing in ${scene.id}`);
    prev = beat.at_pct;
    beats += 1;
  }
}
if (beats < 20) throw new Error(`Phase 7 requires at least 20 visual beats; got ${beats}.`);
if (!design.forbidden?.some((x) => /PowerPoint/i.test(x))) throw new Error('Design system must explicitly forbid PowerPoint-style layouts.');
console.log(`Phase 7 source plan valid: ${plan.scenes.length} scenes, ${plan.asset_needs.length} asset needs, ${beats} beats.`);
