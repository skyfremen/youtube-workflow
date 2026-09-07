import fs from 'node:fs';

const planPath = process.argv[2] || 'content/phase7-plan.json';
const registryPath = process.argv[3] || 'assets/registry.json';
const designPath = process.argv[4] || 'assets/design-system.json';
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
const design = JSON.parse(fs.readFileSync(designPath, 'utf8'));

if (design.id !== 'wacky_insights_v2') throw new Error(`Expected active design system wacky_insights_v2; got ${design.id}`);
if (plan.style_id !== design.id) throw new Error(`Plan style_id must equal ${design.id}.`);
if (plan.planner?.generated_by !== 'ChatGPT') throw new Error('Phase 7 plan must identify ChatGPT as planner.');
if (plan.planner?.design_system !== design.id) throw new Error('Plan design system does not match design-system.json.');
if (!plan.planner?.require_professional_assets) throw new Error('Professional asset quality must be mandatory.');
if (!plan.channel_personality?.educational || !plan.channel_personality?.humorous) throw new Error('Plan must explicitly require educational value plus humour.');
if (!plan.learning_promise || !plan.central_question) throw new Error('Plan must include learning_promise and central_question.');
if (!Array.isArray(plan.educational_points) || plan.educational_points.length < 2) throw new Error('Plan must teach at least 2 meaningful educational points.');
if (!plan.humour_strategy?.final_payoff) throw new Error('Plan must include a humour strategy and final payoff.');
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
    if (need.generation.style_id && need.generation.style_id !== design.id) throw new Error(`Generated asset ${need.generation.asset_id} must use ${design.id}.`);
  }
}

const validTypes = new Set(registry.scene_types || []);
const validMotions = new Set(registry.motions || []);
const validFramings = new Set(registry.shot_framings || []);
const validAngles = new Set(registry.camera_angles || []);
const validTransitions = new Set(registry.transition_types || []);
const minSameEnvDiffs = design.scene_transition_rules?.same_environment_new_scene_minimum_differences ?? 2;
let beats = 0;

const shotDiffCount = (a, b) => {
  if (!a || !b) return 0;
  return ['framing','camera_angle','focal_subject','subject_grouping','prop_state','action_emphasis','story_emphasis']
    .reduce((n, key) => n + ((a[key] ?? null) !== (b[key] ?? null) ? 1 : 0), 0);
};

for (let i = 0; i < plan.scenes.length; i++) {
  const scene = plan.scenes[i];
  if (!validTypes.has(scene.type)) throw new Error(`Unsupported scene type ${scene.type}`);
  if (!scene.environment || !scene.character) throw new Error(`Scene ${scene.id} must remain environment-led.`);
  if ((scene.caption || '').trim().split(/\s+/).length > 7) throw new Error(`Scene ${scene.id} caption is too long.`);
  if (!scene.narration) throw new Error(`Scene ${scene.id} narration missing.`);
  if (!Array.isArray(scene.visuals) || scene.visuals.length < 2) throw new Error(`Scene ${scene.id} needs at least 2 active visuals.`);
  if (!Array.isArray(scene.beats) || scene.beats.length < 4) throw new Error(`Scene ${scene.id} needs at least 4 beats.`);

  if (!scene.shot) throw new Error(`Scene ${scene.id} must include v2 shot metadata.`);
  if (!validFramings.has(scene.shot.framing)) throw new Error(`Scene ${scene.id} has unsupported framing ${scene.shot.framing}.`);
  if (!validAngles.has(scene.shot.camera_angle)) throw new Error(`Scene ${scene.id} has unsupported camera angle ${scene.shot.camera_angle}.`);
  if (!scene.shot.focal_subject) throw new Error(`Scene ${scene.id} must define shot.focal_subject.`);
  if (!validTransitions.has(scene.shot.transition_in)) throw new Error(`Scene ${scene.id} has unsupported transition ${scene.shot.transition_in}.`);

  if (i > 0) {
    const prev = plan.scenes[i - 1];
    const sameEnvironment = prev.environment === scene.environment;
    const sameFraming = prev.shot?.framing === scene.shot.framing;
    const sameAngle = prev.shot?.camera_angle === scene.shot.camera_angle;
    const sameFocus = prev.shot?.focal_subject === scene.shot.focal_subject;

    if (sameEnvironment && sameFraming && sameAngle && sameFocus) {
      throw new Error(`Blink-like cut risk: ${prev.id} -> ${scene.id} repeats environment, framing, angle and focus. Merge into one scene or strongly reframe.`);
    }

    if (sameEnvironment) {
      const differences = shotDiffCount(prev.shot, scene.shot);
      if (differences < minSameEnvDiffs) {
        throw new Error(`Same-environment transition ${prev.id} -> ${scene.id} changes only ${differences} shot dimension(s); v2 requires at least ${minSameEnvDiffs}.`);
      }
      if (scene.shot.transition_in === 'cut_to_distinct_environment') {
        throw new Error(`Scene ${scene.id} claims a distinct-environment cut but reuses the same environment as ${prev.id}.`);
      }
    }

    if (!sameEnvironment && scene.shot.transition_in === 'continuation') {
      throw new Error(`Scene ${scene.id} changes environment but is marked continuation.`);
    }
  }

  let prevPct = -1;
  for (const beat of scene.beats) {
    if (!(beat.at_pct >= 0 && beat.at_pct < 1)) throw new Error(`Invalid beat percentage in ${scene.id}`);
    if (beat.at_pct < prevPct) throw new Error(`Beat order invalid in ${scene.id}`);
    if (!validMotions.has(beat.motion)) throw new Error(`Unsupported motion ${beat.motion}`);
    if (!beat.target) throw new Error(`Beat target missing in ${scene.id}`);
    prevPct = beat.at_pct;
    beats += 1;
  }
}

if (beats < 20) throw new Error(`Phase 7 requires at least 20 visual beats; got ${beats}.`);
if (!design.forbidden?.some((x) => /PowerPoint/i.test(x))) throw new Error('Design system must explicitly forbid PowerPoint-style layouts.');
if (!design.forbidden?.some((x) => /identical shots|blink/i.test(x))) throw new Error('Design system must explicitly forbid blink-like or near-identical scene cuts.');

console.log(`Phase 7/v2 source plan valid: ${plan.scenes.length} scenes, ${plan.asset_needs.length} asset needs, ${beats} beats, transition rules enforced.`);
