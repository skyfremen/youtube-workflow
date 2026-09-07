import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Composition,
  interpolate,
  registerRoot,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import plan from '../content/demo-plan.json';

const FPS = 30;
const totalFrames = plan.duration_seconds * FPS;

const palette = {
  bg: '#F7F1E7', ink: '#202124', accent: '#E8563F', blue: '#3A78C2',
  green: '#4F9D69', yellow: '#F2C14E', fridge: '#DDE7EA', skin: '#F2C8A5', white: '#FFFFFF',
};

const clamp = (v, a=0, b=1) => Math.max(a, Math.min(b, v));
const sec = (frame) => frame / FPS;
const ease = (t) => 1 - Math.pow(1 - clamp(t), 3);

const Person = ({localFrame, mode='normal', x=0, scale=1}) => {
  const t = sec(localFrame);
  const walk = Math.sin(t * Math.PI * 5) * (mode === 'walk' ? 7 : 0);
  const blink = (Math.floor(t * 2.4) % 7 === 0 && (t * 10) % 1 < 0.18) ? 0.12 : 1;
  const look = mode === 'look' ? 10 : 0;
  const shocked = mode === 'shocked';
  const react = mode === 'react';
  const bodyTilt = react ? -5 : shocked ? 4 : 0;
  const armLift = react ? -55 : shocked ? -35 : 8;
  return <div style={{position:'relative', width:260, height:450, transform:`translateX(${x}px) translateY(${walk}px) scale(${scale}) rotate(${bodyTilt}deg)`, transformOrigin:'50% 85%'}}>
    <div style={{position:'absolute', left:76, top:18, width:108, height:108, borderRadius:'50%', background:palette.skin, border:`8px solid ${palette.ink}`}}>
      <div style={{position:'absolute', left:25 + look, top:39, width:13, height:13 * blink, borderRadius:'50%', background:palette.ink}} />
      <div style={{position:'absolute', left:65 + look, top:39, width:13, height:13 * blink, borderRadius:'50%', background:palette.ink}} />
      <div style={{position:'absolute', left:42, top:72, width:42, height: shocked ? 24 : 8, borderRadius:20, border: shocked ? `6px solid ${palette.ink}` : 'none', background: shocked ? palette.white : palette.ink}} />
    </div>
    <div style={{position:'absolute', left:38, top:130, width:184, height:190, borderRadius:36, background:palette.blue, border:`8px solid ${palette.ink}`}} />
    <div style={{position:'absolute', left:16, top:160, width:42, height:155, borderRadius:24, background:palette.skin, border:`7px solid ${palette.ink}`, transform:`rotate(${armLift}deg)`, transformOrigin:'50% 10%'}} />
    <div style={{position:'absolute', right:16, top:160, width:42, height:155, borderRadius:24, background:palette.skin, border:`7px solid ${palette.ink}`, transform:`rotate(${-armLift}deg)`, transformOrigin:'50% 10%'}} />
    <div style={{position:'absolute', left:57, bottom:0, width:46, height:135, borderRadius:20, background:palette.ink, transform:`rotate(${mode === 'walk' ? -walk : 0}deg)`}} />
    <div style={{position:'absolute', right:57, bottom:0, width:46, height:135, borderRadius:20, background:palette.ink, transform:`rotate(${mode === 'walk' ? walk : 0}deg)`}} />
  </div>;
};

const Fridge = ({localFrame, openAt=0.7, closeAt=99}) => {
  const t = sec(localFrame);
  const openP = ease((t - openAt) / 0.45);
  const closeP = ease((t - closeAt) / 0.4);
  const amount = clamp(openP - closeP);
  const doorScale = 1 - amount * 0.82;
  const glow = amount * 0.8;
  return <div style={{width:330, height:520, position:'relative'}}>
    <div style={{position:'absolute', inset:0, border:`10px solid ${palette.ink}`, borderRadius:28, background:'#BFCED3', overflow:'hidden', boxShadow:`0 0 ${50*glow}px rgba(242,193,78,${glow})`}}>
      <div style={{position:'absolute', left:28, top:55, width:260, height:350, border:`7px solid ${palette.ink}`, borderRadius:20, background:'#FFF9E9'}}>
        <div style={{position:'absolute', left:25, right:25, top:110, height:7, background:palette.ink, opacity:.35}} />
        <div style={{position:'absolute', left:25, right:25, top:220, height:7, background:palette.ink, opacity:.35}} />
        <div style={{position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', fontWeight:1000, fontSize:34, opacity:amount}}>EMPTY</div>
      </div>
    </div>
    <div style={{position:'absolute', inset:0, transform:`scaleX(${doorScale})`, transformOrigin:'0% 50%', border:`10px solid ${palette.ink}`, borderRadius:28, background:palette.fridge, boxSizing:'border-box'}}>
      <div style={{position:'absolute', top:190, left:0, right:0, height:10, background:palette.ink}} />
      <div style={{position:'absolute', top:75, right:38, width:18, height:95, borderRadius:10, background:palette.ink}} />
      <div style={{position:'absolute', top:285, right:38, width:18, height:95, borderRadius:10, background:palette.ink}} />
    </div>
  </div>;
};

const PopBadge = ({text, progress, y=0}) => {
  const s = 0.65 + 0.35 * spring({fps:FPS, frame:Math.max(0, progress * 18), config:{damping:10, stiffness:180}});
  return <div style={{padding:'22px 34px', border:`7px solid ${palette.ink}`, borderRadius:24, background:palette.yellow, fontSize:40, fontWeight:1000, transform:`translateY(${y}px) scale(${s}) rotate(-2deg)`, opacity:clamp(progress*5), boxShadow:'10px 10px 0 #202124'}}> {text} </div>;
};

const SceneOne = ({f}) => {
  const t = sec(f);
  const enter = ease(t / 0.7);
  const badgeP = (t - 2.2) / 0.35;
  const clockP = clamp((t - 4.1) / 0.25);
  return <div style={{position:'relative', width:1500, height:650, display:'flex', alignItems:'center', justifyContent:'center', gap:150}}>
    <Person localFrame={f} mode={t < .9 ? 'walk' : t > 1.45 && t < 3.2 ? 'look' : 'normal'} x={-520*(1-enter)} />
    <Fridge localFrame={f} openAt={0.7} closeAt={3.4} />
    {t >= 2.2 && <div style={{position:'absolute', top:70, right:170}}><PopBadge text="STILL NOTHING" progress={badgeP}/></div>}
    {t >= 4.1 && <div style={{position:'absolute', top:30, left:610, fontSize:74, fontWeight:1000, transform:`scale(${.6+.4*clockP}) rotate(${(1-clockP)*-12}deg)`, opacity:clockP}}>⏱ +5 MIN</div>}
  </div>;
};

const DiagramNode = ({label, active, x}) => <div style={{position:'absolute', left:x, top:230, width:260, height:140, border:`8px solid ${palette.ink}`, borderRadius:28, background:active?palette.yellow:palette.white, display:'flex', alignItems:'center', justifyContent:'center', fontSize:42, fontWeight:1000, transform:`scale(${active?1.08:1})`, boxShadow:active?'10px 10px 0 #202124':'none'}}>{label}</div>;

const SceneTwo = ({f}) => {
  const t = sec(f);
  const pan = interpolate(f, [0, 150], [80, -70], {extrapolateLeft:'clamp', extrapolateRight:'clamp'});
  const punch = t > 3.5 ? 1 + 0.12*Math.sin(Math.min((t-3.5)*Math.PI, Math.PI)) : 1;
  return <div style={{position:'relative', width:1500, height:650, transform:`translateX(${pan}px) scale(${punch})`}}>
    <DiagramNode label="BORED" active={t>=.8} x={120}/>
    <div style={{position:'absolute', left:410, top:270, fontSize:70, fontWeight:1000}}>→</div>
    <DiagramNode label="CHECK" active={t>=1.7} x={520}/>
    <div style={{position:'absolute', left:810, top:270, fontSize:70, fontWeight:1000}}>→</div>
    <DiagramNode label="REWARD?" active={t>=2.6} x={920}/>
    <div style={{position:'absolute', right:20, bottom:0}}><Person localFrame={f} mode={t>=4.2?'react':'normal'} scale={0.62}/></div>
  </div>;
};

const SceneThree = ({f}) => {
  const t = sec(f);
  const returnP = ease(t / .7);
  const shake = t>=3.6 && t<4.15 ? Math.sin((t-3.6)*55)*16 : 0;
  const badgeP = (t - 2.6) / .3;
  const endP = clamp((t - 4.3)/.3);
  return <div style={{position:'relative', width:1500, height:650, display:'flex', alignItems:'center', justifyContent:'center', gap:140, transform:`translateX(${shake}px)`}}>
    <Person localFrame={f} mode={t<.8?'walk':t>=1.8?'shocked':'look'} x={-460*(1-returnP)} />
    <Fridge localFrame={f} openAt={.8} />
    {t>=2.6 && <div style={{position:'absolute', top:65, right:120}}><PopBadge text="NO UPDATE AVAILABLE" progress={badgeP}/></div>}
    {t>=4.3 && <div style={{position:'absolute', left:0, right:0, bottom:20, textAlign:'center', fontSize:70, fontWeight:1000, color:palette.accent, transform:`scale(${.75+.25*endP})`, opacity:endP}}>CHECK AGAIN LATER</div>}
  </div>;
};

const SceneVisual = ({scene, localFrame}) => {
  if (scene.id === 1) return <SceneOne f={localFrame}/>;
  if (scene.id === 2) return <SceneTwo f={localFrame}/>;
  return <SceneThree f={localFrame}/>;
};

const Video = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  let start = 0;
  let active = plan.scenes[0];
  let localFrame = frame;
  for (const scene of plan.scenes) {
    const frames = scene.duration * fps;
    if (frame >= start && frame < start + frames) {
      active = scene;
      localFrame = frame - start;
      break;
    }
    start += frames;
  }

  const sceneFrames = active.duration * fps;
  const intro = spring({fps, frame:localFrame, config:{damping:14, stiffness:150}});
  const out = interpolate(localFrame, [sceneFrames-8, sceneFrames], [1,0], {extrapolateLeft:'clamp', extrapolateRight:'clamp'});
  const captionScale = .92 + .08*intro;
  const sceneNo = String(active.id).padStart(2, '0');

  return <AbsoluteFill style={{background:palette.bg, color:palette.ink, fontFamily:'Arial, Helvetica, sans-serif', overflow:'hidden'}}>
    <Audio src={staticFile('narration.wav')} volume={0.96}/>
    <div style={{position:'absolute', top:42, left:62, fontSize:28, fontWeight:1000, letterSpacing:3}}>WACKY INSIGHTS • ANIMATION MVP 2</div>
    <div style={{position:'absolute', top:42, right:62, fontSize:28, fontWeight:900}}>SCENE {sceneNo}</div>
    <div style={{position:'absolute', top:125, left:80, right:80, textAlign:'center', fontSize:68, lineHeight:1.05, fontWeight:1000, transform:`scale(${captionScale})`, opacity:out}}>{active.caption}</div>
    <div style={{position:'absolute', top:300, left:0, right:0, display:'flex', justifyContent:'center', opacity:out}}>
      <SceneVisual scene={active} localFrame={localFrame}/>
    </div>
    <div style={{position:'absolute', left:100, right:100, bottom:48, height:12, borderRadius:20, background:'#D7D2C8'}}>
      <div style={{height:'100%', width:`${Math.min(100, frame / totalFrames * 100)}%`, borderRadius:20, background:palette.accent}} />
    </div>
  </AbsoluteFill>;
};

const Root = () => <Composition id="WackyLongformTest" component={Video} durationInFrames={totalFrames} fps={FPS} width={1920} height={1080}/>;

registerRoot(Root);
