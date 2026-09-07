import React from 'react';
import {AbsoluteFill, Audio, Composition, Img, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import plan from '../content/runtime-plan.json';
import registry from '../assets/registry.json';

const FPS = plan.fps || 24;
const totalFrames = Math.max(1, Math.round(plan.duration_seconds * FPS));
const C = {ink:'#1F2937',muted:'#667085',red:'#F05A47',blue:'#4F7CFF',green:'#22A06B',yellow:'#F7C948',white:'#FFFFFF',shadow:'rgba(30,45,70,.18)'};
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const ease=(v)=>1-Math.pow(1-clamp(v),3);
const Asset=({path,style})=><Img src={staticFile(path)} style={style}/>;

const timeline=[];
let cursor=0;
for(const scene of plan.scenes){
  const frames=Math.max(1,Math.round(scene.duration*FPS));
  timeline.push({...scene,startFrame:cursor,endFrame:cursor+frames,frames});
  cursor+=frames;
}

const beatFrame=(scene,target,fallbackPct=.5)=>{
  const beat=(scene.beats||[]).find(b=>b.target===target);
  return beat?Math.round(beat.at*FPS):Math.round(scene.frames*fallbackPct);
};

const FloatingLabel=({text,x,y,opacity=1,accent=C.red,scale=1,fontSize=28})=><div style={{position:'absolute',left:x,top:y,padding:'10px 17px',borderRadius:999,background:'rgba(255,255,255,.95)',boxShadow:`0 10px 28px ${C.shadow}`,fontSize,fontWeight:900,color:C.ink,opacity,transform:`scale(${scale})`,transformOrigin:'center',border:`3px solid ${accent}`,whiteSpace:'nowrap'}}>{text}</div>;

const Caption=({scene,local})=>{
  const p=interpolate(local,[3,12,Math.max(13,scene.frames-15),Math.max(14,scene.frames-4)],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',left:96,bottom:88,fontSize:34,fontWeight:950,color:C.ink,opacity:p,textShadow:'0 2px 12px rgba(255,255,255,.95)'}}>{scene.caption}</div>;
};

const Character=({id,local,x=470,y=310,scale=1,mirror=false,lookAway=false})=>{
  const a=registry.characters[id];
  const enter=ease(local/20);
  const bob=Math.sin(local/4)*4;
  const headTurn=lookAway?interpolate(local,[18,42],[0,10],{extrapolateLeft:'clamp',extrapolateRight:'clamp'}):Math.sin(local/11)*2;
  return <div style={{position:'absolute',left:x-210*(1-enter),top:y+bob,width:360,height:520,transform:`scale(${mirror?-scale:scale},${scale})`,transformOrigin:'top left'}}>
    <Asset path={a.body} style={{position:'absolute',inset:0,width:'100%',height:'100%'}}/>
    <Asset path={a.head} style={{position:'absolute',left:72,top:10,width:220,height:220,transform:`rotate(${headTurn}deg)`,transformOrigin:'50% 75%'}}/>
  </div>;
};

const Kitchen=({children,pan=0,zoom=1})=>{
  const env=registry.environments.kitchen_01;
  return <div style={{position:'absolute',inset:0,transform:`translateX(${pan}px) scale(${zoom})`,transformOrigin:'center'}}>
    <Asset path={env.file} style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover'}}/>
    {children}
  </div>;
};

const Microwave=({scene,local,x=1110,y=410,scale=.72})=>{
  const a=registry.props.microwave_01;
  const pct=clamp(local/Math.max(1,scene.frames-1));
  const seconds=Math.max(0,30-Math.floor(pct*30));
  const timer=`00:${String(seconds).padStart(2,'0')}`;
  const pulse=1+0.012*Math.sin(local/3);
  return <div style={{position:'absolute',left:x,top:y,width:640,height:420,transform:`scale(${scale*pulse})`,transformOrigin:'top left'}}>
    <Asset path={a.file} style={{position:'absolute',inset:0,width:'100%',height:'100%'}}/>
    <div style={{position:'absolute',left:462,top:92,width:106,height:68,borderRadius:14,background:'#172033',display:'flex',alignItems:'center',justifyContent:'center',fontFamily:'monospace',fontSize:31,fontWeight:800,color:'#8DF0A9'}}>{timer}</div>
  </div>;
};

const Phone=({local,x=1280,y=330,scale=1})=>{
  const float=Math.sin(local/5)*7;
  return <div style={{position:'absolute',left:x,top:y+float,width:170,height:310,borderRadius:34,background:'#1F2937',boxShadow:`0 18px 34px ${C.shadow}`,transform:`scale(${scale})`,border:'7px solid #111827'}}>
    <div style={{position:'absolute',inset:13,borderRadius:24,background:'linear-gradient(180deg,#EAF0FF,#FFFFFF)',overflow:'hidden'}}>
      {[0,1,2,3].map(i=><div key={i} style={{height:52,margin:'16px 12px',borderRadius:14,background:i%2? '#FFE9E5':'#E8EEFF',transform:`translateX(${Math.sin((local+i*8)/8)*7}px)`}}/>)}
    </div>
  </div>;
};

const Scene1=({scene,local})=>{
  const timerAt=beatFrame(scene,'timer',.48);
  const zoomAt=beatFrame(scene,'microwave_01',.72);
  const label=interpolate(local,[timerAt,timerAt+10],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const zoom=interpolate(local,[zoomAt,scene.frames-1],[1.02,1.1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <Kitchen pan={-30} zoom={zoom}>
    <Character id={scene.character} local={local} x={390}/>
    <Microwave scene={scene} local={local}/>
    <FloatingLabel text="30 seconds..." x={1210} y={315} opacity={label} accent={C.red} scale={.88+.12*label}/>
    <div style={{position:'absolute',left:925,top:390,fontSize:88,fontWeight:950,color:C.red,opacity:label,transform:`scale(${.7+.3*label})`}}>?</div>
  </Kitchen>;
};

const Scene2=({scene,local})=>{
  const trackAt=beatFrame(scene,'timer',.28);
  const markersAt=beatFrame(scene,'second_markers',.52);
  const focus=interpolate(local,[trackAt,trackAt+12],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const markers=interpolate(local,[markersAt,markersAt+12],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const zoom=interpolate(local,[0,scene.frames-1],[1.05,1.13],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <Kitchen pan={-110} zoom={zoom}>
    <Character id={scene.character} local={local} x={420}/>
    <Microwave scene={scene} local={local} x={1180} y={400} scale={.78}/>
    <div style={{position:'absolute',left:990,top:260,width:390,height:390,borderRadius:'50%',border:`8px solid ${C.yellow}`,opacity:focus,transform:`scale(${.72+.28*focus})`}}/>
    {[0,1,2,3,4].map(i=><div key={i} style={{position:'absolute',left:1030+i*110,top:255-i%2*28,opacity:markers,transform:`translateY(${(1-markers)*24}px)`,fontSize:25,fontWeight:900,color:C.blue}}>+1s</div>)}
    <FloatingLabel text="attention locked" x={690} y={230} opacity={focus} accent={C.blue}/>
  </Kitchen>;
};

const Scene3=({scene,local})=>{
  const revealAt=beatFrame(scene,'comparison',.05);
  const phoneAt=beatFrame(scene,'phone_side',.52);
  const reveal=interpolate(local,[revealAt,revealAt+12],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const phone=interpolate(local,[phoneAt,phoneAt+12],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',inset:0,background:'#F4F7FB',opacity:reveal}}>
    <div style={{position:'absolute',left:0,top:0,width:'50%',height:'100%',overflow:'hidden'}}>
      <Kitchen pan={100} zoom={1.14}>
        <Character id={scene.character} local={local} x={300} scale={.95}/>
        <Microwave scene={scene} local={local} x={610} y={430} scale={.62}/>
      </Kitchen>
      <FloatingLabel text="watching every second" x={120} y={205} opacity={reveal} accent={C.red}/>
    </div>
    <div style={{position:'absolute',right:0,top:0,width:'50%',height:'100%',overflow:'hidden'}}>
      <Kitchen pan={-900} zoom={1.14}>
        <Character id={scene.character} local={local} x={1450} scale={.95} mirror/>
        <Phone local={local} x={1540} y={315} scale={phone}/>
      </Kitchen>
      <FloatingLabel text="attention keeps jumping" x={150} y={205} opacity={phone} accent={C.blue}/>
    </div>
    <div style={{position:'absolute',left:'50%',top:80,bottom:80,width:4,background:'rgba(31,41,55,.14)'}}/>
  </div>;
};

const Scene4=({scene,local})=>{
  const rewardAt=beatFrame(scene,'reward_label',.3);
  const trackAt=beatFrame(scene,'timer',.55);
  const reward=interpolate(local,[rewardAt,rewardAt+12],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const track=interpolate(local,[trackAt,trackAt+12],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const zoom=interpolate(local,[0,scene.frames-1],[1.1,1.18],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <Kitchen pan={-170} zoom={zoom}>
    <Character id={scene.character} local={local} x={610} y={235} scale={1.28}/>
    <Microwave scene={scene} local={local} x={1320} y={390} scale={.65}/>
    <FloatingLabel text="reward incoming" x={1030} y={190} opacity={reward} accent={C.green} scale={.85+.15*reward}/>
    <div style={{position:'absolute',left:1100,top:300,width:330,height:12,borderRadius:999,background:'rgba(34,160,107,.15)',opacity:track}}><div style={{height:'100%',width:`${20+80*clamp(local/scene.frames)}%`,borderRadius:999,background:C.green}}/></div>
    <div style={{position:'absolute',left:1040,top:330,fontSize:28,fontWeight:900,color:C.green,opacity:track}}>you know exactly when</div>
  </Kitchen>;
};

const Scene5=({scene,local})=>{
  const awayAt=beatFrame(scene,'look_away',.28);
  const punchAt=beatFrame(scene,'punchline',.8);
  const away=interpolate(local,[awayAt,awayAt+10],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const punch=interpolate(local,[punchAt,punchAt+12],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const zoom=interpolate(local,[0,scene.frames-1],[1.02,1.09],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <Kitchen pan={-40} zoom={zoom}>
    <Character id={scene.character} local={local} x={420} lookAway={away>.3}/>
    <Microwave scene={scene} local={local} x={1150} y={405} scale={.72}/>
    <FloatingLabel text="look away" x={610} y={240} opacity={away} accent={C.blue}/>
    <FloatingLabel text="watched microwaves age in dog years" x={800} y={690} opacity={punch} accent={C.red} scale={.88+.12*punch} fontSize={26}/>
  </Kitchen>;
};

const SceneView=({scene,local})=>{
  if(scene.id==='s01') return <Scene1 scene={scene} local={local}/>;
  if(scene.id==='s02') return <Scene2 scene={scene} local={local}/>;
  if(scene.id==='s03') return <Scene3 scene={scene} local={local}/>;
  if(scene.id==='s04') return <Scene4 scene={scene} local={local}/>;
  if(scene.id==='s05') return <Scene5 scene={scene} local={local}/>;
  return null;
};

const Video=()=>{
  const frame=useCurrentFrame();
  const scene=timeline.find(s=>frame>=s.startFrame&&frame<s.endFrame)||timeline[timeline.length-1];
  const local=frame-scene.startFrame;
  const fade=interpolate(local,[0,4,Math.max(5,scene.frames-5),Math.max(6,scene.frames-1)],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <AbsoluteFill style={{fontFamily:'Arial, Helvetica, sans-serif',color:C.ink,overflow:'hidden',background:'#F4F7FB'}}>
    <Audio src={staticFile('narration.wav')} volume={0.96}/>
    <div style={{opacity:fade}}><SceneView scene={scene} local={local}/><Caption scene={scene} local={local}/></div>
  </AbsoluteFill>;
};

registerRoot(()=> <Composition id="WackyLongformTest" component={Video} durationInFrames={totalFrames} fps={FPS} width={1920} height={1080}/>);
