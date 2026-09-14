#!/usr/bin/env python3
"""Wacky Dramas Ad-hoc V1 deterministic private pipeline."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BG=ROOT/"data/backgrounds.json"; HIST=ROOT/"data/history.json"; CTX=ROOT/"content/context.json"
DRAFTS=ROOT/"content/drafts"; REQS=ROOT/"content/requests"; EXECS=ROOT/"content/executions"
RESULTS=ROOT/"content/results"; FAILS=ROOT/"content/failures"
REQUEST_VERSION=EXECUTION_VERSION=RESULT_VERSION=CONTEXT_VERSION=1
RECENT_LIMIT=25; MIN_CATEGORY_BACKGROUNDS=3; MIN_BG=60.0; MAX_SEGMENT=100.0
MIN_NARR=120.0; MAX_NARR=178.0; WORDS_PER_SEC=3.0
TTS_SPEED=1.75
DEFAULT_EMOJIS=["😳","💬","🔥","👀"]
EMOJI_MAP={
    "shock":"😳",
    "surprise":"😮",
    "argument":"💢",
    "anger":"😡",
    "betrayal":"💔",
    "suspicion":"🤨",
    "secret":"🤫",
    "evidence":"📱",
    "money":"💰",
    "revenge":"😈",
    "embarrassment":"😬",
    "victory":"😎",
    "funny":"😂",
    "romance":"❤️",
    "panic":"😱",
    "confusion":"😵",
    "disbelief":"🤯",
    "warning":"⚠️",
    "celebration":"🎉",
    "awkward":"🙃",
}
NATURAL={"natural","neutral","conversational","warm","calm"}
EXPRESSIVE={"expressive","dramatic","comedy","sarcastic","dramatic_comedy","absurd"}
TONES=NATURAL|EXPRESSIVE
DRAFT_RE=re.compile(r"^draft-[A-Za-z0-9-]{8,96}$"); CID_RE=re.compile(r"^wd-[0-9a-f]{24}$")
EID_RE=re.compile(r"^ex-[0-9a-f]{24}$"); DID_RE=re.compile(r"^dp-[0-9a-f]{20}$"); SHA40=re.compile(r"^[0-9a-f]{40}$")
CONTRACT={
 "name":"wacky-dramas-production-v1","request_version":1,"execution_version":1,"result_version":1,
 "visibility":"public","request_path":"content/requests/{content_id}.json",
 "execution_path":"content/executions/{execution_id}.json","result_path":"content/results/{content_id}.json",
 "registry_path":"data/backgrounds.json",
}
CONTRACT_HASH=hashlib.sha256(json.dumps(CONTRACT,sort_keys=True,separators=(",",":")).encode()).hexdigest()

class VError(ValueError):
    def __init__(self,code,field,observed,required,repairable=True):
        self.code,self.field,self.observed,self.required,self.repairable=code,field,observed,required,repairable
        super().__init__(f"{code} field={field} observed={observed!r} required={required}")

def pretty(x): return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode()
def canonical(x): return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write(p,x): p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(pretty(x))
def blob(raw): return hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
def clean(v): return str(v or "").strip()
def text(v,f):
    s=clean(v)
    if not s: raise VError("MISSING_TEXT",f,v,"non-empty text")
    return s
def truncate_utf8(v,limit=5000):
    s=clean(v); raw=s.encode()
    if len(raw)<=limit: return s
    return raw[:limit].decode("utf-8","ignore").rstrip()
def draft_id(path):
    x=Path(path).stem
    if not DRAFT_RE.fullmatch(x): raise VError("INVALID_DRAFT_ID","draft_id",x,"draft-<8..96 letters/digits/hyphens>.json")
    return x
def normalize_gender(v):
    g=clean(v).casefold()
    return g if g in {"female","male"} else "female"
def normalize_tone(v):
    t=clean(v).casefold()
    return t if t in TONES else "natural"
def voice(g,t):
    if g not in {"female","male"}: raise VError("INVALID_LEAD_GENDER","story.lead_gender",g,"female or male")
    if t not in TONES: raise VError("INVALID_STORY_TONE","story.story_tone",t,"approved V1 tone")
    return ("af_bella" if t in EXPRESSIVE else "af_heart") if g=="female" else ("am_fenrir" if t in EXPRESSIVE else "am_echo")
def estimate(hook,script): return round(len((hook+" "+script).split())/WORDS_PER_SEC,2)
def strip_repeated_hook(hook,script):
    h=clean(hook); s=clean(script)
    if h and s[:len(h)].casefold()==h.casefold():
        return s[len(h):].lstrip(" \t\r\n-—–:;,.!?")
    return s
def last_sentence(script):
    s=clean(script)
    if not s: return ""
    parts=[x.strip() for x in re.split(r"(?<=[.!?])\s+",s) if x.strip()]
    return parts[-1] if parts else s
def resolve_payoff(v,script):
    p=clean(v); s=clean(script)
    return p if p and p.casefold() in s.casefold() else last_sentence(s)
def cue_key(v):
    if not isinstance(v,str): return ""
    return re.sub(r"_+","_",re.sub(r"[^a-z0-9]+","_",v.strip().casefold())).strip("_")
def resolve_emojis(cues):
    if not isinstance(cues,list) or len(cues)!=4:
        return list(DEFAULT_EMOJIS)
    mapped=[]
    for cue in cues:
        emoji=EMOJI_MAP.get(cue_key(cue))
        if not emoji:
            return list(DEFAULT_EMOJIS)
        mapped.append(emoji)
    if len(set(mapped))!=4:
        return list(DEFAULT_EMOJIS)
    return mapped

def registry(path=BG):
    x=read(path)
    if not isinstance(x,dict) or set(x)!={"assets"} or not isinstance(x.get("assets"),list):
        raise VError("INVALID_BACKGROUND_REGISTRY",str(path),type(x).__name__,"root object containing exactly assets[]",False)
    return x
def usable(a):
    if not isinstance(a,dict): return False
    try: d=float(a.get("duration_seconds"))
    except (TypeError,ValueError): return False
    return d>=MIN_BG and all(clean(a.get(k)) for k in ("id","category","source_url","download_url"))
def amap(r): return {str(a["id"]):a for a in r["assets"] if isinstance(a,dict) and isinstance(a.get("id"),str)}
def background_category(a): return clean(a.get("category")) or "satisfying_process"
def category_assets(r):
    out={}; seen=set()
    for a in r["assets"]:
        if not usable(a): continue
        bid=clean(a.get("id"))
        if not bid or bid in seen: continue
        seen.add(bid)
        out.setdefault(background_category(a),[]).append(a)
    return out
def viable_background_categories(r):
    groups=category_assets(r)
    return sorted((k for k,v in groups.items() if len(v)>=MIN_CATEGORY_BACKGROUNDS),key=lambda x:(x.casefold(),x))
def resolve_background_category(requested,r):
    groups=category_assets(r)
    viable={k:v for k,v in groups.items() if len(v)>=MIN_CATEGORY_BACKGROUNDS}
    if not viable:
        raise VError("NO_USABLE_BACKGROUND","data/backgrounds.json",0,"at least one category with three distinct valid approved backgrounds",False)
    requested=clean(requested)
    if requested in viable: return requested
    folded=requested.casefold()
    for category in sorted(viable,key=lambda x:(x.casefold(),x)):
        if category.casefold()==folded: return category
    return sorted(viable,key=lambda x:(-len(viable[x]),x.casefold(),x))[0]
def select_background_ids(requested_category,r,seed):
    category=resolve_background_category(requested_category,r)
    assets=category_assets(r)[category]
    ranked=sorted(assets,key=lambda a:(hashlib.sha256(f"{seed}:{clean(a.get('id'))}".encode()).hexdigest(),clean(a.get("id"))))
    ids=[clean(a.get("id")) for a in ranked[:MIN_CATEGORY_BACKGROUNDS]]
    if len(ids)!=MIN_CATEGORY_BACKGROUNDS or len(set(ids))!=MIN_CATEGORY_BACKGROUNDS:
        raise VError("NO_USABLE_BACKGROUND","data/backgrounds.json",len(set(ids)),"three distinct valid approved backgrounds in one category",False)
    return ids
def build_context():
    h=read(HIST)
    if not isinstance(h,list): raise VError("INVALID_HISTORY","data/history.json",type(h).__name__,"array")
    categories=viable_background_categories(registry())
    if not categories: raise VError("NO_USABLE_BACKGROUND","data/backgrounds.json",0,"at least one category with three distinct valid approved backgrounds",False)
    cards=[{k:str(x.get(k) or "") for k in ("title","premise","conflict","twist","payoff")}
           for x in h[-RECENT_LIMIT:] if isinstance(x,dict)]
    out={"context_version":1,"recent_story_cards":cards,"background_categories":categories}
    if len(pretty(out))>40000: raise VError("CONTEXT_TOO_LARGE","content/context.json",len(pretty(out)),"<=40000 bytes")
    write(CTX,out); return out

def normalize_draft(x):
    if not isinstance(x,dict): raise VError("INVALID_DRAFT_ROOT","$",type(x).__name__,"object")
    if x.get("supersedes_draft_id") is not None and not DRAFT_RE.fullmatch(str(x["supersedes_draft_id"])):
        raise VError("INVALID_SUPERSEDES_DRAFT_ID","supersedes_draft_id",x["supersedes_draft_id"],"valid prior draft id")
    w=x.get("winner")
    if not isinstance(w,dict):
        raise VError("INVALID_WINNER_FIELDS","winner",type(w).__name__,"winner object")
    hook=clean(w.get("hook")); script=strip_repeated_hook(hook,w.get("narration"))
    return {
      "winner":{
        "premise":clean(w.get("premise")),
        "category":clean(w.get("category")),
        "conflict":clean(w.get("conflict")),
        "twist":clean(w.get("twist")),
        "hook":hook,
        "narration":script,
        "title":clean(w.get("title")),
        "description":truncate_utf8(w.get("description"),5000),
        "lead_gender":normalize_gender(w.get("lead_gender")),
        "story_tone":normalize_tone(w.get("story_tone")),
        "payoff":resolve_payoff(w.get("payoff"),script),
        "emoji_cues":w.get("emoji_cues"),
        "background_category":clean(w.get("background_category")),
      }
    }

def bg_contract(category,r,seed):
    m=amap(r); seg=[]
    for bid in select_background_ids(category,r,seed):
        a=m[bid]
        seg.append({"background_id":bid,"segment_start_seconds":0.0,"segment_duration_seconds":round(min(float(a["duration_seconds"]),MAX_SEGMENT),3)})
    return {"mode":"concatenated_fit_to_short","segments":seg}

def make_request(did,raw_draft,d,r):
    digest=hashlib.sha256(canonical(raw_draft)).hexdigest(); cid="wd-"+digest[:24]
    w=d["winner"]
    g=w["lead_gender"]; t=w["story_tone"]
    return {
      "request_version":1,"content_id":cid,"source_draft_id":did,
      "channel":{"name":"Wacky Dramas","handle":"@WACKYDRAMAS"},
      "story":{"category":w["category"],"premise":w["premise"],
        "conflict":w["conflict"],"twist":w["twist"],
        "hook":w["hook"],"script":w["narration"],
        "lead_gender":g,"story_tone":t,"punchline":w["payoff"],
        "card_emojis":resolve_emojis(w.get("emoji_cues"))},
      "narration":{"engine":"kokoro","voice":voice(g,t),"speed":TTS_SPEED},
      "background":bg_contract(w.get("background_category"),r,cid),
      "youtube":{"title":w["title"],"description":w["description"],
        "hashtags":["#WackyDramas","#Shorts"],"tags":["Wacky Dramas","Shorts"],"category_id":"24","made_for_kids":False},
      "visibility":"public",
      "render":{"width":1080,"height":1920,"fps":30,"video_codec":"h264","h264_profile":"high","pixel_format":"yuv420p",
        "audio_codec":"aac","audio_sample_rate":48000,"background_music":False},
    }

def validate_request(x,path=None,r=None):
    top={"request_version","content_id","source_draft_id","channel","story","narration","background","youtube","visibility","render"}
    if not isinstance(x,dict) or set(x)!=top: raise VError("INVALID_REQUEST_FIELDS","$",sorted(x) if isinstance(x,dict) else type(x).__name__,"exact V1 request fields",False)
    if x["request_version"]!=1: raise VError("INVALID_REQUEST_VERSION","request_version",x["request_version"],"1",False)
    cid=str(x["content_id"])
    if not CID_RE.fullmatch(cid): raise VError("INVALID_CONTENT_ID","content_id",cid,"wd- plus 24 lowercase hex",False)
    if path and Path(path).name!=cid+".json": raise VError("REQUEST_FILENAME_MISMATCH",str(path),Path(path).name,cid+".json",False)
    if not DRAFT_RE.fullmatch(str(x["source_draft_id"])): raise VError("INVALID_SOURCE_DRAFT_ID","source_draft_id",x["source_draft_id"],"valid draft id",False)
    if x["channel"]!={"name":"Wacky Dramas","handle":"@WACKYDRAMAS"}: raise VError("INVALID_CHANNEL","channel",x["channel"],"canonical channel")
    s=x["story"]; sk={"category","premise","conflict","twist","hook","script","lead_gender","story_tone","punchline","card_emojis"}
    if not isinstance(s,dict) or set(s)!=sk: raise VError("INVALID_STORY_FIELDS","story",s,"exact V1 story fields")
    for k in sk-{"card_emojis"}: text(s[k],"story."+k)
    if str(s["punchline"]).casefold() not in str(s["script"]).casefold(): raise VError("PUNCHLINE_NOT_IN_SCRIPT","story.punchline",s["punchline"],"exact phrase in script")
    if not isinstance(s["card_emojis"],list) or not 4<=len(s["card_emojis"])<=6: raise VError("INVALID_CARD_EMOJIS","story.card_emojis",s["card_emojis"],"4-6 entries")
    v=voice(str(s["lead_gender"]),str(s["story_tone"]))
    if x["narration"]!={"engine":"kokoro","voice":v,"speed":TTS_SPEED}: raise VError("INVALID_NARRATION_CONTRACT","narration",x["narration"],f"kokoro/{v}/{TTS_SPEED}",False)
    secs=estimate(str(s["hook"]),str(s["script"]))
    if secs<MIN_NARR or secs>MAX_NARR: raise VError("NARRATION_TOO_SHORT" if secs<MIN_NARR else "NARRATION_TOO_LONG","story.script",f"estimated_seconds={secs}",f"{MIN_NARR:g}-{MAX_NARR:g}s")
    b=x["background"]
    if not isinstance(b,dict) or set(b)!={"mode","segments"} or b["mode"]!="concatenated_fit_to_short": raise VError("INVALID_BACKGROUND_CONTRACT","background",b,"concatenated_fit_to_short segments",False)
    seg=b["segments"]
    if not isinstance(seg,list) or len(seg)!=3: raise VError("INVALID_BACKGROUND_SEGMENTS","background.segments",seg,"3 segments")
    ids=[]; m=amap(r) if r else {}
    for n,z in enumerate(seg):
        if not isinstance(z,dict) or set(z)!={"background_id","segment_start_seconds","segment_duration_seconds"}: raise VError("INVALID_BACKGROUND_SEGMENT",f"background.segments[{n}]",z,"id/start/duration",False)
        bid=text(z["background_id"],f"background.segments[{n}].background_id"); ids.append(bid)
        try: start=float(z["segment_start_seconds"]); dur=float(z["segment_duration_seconds"])
        except (TypeError,ValueError): raise VError("INVALID_BACKGROUND_TIMING",f"background.segments[{n}]",z,"numeric timing",False)
        if abs(start)>1e-6 or not MIN_BG<=dur<=MAX_SEGMENT: raise VError("INVALID_BACKGROUND_TIMING",f"background.segments[{n}]",z,f"start=0 duration {MIN_BG:g}-{MAX_SEGMENT:g}",False)
        if r:
            a=m.get(bid)
            if not a or not usable(a): raise VError("BACKGROUND_NOT_ALLOWED","background.segments",bid,"approved promoted asset",False)
            if dur>float(a["duration_seconds"])+.05: raise VError("BACKGROUND_RANGE_EXCEEDS_SOURCE","background.segments",bid,"segment fits source",False)
    if len(set(ids))!=3: raise VError("DUPLICATE_BACKGROUND_ID","background.segments",ids,"3 distinct IDs")
    y=x["youtube"]; yk={"title","description","hashtags","tags","category_id","made_for_kids"}
    if not isinstance(y,dict) or set(y)!=yk: raise VError("INVALID_YOUTUBE_FIELDS","youtube",y,"exact V1 YouTube fields")
    if len(text(y["title"],"youtube.title"))>100: raise VError("TITLE_TOO_LONG","youtube.title",len(y["title"]),"<=100")
    desc=text(y["description"],"youtube.description")
    if len(desc.encode())>5000: raise VError("DESCRIPTION_TOO_LONG","youtube.description",len(desc.encode()),"<=5000 bytes")
    if not isinstance(y["hashtags"],list) or not isinstance(y["tags"],list) or y["made_for_kids"] is not False: raise VError("INVALID_YOUTUBE_METADATA","youtube",y,"valid arrays and made_for_kids=false")
    if x["visibility"]!="public": raise VError("VISIBILITY_NOT_PUBLIC","visibility",x["visibility"],"public")
    forbidden={"slot","publish_at","schedule_date","schedule_time","reserved_hour"}
    def walk(v,p="$"):
        if isinstance(v,dict):
            for k,c in v.items():
                if k in forbidden: raise VError("SCHEDULING_FIELD_FORBIDDEN",p+"."+k,c,"no scheduling fields",False)
                walk(c,p+"."+k)
        elif isinstance(v,list):
            for i,c in enumerate(v): walk(c,f"{p}[{i}]")
    walk(x)
    expected={"width":1080,"height":1920,"fps":30,"video_codec":"h264","h264_profile":"high","pixel_format":"yuv420p","audio_codec":"aac","audio_sample_rate":48000,"background_music":False}
    if x["render"]!=expected: raise VError("INVALID_RENDER_CONTRACT","render",x["render"],str(expected),False)
    return x

def fail(did,e): write(FAILS/(did+".json"),{"draft_id":did,"error_code":e.code,"field":e.field,"observed_value":e.observed,"required_constraint":e.required,"repairable":e.repairable})
def finalize(path):
    path=Path(path).resolve(); did=draft_id(path)
    try:
        raw_draft=read(path); d=normalize_draft(raw_draft); r=registry(); q=make_request(did,raw_draft,d,r)
        target=REQS/(q["content_id"]+".json"); validate_request(q,target,r)
    except VError as e: fail(did,e); raise
    raw=pretty(q)
    if target.exists() and target.read_bytes()!=raw: raise VError("IMMUTABLE_REQUEST_CONFLICT",str(target),blob(target.read_bytes()),blob(raw),False)
    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw); return target
def validate_file(path):
    path=Path(path); q=validate_request(read(path),path,registry()); print(f"Request valid: {path.name}; request_version=1"); return q
def make_execution(path,source):
    if not SHA40.fullmatch(source): raise VError("INVALID_SOURCE_SHA","request_source_sha",source,"40 lowercase hex",False)
    path=Path(path); q=read(path); raw=path.read_bytes(); rblob=blob(raw)
    eid="ex-"+hashlib.sha256(f"{q['content_id']}|{rblob}".encode()).hexdigest()[:24]
    did="dp-"+hashlib.sha256(eid.encode()).hexdigest()[:20]
    x={"execution_version":1,"execution_id":eid,"content_id":q["content_id"],"request_path":f"content/requests/{q['content_id']}.json",
       "request_source_sha":source,"request_blob_sha":rblob,"contract_hash":CONTRACT_HASH,"dispatch_id":did,"state":"prepared"}
    target=EXECS/(eid+".json"); rawx=pretty(x)
    if target.exists() and target.read_bytes()!=rawx: raise VError("IMMUTABLE_EXECUTION_CONFLICT",str(target),blob(target.read_bytes()),blob(rawx),False)
    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(rawx); return target,x
def validate_result(x,path=None):
    keys={"result_version","content_id","execution_id","status","youtube_video_id","visibility","verified","published_at"}
    if not isinstance(x,dict) or set(x)!=keys: raise VError("INVALID_RESULT_FIELDS","$",sorted(x) if isinstance(x,dict) else type(x).__name__,"exact V1 result fields",False)
    if x["result_version"]!=1 or not CID_RE.fullmatch(str(x["content_id"])) or not EID_RE.fullmatch(str(x["execution_id"])): raise VError("INVALID_RESULT_IDENTITY","$",x,"V1 result identity",False)
    if path and Path(path).name!=x["content_id"]+".json": raise VError("RESULT_FILENAME_MISMATCH",str(path),Path(path).name,x["content_id"]+".json",False)
    if x["status"]!="published" or x["visibility"]!="public" or x["verified"] is not True: raise VError("RESULT_NOT_VERIFIED_PUBLIC","$",x,"published/public/verified",False)
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}",str(x["youtube_video_id"])): raise VError("INVALID_YOUTUBE_VIDEO_ID","youtube_video_id",x["youtube_video_id"],"11 chars",False)
    text(x["published_at"],"published_at"); return x
def ingest(path):
    path=Path(path); x=validate_result(read(path),path); q=read(REQS/(x["content_id"]+".json")); h=read(HIST)
    if not isinstance(h,list): raise VError("INVALID_HISTORY","data/history.json",type(h).__name__,"array",False)
    if not any(isinstance(i,dict) and i.get("content_id")==x["content_id"] for i in h):
        s=q["story"]; h.append({"content_id":x["content_id"],"title":q["youtube"]["title"],"premise":s["premise"],"category":s["category"],
          "conflict":s["conflict"],"twist":s["twist"],"payoff":s["punchline"],"published_at":x["published_at"]}); write(HIST,h)
    build_context()

def self_test():
    checks=[]
    def ok(name,cond=True):
        if not cond: raise AssertionError(name)
        checks.append(name)
    r=registry(); ok("1 registry parses"); c=build_context(); ok("2 context builds")
    groups=category_assets(r)
    ok("3 context compact",len(pretty(c))<=40000)
    ok("4 viable background categories",bool(c["background_categories"]) and all(len(groups.get(x,[]))>=MIN_CATEGORY_BACKGROUNDS for x in c["background_categories"]))
    src=Path(__file__).read_text(); bad=["minimum "+"32 assets","PASS / "+"RE"+"PLENISH","category "+"minimum","inventory readiness "+"threshold","RE"+"PLENISH"]
    ok("5 no inventory gate",not any(x in src for x in bad))
    bgcat=c["background_categories"][0]
    filler=" ".join(["Then everything changed when the truth finally came out."]*47); payoff="I had the receipts"
    raw={"ignored_root":"allowed",
       "winner":{"premise":"A manager falsely blames an employee.","category":"work","conflict":"The accusation happens in front of the whole team.",
       "twist":"The employee kept screenshots that prove what happened.","hook":"My manager accused me in front of everyone.",
       "narration":f"My manager accused me in front of everyone. {filler} {payoff}. Nobody could answer after that.",
       "title":"My Manager Picked the Wrong Person to Blame","description":"A workplace accusation turns around fast.",
       "lead_gender":"invalid","story_tone":"invalid","payoff":"missing payoff","ignored_winner":"allowed",
       "emoji_cues":["shock","evidence","panic","victory"],"background_category":bgcat,"background_ids":["legacy-id-is-ignored"]}}
    d=normalize_draft(raw); dp=ROOT/"draft-selftest-deadbeef.json"; q=make_request(dp.stem,raw,d,r); validate_request(q,REQS/(q["content_id"]+".json"),r)
    ok("6 extra fields ignored","ignored_root" not in d and "ignored_winner" not in d["winner"] and "background_ids" not in d["winner"])
    ok("7 no draft version","draft_version" not in d)
    ok("8 defaults",q["story"]["lead_gender"]=="female" and q["story"]["story_tone"]=="natural")
    ok("9 repeated hook stripped",not q["story"]["script"].casefold().startswith(q["story"]["hook"].casefold()))
    ok("10 payoff fallback",q["story"]["punchline"]=="Nobody could answer after that.")
    ok("11 mapped emojis",q["story"]["card_emojis"]==["😳","📱","😱","😎"])
    ok("12 emoji fallback",resolve_emojis(["shock","unknown-cue","panic","victory"])==DEFAULT_EMOJIS and resolve_emojis(None)==DEFAULT_EMOJIS)
    ok("13 voices",voice("female","natural")=="af_heart" and voice("female","dramatic")=="af_bella" and voice("male","natural")=="am_echo" and voice("male","dramatic")=="am_fenrir")
    m=amap(r); qids=[x["background_id"] for x in q["background"]["segments"]]
    ok("14 same-category backgrounds",len(set(qids))==3 and all(background_category(m[x])==bgcat for x in qids))
    bad_raw=json.loads(json.dumps(raw)); bad_raw["winner"]["background_category"]="missing-category"
    badq=make_request(dp.stem,bad_raw,normalize_draft(bad_raw),r); fallback=resolve_background_category("missing-category",r)
    ok("15 background category fallback",all(background_category(m[x["background_id"]])==fallback for x in badq["background"]["segments"]))
    long_desc="é"*3000
    ok("16 description truncation",len(truncate_utf8(long_desc).encode())<=5000)
    ok("17 deterministic request",canonical(q)==canonical(make_request(dp.stem,raw,normalize_draft(raw),r)))
    js=json.dumps(q); ok("18 no slot",'"slot"' not in js); ok("19 no schedule",not any(k in js for k in ['"publish_at"','"schedule_date"','"schedule_time"','"reserved_hour"']))
    ok("20 immediate public",q["visibility"]=="public")
    rblob=blob(pretty(q)); eid="ex-"+hashlib.sha256(f"{q['content_id']}|{rblob}".encode()).hexdigest()[:24]
    ok("21 execution identity",bool(EID_RE.fullmatch(eid))); ok("22 contract hash",len(CONTRACT_HASH)==64)
    fake={"result_version":1,"content_id":q["content_id"],"execution_id":eid,"status":"published","youtube_video_id":"abcdefghijk","visibility":"public","verified":True,"published_at":"2026-09-14T04:00:00Z"}
    validate_result(fake); ok("23 result validates")
    wdir=ROOT/".github/workflows"; names={p.name for p in wdir.glob("*.yml")}
    ok("24 workflow set",names=={"adhoc-draft.yml","backgrounds.yml","dispatch.yml","result.yml","context.yml"})
    ok("25 generic workflows",all("daily" not in (wdir/n).read_text().lower() for n in ("dispatch.yml","result.yml","context.yml")))
    legacy="youtube-"+"shorts-"+"bot/"
    live="\n".join(p.read_text(errors="ignore") for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and p.suffix in {".py",".yml",".md",".json"})
    ok("26 no legacy refs",legacy not in live); ok("27 no legacy tree",not (ROOT/("youtube-"+"shorts-"+"bot")).exists())
    a=(ROOT/"ADHOC.md").read_text(); ok("28 normal two reads one write",all(x in a for x in ("content/context.json","content/drafts/")))
    ok("29 winner-only documented","winner" in a and "persist only the winner" in a)
    ok("30 background category documented","background_category" in a and "background_categories" in a)
    ok("31 no background minimum concept","32" not in a); ok("32 history compact",isinstance(read(HIST),list))
    ok("33 no publication schedule object","publication" not in q); ok("34 no analytics","analytics" not in js)
    print(f"SELF_TEST_PASS checks={len(checks)} contract_hash={CONTRACT_HASH}")

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    sub.add_parser("context"); p=sub.add_parser("finalize"); p.add_argument("--draft",required=True)
    p=sub.add_parser("validate"); p.add_argument("--request",required=True)
    p=sub.add_parser("execution"); p.add_argument("--request",required=True); p.add_argument("--request-source-sha",required=True)
    p=sub.add_parser("ingest-result"); p.add_argument("--result",required=True)
    sub.add_parser("contract-hash"); sub.add_parser("self-test"); a=ap.parse_args()
    try:
        if a.cmd=="context":
            c=build_context(); print(f"Context rebuilt: recent={len(c['recent_story_cards'])} background_categories={len(c['background_categories'])}")
        elif a.cmd=="finalize": print(finalize(a.draft).relative_to(ROOT).as_posix())
        elif a.cmd=="validate": validate_file(a.request)
        elif a.cmd=="execution":
            t,x=make_execution(a.request,a.request_source_sha); print(t.relative_to(ROOT).as_posix())
            print(json.dumps({"execution_id":x["execution_id"],"dispatch_id":x["dispatch_id"],"contract_hash":x["contract_hash"]},sort_keys=True))
        elif a.cmd=="ingest-result": ingest(a.result); print("Result ingested")
        elif a.cmd=="contract-hash": print(CONTRACT_HASH)
        else: self_test()
    except VError as e:
        print(str(e),file=sys.stderr); raise SystemExit(2)
if __name__=="__main__": main()
