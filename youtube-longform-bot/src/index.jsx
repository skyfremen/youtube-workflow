import React from 'react';
import {AbsoluteFill, Audio, Composition, Img, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import plan from '../content/runtime-plan.json';
import registry from '../assets/registry.runtime.json';

const FPS = plan.fps || 24;
const totalFrames = Math.max(1, Math.round(plan.duration_seconds * FPS));
const C = {ink:'#1F2937',muted:'#667085',red:'#F05A47',blue:'#4F7CFF',green:'#22A06B',yellow:'#F7C948',white:'#FFFFFF',shadow:'rgba(30,45,70,.18)'};
const accent = {red:C.red,blue:C.blue,green:C.green,yellow:C.yellow};
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const ease=(v)=>1-Math.pow(1-clamp(v),3);

const Asset=({path,style,label='asset'})=>{
  if(!path) throw new Error(`Missing file path for ${label}`);
  return <Img src={staticFile(path)} style={style}/>;
};

const timeline=[];
let cursor=0;
for(const scene of plan.scenes){const frames=Math.max(1,Math.round(scene.duration*FPS));timeline.push({...scene,startFrame:cursor,endFrame:cursor+frames,frames});cursor+=frames;}

const beatFrame=(scene,target,fallback=.5)=>{
  const beat=(scene.beats||[]).find((b)=>b.target===target);
  return beat?Math.round(beat.at*FPS):Math.round(scene.frames*fallback);
};

const Caption=({scene,local})=>{
  const p=interpolate(local,[3,12,Math.max(13,scene.frames-15),Math.max(14,scene.frames-4)],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',left:88,bottom:78,fontSize:34,fontWeight:950,color:C.ink,opacity:p,textShadow:'0 2px 12px rgba(255,255,255,.95)',letterSpacing:.2}}>{scene.caption}</div>;
};

const Character=({id,local,x,y,scale=1,scene})=>{
  const a=registry.characters?.[id];
  if(!a) throw new Error(`Missing character registry entry: ${id}`);
  const start=beatFrame(scene,id,.05);
  const enter=ease((local-start)/16);
  const bob=Math.sin(local/5)*3;
  const sway=Math.sin(local/8)*1.4;
  const wrapperStyle={position:'absolute',left:x-180*(1-enter),top:y+bob,width:360,height:520,opacity:enter,transform:`scale(${scale}) rotate(${sway}deg)`,transformOrigin:'top left'};
  if(a.file){
    return <div style={wrapperStyle}><Asset path={a.file} label={`character ${id}`} style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'contain'}}/></div>;
  }
  if(a.body&&a.head){
    return <div style={wrapperStyle}>
      <Asset path={a.body} label={`character body ${id}`} style={{position:'absolute',inset:0,width:'100%',height:'100%'}}/>
      <Asset path={a.head} label={`character head ${id}`} style={{position:'absolute',left:72,top:10,width:220,height:220,transform:`rotate(${Math.sin(local/11)*2}deg)`,transformOrigin:'50% 75%'}}/>
    </div>;
  }
  throw new Error(`Character ${id} has no renderable file definition`);
};

const Prop=({id,local,x,y,scale=1,scene})=>{
  const a=registry.props?.[id];
  if(!a) throw new Error(`Missing prop registry entry: ${id}`);
  const start=beatFrame(scene,id,.35);
  const reveal=interpolate(local,[start,start+12],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const float=(scene.beats||[]).some((b)=>b.target===id&&b.motion==='float')?Math.sin((local-start)/5)*8:0;
  const pulse=(scene.beats||[]).some((b)=>b.target===id&&['highlight','punch_zoom','pop'].includes(b.motion))?1+.035*Math.max(0,Math.sin((local-start)/6)):1;
  const transform=`translateY(${(1-reveal)*18+float}px) scale(${scale*reveal*pulse})`;
  if(a.file) return <div style={{position:'absolute',left:x,top:y,width:600,height:600,opacity:reveal,transform,transformOrigin:'top left'}}><Asset path={a.file} label={`prop ${id}`} style={{width:'100%',height:'100%',objectFit:'contain'}}/></div>;
  if(a.base&&a.door) return <div style={{position:'absolute',left:x,top:y,width:360,height:620,opacity:reveal,transform,transformOrigin:'top left'}}><Asset path={a.base} label={`prop base ${id}`} style={{position:'absolute',inset:0,width:'100%',height:'100%'}}/><Asset path={a.door} label={`prop door ${id}`} style={{position:'absolute',inset:0,width:'100%',height:'100%'}}/></div>;
  throw new Error(`Prop ${id} has no renderable file definition`);
};

const Infographic=({id,local,x,y,scale=1,scene})=>{
  const a=registry.infographics?.[id];
  if(!a) throw new Error(`Missing infographic registry entry: ${id}`);
  const start=beatFrame(scene,id,.45);
  const reveal=interpolate(local,[start,start+10],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',left:x,top:y,width:700,height:500,opacity:reveal,transform:`translateY(${(1-reveal)*14}px) scale(${scale*reveal})`,transformOrigin:'top left'}}><Asset path={a.file} label={`infographic ${id}`} style={{width:'100%',height:'100%',objectFit:'contain'}}/></div>;
};

const Visual=({visual,scene,local})=>{
  if(registry.characters?.[visual.ref]) return <Character id={visual.ref} local={local} x={visual.x} y={visual.y} scale={visual.scale||1} scene={scene}/>;
  if(registry.props?.[visual.ref]) return <Prop id={visual.ref} local={local} x={visual.x} y={visual.y} scale={visual.scale||1} scene={scene}/>;
  if(registry.infographics?.[visual.ref]) return <Infographic id={visual.ref} local={local} x={visual.x} y={visual.y} scale={visual.scale||1} scene={scene}/>;
  throw new Error(`Visual ${visual.ref} has no registry entry`);
};

const Overlay=({item,scene,local})=>{
  const at=beatFrame(scene,item.id,.55);
  const p=interpolate(local,[at,at+10],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const pop=.82+.18*p;
  return <div style={{position:'absolute',left:item.x,top:item.y,padding:'10px 17px',borderRadius:999,background:'rgba(255,255,255,.95)',boxShadow:`0 10px 28px ${C.shadow}`,fontSize:27,fontWeight:900,color:C.ink,opacity:p,transform:`translateY(${(1-p)*18}px) scale(${pop})`,transformOrigin:'center',border:`3px solid ${accent[item.accent]||C.red}`,whiteSpace:'nowrap'}}>{item.text}</div>;
};

const Scene=({scene,local})=>{
  const env=registry.environments?.[scene.environment];
  if(!env) throw new Error(`Missing environment registry entry: ${scene.environment}`);
  if(!env.file) throw new Error(`Environment ${scene.environment} has no renderable file`);
  const push=interpolate(local,[0,scene.frames-1],[1.02,1.08],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const pan=(scene.type==='behavior_comparison'?interpolate(local,[0,scene.frames-1],[-18,18],{extrapolateLeft:'clamp',extrapolateRight:'clamp'}):0);
  return <div style={{position:'absolute',inset:0,transform:`translateX(${pan}px) scale(${push})`,transformOrigin:'center'}}>
    <Asset path={env.file} label={`environment ${scene.environment}`} style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover'}}/>
    <div style={{position:'absolute',inset:0,background:'linear-gradient(180deg,rgba(255,255,255,.02),rgba(31,41,55,.04))'}}/>
    {(scene.visuals||[]).map((v,i)=><Visual key={`${v.ref}-${i}`} visual={v} scene={scene} local={local}/>)}
    {(scene.overlays||[]).map((o)=><Overlay key={o.id} item={o} scene={scene} local={local}/>)}
  </div>;
};

const Video=()=>{
  const frame=useCurrentFrame();
  const scene=timeline.find((s)=>frame>=s.startFrame&&frame<s.endFrame)||timeline[timeline.length-1];
  const local=frame-scene.startFrame;
  const fade=interpolate(local,[0,4,Math.max(5,scene.frames-5),Math.max(6,scene.frames-1)],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <AbsoluteFill style={{fontFamily:'Arial, Helvetica, sans-serif',color:C.ink,overflow:'hidden',background:'#F4F7FB'}}>
    <Audio src={staticFile('narration.wav')} volume={0.96}/>
    <div style={{opacity:fade}}><Scene scene={scene} local={local}/><Caption scene={scene} local={local}/></div>
  </AbsoluteFill>;
};

registerRoot(()=> <Composition id="WackyLongformTest" component={Video} durationInFrames={totalFrames} fps={FPS} width={1920} height={1080}/>);
