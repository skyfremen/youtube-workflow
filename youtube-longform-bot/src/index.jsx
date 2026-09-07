import React from 'react';
import {AbsoluteFill, Audio, Composition, Img, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import plan from '../content/scene-plan.json';
import registry from '../assets/registry.json';

const FPS = plan.fps || 30;
const totalFrames = Math.round(plan.duration_seconds * FPS);
const C = {ink:'#1F2937',muted:'#667085',red:'#F05A47',blue:'#4F7CFF',green:'#22A06B',yellow:'#F7C948',panel:'#FFFFFF',border:'#D9E2EC',shadow:'rgba(30,45,70,.14)',bg:'#F5F8FC'};
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const ease=(v)=>1-Math.pow(1-clamp(v),3);

const Card=({children,x,y,w,h,opacity=1,scale=1})=><div style={{position:'absolute',left:x,top:y,width:w,height:h,background:C.panel,border:`2px solid ${C.border}`,borderRadius:28,boxShadow:`0 18px 42px ${C.shadow}`,opacity,transform:`scale(${scale})`,transformOrigin:'center'}}>{children}</div>;
const Asset=({path,style})=><Img src={staticFile(path)} style={style}/>;

const timeline=[];
let cursor=0;
for(const scene of plan.scenes){
  const frames=Math.round(scene.duration*FPS);
  timeline.push({...scene,start:cursor,end:cursor+frames,frames});
  cursor+=frames;
}

const Caption=({scene,local})=>{
  const p=interpolate(local,[0,10,scene.frames-12,scene.frames-2],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',left:88,top:72,padding:'16px 24px',borderRadius:18,background:'rgba(255,255,255,.94)',border:`2px solid ${C.border}`,boxShadow:`0 12px 30px ${C.shadow}`,fontSize:44,fontWeight:950,color:C.ink,opacity:p,maxWidth:800}}>{scene.caption}</div>;
};

const Character=({id,local,closeup=false})=>{
  const a=registry.characters[id];
  const enter=ease(local/18);
  const bob=Math.sin(local/6)*2;
  const scale=closeup?1.35:1;
  return <div style={{position:'absolute',left:closeup?670:500-260*(1-enter),top:(closeup?235:310)+bob,width:360,height:520,transform:`scale(${scale})`,transformOrigin:'top left'}}>
    <Asset path={a.body} style={{position:'absolute',inset:0,width:'100%',height:'100%'}}/>
    <Asset path={a.head} style={{position:'absolute',left:72,top:10,width:220,height:220}}/>
  </div>;
};

const Fridge=({id,local})=>{
  const a=registry.props[id];
  const open=interpolate(local,[28,45,120],[0,1,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',left:1170,top:250,width:360,height:620}}>
    <Asset path={a.base} style={{position:'absolute',inset:0,width:'100%',height:'100%'}}/>
    <Asset path={a.door} style={{position:'absolute',inset:0,width:'100%',height:'100%',transform:`perspective(900px) rotateY(${-58*open}deg)`,transformOrigin:'13% 50%'}}/>
  </div>;
};

const EnvironmentCharacter=({scene,local})=>{
  const env=registry.environments[scene.environment];
  const zoom=interpolate(local,[0,scene.frames-1],[1,1.035],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',inset:0,transform:`scale(${zoom})`,transformOrigin:'center'}}>
    <Asset path={env.file} style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover'}}/>
    <Character id={scene.character} local={local}/>
    {(scene.props||[]).includes('fridge_01')&&<Fridge id="fridge_01" local={local}/>}    
    <div style={{position:'absolute',left:1170,top:730,padding:'14px 24px',borderRadius:999,background:C.red,color:'#fff',fontSize:28,fontWeight:900,opacity:interpolate(local,[80,98],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>STILL NOTHING NEW</div>
  </div>;
};

const Infographic=({scene,local,summary=false})=>{
  const a=registry.infographics[scene.infographic];
  const reveal=interpolate(local,[6,26],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const zoom=interpolate(local,[0,scene.frames-1],[1,summary?1.08:1.04],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',inset:0,background:'linear-gradient(180deg,#F8FAFD 0%,#EEF3F8 100%)'}}>
    <div style={{position:'absolute',left:180,top:250,width:1200,height:480,opacity:reveal,transform:`scale(${zoom})`,transformOrigin:'center'}}><Asset path={a.file} style={{width:'100%',height:'100%'}}/></div>
    <Card x={1420} y={300} w={390} h={330} opacity={reveal}><div style={{padding:30}}><div style={{fontSize:18,fontWeight:900,color:C.muted}}>{summary?'TAKEAWAY':'WHAT IS HAPPENING'}</div><div style={{marginTop:24,fontSize:31,fontWeight:900,lineHeight:1.28}}>{summary?'The fridge stayed the same. The reward loop brought you back.':'Your brain checks whether a small reward might appear.'}</div></div></Card>
  </div>;
};

const Comparison=({scene,local})=>{
  const left=interpolate(local,[8,28],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const right=interpolate(local,[35,58],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const pulse=1+0.035*Math.max(0,Math.sin((local-75)/8));
  return <div style={{position:'absolute',inset:0,background:C.bg}}>
    <Card x={220} y={300} w={620} h={380} opacity={left} scale={.94+.06*left}><div style={{padding:42}}><div style={{fontSize:25,fontWeight:900,color:C.blue}}>GRADUAL SIGNAL</div><div style={{fontSize:64,fontWeight:950,marginTop:18}}>{scene.left_label}</div><div style={{fontSize:29,lineHeight:1.35,marginTop:28,color:C.muted,fontWeight:750}}>Builds over time and usually survives a change of scenery.</div></div></Card>
    <Card x={1080} y={300} w={620} h={380} opacity={right} scale={(.94+.06*right)*pulse}><div style={{padding:42}}><div style={{fontSize:25,fontWeight:900,color:C.red}}>INSTANT CUE</div><div style={{fontSize:64,fontWeight:950,marginTop:18}}>{scene.right_label}</div><div style={{fontSize:29,lineHeight:1.35,marginTop:28,color:C.muted,fontWeight:750}}>Can appear from boredom, routine, or simply seeing the kitchen.</div></div></Card>
  </div>;
};

const CharacterCloseup=({scene,local})=>{
  const bubble=interpolate(local,[55,78],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const zoom=interpolate(local,[0,scene.frames-1],[1,1.055],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',inset:0,background:'linear-gradient(135deg,#EEF3FF,#F9FBFD)',transform:`scale(${zoom})`,transformOrigin:'center'}}>
    <Character id={scene.character} local={local} closeup/>
    <Card x={1120} y={300} w={520} h={250} opacity={bubble} scale={.9+.1*bubble}><div style={{padding:38,fontSize:48,fontWeight:950,lineHeight:1.15}}>“Maybe this time?”</div></Card>
  </div>;
};

const SceneView=({scene,local})=>{
  if(scene.type==='environment_character') return <EnvironmentCharacter scene={scene} local={local}/>;
  if(scene.type==='infographic') return <Infographic scene={scene} local={local}/>;
  if(scene.type==='comparison') return <Comparison scene={scene} local={local}/>;
  if(scene.type==='character_closeup') return <CharacterCloseup scene={scene} local={local}/>;
  if(scene.type==='summary') return <Infographic scene={scene} local={local} summary/>;
  return null;
};

const Video=()=>{
  const frame=useCurrentFrame();
  const scene=timeline.find(s=>frame>=s.start&&frame<s.end)||timeline[timeline.length-1];
  const local=frame-scene.start;
  const fade=interpolate(local,[0,6,scene.frames-8,scene.frames-1],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <AbsoluteFill style={{fontFamily:'Arial, Helvetica, sans-serif',color:C.ink,overflow:'hidden'}}>
    <Audio src={staticFile('narration.wav')} volume={0.96}/>
    <div style={{opacity:fade}}><SceneView scene={scene} local={local}/><Caption scene={scene} local={local}/></div>
    <div style={{position:'absolute',left:88,right:88,bottom:22,height:9,borderRadius:999,background:'rgba(31,41,55,.08)'}}><div style={{height:'100%',width:`${Math.min(100,frame/totalFrames*100)}%`,borderRadius:999,background:`linear-gradient(90deg,${C.red},${C.blue})`}}/></div>
  </AbsoluteFill>;
};

registerRoot(()=> <Composition id="WackyLongformTest" component={Video} durationInFrames={totalFrames} fps={FPS} width={1920} height={1080}/>);
