import React from 'react';
import {AbsoluteFill, Audio, Composition, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import plan from '../content/demo-plan.json';

const FPS = 30;
const totalFrames = plan.duration_seconds * FPS;

const palette = {
  bg: '#F5F1E8',
  ink: '#202124',
  accent: '#E8563F',
  blue: '#3A78C2',
  green: '#4F9D69',
  yellow: '#F2C14E',
};

const Person = ({mood='neutral'}) => (
  <div style={{position:'relative', width:250, height:430}}>
    <div style={{position:'absolute', left:75, top:20, width:100, height:100, borderRadius:'50%', background:'#F2C8A5', border:`8px solid ${palette.ink}`}} />
    <div style={{position:'absolute', left:35, top:125, width:180, height:190, borderRadius:35, background:palette.blue, border:`8px solid ${palette.ink}`}} />
    <div style={{position:'absolute', left:15, top:155, width:40, height:160, borderRadius:25, background:'#F2C8A5', border:`7px solid ${palette.ink}`, transform:'rotate(8deg)'}} />
    <div style={{position:'absolute', right:15, top:155, width:40, height:160, borderRadius:25, background:'#F2C8A5', border:`7px solid ${palette.ink}`, transform:'rotate(-8deg)'}} />
    <div style={{position:'absolute', left:55, bottom:0, width:45, height:130, borderRadius:20, background:palette.ink}} />
    <div style={{position:'absolute', right:55, bottom:0, width:45, height:130, borderRadius:20, background:palette.ink}} />
    <div style={{position:'absolute', left:99, top:60, width:12, height:12, borderRadius:'50%', background:palette.ink}} />
    <div style={{position:'absolute', left:140, top:60, width:12, height:12, borderRadius:'50%', background:palette.ink}} />
    <div style={{position:'absolute', left:105, top:84, width:42, height:8, borderRadius:10, background:palette.ink, transform:mood==='happy'?'rotate(0deg)':'rotate(180deg)'}} />
  </div>
);

const Fridge = () => (
  <div style={{width:280, height:500, border:`10px solid ${palette.ink}`, borderRadius:26, background:'#DDE7EA', position:'relative'}}>
    <div style={{position:'absolute', top:180, left:0, right:0, height:10, background:palette.ink}} />
    <div style={{position:'absolute', top:95, right:35, width:18, height:90, borderRadius:10, background:palette.ink}} />
    <div style={{position:'absolute', top:275, right:35, width:18, height:90, borderRadius:10, background:palette.ink}} />
  </div>
);

const SceneVisual = ({scene}) => {
  if (scene.type === 'diagram') {
    return <div style={{display:'flex', gap:35, alignItems:'center', fontSize:54, fontWeight:900}}><span>CUE</span><span>→</span><span>CHECK</span><span>→</span><span>REWARD?</span></div>;
  }
  if (scene.type === 'comparison') {
    return <div style={{display:'flex', gap:40}}>
      <div style={{padding:40, border:`8px solid ${palette.ink}`, borderRadius:30, background:'#fff', fontSize:48, fontWeight:800}}>HUNGER<br/><span style={{fontSize:34}}>gradual</span></div>
      <div style={{padding:40, border:`8px solid ${palette.ink}`, borderRadius:30, background:'#fff', fontSize:48, fontWeight:800}}>HABIT<br/><span style={{fontSize:34}}>sudden</span></div>
    </div>;
  }
  if (scene.type === 'end') {
    return <div style={{display:'flex', alignItems:'center', gap:90}}><Fridge/><Person mood="happy"/></div>;
  }
  return <div style={{display:'flex', alignItems:'center', gap:100}}><Person mood={scene.id===7?'happy':'neutral'}/><Fridge/></div>;
};

const Video = () => {
  const frame = useCurrentFrame();
  let start = 0;
  let active = plan.scenes[0];
  let localFrame = frame;
  for (const scene of plan.scenes) {
    const frames = scene.duration * FPS;
    if (frame >= start && frame < start + frames) {
      active = scene;
      localFrame = frame - start;
      break;
    }
    start += frames;
  }

  const opacity = interpolate(localFrame, [0, 10, Math.max(11, active.duration * FPS - 10), active.duration * FPS], [0, 1, 1, 0], {extrapolateLeft:'clamp', extrapolateRight:'clamp'});
  const lift = interpolate(localFrame, [0, 18], [35, 0], {extrapolateRight:'clamp'});
  const sceneNo = String(active.id).padStart(2, '0');

  return <AbsoluteFill style={{background:palette.bg, color:palette.ink, fontFamily:'Arial, Helvetica, sans-serif'}}>
    <Audio src={staticFile('narration.wav')} volume={0.95}/>
    <div style={{position:'absolute', top:55, left:70, fontSize:30, fontWeight:900, letterSpacing:3}}>WACKY INSIGHTS • TEST 01</div>
    <div style={{position:'absolute', top:52, right:70, fontSize:30, fontWeight:800}}>SCENE {sceneNo}</div>
    <div style={{position:'absolute', top:165, left:90, right:90, textAlign:'center', fontSize:72, lineHeight:1.05, fontWeight:950, transform:`translateY(${lift}px)`, opacity}}>{active.caption}</div>
    <div style={{position:'absolute', top:390, left:0, right:0, display:'flex', justifyContent:'center', alignItems:'center', opacity}}><SceneVisual scene={active}/></div>
    <div style={{position:'absolute', left:120, right:120, bottom:75, height:14, borderRadius:20, background:'#D7D2C8'}}>
      <div style={{height:'100%', width:`${Math.min(100, frame / totalFrames * 100)}%`, borderRadius:20, background:palette.accent}} />
    </div>
  </AbsoluteFill>;
};

const Root = () => <Composition id="WackyLongformTest" component={Video} durationInFrames={totalFrames} fps={FPS} width={1920} height={1080}/>;

registerRoot(Root);
