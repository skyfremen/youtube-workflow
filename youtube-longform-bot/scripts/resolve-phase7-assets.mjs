import fs from 'node:fs';
import path from 'node:path';

const planPath = process.argv[2] || 'content/phase7-plan.json';
const registryPath = process.argv[3] || 'assets/registry.json';
const resolvedPlanPath = process.argv[4] || 'content/phase7-resolved-plan.json';
const runtimeRegistryPath = process.argv[5] || 'assets/registry.runtime.json';

const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
const threshold = plan.planner?.asset_match_threshold ?? 0.55;
const styleId = plan.planner?.design_system || 'wacky_insights_v1';
const publicRoot = 'public';
fs.mkdirSync('output', {recursive:true});
fs.mkdirSync(path.dirname(resolvedPlanPath), {recursive:true});
fs.mkdirSync(path.dirname(runtimeRegistryPath), {recursive:true});

const normalize = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
const tokens = (value) => new Set(normalize(Array.isArray(value) ? value.join(' ') : value).split(/\s+/).filter(Boolean));
const score = (need, assetId, asset) => {
  const a = tokens([assetId, asset.description || '', ...(asset.tags || [])]);
  const n = tokens([need.description || '', ...(need.tags || [])]);
  let hit = 0;
  for (const t of n) if (a.has(t)) hit += 1;
  const lexical = n.size ? hit / n.size : 0;
  const styleBonus = asset.style_id === styleId ? 0.08 : 0;
  const reusableBonus = asset.reusable === true ? 0.04 : 0;
  return Math.min(1, lexical + styleBonus + reusableBonus);
};

const templates = {
  laundry_room: () => `<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <defs>
    <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#F7F9FC"/><stop offset="1" stop-color="#E8EEF5"/></linearGradient>
    <linearGradient id="floor" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#D7DEE8"/><stop offset="1" stop-color="#BAC6D4"/></linearGradient>
    <filter id="shadow"><feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#314158" flood-opacity=".16"/></filter>
  </defs>
  <rect width="1920" height="1080" fill="url(#wall)"/>
  <rect y="760" width="1920" height="320" fill="url(#floor)"/>
  <rect x="0" y="742" width="1920" height="20" fill="#AEB9C7"/>
  <g filter="url(#shadow)">
    <rect x="90" y="150" width="520" height="205" rx="24" fill="#FFFFFF" stroke="#CED7E2" stroke-width="4"/>
    <rect x="120" y="185" width="220" height="135" rx="14" fill="#EEF3F8"/>
    <rect x="365" y="185" width="215" height="135" rx="14" fill="#F9FBFD"/>
    <circle cx="330" cy="252" r="6" fill="#7D8B9D"/><circle cx="376" cy="252" r="6" fill="#7D8B9D"/>
    <rect x="1260" y="140" width="500" height="250" rx="24" fill="#FFFFFF" stroke="#CED7E2" stroke-width="4"/>
    <rect x="1300" y="185" width="420" height="26" rx="13" fill="#DDE5EF"/>
    <rect x="1320" y="225" width="120" height="105" rx="14" fill="#EAF0FF"/>
    <rect x="1460" y="225" width="110" height="105" rx="14" fill="#FDEBE7"/>
    <rect x="1590" y="225" width="105" height="105" rx="14" fill="#E8F6EF"/>
  </g>
  <rect x="720" y="465" width="1040" height="45" rx="16" fill="#8E9BAC"/>
  <rect x="720" y="510" width="1040" height="250" fill="#F6F8FB" stroke="#CBD5E1" stroke-width="4"/>
  <rect x="760" y="550" width="300" height="170" rx="20" fill="#E7EDF5"/>
  <rect x="1090" y="550" width="300" height="170" rx="20" fill="#EDF3F8"/>
  <rect x="1420" y="550" width="300" height="170" rx="20" fill="#E7EDF5"/>
  <g opacity=".8"><rect x="790" y="420" width="110" height="25" rx="12" fill="#F7C948"/><rect x="920" y="420" width="125" height="25" rx="12" fill="#4F7CFF"/></g>
  <text x="120" y="95" font-family="Arial,Helvetica,sans-serif" font-size="24" font-weight="700" fill="#667085">WACKY INSIGHTS • HOME</text>
</svg>`,
  washing_machine: () => `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="650" viewBox="0 0 600 650">
  <defs><linearGradient id="body" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#FFFFFF"/><stop offset="1" stop-color="#DCE4ED"/></linearGradient><filter id="s"><feDropShadow dx="0" dy="16" stdDeviation="16" flood-color="#223047" flood-opacity=".2"/></filter></defs>
  <g filter="url(#s)"><rect x="55" y="30" width="490" height="575" rx="36" fill="url(#body)" stroke="#BAC5D1" stroke-width="5"/>
  <rect x="90" y="70" width="420" height="100" rx="22" fill="#EEF3F8"/><rect x="330" y="95" width="145" height="48" rx="12" fill="#172033"/>
  <circle cx="155" cy="120" r="28" fill="#D4DDE8" stroke="#8E9BAC" stroke-width="5"/><circle cx="270" cy="120" r="12" fill="#4F7CFF"/>
  <circle cx="300" cy="365" r="165" fill="#C9D3DE"/><circle cx="300" cy="365" r="132" fill="#1E2A3B"/><circle cx="300" cy="365" r="103" fill="#7CA4C6" opacity=".7"/><path d="M220 360c45-72 121-56 163 1-31 77-118 93-163-1z" fill="#DDEBFA" opacity=".75"/>
  <rect x="118" y="560" width="364" height="16" rx="8" fill="#AEB9C7"/></g>
</svg>`,
  laundry_basket: () => `<svg xmlns="http://www.w3.org/2000/svg" width="500" height="350" viewBox="0 0 500 350">
  <defs><filter id="s"><feDropShadow dx="0" dy="12" stdDeviation="12" flood-color="#223047" flood-opacity=".18"/></filter></defs>
  <g filter="url(#s)"><path d="M85 120h330l-42 190H127z" fill="#D7DEE8" stroke="#93A1B2" stroke-width="5"/><rect x="70" y="95" width="360" height="55" rx="28" fill="#B7C3D0"/>
  <path d="M130 108c10-57 77-78 121-25 37-46 111-28 121 25" fill="#F05A47" opacity=".85"/><path d="M155 112c20-48 67-52 98-15 29-31 80-28 98 15" fill="#4F7CFF" opacity=".85"/><path d="M215 108c11-36 54-43 77-12 20-20 58-18 70 12" fill="#22A06B" opacity=".8"/>
  <g stroke="#9AA8B7" stroke-width="5" opacity=".55"><path d="M155 168l-18 105M215 168l-8 112M285 168l8 112M345 168l18 105"/></g></g>
</svg>`,
  socks: () => `<svg xmlns="http://www.w3.org/2000/svg" width="420" height="250" viewBox="0 0 420 250">
  <defs><filter id="s"><feDropShadow dx="0" dy="10" stdDeviation="10" flood-color="#223047" flood-opacity=".18"/></filter></defs>
  <g filter="url(#s)"><g transform="translate(80 30) rotate(-12 80 95)"><path d="M30 0h95v102c0 28 18 37 50 55 24 14 19 53-11 60-38 9-96-19-123-50-15-18-11-42-11-68z" fill="#4F7CFF"/><rect x="30" width="95" height="28" rx="8" fill="#2E59C8"/><circle cx="80" cy="70" r="12" fill="#DCE6FF"/></g><g transform="translate(215 20) rotate(15 80 95)"><path d="M30 0h95v102c0 28 18 37 50 55 24 14 19 53-11 60-38 9-96-19-123-50-15-18-11-42-11-68z" fill="#F05A47"/><rect x="30" width="95" height="28" rx="8" fill="#C93E2E"/><path d="M55 60h45v16H55z" fill="#FFE3DD"/></g></g>
</svg>`
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
  if (!templates[gen.template]) throw new Error(`No approved professional SVG template for ${gen.template}`);
  const id = gen.asset_id;
  const rel = `assets/generated/${id}.svg`;
  const abs = path.join(publicRoot, rel);
  fs.mkdirSync(path.dirname(abs), {recursive:true});
  fs.writeFileSync(abs, templates[gen.template]());
  const asset = {
    file: rel,
    description: gen.description,
    tags: gen.tags,
    style_id: styleId,
    quality: 'production',
    reusable: gen.reusable !== false,
    generated_by: 'phase7_asset_intelligence',
    generated_from_need: need.need_id
  };
  registry[bucketName][id] = asset;
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

const resolvedPlan = replaceRefs({...plan, asset_resolution: {threshold, resolved, created}});
fs.writeFileSync(resolvedPlanPath, JSON.stringify(resolvedPlan, null, 2) + '\n');
fs.writeFileSync(runtimeRegistryPath, JSON.stringify(registry, null, 2) + '\n');
fs.writeFileSync('output/phase7-asset-resolution.json', JSON.stringify({threshold, resolved, created}, null, 2) + '\n');
console.log(`Asset resolution complete: ${Object.keys(resolved).length} needs, ${created.length} new assets.`);
