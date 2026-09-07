import React from 'react';
import {AbsoluteFill, Audio, Composition, Img, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import plan from '../content/scene-plan.json';
import registry from '../assets/registry.json';

const FPS = plan.fps || 24;
const totalFrames = Math.round(plan.duration_seconds * FPS);
const C = {ink:'#1F2937',muted:'#667085',red:'#F05A47',blue:'#4F7CFF',green:'#22A06B',yellow:'#F7C948',white:'#FFFFFF',shadow:'rgba(30,45,70,.16)'};
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const ease=(v)=>1-Math.pow(1-clamp(v),3);
const Asset=({path,style})=><Img src={staticFile(path)} style={style}/>;

const timeline=[];
let cursor=0;
for(const scene of plan.scenes){const frames=Math.round(scene.duration*FPS);timeline.push({...scene,start:cursor,end:cursor+frames,frames});cursor+=frames;}

const FloatingLabel=({text,x,y,opacity=1,accent=C.red,scale=1})=><div style={{position:'absolute',left:x,top:y,padding:'11px 18px',borderRadius:999,background:'rgba(255,255,255,.94)',boxShadow:`0 10px 28px ${C.shadow}`,fontSize:28,fontWeight:900,color:C.ink,opacity,transform:`scale(${scale})`,transformOrigin:'center',border:`3px solid ${accent}`}}>{text}</div>;

const Caption=({scene,local})=>{
  const p=interpolate(local,[6,16,scene.frames-20,scene.frames-8],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',left:96,bottom:92,fontSize:34,fontWeight:950,color:C.ink,opacity:p,textShadow:'0 2px 10px rgba(255,255,255,.9)'}}>{scene.caption}</div>;
};

const Character=({id,local,x=500,y=310,scale=1,mirror=false})=>{
  const a=registry.characters[id];
  const walk=ease(local/24);
  const bob=Math.sin(local/4)*4;
  const sway=Math.sin(local/5)*2;
  return <div style={{position:'absolute',left:x-220*(1-walk),top:y+bob,width:360,height:520,transform:`scale(${mirror?-scale:scale},${scale}) rotate(${sway*.35}deg)`,transformOrigin:'top left'}}>
    <Asset path={a.body} style={{position:'absolute',inset:0,width:'100%',height:'100%'}}/>
    <Asset path={a.head} style={{position:'absolute',left:72,top:10,width:220,height:220,transform:`translateX(${Math.sin(local/9)*3}px)`}}/>
  </div>;
};

const Fridge=({id,local,x=1170,y=250,scale=1,openAt=38})=>{
  const a=registry.props[id];
  const open=interpolate(local,[openAt,openAt+16],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',left:x,top:y,width:360,height:620,transform:`scale(${scale})`,transformOrigin:'top left'}}>
    <Asset path={a.base} style={{position:'absolute',inset:0,width:'100%',height:'100%'}}/>
    <Asset path={a.door} style={{position:'absolute',inset:0,width:'100%',height:'100%',transform:`perspective(900px) rotateY(${-58*open}deg)`,transformOrigin:'13% 50%'}}/>
  </div>;
};

const Kitchen=({local,children,pan=0,zoom=1})=>{
  const env=registry.environments.kitchen_01;
  return <div style={{position:'absolute',inset:0,transform:`translateX(${pan}px) scale(${zoom})`,transformOrigin:'center'}}>
    <Asset path={env.file} style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover'}}/>
    {children}
  </div>;
};

const RewardOverlay=({local,x=790,y=225,scale=.68})=>{
  const a=registry.infographics.reward_loop_01;
  const reveal=interpolate(local,[8,28],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const float=Math.sin(local/8)*5;
  return <div style={{position:'absolute',left:x,top:y+float,width:900,height:350,opacity:reveal,transform:`scale(${scale})`,transformOrigin:'top left',filter:'drop-shadow(0 12px 24px rgba(30,45,70,.18))'}}>
    <Asset path={a.file} style={{width:'100%',height:'100%'}}/>
  </div>;
};

const EnvironmentCharacter=({scene,local})=>{
  const zoom=interpolate(local,[0,scene.frames-1],[1,1.06],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const pan=interpolate(local,[20,80],[0,-55],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const empty=interpolate(local,[88,108],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <Kitchen local={local} pan={pan} zoom={zoom}>
    <Character id={scene.character} local={local}/>
    <Fridge id="fridge_01" local={local} openAt={42}/>
    <FloatingLabel text="still empty" x={1260} y={220} opacity={empty} accent={C.red} scale={.9+.1*empty}/>
  </Kitchen>;
};

const EnvironmentOverlay=({scene,local})=>{
  const pan=interpolate(local,[0,scene.frames-1],[-30,-95],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const zoom=interpolate(local,[0,scene.frames-1],[1.04,1.09],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const brain=interpolate(local,[45,65],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <Kitchen local={local} pan={pan} zoom={zoom}>
    <Character id={scene.character} local={local} x={420}/>
    <Fridge id="fridge_01" local={local} x={1260} openAt={0}/>
    <RewardOverlay local={local}/>
    <FloatingLabel text="tiny reward?" x={920} y={610} opacity={brain} accent={C.green} scale={.9+.1*brain}/>
  </Kitchen>;
};

const BehaviorComparison=({scene,local})=>{
  const reveal=interpolate(local,[4,22],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const hunger=interpolate(local,[30,105],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const trigger=interpolate(local,[68,82],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',inset:0,background:'#F4F7FB'}}>
    <div style={{position:'absolute',left:0,top:0,width:'50%',height:'100%',overflow:'hidden',opacity:reveal}}>
      <Kitchen local={local} pan={80} zoom={1.12}>
        <Character id={scene.character} local={local} x={340} y={330} scale={.92}/>
      </Kitchen>
      <div style={{position:'absolute',left:110,top:180,width:520,height:24,borderRadius:999,background:'rgba(79,124,255,.15)'}}><div style={{width:`${18+72*hunger}%`,height:'100%',borderRadius:999,background:C.blue}}/></div>
      <FloatingLabel text="hunger builds" x={150} y={225} opacity={reveal} accent={C.blue}/>
    </div>
    <div style={{position:'absolute',right:0,top:0,width:'50%',height:'100%',overflow:'hidden',opacity:reveal}}>
      <Kitchen local={local} pan={-920} zoom={1.12}>
        <Fridge id="fridge_01" local={local} x={1210} y={260} scale={.92} openAt={84}/>
        <Character id={scene.character} local={local} x={1540} y={330} scale={.92} mirror/>
      </Kitchen>
      <FloatingLabel text="instant cue!" x={220} y={220} opacity={trigger} accent={C.red} scale={.88+.12*trigger}/>
      <div style={{position:'absolute',left:400,top:320,fontSize:92,fontWeight:950,color:C.red,opacity:trigger,transform:`scale(${.7+.3*trigger})`}}>!</div>
    </div>
    <div style={{position:'absolute',left:'50%',top:90,bottom:90,width:4,background:'rgba(31,41,55,.14)'}}/>
  </div>;
};

const CharacterCloseup=({scene,local})=>{
  const zoom=interpolate(local,[0,scene.frames-1],[1.08,1.18],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const thought=interpolate(local,[42,62],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const eye=interpolate(local,[72,96],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <Kitchen local={local} pan={-160} zoom={zoom}>
    <Character id={scene.character} local={local} x={640} y={220} scale={1.34}/>
    <Fridge id="fridge_01" local={local} x={1320} y={280} scale={.78} openAt={120}/>
    <div style={{position:'absolute',left:1060,top:170,opacity:thought,transform:`translateY(${(1-thought)*20}px) scale(${.85+.15*thought})`}}>
      <div style={{padding:'22px 30px',borderRadius:38,background:'rgba(255,255,255,.96)',boxShadow:`0 14px 34px ${C.shadow}`,fontSize:40,fontWeight:950}}>maybe this time?</div>
      <div style={{marginLeft:30,width:24,height:24,borderRadius:'50%',background:C.white,boxShadow:`0 6px 15px ${C.shadow}`}}/>
    </div>
    <div style={{position:'absolute',left:915,top:330,width:130,height:8,borderRadius:999,background:C.yellow,opacity:eye}}/>
  </Kitchen>;
};

const EnvironmentSummary=({scene,local})=>{
  const loop=interpolate(local,[44,66],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const punch=interpolate(local,[92,118],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const zoom=interpolate(local,[0,scene.frames-1],[1.02,1.1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <Kitchen local={local} pan={-40} zoom={zoom}>
    <Character id={scene.character} local={local} x={470}/>
    <Fridge id="fridge_01" local={local} openAt={10}/>
    <div style={{opacity:loop}}><RewardOverlay local={local} x={710} y={190} scale={.58}/></div>
    <FloatingLabel text="fridge: unchanged" x={1210} y={710} opacity={punch} accent={C.red}/>
    <FloatingLabel text="brain: check again" x={760} y={650} opacity={punch} accent={C.blue}/>
  </Kitchen>;
};

const SceneView=({scene,local})=>{
  if(scene.type==='environment_character') return <EnvironmentCharacter scene={scene} local={local}/>;
  if(scene.type==='environment_overlay') return <EnvironmentOverlay scene={scene} local={local}/>;
  if(scene.type==='behavior_comparison') return <BehaviorComparison scene={scene} local={local}/>;
  if(scene.type==='character_closeup') return <CharacterCloseup scene={scene} local={local}/>;
  if(scene.type==='environment_summary') return <EnvironmentSummary scene={scene} local={local}/>;
  return null;
};

const Video=()=>{
  const frame=useCurrentFrame();
  const scene=timeline.find(s=>frame>=s.start&&frame<s.end)||timeline[timeline.length-1];
  const local=frame-scene.start;
  const fade=interpolate(local,[0,5,scene.frames-6,scene.frames-1],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <AbsoluteFill style={{fontFamily:'Arial, Helvetica, sans-serif',color:C.ink,overflow:'hidden',background:'#F4F7FB'}}>
    <Audio src={staticFile('narration.wav')} volume={0.96}/>
    <div style={{opacity:fade}}><SceneView scene={scene} local={local}/><Caption scene={scene} local={local}/></div>
  </AbsoluteFill>;
};

registerRoot(()=> <Composition id="WackyLongformTest" component={Video} durationInFrames={totalFrames} fps={FPS} width={1920} height={1080}/>);
