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
const publicRoot = 'public';

fs.mkdirSync('output', { recursive: true });
fs.mkdirSync(path.dirname(resolvedPlanPath), { recursive: true });
fs.mkdirSync(path.dirname(runtimeRegistryPath), { recursive: true });

const esc = (s) => String(s || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
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

const svgShell = (body, width = 1920, height = 1080) => `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
<defs>
  <filter id="shadow"><feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="#24324A" flood-opacity=".16"/></filter>
  <linearGradient id="soft" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#F8FAFD"/><stop offset="1" stop-color="#E8EEF6"/></linearGradient>
</defs>
${body}
</svg>`;

const environmentSvg = (gen, need) => {
  const id = gen.asset_id || need.need_id;
  const desc = normalize(`${id} ${need.description}`);
  if (desc.includes('kitchen')) {
    return svgShell(`<rect width="1920" height="1080" fill="url(#soft)"/><rect y="760" width="1920" height="320" fill="#D8E0EA"/><rect x="120" y="180" width="520" height="520" rx="28" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="5"/><rect x="170" y="245" width="420" height="210" rx="20" fill="#EAF0F6"/><rect x="720" y="470" width="1000" height="58" rx="18" fill="#7B8797"/><rect x="720" y="528" width="1000" height="230" fill="#F7F9FC" stroke="#CBD5E1" stroke-width="5"/><rect x="1430" y="170" width="290" height="540" rx="28" fill="#E7EDF4" stroke="#B9C5D2" stroke-width="5"/><rect x="1480" y="225" width="190" height="150" rx="20" fill="#C8D4E1"/><circle cx="1660" cy="455" r="10" fill="#6E7B8D"/><rect x="900" y="400" width="130" height="36" rx="18" fill="#F5C451"/><rect x="1060" y="400" width="120" height="36" rx="18" fill="#5D7CFF"/><text x="120" y="105" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700" fill="#475467">WACKY INSIGHTS • KITCHEN</text>`);
  }
  if (desc.includes('living room')) {
    return svgShell(`<rect width="1920" height="1080" fill="#F5F7FB"/><rect y="760" width="1920" height="320" fill="#D6DEE8"/><rect x="150" y="430" width="720" height="300" rx="52" fill="#9FB2C8" filter="url(#shadow)"/><rect x="220" y="375" width="280" height="150" rx="42" fill="#AEBFD2"/><rect x="530" y="375" width="280" height="150" rx="42" fill="#AEBFD2"/><rect x="980" y="570" width="330" height="120" rx="26" fill="#C08E65"/><rect x="1050" y="520" width="190" height="50" rx="14" fill="#263448"/><rect x="1450" y="170" width="320" height="590" rx="16" fill="#EEF2F7" stroke="#B9C5D2" stroke-width="7"/><rect x="1510" y="220" width="205" height="500" fill="#D8E2EE"/><circle cx="1680" cy="470" r="11" fill="#65758B"/><rect x="1020" y="250" width="250" height="180" rx="24" fill="#FFFFFF" stroke="#CCD6E2" stroke-width="5"/><text x="120" y="105" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700" fill="#475467">WACKY INSIGHTS • LIVING ROOM</text>`);
  }
  if (desc.includes('control room') || desc.includes('memory')) {
    return svgShell(`<rect width="1920" height="1080" fill="#172033"/><rect y="790" width="1920" height="290" fill="#222E45"/><rect x="110" y="130" width="500" height="280" rx="30" fill="#243452" stroke="#4C6FFF" stroke-width="5"/><rect x="150" y="180" width="420" height="170" rx="18" fill="#10192A"/><path d="M190 300 C280 210 340 330 430 235 S540 270 555 205" fill="none" stroke="#62D2A2" stroke-width="10"/><rect x="690" y="120" width="540" height="310" rx="30" fill="#243452" stroke="#8EA7FF" stroke-width="5"/><g fill="#314768"><rect x="740" y="180" width="130" height="180" rx="18"/><rect x="900" y="180" width="130" height="180" rx="18"/><rect x="1060" y="180" width="120" height="180" rx="18"/></g><circle cx="805" cy="265" r="34" fill="#F5C451"/><circle cx="965" cy="265" r="34" fill="#62D2A2"/><circle cx="1120" cy="265" r="34" fill="#F06A5A"/><rect x="1310" y="140" width="480" height="590" rx="30" fill="#243452" stroke="#526987" stroke-width="5"/><g fill="#344B6C"><rect x="1360" y="205" width="380" height="55" rx="16"/><rect x="1360" y="285" width="380" height="55" rx="16"/><rect x="1360" y="365" width="380" height="55" rx="16"/><rect x="1360" y="445" width="380" height="55" rx="16"/><rect x="1360" y="525" width="380" height="55" rx="16"/></g><rect x="350" y="610" width="820" height="120" rx="32" fill="#2A3A58"/><circle cx="450" cy="670" r="22" fill="#62D2A2"/><circle cx="520" cy="670" r="22" fill="#F5C451"/><circle cx="590" cy="670" r="22" fill="#F06A5A"/><text x="120" y="85" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700" fill="#DCE6F5">WACKY INSIGHTS • MEMORY CONTROL ROOM</text>`);
  }
  return svgShell(`<rect width="1920" height="1080" fill="url(#soft)"/><rect y="760" width="1920" height="320" fill="#D7E0EA"/><rect x="180" y="180" width="620" height="520" rx="32" fill="#FFFFFF" stroke="#C8D2DE" stroke-width="5"/><rect x="880" y="220" width="760" height="420" rx="32" fill="#EEF3F8" stroke="#C8D2DE" stroke-width="5"/><text x="120" y="105" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700" fill="#475467">${esc(gen.asset_id || need.need_id).toUpperCase()}</text>`);
};

const characterSvg = () => svgShell(`<g filter="url(#shadow)"><ellipse cx="960" cy="990" rx="240" ry="42" fill="#263448" opacity=".16"/><circle cx="960" cy="300" r="145" fill="#F2C7A5"/><path d="M825 285c5-125 265-175 290 10-68-70-200-58-290-10z" fill="#263448"/><circle cx="910" cy="305" r="12" fill="#263448"/><circle cx="1010" cy="305" r="12" fill="#263448"/><path d="M905 365q55 48 110 0" fill="none" stroke="#9B5A4A" stroke-width="10" stroke-linecap="round"/><rect x="790" y="445" width="340" height="365" rx="95" fill="#5D7CFF"/><path d="M820 510L650 705" stroke="#F2C7A5" stroke-width="72" stroke-linecap="round"/><path d="M1100 510l170 195" stroke="#F2C7A5" stroke-width="72" stroke-linecap="round"/><path d="M875 800l-70 165" stroke="#263448" stroke-width="82" stroke-linecap="round"/><path d="M1045 800l70 165" stroke="#263448" stroke-width="82" stroke-linecap="round"/></g>`, 1600, 1080);

const propSvg = (gen, need) => {
  const text = /mission|note|goal|task/i.test(`${gen.asset_id} ${need.description}`) ? 'GET CHARGER' : 'TASK';
  return svgShell(`<g filter="url(#shadow)"><rect x="300" y="180" width="1320" height="720" rx="70" fill="#FFF4A8" stroke="#D7B53A" stroke-width="10"/><rect x="410" y="315" width="1100" height="180" rx="35" fill="#FFFFFF" opacity=".78"/><text x="960" y="435" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="92" font-weight="800" fill="#263448">${text}</text><circle cx="760" cy="625" r="28" fill="#263448"/><circle cx="1160" cy="625" r="28" fill="#263448"/><path d="M790 720q170 100 340 0" fill="none" stroke="#263448" stroke-width="18" stroke-linecap="round"/><path d="M300 400L180 310" stroke="#D7B53A" stroke-width="40" stroke-linecap="round"/><path d="M1620 400l120-90" stroke="#D7B53A" stroke-width="40" stroke-linecap="round"/></g>`);
};

const infographicSvg = () => svgShell(`<g filter="url(#shadow)"><rect x="160" y="220" width="620" height="520" rx="70" fill="#E9F0FF" stroke="#5D7CFF" stroke-width="10"/><rect x="1140" y="220" width="620" height="520" rx="70" fill="#EAF8F2" stroke="#42A87A" stroke-width="10"/><text x="470" y="330" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="54" font-weight="800" fill="#334155">EVENT A</text><text x="1450" y="330" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="54" font-weight="800" fill="#334155">EVENT B</text><circle cx="470" cy="505" r="95" fill="#5D7CFF" opacity=".82"/><circle cx="1450" cy="505" r="95" fill="#42A87A" opacity=".82"/><path d="M800 500h290" stroke="#F0A33A" stroke-width="24" stroke-linecap="round"/><path d="M1060 455l80 45-80 45" fill="none" stroke="#F0A33A" stroke-width="24" stroke-linecap="round" stroke-linejoin="round"/><rect x="900" y="190" width="120" height="620" rx="40" fill="#F0A33A" opacity=".18"/><text x="960" y="875" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="46" font-weight="700" fill="#475467">CONTEXT CHANGE • EVENT BOUNDARY</text></g>`);

const templates = {
  professional_vector_character: characterSvg,
  professional_vector_environment: environmentSvg,
  professional_vector_prop: propSvg,
  professional_vector_infographic_overlay: infographicSvg,
  professional_vector_infographic: infographicSvg,
  laundry_room: environmentSvg,
  washing_machine: propSvg,
  laundry_basket: propSvg,
  socks: propSvg
};

const categoryMap = { character: 'characters', environment: 'environments', prop: 'props', infographic: 'infographics' };
const resolved = {};
const created = [];

for (const need of plan.asset_needs || []) {
  const bucketName = categoryMap[need.category];
  if (!bucketName) throw new Error(`Unsupported asset category ${need.category}`);
  registry[bucketName] ||= {};

  let best = null;
  for (const [id, asset] of Object.entries(registry[bucketName])) {
    const s = score(need, id, asset);
    if (!best || s > best.score) best = { id, asset, score: s };
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
  if (gen.style_id && gen.style_id !== styleId) throw new Error(`Generated asset ${gen.asset_id} style mismatch: ${gen.style_id}`);

  const id = gen.asset_id;
  const rel = `assets/generated/${id}.svg`;
  const abs = path.join(publicRoot, rel);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, template(gen, need));

  const asset = {
    file: rel,
    description: gen.description,
    tags: gen.tags,
    style_id: styleId,
    quality: 'production',
    reusable: gen.reusable !== false,
    generated_by: 'phase7_asset_intelligence',
    generated_from_need: need.need_id,
    actions: Array.isArray(gen.actions) ? gen.actions : []
  };

  registry[bucketName][id] = asset;
  resolved[need.need_id] = id;
  created.push({ id, category: need.category, file: rel, description: gen.description });
  console.log(`GENERATE ${need.need_id} -> ${id} (${rel})`);
}

const replaceRefs = (value) => {
  if (typeof value === 'string' && value.startsWith('$')) {
    const key = value.slice(1);
    if (!resolved[key]) throw new Error(`Unresolved asset placeholder ${value}`);
    return resolved[key];
  }
  if (Array.isArray(value)) return value.map(replaceRefs);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, replaceRefs(v)]));
  return value;
};

const resolvedPlan = replaceRefs({ ...plan, asset_resolution: { threshold, resolved, created } });
fs.writeFileSync(resolvedPlanPath, JSON.stringify(resolvedPlan, null, 2) + '\n');
fs.writeFileSync(runtimeRegistryPath, JSON.stringify(registry, null, 2) + '\n');
fs.writeFileSync('output/phase7-asset-resolution.json', JSON.stringify({ threshold, resolved, created }, null, 2) + '\n');
console.log(`Asset resolution complete: ${Object.keys(resolved).length} needs, ${created.length} new assets.`);
