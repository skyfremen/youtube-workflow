import fs from 'node:fs';
import path from 'node:path';

const planPath = process.argv[2] || 'content/phase7-plan.json';
const registryPath = process.argv[3] || 'assets/registry.json';
const resolvedPlanPath = process.argv[4] || 'content/phase7-resolved-plan.json';
const runtimeRegistryPath = process.argv[5] || 'assets/registry.runtime.json';

const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
const threshold = plan.planner?.asset_match_threshold ?? 0.55;
const styleId = plan.planner?.design_system || 'wacky_insights_v2';
if (styleId !== 'wacky_insights_v2') throw new Error(`Unsupported design system: ${styleId}`);

fs.mkdirSync('output', {recursive:true});
fs.mkdirSync(path.dirname(resolvedPlanPath), {recursive:true});
fs.mkdirSync(path.dirname(runtimeRegistryPath), {recursive:true});

const normalize = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
const tokens = (value) => new Set(normalize(Array.isArray(value) ? value.join(' ') : value).split(/\s+/).filter(Boolean));
const score = (need, assetId, asset) => {
  if (asset.style_id !== styleId) return 0;
  const a = tokens([assetId, asset.description || '', ...(asset.tags || [])]);
  const n = tokens([need.description || '', ...(need.tags || [])]);
  let hits = 0;
  for (const t of n) if (a.has(t)) hits += 1;
  const lexical = n.size ? hits / n.size : 0;
  return Math.min(1, lexical + (asset.reusable === true ? 0.04 : 0) + 0.08);
};

const svg = (body, w=1920, h=1080) => `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><defs><filter id="s"><feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="#24324A" flood-opacity=".16"/></filter><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#F8FAFD"/><stop offset="1" stop-color="#E7EDF5"/></linearGradient></defs>${body}</svg>`;

const character = () => svg(`<ellipse cx="960" cy="980" rx="230" ry="40" fill="#263448" opacity=".15"/><g filter="url(#s)"><circle cx="960" cy="285" r="140" fill="#F2C7A5"/><path d="M825 280c10-150 285-170 300 20-70-70-205-65-300-20z" fill="#263448"/><circle cx="910" cy="300" r="12" fill="#263448"/><circle cx="1010" cy="300" r="12" fill="#263448"/><path d="M905 360q55 48 110 0" fill="none" stroke="#9B5A4A" stroke-width="10" stroke-linecap="round"/><rect x="790" y="430" width="340" height="370" rx="95" fill="#5D7CFF"/><path d="M825 500L650 700M1095 500l175 200" stroke="#F2C7A5" stroke-width="70" stroke-linecap="round"/><path d="M875 790l-70 170M1045 790l70 170" stroke="#263448" stroke-width="82" stroke-linecap="round"/></g>`);

const environment = (gen, need) => {
  const d = normalize(`${gen.asset_id} ${need.description} ${(need.tags||[]).join(' ')}`);
  if (d.includes('living room')) return svg(`<rect width="1920" height="1080" fill="url(#bg)"/><rect y="760" width="1920" height="320" fill="#D6DEE8"/><rect x="150" y="430" width="720" height="300" rx="52" fill="#9FB2C8" filter="url(#s)"/><rect x="220" y="375" width="280" height="150" rx="42" fill="#AEBFD2"/><rect x="530" y="375" width="280" height="150" rx="42" fill="#AEBFD2"/><rect x="980" y="570" width="330" height="120" rx="26" fill="#C08E65"/><rect x="1450" y="170" width="320" height="590" rx="16" fill="#EEF2F7" stroke="#B9C5D2" stroke-width="7"/><rect x="1510" y="220" width="205" height="500" fill="#D8E2EE"/><circle cx="1680" cy="470" r="11" fill="#65758B"/>`);
  if (d.includes('kitchen')) return svg(`<rect width="1920" height="1080" fill="url(#bg)"/><rect y="760" width="1920" height="320" fill="#D8E0EA"/><rect x="120" y="180" width="520" height="520" rx="28" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="5"/><rect x="170" y="245" width="420" height="210" rx="20" fill="#EAF0F6"/><rect x="720" y="470" width="1000" height="58" rx="18" fill="#7B8797"/><rect x="720" y="528" width="1000" height="230" fill="#F7F9FC" stroke="#CBD5E1" stroke-width="5"/><rect x="1430" y="170" width="290" height="540" rx="28" fill="#E7EDF4" stroke="#B9C5D2" stroke-width="5"/><rect x="1480" y="225" width="190" height="150" rx="20" fill="#C8D4E1"/>`);
  if (d.includes('control room') || d.includes('memory')) return svg(`<rect width="1920" height="1080" fill="#172033"/><rect y="790" width="1920" height="290" fill="#222E45"/><rect x="110" y="130" width="500" height="280" rx="30" fill="#243452" stroke="#4C6FFF" stroke-width="5"/><rect x="150" y="180" width="420" height="170" rx="18" fill="#10192A"/><path d="M190 300 C280 210 340 330 430 235 S540 270 555 205" fill="none" stroke="#62D2A2" stroke-width="10"/><rect x="690" y="120" width="540" height="310" rx="30" fill="#243452" stroke="#8EA7FF" stroke-width="5"/><g fill="#314768"><rect x="740" y="180" width="130" height="180" rx="18"/><rect x="900" y="180" width="130" height="180" rx="18"/><rect x="1060" y="180" width="120" height="180" rx="18"/></g><rect x="1310" y="140" width="480" height="590" rx="30" fill="#243452" stroke="#526987" stroke-width="5"/>`);
  return svg(`<rect width="1920" height="1080" fill="url(#bg)"/><rect y="760" width="1920" height="320" fill="#D7E0EA"/><rect x="180" y="180" width="620" height="520" rx="32" fill="#FFFFFF" stroke="#C8D2DE" stroke-width="5"/><rect x="880" y="220" width="760" height="420" rx="32" fill="#EEF3F8" stroke="#C8D2DE" stroke-width="5"/>`);
};

const prop = (gen, need) => {
  const isMission = /mission|note|goal|task/i.test(`${gen.asset_id} ${need.description}`);
  const label = isMission ? 'GET CHARGER' : 'TASK';
  return svg(`<g filter="url(#s)"><rect x="300" y="180" width="1320" height="720" rx="70" fill="#FFF4A8" stroke="#D7B53A" stroke-width="10"/><rect x="410" y="315" width="1100" height="180" rx="35" fill="#FFFFFF" opacity=".78"/><text x="960" y="435" text-anchor="middle" font-family="Arial" font-size="92" font-weight="800" fill="#263448">${label}</text><circle cx="760" cy="625" r="28" fill="#263448"/><circle cx="1160" cy="625" r="28" fill="#263448"/><path d="M790 720q170 100 340 0" fill="none" stroke="#263448" stroke-width="18" stroke-linecap="round"/></g>`);
};

const infographic = () => svg(`<g filter="url(#s)"><rect x="160" y="220" width="620" height="520" rx="70" fill="#E9F0FF" stroke="#5D7CFF" stroke-width="10"/><rect x="1140" y="220" width="620" height="520" rx="70" fill="#EAF8F2" stroke="#42A87A" stroke-width="10"/><text x="470" y="330" text-anchor="middle" font-family="Arial" font-size="54" font-weight="800" fill="#334155">EVENT A</text><text x="1450" y="330" text-anchor="middle" font-family="Arial" font-size="54" font-weight="800" fill="#334155">EVENT B</text><circle cx="470" cy="505" r="95" fill="#5D7CFF" opacity=".82"/><circle cx="1450" cy="505" r="95" fill="#42A87A" opacity=".82"/><path d="M800 500h290" stroke="#F0A33A" stroke-width="24" stroke-linecap="round"/><path d="M1060 455l80 45-80 45" fill="none" stroke="#F0A33A" stroke-width="24" stroke-linecap="round" stroke-linejoin="round"/></g>`);

const templates = {
  professional_vector_character: character,
  professional_vector_environment: environment,
  professional_vector_prop: prop,
  professional_vector_infographic_overlay: infographic,
  professional_vector_infographic: infographic
};

const categoryMap = {character:'characters', environment:'environments', prop:'props', infographic:'infographics'};
const resolved = {};
const created = [];

for (const need of plan.asset_needs || []) {
  const bucketName = categoryMap[need.category];
  if (!bucketName) throw new Error(`Unsupported asset category ${need.category}`);
  registry[bucketName] ||= {};

  let best = null;
  for (const [id, asset] of Object.entries(registry[bucketName])) {
    const s = score(need, id, asset);
    if (!best || s > best.score) best = {id, asset, score:s};
  }
  if (best && best.score >= threshold) {
    resolved[need.need_id] = best.id;
    console.log(`REUSE ${need.need_id} -> ${best.id} score=${best.score.toFixed(2)}`);
    continue;
  }

  const gen = need.generation;
  if (!gen) throw new Error(`No strong match for ${need.need_id} and no generation spec supplied.`);
  const template = templates[gen.template];
  if (!template) throw new Error(`No approved professional SVG template for ${gen.template}`);
  if (gen.style_id && gen.style_id !== styleId) throw new Error(`Generated asset ${gen.asset_id} must use ${styleId}.`);

  const id = gen.asset_id;
  const rel = `assets/generated/${id}.svg`;
  const abs = path.join('public', rel);
  fs.mkdirSync(path.dirname(abs), {recursive:true});
  fs.writeFileSync(abs, template(gen, need));
  registry[bucketName][id] = {
    file: rel,
    description: gen.description,
    tags: gen.tags,
    style_id: styleId,
    quality: 'production',
    reusable: gen.reusable !== false,
    generated_by: 'phase7_asset_intelligence',
    generated_from_need: need.need_id
  };
  resolved[need.need_id] = id;
  created.push({id, category:need.category, file:rel, description:gen.description});
  console.log(`GENERATE ${need.need_id} -> ${id} (${rel})`);
}

const replaceRefs = (value) => {
  if (typeof value === 'string' && value.startsWith('$')) {
    const key = value.slice(1);
    if (!resolved[key]) throw new Error(`Unresolved asset placeholder ${value}`);
    return resolved[key];
  }
  if (Array.isArray(value)) return value.map(replaceRefs);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k,v]) => [k, replaceRefs(v)]));
  return value;
};

const resolvedPlan = replaceRefs({...plan, asset_resolution:{threshold, resolved, created}});
fs.writeFileSync(resolvedPlanPath, JSON.stringify(resolvedPlan, null, 2) + '\n');
fs.writeFileSync(runtimeRegistryPath, JSON.stringify(registry, null, 2) + '\n');
fs.writeFileSync('output/phase7-asset-resolution.json', JSON.stringify({threshold, resolved, created}, null, 2) + '\n');
console.log(`Asset resolution complete: ${Object.keys(resolved).length} needs, ${created.length} new assets.`);
