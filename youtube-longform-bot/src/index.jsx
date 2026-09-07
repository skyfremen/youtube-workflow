import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Composition,
  interpolate,
  registerRoot,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import plan from '../content/demo-plan.json';

const FPS = 30;
const totalFrames = plan.duration_seconds * FPS;
const SCENE_FRAMES = 5 * FPS;

const C = {
  bg1:'#F7F9FC', bg2:'#EDF2F7', ink:'#1F2937', muted:'#667085',
  red:'#F05A47', blue:'#4F7CFF', green:'#22A06B', yellow:'#F7C948',
  panel:'#FFFFFF', border:'#D9E2EC', skin:'#E7B991', hair:'#273142',
  shirt:'#4F7CFF', pants:'#344054', fridge:'#E8EEF5', fridgeEdge:'#CBD5E1',
  counter:'#D8C3A5', cabinet:'#BFD3EF', tile:'#DCE6F0', shadow:'rgba(30,45,70,0.14)'
};

const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const ease=(v)=>1-Math.pow(1-clamp(v),3);

const Card=({x,y,w,h,children,opacity=1,scale=1})=>(
  <div style={{position:'absolute',left:x,top:y,width:w,height:h,background:C.panel,border:`2px solid ${C.border}`,borderRadius:28,boxShadow:`0 18px 42px ${C.shadow}`,opacity,transform:`scale(${scale})`,transformOrigin:'center'}}>{children}</div>
);

const Pill=({x,y,text,color=C.red,opacity=1,scale=1})=>(
  <div style={{position:'absolute',left:x,top:y,padding:'14px 24px',borderRadius:999,background:color,color:'#fff',fontSize:26,fontWeight:900,letterSpacing:.4,boxShadow:`0 10px 26px ${C.shadow}`,opacity,transform:`scale(${scale})`}}>{text}</div>
);

const Kitchen=()=> (
  <svg width="1920" height="1080" viewBox="0 0 1920 1080" style={{position:'absolute',inset:0}}>
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.bg1}/><stop offset="100%" stopColor={C.bg2}/></linearGradient>
      <filter id="soft"><feDropShadow dx="0" dy="12" stdDeviation="14" floodColor="#20334A" floodOpacity="0.12"/></filter>
    </defs>
    <rect width="1920" height="1080" fill="url(#bg)"/>
    <rect x="0" y="690" width="1920" height="390" fill="#E7DCCF"/>
    <rect x="0" y="300" width="1920" height="260" fill="#F8FBFE"/>
    {Array.from({length:14}).map((_,i)=><line key={`v${i}`} x1={i*145} y1="300" x2={i*145} y2="560" stroke="#E7EEF6" strokeWidth="3"/>)}
    {Array.from({length:6}).map((_,i)=><line key={`h${i}`} x1="0" y1={300+i*52} x2="1920" y2={300+i*52} stroke="#E7EEF6" strokeWidth="3"/>)}
    <g filter="url(#soft)">
      <rect x="140" y="520" width="860" height="76" rx="18" fill={C.counter}/>
      <rect x="140" y="596" width="860" height="120" rx="14" fill="#F1E6D8"/>
      <rect x="205" y="372" width="185" height="112" rx="16" fill={C.cabinet}/>
      <rect x="420" y="372" width="185" height="112" rx="16" fill={C.cabinet}/>
      <rect x="635" y="372" width="185" height="112" rx="16" fill={C.cabinet}/>
    </g>
    {[295,510,725].map(x=><circle key={x} cx={x} cy="428" r="6" fill={C.ink} opacity=".45"/>)}
    <rect x="905" y="425" width="52" height="105" rx="14" fill="#DDE5ED"/>
    <rect x="918" y="445" width="26" height="67" rx="10" fill="#AAB8C5"/>
  </svg>
);

const Fridge=({open=0})=>{
  const angle=-62*open;
  return <div style={{position:'absolute',left:1170,top:300,width:320,height:560}}>
    <div style={{position:'absolute',left:20,top:22,width:252,height:520,borderRadius:30,background:C.fridgeEdge,boxShadow:`0 18px 40px ${C.shadow}`}}/>
    <div style={{position:'absolute',left:25,top:20,width:250,height:520,borderRadius:28,background:'#F8FBFD',border:`3px solid ${C.border}`,overflow:'hidden'}}>
      <div style={{position:'absolute',left:28,right:28,top:80,height:18,borderRadius:9,background:'#E4EBF2'}}/>
      <div style={{position:'absolute',left:28,right:28,top:198,height:5,background:'#D6DEE7'}}/>
      <div style={{position:'absolute',left:28,right:28,top:278,height:18,borderRadius:9,background:'#E4EBF2'}}/>
      <div style={{position:'absolute',left:28,right:28,top:392,height:5,background:'#D6DEE7'}}/>
    </div>
    <div style={{position:'absolute',left:25,top:20,width:250,height:520,transformOrigin:'left center',transform:`perspective(850px) rotateY(${angle}deg)`}}>
      <div style={{width:'100%',height:'100%',borderRadius:28,background:C.fridge,border:`3px solid ${C.border}`,boxShadow:`0 18px 40px ${C.shadow}`,position:'relative'}}>
        <div style={{position:'absolute',left:0,right:0,top:198,height:3,background:'#C8D2DD'}}/>
        <div style={{position:'absolute',right:24,top:78,width:11,height:78,borderRadius:7,background:'#8FA1B3'}}/>
        <div style={{position:'absolute',right:24,top:274,width:11,height:78,borderRadius:7,background:'#8FA1B3'}}/>
      </div>
    </div>
  </div>
};

const Character=({x=0,y=0,mood='neutral',arm=0,look=0,scale=1})=>(
  <div style={{position:'absolute',left:x,top:y,transform:`scale(${scale})`,transformOrigin:'top left'}}>
    <svg width="320" height="520" viewBox="0 0 320 520">
      <ellipse cx="165" cy="493" rx="82" ry="16" fill="rgba(25,40,60,.09)"/>
      <path d="M115 145 C108 205 110 270 118 326 L218 326 C228 258 225 195 214 145 Z" fill={C.shirt}/>
      <path d="M132 326 L122 448 L154 448 L176 326 Z" fill={C.pants}/>
      <path d="M190 326 L184 448 L218 448 L232 326 Z" fill={C.pants}/>
      <rect x="116" y="444" width="48" height="13" rx="7" fill="#202B39"/>
      <rect x="194" y="444" width="48" height="13" rx="7" fill="#202B39"/>
      <g transform={`rotate(${-16+arm*30} 116 195)`}><rect x="102" y="174" width="28" height="120" rx="14" fill={C.skin}/><circle cx="116" cy="298" r="14" fill={C.skin}/></g>
      <g transform="rotate(12 222 194)"><rect x="208" y="174" width="28" height="120" rx="14" fill={C.skin}/><circle cx="222" cy="298" r="14" fill={C.skin}/></g>
      <circle cx="168" cy="96" r="61" fill={C.skin}/>
      <path d="M107 91 C108 39 237 29 229 103 C212 80 191 69 160 70 C136 71 121 79 107 91 Z" fill={C.hair}/>
      <rect x="154" y="147" width="29" height="28" rx="10" fill={C.skin}/>
      <rect x={142+look*5} y="94" width="10" height="14" rx="5" fill={C.ink}/>
      <rect x={185+look*5} y="94" width="10" height="14" rx="5" fill={C.ink}/>
      <rect x="136" y={mood==='surprised'?76:80} width="25" height="5" rx="3" fill={C.ink}/>
      <rect x="180" y={mood==='surprised'?76:80} width="25" height="5" rx="3" fill={C.ink}/>
      {mood==='surprised'
        ? <ellipse cx="169" cy="126" rx="10" ry="13" fill="none" stroke={C.ink} strokeWidth="4"/>
        : <path d="M159 126 Q169 132 180 126" fill="none" stroke={C.ink} strokeWidth="4" strokeLinecap="round"/>}
    </svg>
  </div>
);

const SceneOne=({frame})=>{
  const enter=ease(frame/24);
  const door=interpolate(frame,[42,58,91],[0,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const arm=interpolate(frame,[28,43,60],[0,1,.15],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const look=interpolate(frame,[60,75],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const callout=interpolate(frame,[80,92],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const clock=interpolate(frame,[104,118],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const ret=interpolate(frame,[126,145],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const cam=interpolate(frame,[0,149],[1,1.055],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',inset:0,transform:`scale(${cam})`,transformOrigin:'center'}}>
    <Kitchen/>
    <Card x={95} y={82} w={650} h={170}><div style={{padding:'28px 38px'}}><div style={{fontSize:19,fontWeight:900,color:C.red,letterSpacing:1.2}}>WACKY INSIGHTS</div><div style={{marginTop:10,fontSize:58,fontWeight:950,lineHeight:1.02}}>YOU JUST<br/>CHECKED.</div></div></Card>
    <Character x={520-320*(1-enter)} y={350} arm={arm} look={look}/>
    <Fridge open={door}/>
    <Pill x={1188} y={244} text="EMPTY" color={C.red} opacity={callout} scale={.85+.15*callout}/>
    <Card x={1080} y={600} w={420} h={120} opacity={callout} scale={.94+.06*callout}><div style={{padding:'24px 30px'}}><div style={{fontSize:18,fontWeight:800,color:C.muted}}>FRIDGE STATUS</div><div style={{fontSize:34,fontWeight:950,marginTop:4}}>Still nothing new.</div></div></Card>
    <Card x={760} y={245} w={220} h={105} opacity={clock} scale={.82+.18*clock}><div style={{display:'flex',height:'100%',alignItems:'center',justifyContent:'center',fontSize:34,fontWeight:950}}>+5 MIN</div></Card>
    <Pill x={735} y={655} text="...AND YOU'RE BACK" color={C.yellow} opacity={ret} scale={.88+.12*ret}/>
  </div>
};

const Node=({x,label,color,active})=><div style={{position:'absolute',left:x,top:405,width:265,height:142,borderRadius:28,background:active?color:C.panel,color:active?'#fff':C.ink,border:`2px solid ${active?color:C.border}`,boxShadow:`0 18px 38px ${C.shadow}`,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',transform:`scale(${active?1.045:1})`}}><div style={{fontSize:16,fontWeight:900,opacity:.75}}>STEP</div><div style={{fontSize:34,fontWeight:950,marginTop:5,textAlign:'center',whiteSpace:'pre-line'}}>{label}</div></div>;
const Arrow=({x,active})=><svg width="118" height="40" viewBox="0 0 118 40" style={{position:'absolute',left:x,top:456,opacity:active?1:.18}}><line x1="6" y1="20" x2="92" y2="20" stroke={C.red} strokeWidth="6" strokeLinecap="round"/><path d="M90 7 L110 20 L90 33" fill="none" stroke={C.red} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"/></svg>;

const SceneTwo=({frame})=>{
  const f=frame-SCENE_FRAMES;
  const n1=f>=9,n2=f>=33,n3=f>=57,a1=f>=82,a2=f>=90;
  const pulse=interpolate(f,[100,118,149],[1,1.075,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const end=interpolate(f,[126,145],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  return <div style={{position:'absolute',inset:0,background:`linear-gradient(180deg,${C.bg1} 0%,${C.bg2} 100%)`}}>
    <Card x={90} y={82} w={790} h={170}><div style={{padding:'28px 38px'}}><div style={{fontSize:19,fontWeight:900,color:C.blue,letterSpacing:1.2}}>MICRO HABIT LOOP</div><div style={{marginTop:10,fontSize:51,fontWeight:950,lineHeight:1.06}}>BORED → CHECK →<br/>MAYBE REWARD</div></div></Card>
    <Node x={140} label="BOREDOM" color={C.blue} active={n1}/><Arrow x={425} active={a1}/><Node x={555} label="CHECK" color={C.red} active={n2}/><Arrow x={840} active={a2}/><div style={{position:'absolute',transform:`scale(${pulse})`,transformOrigin:'1105px 475px'}}><Node x={970} label={'MAYBE\nREWARD'} color={C.green} active={n3}/></div>
    <Card x={1360} y={300} w={430} h={350}><div style={{padding:'30px'}}><div style={{fontSize:20,fontWeight:900,color:C.muted}}>WHAT'S HAPPENING</div><div style={{marginTop:26,width:92,height:92,borderRadius:'50%',background:'#EAF0FF',display:'flex',alignItems:'center',justifyContent:'center',fontSize:46,fontWeight:950,color:C.blue}}>?</div><div style={{marginTop:22,fontSize:31,fontWeight:900,lineHeight:1.26}}>Your brain checks for a tiny possible reward.</div></div></Card>
    <Pill x={1270} y={740} text="FEELS LIKE A FEED REFRESH" color={C.red} opacity={end} scale={.88+.12*end}/>
  </div>
};

const Video=()=>{
  const frame=useCurrentFrame();
  return <AbsoluteFill style={{fontFamily:'Arial, Helvetica, sans-serif',color:C.ink,overflow:'hidden'}}>
    <Audio src={staticFile('narration.wav')} volume={.96}/>
    {frame<SCENE_FRAMES?<SceneOne frame={frame}/>:<SceneTwo frame={frame}/>} 
    <div style={{position:'absolute',left:90,right:90,bottom:56,display:'flex',justifyContent:'space-between',alignItems:'center'}}><div style={{fontSize:21,fontWeight:850,color:C.muted}}>ART QUALITY BENCHMARK • MVP 3</div><div style={{fontSize:18,fontWeight:850,color:C.muted}}>10 SEC</div></div>
    <div style={{position:'absolute',left:90,right:90,bottom:22,height:9,borderRadius:999,background:'rgba(31,41,55,.08)'}}><div style={{height:'100%',width:`${Math.min(100,frame/totalFrames*100)}%`,borderRadius:999,background:`linear-gradient(90deg,${C.red},${C.blue})`}}/></div>
  </AbsoluteFill>
};

const Root=()=> <Composition id="WackyLongformTest" component={Video} durationInFrames={totalFrames} fps={FPS} width={1920} height={1080}/>;
registerRoot(Root);
