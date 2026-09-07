import React from 'react';
import {AbsoluteFill, Audio, Composition, Img, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import plan from '../content/demo-plan.json';

const FPS = 30;
const totalFrames = plan.duration_seconds * FPS;
const sceneFrames = 4 * FPS;

const C = {
  ink:'#1F2937', muted:'#667085', red:'#F05A47', blue:'#4F7CFF', green:'#22A06B',
  yellow:'#F7C948', panel:'#FFFFFF', border:'#D9E2EC', shadow:'rgba(30,45,70,.14)'
};

const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const ease=(v)=>1-Math.pow(1-clamp(v),3);

const Card=({children,x,y,w,h,opacity=1,scale=1})=><div style={{position:'absolute',left:x,top:y,width:w,height:h,background:C.panel,border:`2px solid ${C.border}`,borderRadius:28,boxShadow:`0 18px 42px ${C.shadow}`,opacity,transform:`scale(${scale})`,transformOrigin:'center'}}>{children}</div>;

const AssetCharacter=({frame})=>{
  const enter=ease(frame/18);
  const look=interpolate(frame,[54,74],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const bob=Math.sin(frame/5)*2;
  return <div style={{position:'absolute',left:500-260*(1-enter),top:310+bob,width:360,height:520}}>
    <Img src={staticFile('assets/asset-mvp/character-body.svg')} style={{position:'absolute',inset:0,width:'100%',height:'100%'}}/>
    <Img src={staticFile('assets/asset-mvp/character-head.svg')} style={{position:'absolute',left:72+look*4,top:10,width:220,height:220,transform:`rotate(${look*3}deg)`,transformOrigin:'50% 75%'}}/>
  </div>;
};

const AssetFridge=({frame})=>{
  const open=interpolate(frame,[38,52,88],[0,1,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const angle=-58*open;
  return <div style={{position:'absolute',left:1170,top:250,width:360,height:620}}>
    <Img src={staticFile('assets/asset-mvp/fridge-base.svg')} style={{position:'absolute',inset:0,width:'100%',height:'100%'}}/>
    <Img src={staticFile('assets/asset-mvp/fridge-door.svg')} style={{position:'absolute',inset:0,width:'100%',height:'100%',transform:`perspective(900px) rotateY(${angle}deg)`,transformOrigin:'13% 50%'}}/>
  </div>;
};

const SetupScene=({frame})=>{
  const callout=interpolate(frame,[76,92],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const cam=interpolate(frame,[0,119],[1,1.035],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',inset:0,transform:`scale(${cam})`,transformOrigin:'center'}}>
    <Img src={staticFile('assets/asset-mvp/kitchen-bg.svg')} style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover'}}/>
    <Card x={90} y={80} w={620} h={165}><div style={{padding:'26px 36px'}}><div style={{fontSize:18,fontWeight:900,color:C.red,letterSpacing:1.2}}>WACKY INSIGHTS</div><div style={{marginTop:10,fontSize:58,fontWeight:950,lineHeight:1.02}}>YOU JUST<br/>CHECKED.</div></div></Card>
    <AssetCharacter frame={frame}/>
    <AssetFridge frame={frame}/>
    <Card x={1120} y={690} w={420} h={115} opacity={callout} scale={.94+.06*callout}><div style={{padding:'22px 28px'}}><div style={{fontSize:17,fontWeight:850,color:C.muted}}>FRIDGE STATUS</div><div style={{fontSize:32,fontWeight:950,marginTop:4}}>Still nothing new.</div></div></Card>
    <div style={{position:'absolute',left:1230,top:225,padding:'12px 22px',borderRadius:999,background:C.red,color:'#fff',fontSize:25,fontWeight:900,opacity:callout,transform:`scale(${.86+.14*callout})`,boxShadow:`0 10px 26px ${C.shadow}`}}>EMPTY</div>
  </div>;
};

const InfographicScene=({frame})=>{
  const local=frame-sceneFrames;
  const reveal=interpolate(local,[8,30],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const zoom=interpolate(local,[72,100,119],[1,1.035,1.06],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',inset:0,background:'linear-gradient(180deg,#F8FAFD 0%,#EEF3F8 100%)'}}>
    <Card x={90} y={80} w={760} h={165}><div style={{padding:'26px 36px'}}><div style={{fontSize:18,fontWeight:900,color:C.blue,letterSpacing:1.2}}>MICRO HABIT LOOP</div><div style={{marginTop:10,fontSize:52,fontWeight:950,lineHeight:1.05}}>BORED → CHECK →<br/>REWARD?</div></div></Card>
    <div style={{position:'absolute',left:120,top:330,width:1110,height:350,opacity:reveal,transform:`scale(${zoom})`,transformOrigin:'center'}}><Img src={staticFile('assets/asset-mvp/reward-loop.svg')} style={{width:'100%',height:'100%'}}/></div>
    <Card x={1370} y={300} w={420} h={350} opacity={reveal}><div style={{padding:30}}><div style={{fontSize:19,fontWeight:900,color:C.muted}}>WHY IT HAPPENS</div><div style={{marginTop:24,width:88,height:88,borderRadius:'50%',background:'#EAF0FF',display:'flex',alignItems:'center',justifyContent:'center',fontSize:44,fontWeight:950,color:C.blue}}>?</div><div style={{marginTop:20,fontSize:30,fontWeight:900,lineHeight:1.28}}>Your brain checks for a tiny possible reward.</div></div></Card>
  </div>;
};

const Video=()=>{
  const frame=useCurrentFrame();
  const local=frame<sceneFrames?frame:frame-sceneFrames;
  const fade=interpolate(local,[0,8,sceneFrames-8,sceneFrames],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <AbsoluteFill style={{fontFamily:'Arial, Helvetica, sans-serif',color:C.ink,overflow:'hidden'}}>
    <Audio src={staticFile('narration.wav')} volume={0.96}/>
    <div style={{opacity:fade}}>{frame<sceneFrames?<SetupScene frame={frame}/>:<InfographicScene frame={frame}/>}</div>
    <div style={{position:'absolute',left:90,right:90,bottom:24,height:9,borderRadius:999,background:'rgba(31,41,55,.08)'}}><div style={{height:'100%',width:`${Math.min(100,frame/totalFrames*100)}%`,borderRadius:999,background:`linear-gradient(90deg,${C.red},${C.blue})`}}/></div>
  </AbsoluteFill>;
};

registerRoot(()=> <Composition id="WackyLongformTest" component={Video} durationInFrames={totalFrames} fps={FPS} width={1920} height={1080}/>);
